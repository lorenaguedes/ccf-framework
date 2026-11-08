"""
Adaptador entre os orquestradores de cenarios (C1 a C3) e o cliente da
cadeia de custodia (modulo_blockchain.registrar_custodia).

Os orquestradores chamam custody_register_fn(evidence_id, hash, metadados).
Aqui o identificador do ledger e derivado do cenario, do provedor e dos
12 primeiros caracteres do hash (evid-c1-aws-1b33f05aac9b), de modo que o
mesmo conteudo gera sempre o mesmo ID (registro idempotente) e conteudos
diferentes nunca colidem.
"""
from modulo_blockchain.registrar_custodia import registrar_e_verificar

_EXTENSOES_IMAGEM = (".jpg", ".jpeg", ".png", ".gif", ".bmp")


_TIPO_POR_MODALIDADE = {"imagem": "imagem", "texto": "mensagens", "logs": "logs"}


def tipo_artefato(metadados: dict) -> str:
    """Classifica o artefato: pela modalidade, quando informada (cenario
    multimodal C4); senao, pelo identificador (imagem, mensagens ou arquivo)."""
    modalidade = metadados.get("modalidade")
    if modalidade in _TIPO_POR_MODALIDADE:
        return _TIPO_POR_MODALIDADE[modalidade]
    ident = str(metadados.get("key") or metadados.get("blob_name") or metadados.get("log_path") or "").lower()
    if ident.endswith(_EXTENSOES_IMAGEM):
        return "imagem"
    if metadados.get("cloud_provider") == "docker":
        return "mensagens"
    return "arquivo"


def id_evidencia(cenario: str, metadados: dict, hash_sha256: str) -> str:
    return f"evid-{cenario.lower()}-{metadados['cloud_provider']}-{hash_sha256[:12]}"


def criar_custody_register_fn(cenario: str, regiao: str = "local"):
    """Cria a funcao de registro real para um cenario (usa o peer CLI)."""
    def custody_register_fn(evidence_id, hash_sha256, metadados):
        return registrar_e_verificar(
            evidence_id=id_evidencia(cenario, metadados, hash_sha256),
            hash_sha256=hash_sha256,
            timestamp=metadados["collected_at"],
            csp_origem=metadados["cloud_provider"],
            regiao=regiao,
            tipo_artefato=tipo_artefato(metadados),
        )
    return custody_register_fn
