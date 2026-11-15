"""
Benchmark do framework: integridade da coleta e latencia de confirmacao no
ledger (criterio de aceite F2 da Tabela 7 do PGT: 1.000 coletas com taxa de
integridade >= 99,9%).

Toda a logica e pura e recebe as operacoes por injecao (testavel sem Docker):

  executar_coletas(n, provedores) - para cada coleta, um objeto SINTETICO de
      tamanho variavel e SHA-256 conhecido (calculado ao gerar o conteudo, de
      forma independente do coletor) e gravado no emulador; o coletor real le o
      objeto, e o hash que ele devolve deve ser igual ao esperado e o tamanho
      igual ao gravado. So a leitura (coleta) e cronometrada.
  executar_fabric(n, registrar) - n registros de evidencias no chaincode, com a
      latencia de ponta a ponta do cliente (consulta previa, invoke e espera
      pela confirmacao do bloco, com intervalo de consulta curto).

Observacao estatistica: com N = 1.000 e nenhuma falha, o limite inferior do IC
de 95% (Wilson) da taxa de integridade e ~99,6%. Portanto o criterio de 99,9% e
atendido pela taxa observada, mas nao e comprovado estatisticamente com esse N
(regra dos tres: seriam necessarias ~3.000 coletas sem falha para limitar a
taxa de falha a 0,1% com 95% de confianca).
"""
import hashlib
import math
import time
from collections import defaultdict
from typing import Callable


def gerar_conteudo(i: int) -> bytes:
    """Conteudo sintetico deterministico; tamanho de 1 KiB a 256 KiB."""
    tamanho = 1024 * (1 + (i * 37) % 256)
    return hashlib.shake_256(f"ccf-benchmark-{i}".encode()).digest(tamanho)


def percentil(valores: list, p: float) -> float | None:
    """Percentil pelo metodo do posto mais proximo."""
    if not valores:
        return None
    ordenados = sorted(valores)
    k = max(0, min(len(ordenados) - 1, math.ceil(p / 100 * len(ordenados)) - 1))
    return ordenados[k]


def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    """Intervalo de Wilson de 95% para uma proporcao."""
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, centro - meia), 4), round(min(1.0, centro + meia), 4))


def _estatisticas(latencias: list) -> dict:
    if not latencias:
        return {"media_s": None, "p50_s": None, "p95_s": None, "max_s": None}
    return {"media_s": round(sum(latencias) / len(latencias), 4),
            "p50_s": round(percentil(latencias, 50), 4),
            "p95_s": round(percentil(latencias, 95), 4),
            "max_s": round(max(latencias), 4)}


def _resumo(registros: list) -> dict:
    n = len(registros)
    ok = sum(1 for r in registros if r["status"] == "ok")
    lats = [r["latencia_s"] for r in registros if r["status"] == "ok"]
    return {"coletas": n, "integras": ok, "falhas": n - ok,
            "taxa_integridade": round(ok / n, 6) if n else None,
            "taxa_integridade_ic95": wilson(ok, n), **_estatisticas(lats)}


def executar_coletas(n: int, provedores: dict, relogio: Callable = time.perf_counter) -> dict:
    """Executa n coletas distribuidas em rodizio entre os provedores.

    Args:
        provedores: {nome: (gravar(chave, bytes), coletar(chave) -> dict)};
            o dict devolvido pelo coletor tem hashes.sha256 e size_bytes.
    """
    nomes = list(provedores)
    registros = []
    for i in range(n):
        nome = nomes[i % len(nomes)]
        gravar, coletar = provedores[nome]
        conteudo = gerar_conteudo(i)
        esperado = hashlib.sha256(conteudo).hexdigest()
        chave = f"bench-{i:04d}.bin"
        reg = {"indice": i, "provedor": nome, "chave": chave, "tamanho": len(conteudo)}
        try:
            gravar(chave, conteudo)
            t0 = relogio()
            coleta = coletar(chave)
            reg["latencia_s"] = relogio() - t0
            if coleta["hashes"]["sha256"] != esperado:
                reg["status"], reg["motivo"] = "hash_divergente", "SHA-256 coletado difere do esperado"
            elif coleta["size_bytes"] != len(conteudo):
                reg["status"], reg["motivo"] = "tamanho_divergente", "tamanho coletado difere do gravado"
            else:
                reg["status"] = "ok"
        except Exception as e:  # falha de coleta e contada, nunca silenciada
            reg["status"], reg["motivo"] = "erro", f"{type(e).__name__}: {e}"[:200]
        registros.append(reg)
    por_prov = defaultdict(list)
    for r in registros:
        por_prov[r["provedor"]].append(r)
    return {"n": n, "global": _resumo(registros),
            "por_provedor": {k: _resumo(v) for k, v in por_prov.items()},
            "falhas": [r for r in registros if r["status"] != "ok"][:20]}


def executar_fabric(n: int, registrar: Callable, sufixo: str, relogio: Callable = time.perf_counter) -> dict:
    """Executa n registros no ledger.

    Args:
        registrar(evidence_id, hash_sha256) -> dict com status e acao; deve
            registrar e esperar a confirmacao do bloco.
        sufixo: torna os IDs unicos entre execucoes (evid-bench-<sufixo>-NNNN).
    """
    lats, falhas = [], []
    t_inicio = relogio()
    for i in range(n):
        eid = f"evid-bench-{sufixo}-{i:04d}"
        h = hashlib.sha256(gerar_conteudo(i)).hexdigest()
        t0 = relogio()
        try:
            r = registrar(eid, h)
            dt = relogio() - t0
            if r.get("status") == "success" and r.get("acao") == "registrada":
                lats.append(dt)
            else:
                falhas.append({"evidence_id": eid, "status": r.get("status"), "acao": r.get("acao")})
        except Exception as e:
            falhas.append({"evidence_id": eid, "erro": f"{type(e).__name__}: {e}"[:200]})
    total = relogio() - t_inicio
    ok = len(lats)
    return {"n": n, "confirmadas": ok, "falhas": n - ok,
            "taxa_sucesso": round(ok / n, 6) if n else None, "taxa_sucesso_ic95": wilson(ok, n),
            "vazao_sequencial_tx_por_s": round(ok / total, 4) if total > 0 else None,
            "duracao_total_s": round(total, 2), **_estatisticas(lats),
            "falhas_detalhe": falhas[:20]}
