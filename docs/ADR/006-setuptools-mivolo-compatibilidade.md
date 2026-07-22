# ADR 006 — Fixacao de setuptools<81 para compatibilidade com MiVOLO

## Contexto
O pacote MiVOLO usa setup.py legado dependente de pkg_resources,
removido em setuptools >=81. Isso causa falha de build mesmo com
--no-build-isolation.

## Decisao
Fixar setuptools<81 no venv antes de instalar MiVOLO via pip
(fora do gerenciamento normal do Poetry).

## Consequencias
- Positivo: permite integracao real do MiVOLO localmente.
- Negativo: dependencia fora do poetry.lock, requer documentacao
  manual no README.
