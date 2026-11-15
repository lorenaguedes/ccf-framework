"""
Benchmark real: N coletas (AWS/Azure/GCP em emuladores) com verificacao de
integridade, e M registros no chaincode com a latencia de confirmacao.

Uso:
  poetry run python -m modulo_integracao.cenarios_simulacao.executar_benchmark_real
      [--n 1000] [--n-fabric 100] [--sem-fabric] [--intervalo-fabric 0.1]

Dados exclusivamente sinteticos. Gera modulo_integracao/logs/benchmark_framework.json.
"""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

from modulo_integracao.benchmark import executar_coletas, executar_fabric

LOGS = Path(__file__).parent.parent / "logs"
BUCKET_AWS = "ccf-bench-bucket"
BUCKET_GCS = "ccf-bench-bucket-gcp"
CONTAINER_AZURE = "ccf-bench-container"


def _provedores() -> dict:  # pragma: no cover - depende dos emuladores
    import requests

    from modulo_coleta.aws_collector import collect_from_s3, get_s3_client
    from modulo_coleta.azure_collector import collect_from_blob, get_blob_service_client
    from modulo_coleta.gcp_collector import FAKE_GCS_ENDPOINT, collect_from_gcs

    s3 = get_s3_client()
    if BUCKET_AWS not in [b["Name"] for b in s3.list_buckets()["Buckets"]]:
        s3.create_bucket(Bucket=BUCKET_AWS)
    requests.post(f"{FAKE_GCS_ENDPOINT}/storage/v1/b?project=ccf-project", json={"name": BUCKET_GCS})
    azure = get_blob_service_client().get_container_client(CONTAINER_AZURE)
    if not azure.exists():
        azure.create_container()

    def gravar_gcs(chave, dados):
        requests.post(f"{FAKE_GCS_ENDPOINT}/upload/storage/v1/b/{BUCKET_GCS}/o?uploadType=media&name={chave}",
                      data=dados).raise_for_status()

    return {
        "aws": (lambda k, d: s3.put_object(Bucket=BUCKET_AWS, Key=k, Body=d), partial(collect_from_s3, BUCKET_AWS)),
        "azure": (lambda k, d: azure.upload_blob(k, d, overwrite=True), partial(collect_from_blob, CONTAINER_AZURE)),
        "gcp": (gravar_gcs, partial(collect_from_gcs, BUCKET_GCS)),
    }


def main(n: int = 1000, n_fabric: int = 100, sem_fabric: bool = False, intervalo_fabric: float = 0.1):  # pragma: no cover
    from modulo_blockchain.registrar_custodia import registrar_e_verificar

    resultado = {"coleta": executar_coletas(n, _provedores())}
    g = resultado["coleta"]["global"]
    print(f"Coleta: {g['integras']}/{g['coletas']} integras ({g['taxa_integridade']:.4%}); "
          f"p50 {g['p50_s']} s, p95 {g['p95_s']} s")
    if not sem_fabric:
        sufixo = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        def registrar(eid, h):
            return registrar_e_verificar(eid, h, datetime.now(timezone.utc).isoformat(), "benchmark", "local",
                                         "arquivo", tentativas_confirmacao=300, intervalo_confirmacao=intervalo_fabric)
        resultado["fabric"] = executar_fabric(n_fabric, registrar, sufixo)
        f = resultado["fabric"]
        resultado["fabric"]["intervalo_consulta_s"] = intervalo_fabric
        print(f"Fabric: {f['confirmadas']}/{f['n']} confirmadas; p50 {f['p50_s']} s, p95 {f['p95_s']} s, "
              f"{f['vazao_sequencial_tx_por_s']} tx/s")
    entrada = {"cenario": "benchmark", "modo": f"n={n}" + ("" if sem_fabric else f",fabric={n_fabric}"),
               "executado_em": datetime.now(timezone.utc).isoformat(),
               "ambiente": {"python": platform.python_version(), "sistema": platform.platform()},
               "resultado": resultado}
    caminho = LOGS / "benchmark_framework.json"
    caminho.write_text(json.dumps(entrada, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Log salvo em: {caminho}")


if __name__ == "__main__":  # pragma: no cover
    p = argparse.ArgumentParser(description="Benchmark de coleta e custodia.")
    p.add_argument("--n", type=int, default=1000, help="numero de coletas")
    p.add_argument("--n-fabric", type=int, default=100, help="numero de registros no ledger")
    p.add_argument("--sem-fabric", action="store_true", help="so a parte de coleta")
    p.add_argument("--intervalo-fabric", type=float, default=0.1, help="intervalo de consulta da confirmacao (s)")
    a = p.parse_args()
    main(a.n, a.n_fabric, a.sem_fabric, a.intervalo_fabric)
