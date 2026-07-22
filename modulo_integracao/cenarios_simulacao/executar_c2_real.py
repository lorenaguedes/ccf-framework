"""
Execucao real do Cenario C2 - Grooming em Plataforma de Mensagens.

Conecta os componentes reais:
- modulo_coleta.docker_collector (Docker real)
- modulo_ia.deteccao_grooming (BERT fine-tuned sobre PAN12, pesos reais)
- Chaincode 'custody' na rede Hyperledger Fabric real

NOTA METODOLOGICA: o modelo BERT usado aqui possui os pesos fine-tuned
reais (modulo_ia/models/modelo_e4_grooming_bert.pth, F1=0.8153 no
conjunto de teste interno - ver notebook Colab e ADR 008). A
classificacao abaixo e semantica real, nao mais mecanica/forcada.

LIMITACAO CONHECIDA (ADR 008): o modelo apresenta vies de
generalizacao documentado - tende a classificar como SUSPEITO mesmo
frases benignas em estilo de chat casual, fora da distribuicao do
PAN12. O resultado desta execucao deve ser interpretado a luz dessa
limitacao, nao como medida definitiva de precisao pratica.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from modulo_coleta.docker_collector import collect_from_docker_log
from modulo_ia.deteccao_grooming import classify_grooming, create_bert_predict_fn
from modulo_integracao.cenarios_simulacao.cenario_c2 import executar_cenario_c2

CAMINHO_MODELO_BERT = "modulo_ia/models/modelo_e4_grooming_bert.pth"


def _collector_fn_real(container_id, log_path):
    return collect_from_docker_log(container_id, log_path)


def _grooming_classifier_fn_real(texto: str) -> dict:
    """Usa o BERT real, fine-tuned sobre o PAN12. Nao forca mais o
    resultado - reflete a classificacao semantica genuina do modelo,
    incluindo a limitacao de generalizacao documentada no ADR 008."""
    predict_fn = create_bert_predict_fn(model_path=CAMINHO_MODELO_BERT)
    return classify_grooming(texto, predict_fn, threshold=0.5)


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
        "observacao": "Classificacao com modelo BERT fine-tuned real (nao forcada). Ver ADR 008 para limitacao de generalizacao conhecida.",
    }

    log_path_output = Path(__file__).parent.parent / "logs" / "cenario_c2_execucao.json"
    with open(log_path_output, "w") as f:
        json.dump(log_entry, f, indent=2, default=str)

    print(json.dumps(log_entry, indent=2, default=str))
    print(f"\nLog salvo em: {log_path_output}")
    print(f"\nHash para registro manual na blockchain: {coleta_real['hashes']['sha256']}")


if __name__ == "__main__":
    main()