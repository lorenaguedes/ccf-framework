"""
Cenario de custodia completa (hipotese H2): registro, transferencia entre
organizacoes, rejeicoes e reconstituicao da cadeia a partir do ledger.

Os cenarios C1 a C4 registram a evidencia e verificam a integridade, mas o
historico de transferencias fica vazio. Este cenario exercita, na rede
Hyperledger Fabric real (duas organizacoes), o que a hipotese H2 afirma:

1. a Org1 coleta e registra a evidencia (custodiante inicial = Org1);
2. a Org1 transfere a custodia para a Org2 (encaminhamento ao laboratorio);
3. NEGATIVO: a Org1, que deixou de ser custodiante, tenta transferir de novo
   e o contrato deve rejeitar;
4. NEGATIVO: a Org2 tenta transferir a custodia para si mesma e o contrato
   deve rejeitar;
5. a Org2 devolve a custodia a Org1 (devolucao apos analise);
6. a cadeia e reconstituida a partir do ledger (VerificarIntegridade): dois
   eventos encadeados (o cedente de cada um e o cessionario do anterior),
   instantes nao decrescentes, custodiante final coerente e hash integro.

Mede-se tambem a latencia de confirmacao de cada transacao (do envio ao
commit visivel no peer). O cenario so e SUCESSO se todas as verificacoes
passarem, incluindo as duas rejeicoes esperadas.

LIMITE: a rede e de duas organizacoes em uma unica maquina; a identidade
registrada e a da organizacao (MSP), nao a do operador; o instante da
transacao e carimbado pelo cliente, nao por autoridade de tempo independente.

Uso (apos preparar_ambiente_c1_c3 e com o chaincode v2 implantado):
  poetry run python -m modulo_integracao.cenarios_simulacao.executar_custodia_completa_real
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

LOGS = Path(__file__).parent.parent / "logs"
BUCKET = "ccf-evidence-bucket"
KEY = "evidencia-c1-real.jpg"
MSP1, MSP2 = "Org1MSP", "Org2MSP"


def _instante(ts: str) -> datetime:
    """Converte RFC 3339 com ate 9 casas fracionarias (nanossegundos) em datetime."""
    ts = re.sub(r"(\.\d{6})\d+", r"\1", ts).replace("Z", "+00:00")
    return datetime.fromisoformat(ts)


def _verificacao(vid: str, descricao: str, esperado, obtido, ok: bool) -> dict:
    return {"id": vid, "descricao": descricao, "esperado": esperado, "obtido": obtido, "ok": bool(ok)}


def _tentar_rejeicao(acao: Callable, trecho: str) -> tuple[bool, str]:
    """Executa uma acao que o contrato deve rejeitar; (rejeitada_como_esperado, mensagem)."""
    try:
        acao()
    except RuntimeError as e:
        mensagem = str(e)
        return trecho in mensagem, mensagem
    return False, "a acao foi aceita pelo contrato"


def executar_cenario_custodia(
    *,
    coletar: Callable[[], dict],
    registrar: Callable[[str, str, str], dict],
    transferir: Callable[[str, str, str, int], dict],
    consultar: Callable[[str], dict | None],
    verificar: Callable[[str, str], dict],
    sufixo: str | None = None,
    relogio: Callable[[], float] = time.monotonic,
) -> dict:
    """Orquestra o cenario com funcoes injetaveis (testavel sem rede).

    Args:
        coletar: devolve a evidencia coletada (com hashes, collected_at, cloud_provider).
        registrar: (evidence_id, hash, collected_at) -> registro de custodia.
        transferir: (evidence_id, msp_cessionario, motivacao, org_chamadora) -> resultado.
        consultar: evidence_id -> estado da evidencia no ledger.
        verificar: (evidence_id, hash_recalculado) -> VerificarIntegridade.
        sufixo: torna o ID unico por execucao (uma evidencia so pode ser registrada uma vez).
    """
    sufixo = sufixo or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    evidencia = coletar()
    h = evidencia["hashes"]["sha256"]
    eid = f"evid-custodia-{evidencia['cloud_provider']}-{h[:12]}-{sufixo}"
    verificacoes, latencias = [], {}

    t0 = relogio()
    registro = registrar(eid, h, evidencia["collected_at"])
    latencias["registro_s"] = round(relogio() - t0, 3)
    estado = consultar(eid) or {}
    verificacoes.append(_verificacao(
        "V1", "Registro novo pelo contrato, custodiante inicial = Org1, historico vazio",
        {"acao": "registrada", "custodiante": MSP1, "historico": 0},
        {"acao": registro.get("acao"), "custodiante": estado.get("custodiante_atual"),
         "historico": len(estado.get("historico_transferencias") or [])},
        registro.get("status") == "success" and registro.get("acao") == "registrada"
        and estado.get("custodiante_atual") == MSP1 and not estado.get("historico_transferencias")))

    t1 = transferir(eid, MSP2, "encaminhamento ao laboratorio pericial", 1)
    latencias["transferencia_org1_para_org2_s"] = t1["latencia_confirmacao_s"]
    verificacoes.append(_verificacao(
        "V2", "Org1 transfere a custodia para a Org2",
        {"custodiante": MSP2, "n_transferencias": 1},
        {"custodiante": t1["custodiante_atual"], "n_transferencias": t1["n_transferencias"]},
        t1["custodiante_atual"] == MSP2 and t1["n_transferencias"] == 1))

    ok, msg = _tentar_rejeicao(
        lambda: transferir(eid, MSP1, "tentativa indevida do antigo custodiante", 1), "não autorizada")
    verificacoes.append(_verificacao(
        "V3", "Antigo custodiante (Org1) nao pode transferir de novo: contrato rejeita",
        "rejeicao 'transferencia nao autorizada'", msg, ok))

    ok, msg = _tentar_rejeicao(
        lambda: transferir(eid, MSP2, "autotransferencia", 2), "já é o custodiante")
    verificacoes.append(_verificacao(
        "V4", "Custodiante (Org2) nao pode transferir para si mesmo: contrato rejeita",
        "rejeicao 'cessionario ja e o custodiante'", msg, ok))

    t2 = transferir(eid, MSP1, "devolucao apos a analise pericial", 2)
    latencias["transferencia_org2_para_org1_s"] = t2["latencia_confirmacao_s"]
    verificacoes.append(_verificacao(
        "V5", "Org2 devolve a custodia a Org1",
        {"custodiante": MSP1, "n_transferencias": 2},
        {"custodiante": t2["custodiante_atual"], "n_transferencias": t2["n_transferencias"]},
        t2["custodiante_atual"] == MSP1 and t2["n_transferencias"] == 2))

    recoleta = coletar()["hashes"]["sha256"]
    ver = verificar(eid, recoleta)
    final = consultar(eid) or {}
    hist = ver.get("historico_transferencias") or []
    encadeada = (len(hist) == 2 and hist[0]["msp_cedente"] == final.get("agente_coletor_msp")
                 and hist[1]["msp_cedente"] == hist[0]["msp_cessionario"]
                 and hist[-1]["msp_cessionario"] == final.get("custodiante_atual"))
    crescente = all(_instante(hist[i]["timestamp"]) <= _instante(hist[i + 1]["timestamp"])
                    for i in range(len(hist) - 1))
    verificacoes.append(_verificacao(
        "V6", "Cadeia reconstituida do ledger: eventos encadeados, instantes nao decrescentes, hash integro",
        {"integridade_valida": True, "encadeada": True, "instantes_nao_decrescentes": True, "eventos": 2},
        {"integridade_valida": ver.get("integridade_valida"), "encadeada": encadeada,
         "instantes_nao_decrescentes": crescente, "eventos": len(hist)},
        ver.get("integridade_valida") is True and encadeada and crescente))

    return {
        "evidence_id": eid,
        "hash": h,
        "verificacoes": verificacoes,
        "cadeia_reconstituida": hist,
        "estado_final": {"custodiante_atual": final.get("custodiante_atual"),
                         "agente_coletor_msp": final.get("agente_coletor_msp"),
                         "registrado_em": final.get("registrado_em")},
        "latencias_confirmacao": latencias,
        "n_verificacoes": len(verificacoes),
        "n_verificacoes_ok": sum(v["ok"] for v in verificacoes),
        "status_cenario": "SUCESSO" if all(v["ok"] for v in verificacoes) else "FALHA",
    }


def main():
    from modulo_blockchain.registrar_custodia import (
        consultar_evidencia,
        registrar_e_verificar,
        transferir_custodia,
        verificar_integridade,
    )
    from modulo_coleta.aws_collector import collect_from_s3

    resultado = executar_cenario_custodia(
        coletar=lambda: collect_from_s3(BUCKET, KEY),
        registrar=lambda eid, h, ts: registrar_e_verificar(
            evidence_id=eid, hash_sha256=h, timestamp=ts, csp_origem="aws",
            regiao="local", tipo_artefato="imagem"),
        transferir=lambda eid, msp, mot, org: transferir_custodia(eid, msp, mot, org=org),
        consultar=consultar_evidencia,
        verificar=verificar_integridade,
    )
    log = {"cenario": "custodia_completa", "executado_em": datetime.now(timezone.utc).isoformat(),
           "resultado": resultado}
    caminho = LOGS / "cenario_custodia_completa.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False, default=str)
    print(json.dumps(log, indent=2, ensure_ascii=False, default=str))
    print(f"\nLog salvo em: {caminho}")
    print(f"Verificacoes: {resultado['n_verificacoes_ok']}/{resultado['n_verificacoes']} - {resultado['status_cenario']}")


if __name__ == "__main__":
    main()
