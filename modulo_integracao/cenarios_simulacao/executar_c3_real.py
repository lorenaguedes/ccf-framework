"""
Execucao real do Cenario C3 - Operacao Combinada em Multi-Nuvem.

Conecta os 3 conectores reais de coleta multi-nuvem, correlacionando
evidencias de AWS, GCP e Azure em uma unica investigacao, conforme
Tabela 16 do PGT: "evidencias distribuidas em AWS (imagens), GCP (logs
de acesso anomalo) e Azure (metadados de conta)."

Cada evidencia e registrada no chaincode 'custody' (Fabric real) e tem
o hash conferido no ledger; em seguida e recoletada e verificada pela
funcao VerificarIntegridade. O cenario valida coleta, correlacao e
custodia: nao ha etapa de classificacao por IA, e os laudos declaram
isso explicitamente.

Criterio de sucesso: pipeline end-to-end sem erros, correlacao de
evidencias de 3 CSPs no mesmo laudo, cadeia de custodia verificavel.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from modulo_blockchain.registrar_custodia import verificar_integridade
from modulo_coleta.aws_collector import collect_from_s3
from modulo_coleta.azure_collector import collect_from_blob
from modulo_coleta.gcp_collector import collect_from_gcs
from modulo_integracao.cenarios_simulacao.cenario_c3 import executar_cenario_c3
from modulo_integracao.cenarios_simulacao.custodia_real import criar_custody_register_fn, id_evidencia

LOGS = Path(__file__).parent.parent / "logs"

_COLETORES = {
    "aws": lambda: collect_from_s3("ccf-evidence-bucket", "evidencia-c1-real.jpg"),
    "gcp": lambda: collect_from_gcs("ccf-evidence-bucket-gcp", "evidencia-teste-integracao.txt"),
    "azure": lambda: collect_from_blob("ccf-evidence-container", "evidencia-teste-integracao.txt"),
}


def _aws_collector_fn(bucket, key):
    return _COLETORES["aws"]()


def _gcp_collector_fn(bucket, key):
    return _COLETORES["gcp"]()


def _azure_collector_fn(container, blob):
    return _COLETORES["azure"]()


def main():
    resultado = executar_cenario_c3(
        aws_collector_fn=_aws_collector_fn,
        gcp_collector_fn=_gcp_collector_fn,
        azure_collector_fn=_azure_collector_fn,
        custody_register_fn=criar_custody_register_fn("c3"),
    )

    # Verificacao de integridade: recoleta cada evidencia e confere com o ledger.
    verificacoes = []
    for ev in resultado["evidencias"]:
        if ev["cloud_provider"] in resultado["erros_custodia"]:
            continue  # nao registrada no ledger: nao ha o que verificar
        recoleta = _COLETORES[ev["cloud_provider"]]()
        eid = id_evidencia("c3", ev, ev["hashes"]["sha256"])
        verificacoes.append({"cloud_provider": ev["cloud_provider"],
                             **verificar_integridade(eid, recoleta["hashes"]["sha256"])})
    resultado["verificacoes_integridade"] = verificacoes

    log_entry = {
        "cenario": "C3",
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": resultado,
    }
    log_path = LOGS / "cenario_c3_execucao.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, indent=2, default=str, ensure_ascii=False)

    print(json.dumps(log_entry, indent=2, default=str, ensure_ascii=False))
    print(f"\nLog salvo em: {log_path}")

    from modulo_integracao.cenarios_simulacao.gerar_laudos_c1_c3 import (
        gerar_laudo_consolidado_c3,
        gerar_laudos_c3,
    )
    for saida in gerar_laudos_c3(log_path):
        print(f"Laudo salvo em: {saida}")
    gerar_laudo_consolidado_c3(log_path, LOGS / "laudo_c3_consolidado.pdf")
    print(f"Laudo consolidado salvo em: {LOGS / 'laudo_c3_consolidado.pdf'}")


if __name__ == "__main__":
    main()
