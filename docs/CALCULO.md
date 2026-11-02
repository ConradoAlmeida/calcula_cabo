# Cálculo

[← Voltar ao README](../README.md) · [Operação](OPERACAO.md) · [Arquitetura](ARQUITETURA.md)

> Dados de entrada, calibração no config.ini, método de instalação, queda de tensão, análise térmica, memorial e bitolas.

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
| Diâmetro externo do cabo | mm | estimado | Se omitido, o diâmetro é estimado a partir da bitola |
| Salvar relatório TXT | s/n | — | Nome do arquivo é derivado dos parâmetros de entrada |
| Incluir tabela de referência no TXT | s/n | — | Só aparece se o relatório for salvo |
| Ver tabela de referência no terminal | s/n | — | Após o cálculo |

## Configuração e calibração (`config.ini`)

Todas as constantes físicas, as tabelas de conversão e os valores padrão de entrada ficam em [`config.ini`](../config.ini). Edite os números lá para **recalibrar ou conferir** os cálculos sem tocar no código. Cada campo tem um valor padrão embutido no código, então o programa continua funcionando mesmo sem o arquivo.

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
