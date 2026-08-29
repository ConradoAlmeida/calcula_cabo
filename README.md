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

## Como o cálculo funciona

### Queda de tensão

Resistividade do cobre a 20 °C:

```text
ρ = 0,0175 Ω·mm²/m
```

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

- potência dissipada por efeito Joule (W/m)
- temperatura de regime em ar parado
- tempo aproximado até atingir a temperatura máxima do cabo

O modelo térmico é uma **aproximação** (convecção com `h = 10 W/(m²·°C)`). Não substitui tabelas de capacidade de corrente nem normas de instalação.

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
