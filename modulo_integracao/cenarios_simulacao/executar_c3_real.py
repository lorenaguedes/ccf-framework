"""
Execucao real do Cenario C3 - Operacao Combinada em Multi-Nuvem.

Conecta os 3 conectores reais de coleta multi-nuvem, correlacionando
evidencias de AWS, GCP e Azure em uma unica investigacao, conforme
Tabela 16 do PGT: "evidencias distribuidas em AWS (imagens), GCP (logs
de acesso anomalo) e Azure (metadados de conta)."

Criterio de sucesso: pipeline end-to-end sem erros, correlacao de
evidencias de 3 CSPs no mesmo laudo.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from modulo_coleta.aws_collector import collect_from_s3
from modulo_coleta.azure_collector import collect_from_blob
from modulo_coleta.gcp_collector import collect_from_gcs
from modulo_integracao.cenarios_simulacao.cenario_c3 import executar_cenario_c3


def _aws_collector_fn(bucket, key):
    return collect_from_s3("ccf-evidence-bucket", "evidencia-c1-real.jpg")


def _gcp_collector_fn(bucket, key):
    return collect_from_gcs("ccf-evidence-bucket-gcp", "evidencia-teste-integracao.txt")


def _azure_collector_fn(container, blob):
    return collect_from_blob("ccf-evidence-container", "evidencia-teste-integracao.txt")


def _custody_register_fn_placeholder(evidence_id, hash_sha256, metadata):
    """Placeholder - registro real feito via peer CLI separadamente,
    uma chamada por evidencia coletada (3 no total)."""
    return {"status": "pendente_shell", "evidence_id": evidence_id, "hash": hash_sha256}


def main():
    resultado = executar_cenario_c3(
        aws_collector_fn=_aws_collector_fn,
        gcp_collector_fn=_gcp_collector_fn,
        azure_collector_fn=_azure_collector_fn,
        custody_register_fn=_custody_register_fn_placeholder,
    )

    log_entry = {
        "cenario": "C3",
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": resultado,
    }

    log_path = Path(__file__).parent.parent / "logs" / "cenario_c3_execucao.json"
    with open(log_path, "w") as f:
        json.dump(log_entry, f, indent=2, default=str)

    print(json.dumps(log_entry, indent=2, default=str))
    print(f"\nLog salvo em: {log_path}")

    print("\n=== Hashes para registro manual na blockchain ===")
    for ev in resultado["evidencias"]:
        print(f"{ev['cloud_provider']}: {ev['hashes']['sha256']}")


if __name__ == "__main__":
    main()