# Cálculo

[← Voltar ao README](../README.md) · [Operação](OPERACAO.md) · [Arquitetura](ARQUITETURA.md)

> Dados de entrada, calibração no config.ini, tipo de condutor, método de instalação, queda de tensão, análise térmica, memorial e bitolas.

---

## Dados de entrada

| Campo | Unidade | Padrão | Observação |
| --- | --- | --- | --- |
| Distância entre fonte e equipamento | m | 10 | Considerada só a ida; o cálculo usa **ida + volta** (`2 × distância`) |
| Corrente do equipamento | A | 5 | — |
| Tensão do sistema | V DC | 12 | — |
| Queda de tensão máxima | % | 3 | Limite usado para dimensionar a bitola |
| Temperatura máxima do cabo | °C | 200 | Usada na análise térmica |
| Temperatura ambiente | °C | 25 | Usada na análise térmica |
| Tipo de condutor | — | Cobre nu sólido | Nu/estanhado; sólido, multifilamento rígido ou flexível |
| AWG em foco | AWG | — | Inclui a bitola na tabela comparativa, mesmo reprovada |
| Diâmetro externo do cabo | mm | estimado | Se omitido, o diâmetro é estimado a partir da bitola |
| Salvar relatório TXT | s/n | — | Nome do arquivo é derivado dos parâmetros de entrada |
| Incluir tabela de referência no TXT | s/n | — | Só aparece se o relatório for salvo |
| Ver tabela de referência no terminal | s/n | — | Após o cálculo |

## Configuração e calibração (`config.ini`)

Todas as constantes físicas, as tabelas de conversão e os valores padrão de entrada ficam em [`config.ini`](../config.ini). Edite os números lá para **recalibrar ou conferir** os cálculos sem tocar no código. Cada campo tem um valor padrão embutido no código, então o programa continua funcionando mesmo sem o arquivo.

| Seção | Conteúdo |
| --- | --- |
| `[fisica]` | Resistividade do cobre nu sólido (Ω·mm²/m) a `T₀`, temperatura de referência `T₀` (°C), coeficiente de temperatura α₀ (1/°C), densidade (kg/m³), calor específico (J/(kg·°C)), coeficiente de convecção (W/(m²·°C)) e espessura de isolação (mm). |
| `[padroes]` | Valores fixos de entrada usados quando um campo é deixado em branco. |
| `[queda_circuito]` | Limites 3% (crítico) e 5% (comum) e rótulos para presets na interface. |
| `[bitolas_comerciais]` | Lista de bitolas comerciais (mm²). |
| `[conversao_awg]` | Tabela de conversão mm² → AWG/MCM. |
| `[capacidade_corrente]` | Capacidade de corrente aproximada por bitola (tabela de referência). |
| `[condutores]` | Tipo de condutor → fator de resistividade sobre o cobre nu sólido; `padrao` define o tipo inicial. |
| `[condutores_rotulos]` | Rótulos exibidos na interface para cada tipo de condutor. |
| `[instalacao]` | Método de instalação → coeficiente de convecção efetivo (W/(m²·°C)); `padrao` define o método inicial. |
| `[instalacao_rotulos]` | Rótulos exibidos na interface para cada método. |
| `[agrupamento]` | Fator de convecção conforme o número de condutores agrupados lado a lado. |

### Método de instalação e agrupamento

A análise térmica considera **como** o cabo é instalado e **quantos** condutores estão agrupados, porque ambos afetam a dissipação de calor. O coeficiente de convecção efetivo é:

```text
h_efetivo = h(método de instalação) × fator(nº de condutores agrupados)
```

Um `h` menor (compartimento fechado, embutido na estrutura, muitos condutores no chicote) significa pior dissipação e, portanto, **temperatura mais alta**. Os métodos e fatores são totalmente configuráveis em `config.ini` e aparecem como um seletor e um campo numérico na interface web.

### Tipo de condutor

O tipo de condutor altera a **resistividade** usada em todo o cálculo: seção por queda, equilíbrio térmico, queda em regime, tempo de aquecimento, tabela comparativa, memorial e relatório TXT. O padrão é o cobre nu sólido, que preserva o comportamento anterior.

Os fatores são aplicados sobre a resistividade do cobre nu sólido (`ρ₀ = 0,0175 Ω·mm²/m`) e seguem a **IEC 60228:2024** (classes 1, 2, 5/6) e a **NEC 2023, Capítulo 9, Tabela 8** para o cobre estanhado:

| Condutor | Classe | Fator sobre cobre nu sólido | ρ efetiva (Ω·mm²/m) |
| --- | --- | ---: | ---: |
| Cobre nu — sólido (maciço) | 1 | `1,00` (padrão) | 0,01750 |
| Cobre estanhado — sólido (maciço) | 1 | `1,04` | 0,01820 |
| Cobre nu — multifilamento rígido | 2 | `1,05` | 0,018375 |
| Cobre estanhado — multifilamento rígido | 2 | `1,07` | 0,018725 |
| Cobre nu — multifilamento flexível | 4/5 | `1,10` | 0,01925 |
| Cobre estanhado — multifilamento flexível | 4/5 | `1,14` | 0,01995 |

A classe 2 (poucos fios grossos, cabo rígido) tem passo de torção maior e penalidade menor. As classes 4/5 (muitos fios finos, cabo flexível/manga) têm passo curto e comprimento real maior; por isso a resistência sobe mais. O estanho reduz a seção efetiva de cobre e acrescenta a resistência da camada, mas como a cobertura é fina o efeito efetivo é de poucos por cento — não os ~6× da resistividade do estanho isolado.

A IEC 60228 fixa limites máximos de resistência DC por classe e bitola; os fatores acima são uma aproximação por classe para uso na calculadora. Se você usar outra referência, basta recalibrar `[condutores]` no `config.ini`.

### AWG em foco

O campo **AWG em foco** inclui uma bitola extra na tabela comparativa, independentemente de ela estar aprovada ou reprovada e de estar fora da janela normal (até quatro anteriores + recomendada + até duas acima). É útil para conferir um cabo específico que você já tem em mãos.

- Se o AWG existe em `[conversao_awg]`, o programa usa a bitola comercial correspondente (por exemplo, `12` → 4,00 mm²).
- Se o AWG não existe na tabela comercial (por exemplo, `17`), o programa usa a área geométrica exata do AWG, calculada por `d = 0,127 × 92^((36−n)/39)`.
- A linha do foco é marcada com **foco** na interface e com `*` no TXT/memorial.
- O campo aceita `0` a `40`, além de `1/0`, `2/0`, `3/0` e `4/0`.

Para conferir os números em uso a qualquer momento (via web), acesse `GET /api/config`, que devolve a configuração ativa em JSON.

## Como o cálculo funciona

### Queda de tensão

Resistividade do cobre nu sólido a 20 °C (base do dimensionamento por queda de tensão):

```text
ρ₀ = 0,0175 Ω·mm²/m
```

O tipo de condutor escolhido multiplica esse valor pelo fator da seção anterior antes de qualquer cálculo.

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

Para até quatro anteriores, a recomendada e até duas acima, o programa estima:

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
0,13  0,16  0,20  0,25  0,35  0,40  0,50  0,75  1,0  1,5  2,5  4
6  10  16  25  35  50  70  95  120  150  185  240  300  400  500  630 mm²
```

A menor bitola é **0,13 mm² (AWG 26)**; a maior é **630 mm²**. A tabela comparativa mostra até quatro anteriores, a recomendada e até duas acima.
