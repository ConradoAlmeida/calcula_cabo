# calcula-cabo

Calculadora de bitola ideal para cabos de energia elétrica **DC**.

O programa dimensiona a seção do condutor de cobre a partir da queda de tensão máxima permitida, escolhe a bitola comercial imediatamente superior e compara o resultado com as bitolas vizinhas, incluindo uma análise térmica aproximada.

## O que o programa faz

- Calcula a seção teórica do cabo (mm²) pela fórmula de queda de tensão.
- Seleciona a bitola comercial mais próxima **para cima**.
- Converte a bitola recomendada para **AWG** / MCM.
- Mostra queda de tensão real (V e %) com a bitola escolhida.
- Compara a bitola anterior, a recomendada e a seguinte (queda e aquecimento).
- Opcionalmente gera um relatório completo em `.txt`.
- Opcionalmente exibe uma tabela de referência de bitolas e capacidade de corrente.

## Requisitos

- Python **3.14** ou superior (definido em `pyproject.toml`)
- Nenhuma dependência externa

O projeto usa o gerenciador [uv](https://docs.astral.sh/uv/), mas o script principal também pode ser executado com o Python do sistema.

## Como executar

### Com uv

```bash
uv run python calcular_bitola_cabo_dc.py
```

### Com Python

```bash
python calcular_bitola_cabo_dc.py
```

O programa é interativo. Basta responder às perguntas no terminal. Se um campo for deixado em branco, o valor padrão é usado.

## Interface web

Além da CLI, o projeto oferece uma interface web (Flask + [Bootstrap 5.3](https://getbootstrap.com/)) que reaproveita as mesmas funções de cálculo. A aplicação Flask fica em `app.py`.

### Executar em desenvolvimento

```bash
uv run python app.py
```

A aplicação sobe em `http://localhost:8000` (a porta pode ser alterada com a variável de ambiente `PORT`).

### Executar em produção (gunicorn)

```bash
uv run gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
```

### Endpoints

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/` | Página com o formulário e os resultados. |
| `GET` | `/health` | Verificação de saúde (`{"status": "ok"}`). |
| `POST` | `/api/calcular` | Recebe os parâmetros em JSON e devolve o dimensionamento e a análise térmica. |
| `POST` | `/api/relatorio` | Gera e devolve o relatório `.txt` para download. |
| `GET` | `/api/config` | Devolve a configuração/calibração ativa (constantes, tabelas e padrões) para conferência. |

O Bootstrap é servido localmente (`static/vendor/bootstrap/`), então a interface funciona sem acesso à internet.

## Deploy com Docker / Podman

O projeto inclui um `Dockerfile` (imagem base `ghcr.io/astral-sh/uv:python3.14-bookworm-slim`, servida por gunicorn como usuário sem privilégios).

### Docker

```bash
docker build -t calcula-cabo .
docker run --rm -p 8000:8000 calcula-cabo
```

### Podman

```bash
podman build -t calcula-cabo .
podman run --rm -p 8000:8000 calcula-cabo
```

Depois, acesse `http://localhost:8000`.

## Dados de entrada

| Campo | Unidade | Padrão | Observação |
| --- | --- | --- | --- |
| Distância entre fonte e equipamento | m | 10 | Considerada só a ida; o cálculo usa **ida + volta** (`2 × distância`) |
| Corrente do equipamento | A | 5 | — |
| Tensão do sistema | V DC | 12 | — |
| Queda de tensão máxima | % | 3 | Limite usado para dimensionar a bitola |
| Temperatura máxima do cabo | °C | 200 | Usada na análise térmica |
| Temperatura ambiente | °C | 25 | Usada na análise térmica |
| Diâmetro externo do cabo | mm | estimado | Se omitido, o diâmetro é estimado a partir da bitola |
| Salvar relatório TXT | s/n | — | Nome do arquivo é derivado dos parâmetros de entrada |
| Incluir tabela de referência no TXT | s/n | — | Só aparece se o relatório for salvo |
| Ver tabela de referência no terminal | s/n | — | Após o cálculo |

## Configuração e calibração (`config.ini`)

Todas as constantes físicas, as tabelas de conversão e os valores padrão de entrada ficam em [`config.ini`](config.ini). Edite os números lá para **recalibrar ou conferir** os cálculos sem tocar no código. Cada campo tem um valor padrão embutido no código, então o programa continua funcionando mesmo sem o arquivo.

| Seção | Conteúdo |
| --- | --- |
| `[fisica]` | Resistividade do cobre (Ω·mm²/m) a `T₀`, temperatura de referência `T₀` (°C), coeficiente de temperatura α₀ (1/°C), densidade (kg/m³), calor específico (J/(kg·°C)), coeficiente de convecção (W/(m²·°C)) e espessura de isolação (mm). |
| `[padroes]` | Valores fixos de entrada usados quando um campo é deixado em branco. |
| `[bitolas_comerciais]` | Lista de bitolas comerciais (mm²). |
| `[conversao_awg]` | Tabela de conversão mm² → AWG/MCM. |
| `[capacidade_corrente]` | Capacidade de corrente aproximada por bitola (tabela de referência). |
| `[instalacao]` | Método de instalação → coeficiente de convecção efetivo (W/(m²·°C)); `padrao` define o método inicial. |
| `[instalacao_rotulos]` | Rótulos exibidos na interface para cada método. |
| `[agrupamento]` | Fator de convecção conforme o número de condutores agrupados lado a lado. |

### Método de instalação e agrupamento

A análise térmica considera **como** o cabo é instalado e **quantos** condutores estão agrupados, porque ambos afetam a dissipação de calor. O coeficiente de convecção efetivo é:

```text
h_efetivo = h(método de instalação) × fator(nº de condutores agrupados)
```

Um `h` menor (eletroduto embutido, enterrado, muitos condutores juntos) significa pior dissipação e, portanto, **temperatura mais alta**. Os métodos e fatores são totalmente configuráveis em `config.ini` e aparecem como um seletor e um campo numérico na interface web.

Para conferir os números em uso a qualquer momento (via web), acesse `GET /api/config`, que devolve a configuração ativa em JSON.

## Como o cálculo funciona

### Queda de tensão

Resistividade do cobre a 20 °C (usada no dimensionamento por queda de tensão):

```text
ρ₀ = 0,0175 Ω·mm²/m
```

Na **análise térmica**, a resistividade varia com a temperatura de operação:

```text
ρ(T) = ρ₀ · (1 + α₀ · (T − T₀))
```

com `T₀ = 20 °C` e `α₀ ≈ 0,00393 /°C` (configurável em `config.ini`). O modelo resolve o equilíbrio com realimentação: quanto mais quente o cabo, maior ρ e maior potência dissipada — até convergir em `T_regime` ou indicar runaway térmico (sem equilíbrio finito).

O dimensionamento por queda de tensão usa ρ(T) em regime quando os parâmetros térmicos estão disponíveis. A interface mostra:

- **Vdrop inicial**: queda com o cabo frio (T ambiente) — valor na largada.
- **Vdrop T. final**: queda em regime permanente, com ρ(T_regime) e realimentação térmica — até onde a queda pode chegar em operação.

O limite de queda percentual é verificado contra o **Vdrop T. final** (pior caso em operação).

Comprimento total (ida e volta):

```text
L = 2 × distância
```

Seção teórica:

```text
S = (ρ × L × I) / V_queda
```

em que `V_queda` é a queda máxima permitida em volts (`% × tensão`).

A bitola comercial escolhida é a primeira da tabela maior ou igual a `S`. Com essa bitola, o programa recalcula resistência, queda em volts e queda percentual.

### Análise térmica

Para a bitola recomendada e as vizinhas imediatas, o programa estima:

- potência dissipada por efeito Joule (W/m), com ρ(T) em regime
- temperatura de regime com realimentação térmica (ρ sobe com T)
- margem térmica até a temperatura máxima da isolação
- tempo aproximado até atingir a temperatura máxima do cabo

O modelo térmico é uma **aproximação** (convecção configurável por método de instalação). Não substitui tabelas de capacidade de corrente nem normas de instalação.

### Memorial de cálculo (web)

Após dimensionar na interface web, o botão **Memorial** abre a página `/memorial` com o detalhamento passo a passo: entradas, constantes, dimensionamento, quedas de tensão (inicial e em regime), equilíbrio térmico e tabela comparativa. Útil para conferência e validação dos resultados.

### Bitolas comerciais

O programa usa a tabela:

```text
0,5  0,75  1,0  1,5  2,5  4  6  10  16  25  35  50
70  95  120  150  185  240  300  400  500  630 mm²
```

## Relatório em TXT

Se você escolher salvar o relatório, o arquivo é gerado no diretório atual com um nome estável baseado nos parâmetros, por exemplo:

```text
relatorio_bitola_dc_d7_i7_v12_q5_ta25_tm200_deestimado_refsim_7dd0effa.txt
```

Se já existir um relatório com a mesma combinação de entradas, o programa pergunta se deseja reutilizar o arquivo sem recalcular.

O TXT contém:

1. dados de entrada
2. resumo executivo
3. tabela de dimensionamento
4. análise térmica comparativa
5. tabela de referência (opcional)

## Estrutura do projeto

```text
calcula_cabo/
├── calcular_bitola_cabo_dc.py   # calculadora interativa (script principal / funções de cálculo)
├── config.ini                   # constantes, tabelas e valores padrão (calibração)
├── test_calculos.py             # testes de verificação dos cálculos e do config.ini
├── app.py                       # aplicação web Flask (reaproveita as funções de cálculo)
├── templates/
│   └── index.html               # página da interface web
├── static/
│   ├── css/style.css            # ajustes de estilo sobre o Bootstrap
│   ├── js/app.js                # lógica da interface (fetch da API + render)
│   └── vendor/bootstrap/        # Bootstrap 5.3 servido localmente
├── main.py                      # ponto de entrada gerado pelo uv
├── Dockerfile                   # imagem de container (gunicorn)
├── .dockerignore
├── pyproject.toml
├── uv.lock
├── .python-version
└── README.md
```

Para usar as funções em outro script:

```python
from calcular_bitola_cabo_dc import calcular_bitola_cb, calcular_tempo_aquecimento

resultado = calcular_bitola_cb(
    distancia=7,
    corrente=7,
    tensao=12,
    queda_percentual=5,
)
print(resultado["bitola_recomendada"], resultado["bitola_awg"])
```

## Exemplo

Para 7 m, 7 A, 12 V DC e queda máxima de 5%:

| Seção calculada | Bitola recomendada | AWG | Queda real | Status |
| --- | --- | --- | --- | --- |
| 2,86 mm² | 4,00 mm² | 12 | 0,43 V (3,57%) | ADEQUADA |

## Avisos

- O dimensionamento considera apenas **queda de tensão** em condutor de cobre DC.
- A capacidade de corrente da tabela de referência é aproximada (cerca de 30 °C) e serve só como consulta.
- A análise térmica não modela agrupamento de circuitos, isolamento específico, enterro, dutos nem ventilação forçada.
- Para instalações reais, confira também as normas aplicáveis (por exemplo NBR 5410) e as tabelas do fabricante do cabo.
