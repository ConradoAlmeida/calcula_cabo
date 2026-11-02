# calcula-cabo

Calculadora de bitola de cabo de energia **DC**. Dimensiona a seção do condutor
de cobre pela queda de tensão máxima **e** pela análise térmica em regime,
escolhe a menor bitola comercial que atende aos dois critérios e compara com as
bitolas vizinhas. Tem CLI interativa e interface web com memorial de cálculo.

## O que o programa faz

- Calcula a seção teórica do cabo (mm²) pela fórmula de queda de tensão.
- Seleciona a **menor** bitola comercial com **Vdrop T. final** dentro do limite **e** critério térmico aprovado.
- Converte a bitola recomendada para **AWG** / MCM.
- Mostra queda de tensão inicial (cabo frio) e em regime (ρ(T_regime)).
- Compara a bitola anterior, a recomendada e a seguinte (queda, ρ(T) e aquecimento).
- Exibe status unificado **APROVADO** / **REPROVADO** (queda + térmica).
- Opcionalmente gera um relatório completo em `.txt`.
- Opcionalmente exibe uma tabela de referência de bitolas e capacidade de corrente.
- Memorial de cálculo passo a passo na interface web (com diagramas).

## Início rápido

```bash
# CLI interativa
uv run python calcular_bitola_cabo_dc.py

# interface web (Flask)
uv run python app.py          # http://localhost:8000

# produção
uv run gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [Instalação](docs/INSTALACAO.md) | Requisitos, execução, web, Credenciais e Docker |
| [Operação](docs/OPERACAO.md) | Endpoints, relatório TXT e exemplo |
| [Cálculo](docs/CALCULO.md) | Entradas, `config.ini`, térmica, memorial e bitolas |
| [Arquitetura](docs/ARQUITETURA.md) | Estrutura do projeto e reuso das funções |
| [Regras para agentes](AGENTS.md) | Comandos, convenções e regras do repositório |

## Avisos

- O dimensionamento considera **queda de tensão em regime** e **análise térmica aproximada** em condutor de cobre DC.
- A capacidade de corrente da tabela de referência é aproximada (cerca de 30 °C) e serve só como consulta.
- A análise térmica não modela dutos ventilados, enterro com resistividade térmica do solo, nem agrupamento de circuitos distintos — apenas o fator de convecção configurável.
- Para instalações reais, confira também as normas aplicáveis (por exemplo NBR 5410) e as tabelas do fabricante do cabo.
