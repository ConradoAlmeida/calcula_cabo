# calcula-cabo

Calculadora de bitola de cabo de energia **DC**. Dimensiona a seção do condutor
de cobre pela queda de tensão máxima **e** pela análise térmica em regime,
escolhe a menor bitola comercial que atende aos dois critérios e compara a
recomendada com as anteriores reprovadas. Tem CLI interativa e interface web
com memorial de cálculo.

## O que o programa faz

- Calcula a seção teórica do cabo (mm²) pela fórmula de queda de tensão.
- Seleciona a **menor** bitola comercial com **Vdrop T. final** dentro do limite **e** critério térmico aprovado.
- Permite escolher o condutor: **cobre nu** (padrão), **estanhado**, **multifilamento rígido (classe 2)** e **multifilamento flexível (classes 4/5)**, com ou sem estanho.
- Converte a bitola recomendada para **AWG** / MCM.
- Usa uma tabela comercial de **0,13 mm² (AWG 26)** até 630 mm².
- Mostra queda de tensão inicial (cabo frio) e em regime (ρ(T_regime)).
- Compara até quatro anteriores reprovadas, a recomendada e até duas bitolas acima, em ordem crescente.
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
- Os fatores de resistência dos condutores seguem a IEC 60228:2024 (classes 1, 2, 5/6) e a NEC 2023, Capítulo 9, Tabela 8, para o cobre estanhado; podem ser recalibrados em `config.ini`.
- A capacidade de corrente da tabela de referência é aproximada (cerca de 30 °C) e serve só como consulta.
- A análise térmica não modela dutos ventilados, enterro com resistividade térmica do solo, nem agrupamento de circuitos distintos — apenas o fator de convecção configurável.
- Para instalações reais, confira também as normas aplicáveis (por exemplo NBR 5410) e as tabelas do fabricante do cabo.
