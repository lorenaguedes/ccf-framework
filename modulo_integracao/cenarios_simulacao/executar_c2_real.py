"""
Execucao real do Cenario C2 - Grooming em Plataforma de Mensagens.

Conecta os componentes reais:
- modulo_coleta.docker_collector (Docker real)
- modulo_ia.deteccao_grooming (embeddings multilingues + regressao
  logistica, treinados sobre o PAN12 com rotulos por janela)
- Chaincode 'custody' na rede Hyperledger Fabric real

NOTA METODOLOGICA: o classificador usado aqui e o modelo final do
estagio E4 (modulo_ia/models/modelo_e4_embeddings.json, exportado do
notebook E4; secao 4.4.4 do PGT). A classificacao e semantica real,
nao mecanica/forcada. O limiar de decisao e o gravado no proprio
arquivo do modelo (calibrado na validacao).

LIMITACAO CONHECIDA (secao 4.4.4.7 e ADR 008): o estagio e uma triagem
sujeita a revisao humana. A precisao em prevalencias realistas e baixa
e adultos em interacao segura com criancas podem ser sinalizados. O
resultado desta execucao nao e medida de precisao pratica.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from modulo_coleta.docker_collector import collect_from_docker_log
from modulo_ia.deteccao_grooming import (
    carregar_config,
    classificar_conversa,
    create_embedding_predict_fn,
)
from modulo_integracao.cenarios_simulacao.cenario_c2 import executar_cenario_c2

CAMINHO_MODELO_E4 = "modulo_ia/models/modelo_e4_embeddings.json"


def _collector_fn_real(container_id, log_path):
    return collect_from_docker_log(container_id, log_path)


_PREDICT_FN = None


def _grooming_classifier_fn_real(texto: str) -> dict:
    """Usa o modelo real do E4 (embeddings multilingues + regressao
    logistica). O texto da conversa e dividido em linhas (mensagens) e
    classificado por janelas de 5 mensagens; o resultado e o da janela
    mais suspeita. Nao forca o resultado: reflete a classificacao do
    modelo, incluindo as limitacoes documentadas."""
    global _PREDICT_FN
    if _PREDICT_FN is None:  # carrega o codificador uma unica vez
        _PREDICT_FN = create_embedding_predict_fn(CAMINHO_MODELO_E4)
    limiar = carregar_config(CAMINHO_MODELO_E4)["limiar_f1max"]
    return classificar_conversa(texto.splitlines(), _PREDICT_FN, threshold=limiar)


def _custody_register_fn_placeholder(evidence_id, hash_sha256, metadata):
    """Placeholder - o registro real e feito via peer CLI separadamente,
    mesmo padrao adotado no Cenario C1."""
    return {"status": "pendente_shell", "evidence_id": evidence_id}


def main():
    container_id = "container-msgs-c2"
    log_path = "/logs/conversa.txt"

    coleta_real = collect_from_docker_log(container_id, log_path)
    texto_conversa = coleta_real["conteudo_texto"]

    resultado = executar_cenario_c2(
        container_id=container_id,
        log_path=log_path,
        texto_conversa=texto_conversa,
        collector_fn=_collector_fn_real,
        grooming_classifier_fn=_grooming_classifier_fn_real,
        custody_register_fn=_custody_register_fn_placeholder,
    )

    log_entry = {
        "cenario": "C2",
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": resultado,
        "hash_para_registro_blockchain": coleta_real["hashes"]["sha256"],
        "observacao": "Classificacao com o modelo E4 real (embeddings multilingues + regressao logistica; nao forcada). Triagem sujeita a revisao humana; ver ADR 008 e secao 4.4.4.7 do PGT.",
    }

    log_path_output = Path(__file__).parent.parent / "logs" / "cenario_c2_execucao.json"
    with open(log_path_output, "w") as f:
        json.dump(log_entry, f, indent=2, default=str)

    print(json.dumps(log_entry, indent=2, default=str))
    print(f"\nLog salvo em: {log_path_output}")
    print(f"\nHash para registro manual na blockchain: {coleta_real['hashes']['sha256']}")


if __name__ == "__main__":
    main()