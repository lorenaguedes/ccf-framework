"""
Execucao real do Cenario C2 - Grooming em Plataforma de Mensagens.

Conecta os componentes reais:
- modulo_coleta.docker_collector (Docker real)
- modulo_ia.deteccao_grooming (BERT - SEM fine-tuning, ver nota)
- Chaincode 'custody' na rede Hyperledger Fabric real

NOTA METODOLOGICA IMPORTANTE: o modelo BERT usado aqui NAO possui os
pesos fine-tuned sobre o PAN12 (o arquivo .pth gerado no Colab nao foi
transferido para o ambiente local nesta fase do projeto). Portanto,
a classificacao de grooming neste script E MECANICA, nao semantica -
valida a integracao real do pipeline (Docker -> BERT -> Blockchain),
mas NAO a qualidade da deteccao (essa validacao foi feita
separadamente no Colab, com F1=0.8149 - ver notebook e log da sessao).
Para fins de teste E2E do branch positivo (registro na blockchain),
o resultado da classificacao e forcado para SUSPEITO, de forma
documentada e transparente.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from modulo_coleta.docker_collector import collect_from_docker_log
from modulo_ia.deteccao_grooming import classify_grooming, create_bert_predict_fn
from modulo_integracao.cenarios_simulacao.cenario_c2 import executar_cenario_c2


def _collector_fn_real(container_id, log_path):
    return collect_from_docker_log(container_id, log_path)


def _grooming_classifier_fn_real_forcado(texto: str) -> dict:
    """Usa o BERT real (mecanicamente), mas forca o resultado para
    SUSPEITO para validar o branch de registro de custodia - ver nota
    do modulo sobre a ausencia dos pesos fine-tuned localmente."""
    predict_fn = create_bert_predict_fn()  # sem model_path = sem fine-tuning
    resultado = classify_grooming(texto, predict_fn, threshold=0.5)
    resultado["flag"] = "SUSPEITO"  # forcado - ver nota do modulo
    if not resultado["tokens_relevantes"]:
        resultado["tokens_relevantes"] = texto.split()[:5]
    return resultado


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
        grooming_classifier_fn=_grooming_classifier_fn_real_forcado,
        custody_register_fn=_custody_register_fn_placeholder,
    )

    log_entry = {
        "cenario": "C2",
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": resultado,
        "hash_para_registro_blockchain": coleta_real["hashes"]["sha256"],
    }

    log_path_output = Path(__file__).parent.parent / "logs" / "cenario_c2_execucao.json"
    with open(log_path_output, "w") as f:
        json.dump(log_entry, f, indent=2, default=str)

    print(json.dumps(log_entry, indent=2, default=str))
    print(f"\nLog salvo em: {log_path_output}")
    print(f"\nHash para registro manual na blockchain: {coleta_real['hashes']['sha256']}")


if __name__ == "__main__":
    main()