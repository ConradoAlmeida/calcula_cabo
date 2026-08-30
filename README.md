# calcula-cabo

Calculadora de bitola ideal para cabos de energia elétrica **DC**.

O programa dimensiona a seção do condutor de cobre a partir da queda de tensão máxima permitida **e** da análise térmica em regime, escolhe a **menor** bitola comercial que atende ambos os critérios (status **APROVADO**) e compara o resultado com as bitolas vizinhas.

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

## Docker

```bash
docker compose up -d --build
```

Acessar em `http://<ip-do-host>:8000`.

O `config.ini` do host é montado no container (somente leitura). Edite-o para recalibrar sem rebuild.

### moyaserver (produção)

Repositório espelhado no Gitea: `ssh://git@moya-git.local:222/moya-dev/calcula_cabo.git`  
(mirror read-only do GitHub; o push de desenvolvimento vai para `origin` no GitHub.)

Fluxo:

1. **Development:** `git push origin master` (GitHub)
2. **Gitea:** sincroniza o mirror (automático ou manual em *Sync Mirror* no Gitea)
3. **moyaserver:** `git pull` + rebuild abaixo

A porta **8000** do host já é usada pelo Portainer; use o overlay `docker-compose.moya.yml` (publica em **8030**):

```bash
git clone ssh://git@moya-git.local:222/moya-dev/calcula_cabo.git
cd calcula_cabo
docker compose -f docker-compose.yml -f docker-compose.moya.yml up -d --build
```

Atualizar:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.moya.yml up -d --build
```

Após push no GitHub, aguarde o mirror do Gitea ou dispare *Sync Mirror* antes do `git pull` no servidor.

Acesso interno: `http://moya-calcula-cabo.local` (via Caddy no moyaserver).

### Build manual (sem Compose)

```bash
docker build -t calcula-cabo .
docker run --rm -p 8000:8000 -v ./config.ini:/app/config.ini:ro calcula-cabo
```

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
| `[queda_circuito]` | Limites 3% (crítico) e 5% (comum) e rótulos para presets na interface. |
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

Um `h` menor (compartimento fechado, embutido na estrutura, muitos condutores no chicote) significa pior dissipação e, portanto, **temperatura mais alta**. Os métodos e fatores são totalmente configuráveis em `config.ini` e aparecem como um seletor e um campo numérico na interface web.

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

**Limites por tipo de circuito** (IEC 60364-5-52 Anexo G / prática embarcada UAS):

| Tipo | Limite | Uso típico |
| --- | --- | --- |
| **Crítico** | **3%** | Controle, sensores, aviônica, FC |
| **Comum** | **5%** | Propulsão, barramento de potência |

Configurável em `config.ini` (`[queda_circuito]`). A interface web oferece presets **3% Crítico** e **5% Comum**.

**Certificação (RBAC 100, STANAG):** documente cada trecho no formato **requisito → método → evidência**. O memorial e o relatório TXT incluem rodapé com essa orientação e servem como evidência de dimensionamento.

**Seleção da bitola:** percorre as bitolas comerciais da menor para a maior e adota a primeira com **Vdrop T. final ≤ limite** e **alerta térmico ok** (T_regime abaixo de 70% de T_max). Se nenhuma atender, usa a maior da tabela (status REPROVADO).

Comprimento total (ida e volta):

```text
L = 2 × distância
```

Na análise térmica, usa-se o trecho de **um condutor** (distância fonte → equipamento). A potência total dissipada escala com o comprimento, mas **W/m** e **T_regime** permanecem constantes para a mesma bitola e corrente — mais calor gerado, mais área lateral para dissipar.

Seção teórica:

```text
S = (ρ × L × I) / V_queda
```

em que `V_queda` é a queda máxima permitida em volts (`% × tensão`).

Com essa bitola, o programa recalcula resistência, queda em volts e queda percentual (inicial e em regime).

### Análise térmica

Para a bitola recomendada e as vizinhas imediatas, o programa estima:

- potência dissipada por efeito Joule (W/m e W total no trecho), com ρ(T) em regime
- temperatura de regime com realimentação térmica (ρ sobe com T)
- resistividade inicial (T ambiente) e em regime (ρ(T_regime))
- tempo aproximado até atingir a temperatura máxima do cabo

**Status térmico:** `ok` (< 70% de T_max), `atencao` (70–90%), `critico` (≥ 90% ou runaway). Runaway (Kα ≥ 1, T = ∞) é sempre crítico.

**Status da bitola:** **APROVADO** quando queda e térmica estão ok; **REPROVADO** caso contrário.

O modelo térmico é uma **aproximação** (convecção configurável por método de instalação e agrupamento). Não substitui tabelas de capacidade de corrente nem normas de instalação.

### Memorial de cálculo (web)

Após dimensionar na interface web, o botão **Memorial** abre a página `/memorial` com:

1. **Resumo executivo** — objetivo, comprimentos elétrico vs térmico, ρ(T) e dissipação
2. Dados de entrada e constantes físicas
3. Dimensionamento (queda + térmica) e bitola adotada
4. Queda de tensão inicial e em regime
5. Equilíbrio térmico da bitola recomendada
6. Tabela comparativa com status APROVADO/REPROVADO
7. Diagramas Mermaid do fluxo de cálculo

Útil para conferência e validação dos resultados.

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
│   ├── index.html               # página da interface web
│   └── memorial.html            # memorial de cálculo passo a passo
├── static/
│   ├── css/style.css            # tema escuro (identidade moya-weather-pro)
│   ├── js/app.js                # lógica da interface (fetch da API + render)
│   ├── js/memorial.js           # render do memorial e diagramas Mermaid
│   └── vendor/bootstrap/        # Bootstrap 5.3 servido localmente
├── main.py                      # ponto de entrada gerado pelo uv
├── Dockerfile                   # imagem de container (gunicorn)
├── docker-compose.yml           # build e deploy conteinerizado
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

| Seção calculada | Bitola recomendada | AWG | Queda T. final | Status |
| --- | --- | --- | --- | --- |
| 2,86 mm² | 4,00 mm² | 12 | 0,43 V (3,57%) | APROVADO |

## Avisos

- O dimensionamento considera **queda de tensão em regime** e **análise térmica aproximada** em condutor de cobre DC.
- A capacidade de corrente da tabela de referência é aproximada (cerca de 30 °C) e serve só como consulta.
- A análise térmica não modela dutos ventilados, enterro com resistividade térmica do solo, nem agrupamento de circuitos distintos — apenas o fator de convecção configurável.
- Para instalações reais, confira também as normas aplicáveis (por exemplo NBR 5410) e as tabelas do fabricante do cabo.
