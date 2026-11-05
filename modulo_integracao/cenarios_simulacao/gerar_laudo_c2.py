"""
Gera o laudo pericial (PDF) do Cenario C2 a partir do log de execucao
real (modulo_integracao/logs/cenario_c2_execucao.json), com o artefato
de explicabilidade do E4 (oclusao por mensagem) na secao 4 do laudo.

Uso:  poetry run python -m modulo_integracao.cenarios_simulacao.gerar_laudo_c2

O registro de custodia e lido do log. Se o registro ainda estiver
pendente (feito via peer CLI), o laudo o declara como pendente, sem
afirmar sucesso.
"""
import json
from pathlib import Path

from modulo_ia.deteccao_grooming import carregar_config
from modulo_integracao.laudo_pericial import (
    gerar_pdf_laudo,
    montar_conteudo_laudo,
    montar_xai_texto,
)

LOGS = Path(__file__).parent.parent / "logs"
CAMINHO_MODELO_E4 = "modulo_ia/models/modelo_e4_embeddings.json"


def gerar_laudo_c2(caminho_log: Path = LOGS / "cenario_c2_execucao.json",
                   saida: Path = LOGS / "laudo_c2.pdf") -> dict:
    log = json.loads(caminho_log.read_text(encoding="utf-8"))
    resultado = log["resultado"]
    classificacao = resultado["classificacao_grooming"]
    limiar = carregar_config(CAMINHO_MODELO_E4)["limiar_f1max"]
    custodia = resultado.get("registro_custodia")
    if custodia and custodia.get("status") == "pendente_shell":
        custodia = {**custodia, "status": "pendente: registro via peer CLI"}
    conteudo = montar_conteudo_laudo(
        evidencia=resultado["coleta"],
        classificacao=classificacao,
        xai_info=montar_xai_texto(classificacao, limiar),
        historico_blockchain=custodia,
        cenario="C2",
    )
    gerar_pdf_laudo(conteudo, str(saida))
    return conteudo


if __name__ == "__main__":
    c = gerar_laudo_c2()
    print(json.dumps(c["artefatos_xai"], indent=2, ensure_ascii=False))
