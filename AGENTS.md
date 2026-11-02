# AGENTS.md — calcula-cabo

Instruções para agentes de IA e automação que trabalharem neste repositório.

## O que é

Calculadora de bitola de cabo DC com CLI interativa e interface web Flask. O
dimensionamento combina queda de tensão e análise térmica; as constantes e
tabelas ficam em `config.ini`.

O `README.md` é um índice. Leia o documento da área em `docs/` conforme a
tarefa: `INSTALACAO.md`, `OPERACAO.md`, `CALCULO.md` ou `ARQUITETURA.md`. Não
carregue o README inteiro.

## Comandos

```bash
uv run python calcular_bitola_cabo_dc.py   # CLI
uv run python app.py                      # web em :8000
uv run pytest                             # testes
docker compose up -d --build              # container
```

## Regras que não podem ser quebradas

1. **Constantes físicas e tabelas ficam em `config.ini`.** Não hardcode
   resistividade, coeficientes, bitolas ou capacidade de corrente no código.
2. **CLI e web usam as mesmas funções.** `app.py` deve importar de
   `calcular_bitola_cabo_dc.py`; não duplique a fórmula.
3. **Mudou cálculo? Atualize os testes** (`test_calculos.py`) e o memorial.
4. **Segredos fora do Git.** `CREDENTIALS_API_TOKEN` e `FLASK_SECRET_KEY` vêm
   do `.env`; nunca comite `.env`.
5. **Deploy:** push no GitHub (`origin`); o Gitea espelha; no moyaserver use o
   overlay `docker-compose.moya.yml` (porta 8030).
6. **Avisos são parte do produto.** Não remova as ressalvas de norma/tabela do
   fabricante do README.

## Mapa rápido

- `calcular_bitola_cabo_dc.py` — fórmulas, bitolas, térmica e relatório.
- `app.py` — Flask, rotas e API.
- `config.ini` — física, padrões, bitolas e instalação.
- `templates/`, `static/` — UI e memorial (Mermaid).
- `test_calculos.py`, `test_acesso.py` — testes.

## Verificação

1. `uv run pytest`
2. `uv run python app.py` e conferir `/health`.
3. Se mexeu em `config.ini`, rodar um caso conhecido (7 m, 7 A, 12 V, 5%).
