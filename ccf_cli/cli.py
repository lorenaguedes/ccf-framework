"""
CLI do framework CCF: comandos curtos no lugar das chamadas longas de modulos.

  ./ccf status                  verifica emuladores, rede Fabric, versao do chaincode e logs
  ./ccf ambiente [up|parar]     emuladores multi-cloud (LocalStack, Azurite, fake-gcs)
  ./ccf fabric [iniciar|deploy|parar]   rede Hyperledger Fabric e chaincode v2
  ./ccf preparar                cria as evidencias SINTETICAS nos emuladores e no container C2
  ./ccf cenario c1|c2|c3|c4|adulteracao|todos [--controle] [--forcado]
  ./ccf demo [--completo] [--pausar]
  ./ccf resumo                  tabela dos logs de execucao
  ./ccf laudos                  lista os laudos PDF gerados
  ./ccf testes [--go]           suite pytest (e testes do chaincode)

Todas as execucoes usam dados sinteticos. Os executores sao injetaveis (testes).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOGS = RAIZ / "modulo_integracao" / "logs"
CEN = "modulo_integracao.cenarios_simulacao."
CHAINCODE_DIR = RAIZ / "modulo_blockchain" / "chaincode" / "custody"
EMULADORES = ("localstack", "azurite", "fake-gcs-server")
PEER = "peer0.org1.example.com"
LOGS_ESPERADOS = ("cenario_c1_ramo_nsfw_forcado.json", "cenario_c2_execucao.json",
                  "cenario_c3_execucao.json", "cenario_c4_execucao.json",
                  "cenario_c4_controle.json", "teste_adulteracao_execucao.json")
CENARIOS = ("c1", "c2", "c3", "c4", "adulteracao")


def _py(modulo: str, *args: str) -> list:
    return ["poetry", "run", "python", "-m", CEN + modulo, *args]


def comandos_cenario(nome: str, controle: bool = False, forcado: bool = False) -> list:
    """Lista de comandos (cada um e uma lista argv) que compoem o cenario."""
    if nome == "c1":
        return [_py("executar_c1_real", *(["--validar-ramo-nsfw"] if forcado else []))]
    if nome == "c2":
        return [_py("preparar_ambiente_c2", *(["--controle"] if controle else [])),
                _py("executar_c2_real", *(["--controle"] if controle else []))]
    if nome == "c3":
        return [_py("executar_c3_real")]
    if nome == "c4":
        return [_py("executar_c4_real", *(["--controle"] if controle else []))]
    if nome == "adulteracao":
        return [_py("executar_adulteracao_real")]
    raise ValueError(f"cenario desconhecido: {nome}")


def _rodar(cmd: list, executar, cwd: Path = RAIZ) -> int:
    print(f"\n$ {' '.join(map(str, cmd))}", flush=True)
    return executar(cmd, cwd=cwd).returncode


def _sequencia(cmds: list, executar) -> int:
    for cmd in cmds:
        rc = _rodar(cmd, executar)
        if rc != 0:
            print(f"\n[ccf] falhou (codigo {rc}); sequencia interrompida.")
            return rc
    return 0


# ---------------------------------------------------------------- status
def _saida(cmd: list, executar, **kw) -> str:
    try:
        r = executar(cmd, capture_output=True, text=True, **kw)
    except FileNotFoundError:
        return ""
    return r.stdout if r.returncode == 0 else ""


def versao_chaincode(executar=subprocess.run) -> str | None:
    from modulo_blockchain.registrar_custodia import CANAL, CHAINCODE, ambiente_peer
    saida = _saida(["peer", "lifecycle", "chaincode", "querycommitted", "-C", CANAL, "-n", CHAINCODE],
                   executar, env=ambiente_peer())
    m = re.search(r"Version:\s*([^,\s]+)", saida)
    return m.group(1) if m else None


def verificar_status(executar=subprocess.run, logs_dir: Path = LOGS) -> list:
    """Retorna [(rotulo, ok, detalhe)]."""
    from modulo_blockchain.registrar_custodia import CHAINCODE_VERSAO_ESPERADA
    nomes = set(_saida(["docker", "ps", "--format", "{{.Names}}"], executar).split())
    itens = [(f"emulador {n}", n in nomes, "em execucao" if n in nomes else "parado: ./ccf ambiente up")
             for n in EMULADORES]
    itens.append(("rede Fabric (peer)", PEER in nomes,
                  "em execucao" if PEER in nomes else "parada: ./ccf fabric iniciar"))
    versao = versao_chaincode(executar) if PEER in nomes else None
    if versao is None:
        itens.append(("chaincode custody", False, "nao implantado: ./ccf fabric deploy"))
    elif versao != CHAINCODE_VERSAO_ESPERADA:
        itens.append(("chaincode custody", False,
                      f"versao {versao}, esperada {CHAINCODE_VERSAO_ESPERADA}: ./ccf fabric deploy"))
    else:
        itens.append(("chaincode custody", True, f"versao {versao}"))
    for nome in LOGS_ESPERADOS:
        existe = (logs_dir / nome).exists()
        itens.append((f"log {nome}", existe, "presente" if existe else "ausente (rode o cenario)"))
    return itens


def cmd_status(args, executar) -> int:
    itens = verificar_status(executar)
    for rotulo, ok, detalhe in itens:
        print(f"[{'OK' if ok else '!!'}] {rotulo:<44} {detalhe}")
    infra = [ok for r, ok, _ in itens if not r.startswith("log ")]
    return 0 if all(infra) else 1


# ---------------------------------------------------------------- infra
def cmd_ambiente(args, executar) -> int:
    cmd = ["docker", "compose", "down"] if args.acao == "parar" else ["docker", "compose", "up", "-d"]
    rc = _rodar(cmd, executar)
    return rc or (_rodar(["docker", "compose", "ps"], executar) if args.acao == "up" else 0)


def cmd_fabric(args, executar) -> int:
    from modulo_blockchain.registrar_custodia import FABRIC_TEST_NETWORK_DIR as rede
    nw = ["./network.sh"]
    deploy = nw + ["deployCC", "-ccn", "custody", "-ccp", str(CHAINCODE_DIR), "-ccl", "go",
                   "-c", "ccfchannel", "-ccv", "2.0", "-ccs", "2"]
    if args.acao == "parar":
        print("ATENCAO: 'network.sh down' APAGA o ledger.")
        return _rodar(nw + ["down"], executar, cwd=rede)
    if args.acao == "iniciar":
        rc = _rodar(nw + ["up", "createChannel", "-c", "ccfchannel", "-ca"], executar, cwd=rede)
        return rc or _rodar(deploy, executar, cwd=rede)
    return _rodar(deploy, executar, cwd=rede)  # deploy: atualiza o chaincode (ledger preservado)


# ---------------------------------------------------------------- execucao
def cmd_preparar(args, executar) -> int:
    return _sequencia([_py("preparar_ambiente_c1_c3"), _py("preparar_ambiente_c4"),
                       _py("preparar_ambiente_c2")], executar)


def cmd_cenario(args, executar) -> int:
    nomes = CENARIOS if args.nome == "todos" else (args.nome,)
    cmds = [c for n in nomes for c in comandos_cenario(n, args.controle, args.forcado)]
    return _sequencia(cmds, executar)


def cmd_demo(args, executar, entrada=input) -> int:
    passos = [("Caso multimodal C4 (suspeito)", comandos_cenario("c4")),
              ("Caso de controle benigno C4", comandos_cenario("c4", controle=True)),
              ("Teste de adulteracao de 1 byte", comandos_cenario("adulteracao"))]
    if args.completo:
        passos = ([("C1 (ramo NSFW forcado)", comandos_cenario("c1", forcado=True)),
                   ("C2 (conversa -> grooming)", comandos_cenario("c2")),
                   ("C3 (3 provedores)", comandos_cenario("c3"))] + passos)
    if cmd_status(args, executar) != 0:
        print("\n[ccf] infraestrutura incompleta; corrija os itens !! antes da demonstracao.")
        return 1
    for i, (titulo, cmds) in enumerate(passos, 1):
        print(f"\n===== Passo {i}/{len(passos)}: {titulo} =====")
        if args.pausar:
            entrada("Enter para executar...")
        rc = _sequencia(cmds, executar)
        if rc:
            return rc
    print("\n===== Resumo =====")
    return cmd_resumo(args, executar)


# ---------------------------------------------------------------- consulta
def resumo_logs(logs_dir: Path = LOGS) -> list:
    linhas = []
    for f in sorted(logs_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            linhas.append((f.name, "?", "?", "log ilegivel"))
            continue
        if not isinstance(d, dict):
            continue
        res = d.get("resultado") if isinstance(d.get("resultado"), dict) else {}
        av = res.get("avaliacao_caso") or {}
        extra = f"prioridade {av['prioridade']}" if av.get("prioridade") else ""
        linhas.append((f.name, str(d.get("cenario", "")), str(d.get("modo", "")),
                       str(d.get("executado_em", ""))[:19] + ("  " + extra if extra else "")))
    return linhas


def cmd_resumo(args, executar) -> int:
    linhas = resumo_logs()
    if not linhas:
        print("Nenhum log em modulo_integracao/logs. Rode: ./ccf cenario todos")
        return 1
    for nome, cen, modo, detalhe in linhas:
        print(f"{nome:<40} {cen:<12} {modo:<18} {detalhe}")
    return 0


def cmd_laudos(args, executar) -> int:
    pdfs = sorted(LOGS.glob("laudo_*.pdf"))
    for p in pdfs:
        print(p.relative_to(RAIZ))
    return 0 if pdfs else 1


def cmd_testes(args, executar) -> int:
    cmds = [["poetry", "run", "pytest", "-q"]]
    if args.go:
        cmds.append(["go", "test", "./..."])
    rc = _rodar(cmds[0], executar)
    if rc == 0 and args.go:
        rc = _rodar(cmds[1], executar, cwd=CHAINCODE_DIR)
    return rc


# ---------------------------------------------------------------- parser
def criar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ccf", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ajuda", action="help", help="mostra esta ajuda")
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("status").set_defaults(f=cmd_status)
    a = sub.add_parser("ambiente")
    a.add_argument("acao", nargs="?", choices=("up", "parar"), default="up")
    a.set_defaults(f=cmd_ambiente)
    fb = sub.add_parser("fabric")
    fb.add_argument("acao", choices=("iniciar", "deploy", "parar"))
    fb.set_defaults(f=cmd_fabric)
    sub.add_parser("preparar").set_defaults(f=cmd_preparar)
    c = sub.add_parser("cenario")
    c.add_argument("nome", choices=CENARIOS + ("todos",))
    c.add_argument("--controle", action="store_true", help="caso de controle benigno (c2, c4)")
    c.add_argument("--forcado", action="store_true", help="C1: classificador forcado (declarado no laudo)")
    c.set_defaults(f=cmd_cenario)
    d = sub.add_parser("demo")
    d.add_argument("--completo", action="store_true")
    d.add_argument("--pausar", action="store_true", help="espera Enter entre os passos")
    d.set_defaults(f=cmd_demo)
    sub.add_parser("resumo").set_defaults(f=cmd_resumo)
    sub.add_parser("laudos").set_defaults(f=cmd_laudos)
    t = sub.add_parser("testes")
    t.add_argument("--go", action="store_true", help="inclui go test do chaincode")
    t.set_defaults(f=cmd_testes)
    return p


def main(argv=None, executar=subprocess.run) -> int:
    args = criar_parser().parse_args(argv)
    try:
        return args.f(args, executar)
    except KeyboardInterrupt:
        print("\n[ccf] interrompido.")
        return 130
