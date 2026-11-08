"""
Teste negativo de integridade: a cadeia de custodia detecta adulteracao.

Os cenarios C1 a C3 exercitam a verificacao de integridade apenas no caso
positivo (a evidencia recoletada e identica a original). Este teste mostra
o caso negativo, ponta a ponta, na rede Hyperledger Fabric real:

1. coleta a evidencia sintetica do C1 e a registra no ledger (idempotente);
2. grava, no mesmo bucket, uma COPIA adulterada (um byte alterado); o
   objeto original nunca e modificado;
3. recoleta a copia adulterada e chama VerificarIntegridade com o hash
   recalculado: o contrato deve responder integridade_valida = false;
4. controle: recoleta o objeto original e confirma integridade_valida = true.

O teste so e bem-sucedido se o controle passar E a adulteracao for detectada.

Uso (apos preparar_ambiente_c1_c3):
  poetry run python -m modulo_integracao.cenarios_simulacao.executar_adulteracao_real
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

LOGS = Path(__file__).parent.parent / "logs"
BUCKET = "ccf-evidence-bucket"
KEY = "evidencia-c1-real.jpg"
KEY_ADULTERADA = "evidencia-c1-real-adulterada.jpg"


def adulterar_um_byte(conteudo: bytes, deslocamento: int | None = None) -> tuple[bytes, dict]:
    """Inverte o bit menos significativo de um byte (por padrao, o do meio)."""
    if not conteudo:
        raise ValueError("Conteudo vazio: nao ha byte a adulterar.")
    pos = len(conteudo) // 2 if deslocamento is None else deslocamento
    alterado = bytearray(conteudo)
    antes = alterado[pos]
    alterado[pos] = antes ^ 0x01
    return bytes(alterado), {"deslocamento": pos, "byte_antes": antes, "byte_depois": alterado[pos]}


def executar_teste_adulteracao(
    *,
    ler: Callable[[str], bytes],
    gravar: Callable[[str, bytes], None],
    coletar: Callable[[str], dict],
    registrar: Callable[[str, str, str], dict],
    verificar: Callable[[str, str], dict],
    key: str = KEY,
    key_adulterada: str = KEY_ADULTERADA,
) -> dict:
    """Orquestra o teste com funcoes injetaveis (testavel sem rede).

    Args:
        ler/gravar: acesso aos objetos do storage por chave.
        coletar: recoleta o objeto por chave e devolve a evidencia (com hashes).
        registrar: (evidence_id, hash_sha256, collected_at) -> registro de custodia.
        verificar: (evidence_id, hash_recalculado) -> resultado de VerificarIntegridade.
    """
    original = coletar(key)
    hash_original = original["hashes"]["sha256"]
    evidence_id = f"evid-adulteracao-{original['cloud_provider']}-{hash_original[:12]}"
    registro = registrar(evidence_id, hash_original, original["collected_at"])
    if registro.get("status") != "success":
        raise RuntimeError(f"Registro de custodia falhou: {registro}")

    adulterado, detalhe = adulterar_um_byte(ler(key))
    gravar(key_adulterada, adulterado)
    hash_adulterado = coletar(key_adulterada)["hashes"]["sha256"]

    controle = verificar(evidence_id, coletar(key)["hashes"]["sha256"])
    adulteracao = verificar(evidence_id, hash_adulterado)

    controle_ok = controle["integridade_valida"] is True
    detectada = adulteracao["integridade_valida"] is False and hash_adulterado != hash_original
    return {
        "evidence_id": evidence_id,
        "registro_custodia": registro,
        "adulteracao_aplicada": {**detalhe, "chave_copia_adulterada": key_adulterada},
        "hash_original": hash_original,
        "hash_adulterado": hash_adulterado,
        "verificacao_controle": controle,
        "verificacao_adulterada": adulteracao,
        "controle_ok": controle_ok,
        "adulteracao_detectada": detectada,
        "status_teste": "SUCESSO" if (controle_ok and detectada) else "FALHA",
    }


def main():
    from modulo_blockchain.registrar_custodia import registrar_e_verificar, verificar_integridade
    from modulo_coleta.aws_collector import collect_from_s3, get_s3_client

    s3 = get_s3_client()
    resultado = executar_teste_adulteracao(
        ler=lambda k: s3.get_object(Bucket=BUCKET, Key=k)["Body"].read(),
        gravar=lambda k, b: s3.put_object(Bucket=BUCKET, Key=k, Body=b),
        coletar=lambda k: collect_from_s3(BUCKET, k),
        registrar=lambda eid, h, ts: registrar_e_verificar(
            evidence_id=eid, hash_sha256=h, timestamp=ts, csp_origem="aws",
            regiao="local", tipo_artefato="imagem"),
        verificar=verificar_integridade,
    )
    log = {
        "teste": "adulteracao",
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": resultado,
    }
    caminho = LOGS / "teste_adulteracao_execucao.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False, default=str)
    print(json.dumps(log, indent=2, ensure_ascii=False, default=str))
    print(f"\nLog salvo em: {caminho}")


if __name__ == "__main__":
    main()
