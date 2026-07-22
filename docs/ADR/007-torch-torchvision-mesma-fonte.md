# ADR 007 — Instalar torch e torchvision da mesma fonte (indice CPU)

## Contexto
Instalar torchvision via pip padrao (PyPI) enquanto torch vem do
indice CPU-only (download.pytorch.org/whl/cpu) causa erro
"operator torchvision::nms does not exist" - apesar dos numeros de
versao serem nominalmente compativeis (torch 2.13.0 <-> torchvision
0.28.0), os binarios sao compilados de fontes diferentes (CUDA vs CPU).

## Decisao
Sempre instalar/reinstalar torchvision com
--index-url https://download.pytorch.org/whl/cpu, garantindo
compatibilidade binaria com o torch CPU-only ja instalado.

## Consequencias
- Positivo: resolve o erro de operador ausente definitivamente.
- Negativo: instalacoes futuras de pacotes que dependem de
  torchvision (como o MiVOLO) podem reintroduzir o problema se
  nao especificarem o indice corretamente - documentar no README.
