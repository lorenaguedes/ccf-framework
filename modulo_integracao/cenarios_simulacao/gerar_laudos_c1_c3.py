"""
Gera os laudos periciais (PDF) dos Cenarios C1 e C3 a partir dos logs de
execucao real em modulo_integracao/logs/, no mesmo padrao do laudo do C2.

Uso:
  poetry run python -m modulo_integracao.cenarios_simulacao.gerar_laudos_c1_c3

Regras de fidelidade do laudo (secao 4.4.6 do PGT):
- C1: usa a classificacao do log. Conteudo SFW consta como "nao aplicavel";
  se o log for de uma execucao com classificador forcado, o laudo traz
  classificador_forcado: true na secao de classificacao.
- C3: o cenario nao tem etapa de IA; o laudo declara "classificacao nao
  executada", sem afirmar classificacao alguma, e inclui o registro de
  custodia e a verificacao de integridade de cada evidencia.
"""
import json
from pathlib import Path

from modulo_integracao.laudo_pericial import (
    gerar_pdf_laudo,
    gerar_pdf_laudo_consolidado,
    montar_conteudo_laudo,
    montar_conteudo_laudo_consolidado,
    montar_xai_imagem,
)

LOGS = Path(__file__).parent.parent / "logs"


def _ler(caminho: Path) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))["resultado"]


def _custodia_com_verificacao(registro: dict | None, verificacao: dict | None) -> dict | None:
    if registro is None:
        return None
    if verificacao:
        return {**registro, "verificacao_integridade": {
            "hash_original": verificacao.get("hash_original"),
            "hash_recalculado": verificacao.get("hash_recalculado"),
            "integridade_valida": verificacao.get("integridade_valida"),
        }}
    return registro


def conteudo_laudo_c1(caminho_log: Path = LOGS / "cenario_c1_execucao.json") -> dict:
    resultado = _ler(caminho_log)
    return montar_conteudo_laudo(
        evidencia=resultado["coleta"],
        classificacao=resultado["classificacao"],
        xai_info=montar_xai_imagem(resultado["classificacao"], resultado.get("explicabilidade")),
        historico_blockchain=_custodia_com_verificacao(
            resultado.get("registro_custodia"), resultado.get("verificacao_integridade")),
        cenario="C1",
    )


def conteudos_laudo_c3(caminho_log: Path = LOGS / "cenario_c3_execucao.json") -> dict:
    """Retorna {provedor: conteudo do laudo} para cada evidencia do C3."""
    resultado = _ler(caminho_log)
    registros = {r["hash"]: r for r in resultado["registros_custodia"]}
    verificacoes = {v["cloud_provider"]: v for v in resultado.get("verificacoes_integridade", [])}
    conteudos = {}
    for ev in resultado["evidencias"]:
        provedor = ev["cloud_provider"]
        conteudos[provedor] = montar_conteudo_laudo(
            evidencia=ev,
            classificacao={
                "classificacao_executada": False,
                "observacao": f"Evidencia correlacionada de operacao multi-nuvem ({provedor}); "
                              "o cenario valida coleta e custodia, sem etapa de classificacao por IA.",
            },
            xai_info=None,
            historico_blockchain=_custodia_com_verificacao(
                registros.get(ev["hashes"]["sha256"]), verificacoes.get(provedor)),
            cenario="C3",
        )
    return conteudos


def conteudo_laudo_consolidado_c3(caminho_log: Path = LOGS / "cenario_c3_execucao.json") -> dict:
    """Laudo unico do C3, correlacionando as evidencias dos tres provedores
    (criterio de sucesso da Tabela 16 do PGT)."""
    resultado = _ler(caminho_log)
    registros = {r["hash"]: r for r in resultado["registros_custodia"]}
    verificacoes = {v["cloud_provider"]: v for v in resultado.get("verificacoes_integridade", [])}
    historicos = {
        ev["cloud_provider"]: _custodia_com_verificacao(
            registros.get(ev["hashes"]["sha256"]), verificacoes.get(ev["cloud_provider"]))
        for ev in resultado["evidencias"]
    }
    return montar_conteudo_laudo_consolidado(
        resultado["evidencias"], resultado["correlacao"], historicos, cenario="C3")


def gerar_laudo_consolidado_c3(caminho_log: Path = LOGS / "cenario_c3_execucao.json",
                               saida: Path = LOGS / "laudo_c3_consolidado.pdf") -> dict:
    conteudo = conteudo_laudo_consolidado_c3(caminho_log)
    gerar_pdf_laudo_consolidado(conteudo, str(saida))
    return conteudo


def gerar_laudo_c1(caminho_log: Path = LOGS / "cenario_c1_execucao.json",
                   saida: Path = LOGS / "laudo_c1.pdf") -> dict:
    conteudo = conteudo_laudo_c1(caminho_log)
    gerar_pdf_laudo(conteudo, str(saida))
    return conteudo


def gerar_laudos_c3(caminho_log: Path = LOGS / "cenario_c3_execucao.json",
                    saida_dir: Path = LOGS) -> list:
    saidas = []
    for provedor, conteudo in conteudos_laudo_c3(caminho_log).items():
        saida = Path(saida_dir) / f"laudo_c3_{provedor}.pdf"
        gerar_pdf_laudo(conteudo, str(saida))
        saidas.append(saida)
    return saidas


if __name__ == "__main__":
    for caminho in (LOGS / "cenario_c1_execucao.json",):
        if caminho.exists():
            gerar_laudo_c1(caminho)
            print("Laudo salvo em: modulo_integracao/logs/laudo_c1.pdf")
    if (LOGS / "cenario_c3_execucao.json").exists():
        for s in gerar_laudos_c3():
            print(f"Laudo salvo em: {s}")
        gerar_laudo_consolidado_c3()
        print("Laudo salvo em: modulo_integracao/logs/laudo_c3_consolidado.pdf")
