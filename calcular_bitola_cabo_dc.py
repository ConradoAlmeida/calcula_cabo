#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para calcular a bitola ideal de cabo de energia elétrica DC.
Baseado na queda de tensão máxima permitida e resistividade do condutor.
"""

from dataclasses import dataclass, field
from datetime import datetime
import configparser
import hashlib
import os

# ---------------------------------------------------------------------------
# Configuração / calibração (config.ini)
# ---------------------------------------------------------------------------
# Todas as constantes físicas, tabelas de conversão e valores padrão ficam em
# config.ini. Os valores abaixo são os padrões embutidos, usados quando o
# arquivo (ou uma chave) está ausente. Assim o módulo continua funcionando
# mesmo sem o config.ini.

CONFIG_PATH_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

_FISICA_PADRAO = {
    "resistividade_cobre": 0.0175,   # Ohm·mm²/m
    "temperatura_referencia": 20.0,  # °C — referência de ρ₀
    "coef_temp_cobre": 0.00393,      # 1/°C — coeficiente de temperatura
    "densidade_cobre": 8900.0,       # kg/m³
    "calor_especifico_cobre": 385.0, # J/(kg·°C)
    "coef_conveccao": 10.0,          # W/(m²·°C)
    "espessura_isolacao": 2.0,       # mm
}

_PADROES_ENTRADA = {
    "distancia": 10.0,
    "corrente": 5.0,
    "tensao": 12.0,
    "queda_percentual": 3.0,
    "temp_max": 200.0,
    "temp_amb": 25.0,
}

_BITOLAS_PADRAO = [
    0.5, 0.75, 1.0, 1.5, 2.5, 4.0, 6.0, 10.0,
    16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0,
    150.0, 185.0, 240.0, 300.0, 400.0, 500.0, 630.0,
]

_CONVERSAO_AWG_PADRAO = {
    0.5: 20, 0.75: 19, 1.0: 18, 1.5: 16, 2.5: 14, 4.0: 12, 6.0: 10,
    10.0: 8, 16.0: 6, 25.0: 4, 35.0: 2, 50.0: 1, 70.0: "1/0", 95.0: "2/0",
    120.0: "3/0", 150.0: "4/0", 185.0: "250 MCM", 240.0: "300 MCM",
    300.0: "350 MCM", 400.0: "400 MCM", 500.0: "500 MCM", 630.0: "600 MCM",
}

_CAPACIDADE_PADRAO = {
    1.5: 16, 2.5: 20, 4.0: 25, 6.0: 32, 10.0: 44, 16.0: 60, 25.0: 80,
    35.0: 100, 50.0: 125, 70.0: 160, 95.0: 195, 120.0: 225, 150.0: 260,
    185.0: 300, 240.0: 355,
}

# Métodos de instalação -> coeficiente de convecção efetivo (W/(m²·°C)).
_INSTALACAO_PADRAO = {
    "ar_livre": 10.0,
    "eletroduto_aparente": 6.0,
    "eletroduto_embutido": 4.0,
    "enterrado": 3.0,
}
_INSTALACAO_ROTULOS_PADRAO = {
    "ar_livre": "Ao ar livre (exposto)",
    "eletroduto_aparente": "Em eletroduto aparente",
    "eletroduto_embutido": "Em eletroduto embutido na parede",
    "enterrado": "Enterrado / subterrâneo",
}
_INSTALACAO_METODO_PADRAO = "ar_livre"

# Fator aplicado ao coeficiente de convecção conforme o nº de condutores
# agrupados lado a lado (mais condutores juntos = pior dissipação).
_AGRUPAMENTO_PADRAO = {
    1: 1.00, 2: 0.85, 3: 0.79, 4: 0.75, 5: 0.73, 6: 0.72, 7: 0.71, 8: 0.70,
}


@dataclass
class Config:
    """Constantes e tabelas usadas pelos cálculos (carregadas de config.ini)."""
    resistividade_cobre: float
    temperatura_referencia: float
    coef_temp_cobre: float
    densidade_cobre: float
    calor_especifico_cobre: float
    coef_conveccao: float
    espessura_isolacao: float
    padroes: dict = field(default_factory=dict)
    bitolas_comerciais: list = field(default_factory=list)
    conversao_awg: dict = field(default_factory=dict)
    capacidade_corrente: dict = field(default_factory=dict)
    instalacao: dict = field(default_factory=dict)
    instalacao_rotulos: dict = field(default_factory=dict)
    instalacao_padrao: str = _INSTALACAO_METODO_PADRAO
    agrupamento: dict = field(default_factory=dict)


def _num_awg(texto):
    """Converte o valor AWG: inteiro quando possível, senão mantém o texto."""
    texto = str(texto).strip()
    try:
        return int(texto)
    except ValueError:
        return texto


def _num_corrente(texto):
    """Corrente máxima: inteiro quando for um valor inteiro, senão float."""
    valor = float(texto)
    return int(valor) if valor.is_integer() else valor


def carregar_config(caminho=None):
    """Carrega config.ini sobre os padrões embutidos e devolve um Config."""
    fisica = dict(_FISICA_PADRAO)
    padroes = dict(_PADROES_ENTRADA)
    bitolas = list(_BITOLAS_PADRAO)
    conversao = dict(_CONVERSAO_AWG_PADRAO)
    capacidade = dict(_CAPACIDADE_PADRAO)
    instalacao = dict(_INSTALACAO_PADRAO)
    instalacao_rotulos = dict(_INSTALACAO_ROTULOS_PADRAO)
    instalacao_padrao = _INSTALACAO_METODO_PADRAO
    agrupamento = dict(_AGRUPAMENTO_PADRAO)

    caminho = caminho or CONFIG_PATH_PADRAO
    if os.path.exists(caminho):
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str  # preserva as chaves como estão
        parser.read(caminho, encoding="utf-8")

        if parser.has_section("fisica"):
            for chave in fisica:
                if parser.has_option("fisica", chave):
                    fisica[chave] = parser.getfloat("fisica", chave)

        if parser.has_section("padroes"):
            for chave in padroes:
                if parser.has_option("padroes", chave):
                    padroes[chave] = parser.getfloat("padroes", chave)

        if parser.has_option("bitolas_comerciais", "valores"):
            bruto = parser.get("bitolas_comerciais", "valores")
            itens = [x for x in bruto.replace(";", ",").split(",") if x.strip()]
            if itens:
                bitolas = sorted(float(x) for x in itens)

        if parser.has_section("conversao_awg"):
            itens = parser.items("conversao_awg")
            if itens:
                conversao = {float(k): _num_awg(v) for k, v in itens}

        if parser.has_section("capacidade_corrente"):
            itens = parser.items("capacidade_corrente")
            if itens:
                capacidade = {float(k): _num_corrente(v) for k, v in itens}

        if parser.has_section("instalacao"):
            metodos = {}
            for chave, valor in parser.items("instalacao"):
                if chave == "padrao":
                    instalacao_padrao = valor.strip()
                    continue
                try:
                    metodos[chave] = float(valor)
                except ValueError:
                    continue
            if metodos:
                instalacao = metodos

        if parser.has_section("instalacao_rotulos"):
            rotulos = dict(parser.items("instalacao_rotulos"))
            if rotulos:
                instalacao_rotulos = rotulos

        if parser.has_section("agrupamento"):
            itens = parser.items("agrupamento")
            if itens:
                agrupamento = {int(k): float(v) for k, v in itens}

    # Garante que o método padrão exista entre os métodos disponíveis.
    if instalacao_padrao not in instalacao and instalacao:
        instalacao_padrao = next(iter(instalacao))

    return Config(
        resistividade_cobre=fisica["resistividade_cobre"],
        temperatura_referencia=fisica["temperatura_referencia"],
        coef_temp_cobre=fisica["coef_temp_cobre"],
        densidade_cobre=fisica["densidade_cobre"],
        calor_especifico_cobre=fisica["calor_especifico_cobre"],
        coef_conveccao=fisica["coef_conveccao"],
        espessura_isolacao=fisica["espessura_isolacao"],
        padroes=padroes,
        bitolas_comerciais=bitolas,
        conversao_awg=conversao,
        capacidade_corrente=capacidade,
        instalacao=instalacao,
        instalacao_rotulos=instalacao_rotulos,
        instalacao_padrao=instalacao_padrao,
        agrupamento=agrupamento,
    )


def metodos_instalacao(cfg=None):
    """Lista os métodos de instalação disponíveis (id, rótulo e coeficiente)."""
    cfg = cfg or CFG
    metodos = []
    for chave, coef in cfg.instalacao.items():
        metodos.append({
            "id": chave,
            "rotulo": cfg.instalacao_rotulos.get(chave, chave.replace("_", " ").capitalize()),
            "coef_conveccao": coef,
        })
    return metodos


def fator_agrupamento(n_condutores, cfg=None):
    """Fator de convecção conforme o nº de condutores agrupados lado a lado."""
    cfg = cfg or CFG
    tabela = cfg.agrupamento
    if not tabela:
        return 1.0
    n = max(1, int(n_condutores))
    if n in tabela:
        return tabela[n]
    maior = max(tabela)
    return tabela[maior] if n > maior else 1.0


def coef_conveccao_efetivo(metodo=None, n_condutores=1, cfg=None):
    """Coeficiente de convecção efetivo (W/(m²·°C)) para o método e agrupamento.

    h_efetivo = h(método de instalação) × fator(nº de condutores agrupados)
    """
    cfg = cfg or CFG
    metodo = metodo or cfg.instalacao_padrao
    base = cfg.instalacao.get(metodo)
    if base is None:
        base = cfg.coef_conveccao
    return base * fator_agrupamento(n_condutores, cfg)


def config_para_dict(cfg=None):
    """Serializa a configuração atual (para inspeção/verificação dos números)."""
    cfg = cfg or CFG
    return {
        "fisica": {
            "resistividade_cobre": cfg.resistividade_cobre,
            "temperatura_referencia": cfg.temperatura_referencia,
            "coef_temp_cobre": cfg.coef_temp_cobre,
            "densidade_cobre": cfg.densidade_cobre,
            "calor_especifico_cobre": cfg.calor_especifico_cobre,
            "coef_conveccao": cfg.coef_conveccao,
            "espessura_isolacao": cfg.espessura_isolacao,
        },
        "padroes": dict(cfg.padroes),
        "bitolas_comerciais": list(cfg.bitolas_comerciais),
        "conversao_awg": {str(k): v for k, v in cfg.conversao_awg.items()},
        "capacidade_corrente": {str(k): v for k, v in cfg.capacidade_corrente.items()},
        "instalacao": metodos_instalacao(cfg),
        "instalacao_padrao": cfg.instalacao_padrao,
        "agrupamento": {str(k): v for k, v in cfg.agrupamento.items()},
    }


# Configuração ativa do módulo. Recarregável via carregar_config().
CFG = carregar_config()

# Compatibilidade: nome histórico ainda exportado.
BITOLAS_COMERCIAIS = CFG.bitolas_comerciais


def imprimir_tabela(titulo, cabecalhos, linhas):
    """Imprime tabela ASCII com largura automática por coluna."""
    print(formatar_tabela(titulo, cabecalhos, linhas))


def formatar_tabela(titulo, cabecalhos, linhas):
    """Retorna uma tabela ASCII formatada como texto."""
    larguras = [len(str(coluna)) for coluna in cabecalhos]

    for linha in linhas:
        for i, valor in enumerate(linha):
            larguras[i] = max(larguras[i], len(str(valor)))

    separador = "+-" + "-+-".join("-" * largura for largura in larguras) + "-+"
    cabecalho_formatado = "| " + " | ".join(
        str(coluna).ljust(larguras[i]) for i, coluna in enumerate(cabecalhos)
    ) + " |"

    linhas_saida = [f"\n{titulo}", separador, cabecalho_formatado, separador]

    for linha in linhas:
        linha_formatada = "| " + " | ".join(
            str(valor).ljust(larguras[i]) for i, valor in enumerate(linha)
        ) + " |"
        linhas_saida.append(linha_formatada)

    linhas_saida.append(separador)
    return "\n".join(linhas_saida)


def obter_bitolas_analise_termica(bitola_recomendada):
    """Retorna bitola recomendada e vizinhas imediatas na tabela comercial."""
    tabela = CFG.bitolas_comerciais
    indice = tabela.index(bitola_recomendada)
    indices = [indice - 1, indice, indice + 1]

    bitolas = []
    for i in indices:
        if 0 <= i < len(tabela):
            bitolas.append(tabela[i])

    return bitolas


def resistividade_em_temperatura(temperatura_c, cfg=None):
    """Resistividade do cobre em função da temperatura.

    ρ(T) = ρ₀ · (1 + α₀ · (T − T₀))

    Equivalente a σ(T) = σ₀ / (1 + α₀ · (T − T₀)).
    """
    cfg = cfg or CFG
    delta = temperatura_c - cfg.temperatura_referencia
    return cfg.resistividade_cobre * (1 + cfg.coef_temp_cobre * delta)


def calcular_equilibrio_termico(
    bitola,
    corrente,
    temp_ambiente,
    h_conveccao,
    area_lateral,
    comprimento=1.0,
    temp_limite=None,
    cfg=None,
):
    """Resolve T de regime com realimentação ρ(T) → P → T.

    Usa a forma fechada de ΔT = (K + Kα(T_amb − T₀)) / (1 − Kα), em que
    K é o ΔT com ρ₀. Se Kα ≥ 1 não há equilíbrio finito (runaway térmico);
    nesse caso retorna T = ∞ e estima P com ρ(T_limite) quando informado.
    """
    cfg = cfg or CFG

    if area_lateral <= 0 or h_conveccao <= 0 or bitola <= 0:
        return {
            "temp_regimen": float("inf"),
            "potencia_gerada": 0.0,
            "resistividade_operacao": cfg.resistividade_cobre,
            "iteracoes": 0,
        }

    rho0 = cfg.resistividade_cobre
    alpha = cfg.coef_temp_cobre
    t0 = cfg.temperatura_referencia

    resistencia_ref = (rho0 * comprimento) / bitola
    potencia_ref = (corrente ** 2) * resistencia_ref
    k_delta = potencia_ref / (h_conveccao * area_lateral)
    ka = k_delta * alpha

    if ka >= 1.0:
        temp_para_p = temp_limite if temp_limite is not None else temp_ambiente + 1000
        rho = resistividade_em_temperatura(temp_para_p, cfg)
        potencia = (corrente ** 2) * ((rho * comprimento) / bitola)
        return {
            "temp_regimen": float("inf"),
            "potencia_gerada": potencia,
            "resistividade_operacao": rho,
            "iteracoes": 0,
        }

    delta_t = (k_delta + k_delta * alpha * (temp_ambiente - t0)) / (1 - ka)
    temp_regimen = temp_ambiente + delta_t
    rho = resistividade_em_temperatura(temp_regimen, cfg)
    potencia = (corrente ** 2) * ((rho * comprimento) / bitola)

    return {
        "temp_regimen": temp_regimen,
        "potencia_gerada": potencia,
        "resistividade_operacao": rho,
        "iteracoes": 1,
    }


def classificar_alerta_termico(temp_regimen, temp_maxima):
    """Classifica o alerta térmico com base na fração de T_max atingida."""
    if temp_regimen == float("inf") or temp_maxima <= 0:
        return "ok"

    if temp_regimen >= temp_maxima:
        return "critico"

    pct = 100.0 * temp_regimen / temp_maxima
    if pct >= 90:
        return "critico"
    if pct >= 70:
        return "atencao"
    return "ok"


def parametros_dissipacao(bitola, diametro_externo=None, comprimento=1.0, cfg=None):
    """Estima diâmetro externo e área lateral de dissipação para um trecho de cabo."""
    cfg = cfg or CFG
    if diametro_externo is None:
        diametro_condutor = (4 * bitola / 3.14159) ** 0.5
        diametro_externo = diametro_condutor + cfg.espessura_isolacao

    raio_externo = diametro_externo / 2 / 1000
    area_lateral = 2 * 3.14159 * raio_externo * comprimento
    return diametro_externo, area_lateral


def temperatura_regime_para_bitola(
    bitola,
    corrente,
    temp_ambiente,
    h_conveccao,
    diametro_externo=None,
    temp_limite=None,
    cfg=None,
):
    """Retorna o equilíbrio térmico (T_regime, P, ρ) para uma bitola."""
    _, area_lateral = parametros_dissipacao(bitola, diametro_externo, cfg=cfg)
    return calcular_equilibrio_termico(
        bitola, corrente, temp_ambiente, h_conveccao, area_lateral,
        1.0, temp_limite, cfg,
    )


def _temperatura_para_queda(
    temperatura_operacao,
    bitola,
    corrente,
    temp_ambiente,
    h_conveccao,
    diametro_externo,
    temp_limite,
    cfg,
):
    """Resolve a temperatura usada em ρ(T) para o cálculo de queda."""
    if temperatura_operacao is not None:
        return temperatura_operacao

    if temp_ambiente is not None and h_conveccao is not None and bitola > 0:
        equilibrio = temperatura_regime_para_bitola(
            bitola, corrente, temp_ambiente, h_conveccao,
            diametro_externo, temp_limite, cfg,
        )
        temp = equilibrio["temp_regimen"]
        if temp == float("inf"):
            if temp_limite is not None:
                return temp_limite
            return temp_ambiente + 200.0
        return temp

    return cfg.temperatura_referencia


def calcular_queda_para_bitola(
    bitola,
    comprimento_total,
    corrente,
    tensao,
    temperatura_operacao=None,
    temp_ambiente=None,
    h_conveccao=None,
    diametro_externo=None,
    temp_limite=None,
    cfg=None,
):
    """Calcula queda de tensão para uma bitola específica.

    Usa ρ(T) na temperatura de operação. Se ``temperatura_operacao`` não for
    informada, mas houver parâmetros térmicos, calcula T_regime com
    realimentação ρ(T) → P → T.
    """
    cfg = cfg or CFG
    temp = _temperatura_para_queda(
        temperatura_operacao, bitola, corrente, temp_ambiente,
        h_conveccao, diametro_externo, temp_limite, cfg,
    )
    resistividade = resistividade_em_temperatura(temp, cfg)
    resistencia = (resistividade * comprimento_total) / bitola
    queda_tensao = corrente * resistencia
    queda_percentual = (queda_tensao / tensao) * 100

    return {
        "resistencia_ohm": resistencia,
        "queda_tensao_volts": queda_tensao,
        "queda_tensao_percentual": queda_percentual,
        "temperatura_operacao": temp,
        "resistividade_operacao": resistividade,
    }


def calcular_queda_comparativa(
    bitola,
    comprimento_total,
    corrente,
    tensao,
    temp_ambiente=None,
    h_conveccao=None,
    diametro_externo=None,
    temp_limite=None,
    cfg=None,
):
    """Calcula queda de tensão na largada (T ambiente) e em regime (T final).

    - **Inicial**: ρ(T_ambiente) — cabo frio na partida.
    - **Final**: ρ(T_regime) com realimentação térmica — operação em regime.
    """
    cfg = cfg or CFG
    temp_inicial = temp_ambiente if temp_ambiente is not None else cfg.temperatura_referencia

    queda_inicial = calcular_queda_para_bitola(
        bitola, comprimento_total, corrente, tensao,
        temperatura_operacao=temp_inicial, cfg=cfg,
    )

    if temp_ambiente is not None and h_conveccao is not None:
        queda_final = calcular_queda_para_bitola(
            bitola, comprimento_total, corrente, tensao,
            temp_ambiente=temp_ambiente,
            h_conveccao=h_conveccao,
            diametro_externo=diametro_externo,
            temp_limite=temp_limite,
            cfg=cfg,
        )
    else:
        queda_final = queda_inicial

    return {
        "queda_inicial_volts": queda_inicial["queda_tensao_volts"],
        "queda_inicial_percentual": queda_inicial["queda_tensao_percentual"],
        "queda_final_volts": queda_final["queda_tensao_volts"],
        "queda_final_percentual": queda_final["queda_tensao_percentual"],
        "temperatura_inicial": queda_inicial["temperatura_operacao"],
        "temperatura_final": queda_final["temperatura_operacao"],
        "resistencia_ohm_inicial": queda_inicial["resistencia_ohm"],
        "resistencia_ohm_final": queda_final["resistencia_ohm"],
    }

def mm2_para_awg(mm2):
    """
    Converte bitola de mm² para AWG (American Wire Gauge)
    Args:
        mm2 (float): Bitola em mm²
    Returns:
        int or str: Valor AWG ou a bitola em mm² se não houver equivalente direto
    """
    # Tabela de conversão de mm² para AWG carregada de config.ini
    return CFG.conversao_awg.get(mm2, f"{mm2} mm²")


def calcular_bitola_cb(
    distancia,
    corrente,
    tensao,
    queda_percentual=3,
    temp_ambiente=None,
    coef_conveccao=None,
    diametro_externo=None,
    temp_maxima=None,
):
    """
    Calcula a bitola ideal do cabo baseado em:
    - Distância entre a fonte e o equipamento
    - Corrente do equipamento
    - Tensão do sistema
    - Queda percentual máxima permitida (padrão: 3%)

    Quando ``temp_ambiente`` e ``coef_conveccao`` são informados, o
    dimensionamento e a queda real usam ρ(T_regime) com realimentação térmica.
    Caso contrário, usa ρ₀ a temperatura de referência (20 °C).
    
    Args:
        distancia (float): Distância em metros (ida + volta)
        corrente (float): Corrente em Amperes
        tensao (float): Tensão em Volts (DC)
        queda_percentual (float): Queda de tensão máxima em % (padrão: 3%)
        temp_ambiente (float): Temperatura ambiente para ρ(T) na queda (opcional)
        coef_conveccao (float): Coeficiente h efetivo W/(m²·°C) (opcional)
        diametro_externo (float): Diâmetro externo em mm (opcional)
        temp_maxima (float): T máxima para estimar ρ em runaway térmico (opcional)
    
    Returns:
        dict: Dicionário com resultados do cálculo
    """
    comprimento_total = distancia * 2
    queda_tensao_max = (queda_percentual / 100) * tensao
    usa_rho_t = temp_ambiente is not None and coef_conveccao is not None

    if usa_rho_t:
        resistividade_estimada = resistividade_em_temperatura(temp_ambiente)
    else:
        resistividade_estimada = CFG.resistividade_cobre

    secao_calculada = (resistividade_estimada * comprimento_total * corrente) / queda_tensao_max

    indice_inicial = 0
    for i, bitola in enumerate(CFG.bitolas_comerciais):
        if bitola >= secao_calculada:
            indice_inicial = i
            break
    else:
        indice_inicial = len(CFG.bitolas_comerciais) - 1

    bitola_ideal = None
    queda_escolhida = None
    temperatura_operacao = CFG.temperatura_referencia
    resistividade_operacao = CFG.resistividade_cobre

    for bitola in CFG.bitolas_comerciais[indice_inicial:]:
        if usa_rho_t:
            queda_cmp = calcular_queda_comparativa(
                bitola, comprimento_total, corrente, tensao,
                temp_ambiente=temp_ambiente,
                h_conveccao=coef_conveccao,
                diametro_externo=diametro_externo,
                temp_limite=temp_maxima,
            )
            queda_volts = queda_cmp["queda_final_volts"]
        else:
            queda = calcular_queda_para_bitola(
                bitola, comprimento_total, corrente, tensao,
            )
            queda_volts = queda["queda_tensao_volts"]
            queda_cmp = None

        if queda_volts <= queda_tensao_max:
            bitola_ideal = bitola
            if usa_rho_t:
                queda_escolhida = queda_cmp
                temperatura_operacao = queda_cmp["temperatura_final"]
                resistividade_operacao = resistividade_em_temperatura(
                    temperatura_operacao
                )
            else:
                queda_escolhida = queda
                temperatura_operacao = queda["temperatura_operacao"]
                resistividade_operacao = queda["resistividade_operacao"]
            break

    if bitola_ideal is None:
        bitola_ideal = CFG.bitolas_comerciais[-1]
        if usa_rho_t:
            queda_escolhida = calcular_queda_comparativa(
                bitola_ideal, comprimento_total, corrente, tensao,
                temp_ambiente=temp_ambiente,
                h_conveccao=coef_conveccao,
                diametro_externo=diametro_externo,
                temp_limite=temp_maxima,
            )
            temperatura_operacao = queda_escolhida["temperatura_final"]
            resistividade_operacao = resistividade_em_temperatura(temperatura_operacao)
        else:
            queda_escolhida = calcular_queda_para_bitola(
                bitola_ideal, comprimento_total, corrente, tensao,
            )
            temperatura_operacao = queda_escolhida["temperatura_operacao"]
            resistividade_operacao = queda_escolhida["resistividade_operacao"]

    if usa_rho_t:
        secao_calculada = (
            resistividade_operacao * comprimento_total * corrente
        ) / queda_tensao_max
        queda_inicial_volts = queda_escolhida["queda_inicial_volts"]
        queda_inicial_percentual = queda_escolhida["queda_inicial_percentual"]
        queda_final_volts = queda_escolhida["queda_final_volts"]
        queda_final_percentual = queda_escolhida["queda_final_percentual"]
        resistencia_ohm = queda_escolhida["resistencia_ohm_final"]
    else:
        queda_inicial_volts = queda_escolhida["queda_tensao_volts"]
        queda_inicial_percentual = queda_escolhida["queda_tensao_percentual"]
        queda_final_volts = queda_inicial_volts
        queda_final_percentual = queda_inicial_percentual
        resistencia_ohm = queda_escolhida["resistencia_ohm"]

    bitola_awg = mm2_para_awg(bitola_ideal)

    return {
        "secao_calculada": round(secao_calculada, 2),
        "bitola_recomendada": bitola_ideal,
        "bitola_awg": bitola_awg,
        "comprimento_total": comprimento_total,
        "resistencia_ohm": round(resistencia_ohm, 4),
        "queda_tensao_volts": round(queda_final_volts, 2),
        "queda_tensao_percentual": round(queda_final_percentual, 2),
        "queda_inicial_volts": round(queda_inicial_volts, 2),
        "queda_inicial_percentual": round(queda_inicial_percentual, 2),
        "queda_final_volts": round(queda_final_volts, 2),
        "queda_final_percentual": round(queda_final_percentual, 2),
        "queda_maxima_permitida": queda_tensao_max,
        "queda_maxima_percentual": queda_percentual,
        "temperatura_operacao": round(temperatura_operacao, 2),
        "resistividade_operacao": round(resistividade_operacao, 6),
        "usa_rho_temperatura": usa_rho_t,
    }


def calcular_tempo_aquecimento(bitola, corrente, temp_maxima, temp_ambiente=25, diametro_externo=None, coef_conveccao=None):
    """
    Calcula o tempo para o cabo alcançar a temperatura máxima suportada.
    
    Utiliza modelo de aquecimento com dissipação térmica por convecção.
    
    Args:
        bitola (float): Bitola do cabo em mm²
        corrente (float): Corrente em Amperes
        temp_maxima (float): Temperatura máxima suportada pelo cabo em °C
        temp_ambiente (float): Temperatura ambiente em °C (padrão: 25°C)
        diametro_externo (float): Diâmetro externo do cabo em mm (opcional)
        coef_conveccao (float): Coeficiente de convecção efetivo W/(m²·°C).
            Se None, usa o valor de config.ini ([fisica] coef_conveccao). Passe
            o valor de coef_conveccao_efetivo() para considerar o método de
            instalação e o agrupamento de condutores.
    
    Returns:
        dict: Dicionário com resultados do cálculo térmico
    """
    
    # Propriedades do cobre (config.ini)
    densidade_cobre = CFG.densidade_cobre  # kg/m³
    calor_especifico_cobre = CFG.calor_especifico_cobre  # J/(kg·°C)
    
    # Se não informar o diâmetro, estimar baseado na bitola
    if diametro_externo is None:
        # Estimativa: d = √(4×A/π) para condutor equivalente
        diametro_condutor = (4 * bitola / 3.14159) ** 0.5
        # Adicionar isolação (espessura típica 1-1.5mm)
        diametro_externo = diametro_condutor + CFG.espessura_isolacao
    
    # Calcular para 1 metro de cabo
    comprimento = 1.0  # metro
    
    # Raio externo em metros (para cálculo de área de dissipação)
    raio_externo = diametro_externo / 2 / 1000  # converter mm para m
    
    # Área de superfície lateral do cilindro (área para dissipação térmica)
    area_lateral = 2 * 3.14159 * raio_externo * comprimento
    
    # Volume e massa do cobre no trecho de 1m
    area_cobre = bitola / 1e6  # converter mm² para m²
    volume_cobre = area_cobre * comprimento
    massa_cobre = volume_cobre * densidade_cobre
    
    # Coeficiente de transferência térmica por convecção efetivo.
    h_conveccao = coef_conveccao if coef_conveccao is not None else CFG.coef_conveccao  # W/(m²·°C)

    # Equilíbrio térmico com ρ(T): quanto mais quente, maior ρ e maior P dissipada.
    equilibrio = calcular_equilibrio_termico(
        bitola, corrente, temp_ambiente, h_conveccao, area_lateral,
        comprimento, temp_maxima, CFG,
    )
    temp_regimen = equilibrio["temp_regimen"]
    potencia_gerada = equilibrio["potencia_gerada"]
    resistividade_operacao = equilibrio["resistividade_operacao"]
    
    # Capacidade térmica total do cobre
    capacidade_termica = massa_cobre * calor_especifico_cobre  # J/°C

    # Diferença de temperatura a atingir
    delta_temp = temp_maxima - temp_ambiente

    # Margem até o limite de isolação (negativa se T_regime > T_max)
    if temp_regimen == float("inf"):
        margem_termica = float("-inf")
        pct_limite_termico = float("inf")
    else:
        margem_termica = temp_maxima - temp_regimen
        pct_limite_termico = 100.0 * temp_regimen / temp_maxima if temp_maxima > 0 else float("inf")
    
    # Cálculo do tempo até atingir temperatura máxima
    if temp_regimen <= temp_maxima:
        # O cabo nunca atingirá a temperatura máxima
        # Usar modelo exponencial: T(t) = T_amb + (P/hA) × (1 - e^(-t/τ))
        tau = capacidade_termica / (h_conveccao * area_lateral)  # constante de tempo
        
        # Isolando t: t = -τ × ln(1 - ΔT/ΔT_regime)
        delta_regime = temp_regimen - temp_ambiente
        razao = delta_temp / delta_regime
        
        if razao >= 1.0:
            tempo_segundos = float('inf')
        elif razao <= 0:
            tempo_segundos = 0
        else:
            tempo_segundos = -tau * (1 - razao)
    else:
        # O cabo ultrapassará a temperatura máxima
        # Aquecimento inicial com aproximação linear
        # Quando a taxa é aproximadamente constante: dT/dt ≈ P / C_t
        # t ≈ C_t × ΔT / P (modelo linear)
        if potencia_gerada > 0:
            tempo_segundos = (capacidade_termica * delta_temp) / potencia_gerada
        else:
            tempo_segundos = float('inf')
    
    # Converter para minutos e horas
    if tempo_segundos == float('inf'):
        tempo_minutos = float('inf')
        tempo_horas = float('inf')
    else:
        tempo_minutos = tempo_segundos / 60
        tempo_horas = tempo_minutos / 60
    
    # Formatação para exibição
    if tempo_segundos == float('inf'):
        tempo_str_s = "Nunca atingirá"
        tempo_str_m = "Nunca atingirá"
        tempo_str_h = "Nunca atingirá"
    else:
        tempo_str_s = f"{tempo_segundos:.1f}"
        tempo_str_m = f"{tempo_minutos:.2f}"
        tempo_str_h = f"{tempo_horas:.4f}"
    
    return {
        'potencia_gerada_watts': round(potencia_gerada, 2),
        'temp_regimen_celsius': round(temp_regimen, 2) if temp_regimen != float('inf') else "Infinita",
        'capacidade_termica_J_C': round(capacidade_termica, 3),
        'area_dissipacao_m2': round(area_lateral, 6),
        'tempo_segundos': tempo_str_s,
        'tempo_minutos': tempo_str_m,
        'tempo_horas': tempo_str_h,
        'diametro_externo_mm': round(diametro_externo, 2),
        'massa_cobre_kg': round(massa_cobre, 6),
        'delta_temp': delta_temp,
        'temp_regimen_value': temp_regimen,
        'resistividade_operacao': round(resistividade_operacao, 6),
        'margem_termica_celsius': round(margem_termica, 2) if margem_termica not in (float('inf'), float('-inf')) else margem_termica,
        'pct_limite_termico': round(pct_limite_termico, 1) if pct_limite_termico != float('inf') else pct_limite_termico,
        'alerta_termico': classificar_alerta_termico(temp_regimen, temp_maxima),
        'iteracoes_rho_t': equilibrio["iteracoes"],
    }


def tabela_bitolas():
    """Exibe uma tabela de referência de bitolas comerciais e suas capacidades"""
    print(obter_tabela_bitolas_texto())


def obter_tabela_bitolas_texto(linhas=None):
    """Retorna em texto a tabela de referência de bitolas."""
    resistividade = CFG.resistividade_cobre

    if linhas is None:
        linhas = []
        for bitola, corrente_max in CFG.capacidade_corrente.items():
            resistencia_km = (resistividade / bitola) * 1000
            awg = mm2_para_awg(bitola)
            linhas.append([
                f"{bitola:.1f}",
                str(awg),
                str(corrente_max),
                f"{resistencia_km:.4f}"
            ])

    tabela = formatar_tabela(
        "TABELA DE REFERENCIA - BITOLAS COMERCIAIS E CAPACIDADE DE CORRENTE",
        ["Bitola (mm2)", "AWG", "Corrente Max (A)*", "Resistencia/km (Ohm)"],
        linhas
    )

    return f"{tabela}\n* Valores aproximados para temperatura de 30C\n"


def _fmt(valor, casas=2):
    """Formata número para exibição no memorial."""
    if valor == float("inf"):
        return "∞"
    if isinstance(valor, float):
        return f"{valor:.{casas}f}".rstrip("0").rstrip(".")
    return str(valor)


def gerar_memorial_calculo(entradas, resultado, h_efetivo, cfg=None):
    """Monta memorial de cálculo estruturado para validação pelo usuário."""
    cfg = cfg or CFG
    distancia = entradas["distancia"]
    corrente = entradas["corrente"]
    tensao = entradas["tensao"]
    queda_pct = entradas["queda_percentual"]
    temp_amb = entradas["temp_amb"]
    temp_max = entradas["temp_max"]
    diametro_in = entradas.get("diametro")
    metodo_id = entradas.get("metodo_instalacao", cfg.instalacao_padrao)
    metodo_rotulo = cfg.instalacao_rotulos.get(metodo_id, metodo_id)
    n_cond = entradas.get("n_condutores", 1)

    comprimento = resultado["comprimento_total"]
    v_queda_max = resultado["queda_maxima_permitida"]
    bitola = resultado["bitola_recomendada"]
    usa_rho_t = resultado.get("usa_rho_temperatura", True)

    rho0 = cfg.resistividade_cobre
    t0 = cfg.temperatura_referencia
    alpha = cfg.coef_temp_cobre

    secoes = []

    secoes.append({
        "id": "entradas",
        "titulo": "1. Dados de entrada",
        "itens": [
            {"rotulo": "Distância fonte → equipamento", "valor": f"{_fmt(distancia)} m (ida)"},
            {"rotulo": "Corrente de operação", "valor": f"{_fmt(corrente)} A"},
            {"rotulo": "Tensão do sistema", "valor": f"{_fmt(tensao)} V DC"},
            {"rotulo": "Queda de tensão máxima", "valor": f"{_fmt(queda_pct)} %"},
            {"rotulo": "Temperatura ambiente", "valor": f"{_fmt(temp_amb)} °C"},
            {"rotulo": "Temperatura máxima do cabo", "valor": f"{_fmt(temp_max)} °C"},
            {"rotulo": "Método de instalação", "valor": metodo_rotulo},
            {"rotulo": "Condutores agrupados", "valor": str(n_cond)},
            {"rotulo": "Coeficiente de convecção efetivo", "valor": f"{_fmt(h_efetivo)} W/(m²·°C)"},
            {
                "rotulo": "Diâmetro externo",
                "valor": f"{_fmt(diametro_in)} mm" if diametro_in else "estimado a partir da bitola",
            },
        ],
    })

    secoes.append({
        "id": "constantes",
        "titulo": "2. Constantes físicas (config.ini)",
        "itens": [
            {"rotulo": "ρ₀ — resistividade do cobre", "valor": f"{_fmt(rho0, 4)} Ω·mm²/m"},
            {"rotulo": "T₀ — temperatura de referência", "valor": f"{_fmt(t0)} °C"},
            {"rotulo": "α₀ — coeficiente de temperatura", "valor": f"{_fmt(alpha, 5)} /°C"},
            {"rotulo": "Fórmula ρ(T)", "valor": "ρ(T) = ρ₀ · (1 + α₀ · (T − T₀))"},
        ],
    })

    passos_dim = [
        {
            "titulo": "Comprimento total do circuito",
            "formula": "L = 2 × d",
            "calculo": f"L = 2 × {_fmt(distancia)} = {_fmt(comprimento)} m",
            "nota": "Considera ida e volta.",
        },
        {
            "titulo": "Queda de tensão máxima permitida",
            "formula": "V_queda_max = (queda% / 100) × V",
            "calculo": (
                f"V_queda_max = ({_fmt(queda_pct)} / 100) × {_fmt(tensao)} "
                f"= {_fmt(v_queda_max)} V"
            ),
        },
    ]

    if usa_rho_t:
        rho_est = resistividade_em_temperatura(temp_amb, cfg)
        secao_est = (rho_est * comprimento * corrente) / v_queda_max
        passos_dim.extend([
            {
                "titulo": "Estimativa de seção (ρ na largada)",
                "formula": "S ≈ (ρ(T_amb) × L × I) / V_queda_max",
                "calculo": (
                    f"ρ({_fmt(temp_amb)} °C) = {_fmt(rho_est, 6)} Ω·mm²/m → "
                    f"S ≈ {_fmt(secao_est)} mm²"
                ),
            },
            {
                "titulo": "Critério de seleção da bitola comercial",
                "formula": "Vdrop_T.final ≤ V_queda_max",
                "calculo": (
                    "Para cada bitola candidata, calcula-se T_regime com ρ(T) e "
                    "verifica-se a queda em regime até a primeira que atende o limite."
                ),
            },
        ])
    else:
        passos_dim.append({
            "titulo": "Seção teórica mínima",
            "formula": "S = (ρ₀ × L × I) / V_queda_max",
            "calculo": f"S = {_fmt(resultado['secao_calculada'])} mm²",
        })

    passos_dim.append({
        "titulo": "Bitola comercial adotada",
        "formula": "primeira bitola da tabela que atende o critério",
        "calculo": (
            f"{_fmt(bitola)} mm² (AWG {resultado['bitola_awg']}) — "
            f"seção calculada: {_fmt(resultado['secao_calculada'])} mm²"
        ),
    })

    secoes.append({
        "id": "dimensionamento",
        "titulo": "3. Dimensionamento por queda de tensão",
        "passos": passos_dim,
    })

    queda = calcular_queda_comparativa(
        bitola, comprimento, corrente, tensao,
        temp_ambiente=temp_amb, h_conveccao=h_efetivo,
        diametro_externo=diametro_in, temp_limite=temp_max, cfg=cfg,
    )
    rho_ini = resistividade_em_temperatura(queda["temperatura_inicial"], cfg)
    rho_fin = resistividade_em_temperatura(queda["temperatura_final"], cfg)
    r_ini = queda["resistencia_ohm_inicial"]
    r_fin = queda["resistencia_ohm_final"]

    passos_queda = [
        {
            "titulo": "Vdrop inicial (cabo frio, T ambiente)",
            "formula": "R = ρ(T_amb) × L / S  →  V = I × R",
            "calculo": (
                f"ρ({_fmt(queda['temperatura_inicial'])} °C) = {_fmt(rho_ini, 6)} Ω·mm²/m · "
                f"R = {_fmt(r_ini, 6)} Ω · V = {_fmt(corrente)} × {_fmt(r_ini, 6)} = "
                f"{_fmt(queda['queda_inicial_volts'])} V ({_fmt(queda['queda_inicial_percentual'])} %)"
            ),
        },
        {
            "titulo": "Vdrop em regime (T final com ρ(T))",
            "formula": "R = ρ(T_regime) × L / S  →  V = I × R",
            "calculo": (
                f"ρ({_fmt(queda['temperatura_final'])} °C) = {_fmt(rho_fin, 6)} Ω·mm²/m · "
                f"R = {_fmt(r_fin, 6)} Ω · V = {_fmt(queda['queda_final_volts'])} V "
                f"({_fmt(queda['queda_final_percentual'])} %)"
            ),
            "nota": f"Limite: {_fmt(queda_pct)} % — status: {'OK' if queda['queda_final_percentual'] <= queda_pct else 'ACIMA DO LIMITE'}.",
        },
    ]

    secoes.append({
        "id": "queda",
        "titulo": "4. Queda de tensão — bitola recomendada",
        "passos": passos_queda,
    })

    diametro_ext, area_lat = parametros_dissipacao(bitola, diametro_in, cfg=cfg)
    equilibrio = temperatura_regime_para_bitola(
        bitola, corrente, temp_amb, h_efetivo, diametro_in, temp_max, cfg,
    )
    termico = calcular_tempo_aquecimento(
        bitola, corrente, temp_max, temp_amb, diametro_in, h_efetivo,
    )

    rho_ref = (rho0 * 1.0) / bitola
    p_ref = (corrente ** 2) * rho_ref
    k_delta = p_ref / (h_efetivo * area_lat) if area_lat > 0 else 0
    ka = k_delta * alpha

    passos_term = [
        {
            "titulo": "Geometria do cabo (trecho de 1 m)",
            "formula": "área lateral ≈ π × D_ext × L",
            "calculo": (
                f"D_ext ≈ {_fmt(diametro_ext)} mm · área dissipação ≈ "
                f"{_fmt(area_lat, 6)} m²"
            ),
        },
        {
            "titulo": "Potência Joule de referência (ρ₀)",
            "formula": "P₀ = I² × (ρ₀ / S)",
            "calculo": f"P₀ ≈ {_fmt(p_ref)} W/m",
        },
    ]

    if equilibrio["temp_regimen"] == float("inf"):
        passos_term.append({
            "titulo": "Equilíbrio térmico",
            "formula": "Kα ≥ 1 → sem T de regime finita (runaway)",
            "calculo": f"Kα = {_fmt(ka, 4)} — cabo continua aquecendo sem estabilizar.",
        })
    else:
        passos_term.extend([
            {
                "titulo": "Incremento térmico com ρ(T)",
                "formula": "ΔT = (K + Kα(T_amb − T₀)) / (1 − Kα)",
                "calculo": (
                    f"K = {_fmt(k_delta, 2)} °C · Kα = {_fmt(ka, 4)} · "
                    f"ΔT = {_fmt(equilibrio['temp_regimen'] - temp_amb, 2)} °C"
                ),
            },
            {
                "titulo": "Temperatura de regime",
                "formula": "T_regime = T_amb + ΔT",
                "calculo": (
                    f"T_regime = {_fmt(temp_amb)} + {_fmt(equilibrio['temp_regimen'] - temp_amb, 2)} "
                    f"= {_fmt(equilibrio['temp_regimen'])} °C"
                ),
                "nota": (
                    f"Margem até T_max: {_fmt(termico['margem_termica_celsius'])} °C · "
                    f"P em regime: {_fmt(termico['potencia_gerada_watts'])} W/m"
                ),
            },
        ])

    secoes.append({
        "id": "termico",
        "titulo": "5. Análise térmica — bitola recomendada",
        "passos": passos_term,
    })

    comparativo = []
    for b in obter_bitolas_analise_termica(bitola):
        q = calcular_queda_comparativa(
            b, comprimento, corrente, tensao,
            temp_ambiente=temp_amb, h_conveccao=h_efetivo,
            diametro_externo=diametro_in, temp_limite=temp_max, cfg=cfg,
        )
        t = calcular_tempo_aquecimento(
            b, corrente, temp_max, temp_amb, diametro_in, h_efetivo,
        )
        comparativo.append({
            "bitola": f"{_fmt(b)} mm²",
            "awg": str(mm2_para_awg(b)),
            "vdrop_ini": f"{_fmt(q['queda_inicial_volts'])} V ({_fmt(q['queda_inicial_percentual'])} %)",
            "vdrop_fin": f"{_fmt(q['queda_final_volts'])} V ({_fmt(q['queda_final_percentual'])} %)",
            "temp_regime": str(t["temp_regimen_celsius"]),
            "recomendada": b == bitola,
        })

    secoes.append({
        "id": "comparativo",
        "titulo": "6. Comparativo — bitolas vizinhas",
        "tabela": comparativo,
    })

    diagramas = [
        {
            "id": "fluxo_geral",
            "titulo": "Visão geral do fluxo de cálculo",
            "descricao": (
                "As entradas alimentam o dimensionamento e a análise térmica. "
                "A queda em regime (Vdrop T. final) usa ρ(T_regime) e define se a bitola atende o limite."
            ),
            "mermaid": (
                "flowchart TD\n"
                "    subgraph entradas [Entradas do usuario]\n"
                "        IN1[Distancia corrente tensao]\n"
                "        IN2[Temp ambiente e instalacao]\n"
                "    end\n"
                "    subgraph dimensionamento [Dimensionamento]\n"
                "        D1[L = 2 x distancia]\n"
                "        D2[Bitola com Vdrop T.final dentro do limite]\n"
                "    end\n"
                "    subgraph vdropFluxo [Queda de tensao]\n"
                "        V1[Vdrop inicial: rho a T amb]\n"
                "        V2[Vdrop T.final: rho a T regime]\n"
                "    end\n"
                "    subgraph termicoLoop [Realimentacao termica]\n"
                "        T1[rho T] --> T2[P = I2 x R]\n"
                "        T2 --> T3[T_regime = T_amb + P/hA]\n"
                "        T3 --> T1\n"
                "    end\n"
                "    entradas --> dimensionamento\n"
                "    dimensionamento --> vdropFluxo\n"
                "    entradas --> termicoLoop\n"
                "    termicoLoop --> vdropFluxo"
            ),
        },
        {
            "id": "realimentacao",
            "titulo": "Realimentação térmica ρ(T)",
            "descricao": (
                "Comparacao conceitual: sem ρ(T) a temperatura é subestimada; "
                "com realimentação, ρ sobe com T, aumenta P e converge em T_regime."
            ),
            "mermaid": (
                "flowchart TD\n"
                "    subgraph modeloFixo [Sem rho T na queda]\n"
                "        A1[rho = rho0 fixo] --> B1[P = I2R]\n"
                "        B1 --> C1[T_regime = T_amb + P/hA]\n"
                "    end\n"
                "    subgraph modeloRealim [Modelo adotado]\n"
                "        A2[T de operacao] --> B2[rho T]\n"
                "        B2 --> C2[P = I2 x rho T x L/S]\n"
                "        C2 --> D2[T_novo = T_amb + P/hA]\n"
                "        D2 --> E2{Convergiu?}\n"
                "        E2 -->|nao| A2\n"
                "        E2 -->|sim| F2[T_regime e Vdrop T.final]\n"
                "    end"
            ),
        },
    ]

    return {
        "titulo": "Memorial de Cálculo — Bitola de Cabo DC",
        "diagramas": diagramas,
        "secoes": secoes,
    }


def salvar_relatorio_txt(
    dados_entrada,
    resultado_principal,
    linhas_principal,
    linhas_termicas,
    incluir_tabela_referencia=False,
    caminho_arquivo=None
):
    """Salva relatório completo em arquivo TXT e retorna o caminho."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not caminho_arquivo:
        caminho_arquivo = f"relatorio_bitola_dc_{timestamp}.txt"

    metodo_id = dados_entrada.get('metodo_instalacao', CFG.instalacao_padrao)
    metodo_rotulo = CFG.instalacao_rotulos.get(metodo_id, metodo_id)
    n_condutores = dados_entrada.get('n_condutores', 1)
    h_efetivo = coef_conveccao_efetivo(metodo_id, n_condutores)

    secao_entrada = [
        "DADOS DE ENTRADA",
        f"- Distancia (m): {dados_entrada['distancia']}",
        f"- Corrente (A): {dados_entrada['corrente']}",
        f"- Tensao (V): {dados_entrada['tensao']}",
        f"- Queda maxima permitida (%): {dados_entrada['queda_percentual']}",
        f"- Temperatura ambiente (C): {dados_entrada['temp_amb']}",
        f"- Temperatura maxima do cabo (C): {dados_entrada['temp_max']}",
        f"- Diametro externo (mm): {dados_entrada['diametro'] if dados_entrada['diametro'] else 'estimado'}",
        f"- Metodo de instalacao: {metodo_rotulo}",
        f"- Condutores agrupados: {n_condutores}",
        f"- Coef. conveccao efetivo (W/m2.C): {h_efetivo:.2f}",
        ""
    ]

    tabela_principal = formatar_tabela(
        "RESULTADO PRINCIPAL - DIMENSIONAMENTO",
        [
            "Secao calc. (mm2)", "Bitola recomendada", "AWG",
            "Vdrop inicial (V)", "Vdrop inicial (%)",
            "Vdrop T.final (V)", "Vdrop T.final (%)",
            "Limite (%)", "Status",
        ],
        linhas_principal
    )

    tabela_termica = formatar_tabela(
        "ANALISE TERMICA COMPARATIVA (AWG ANTERIOR, RECOMENDADO E PROXIMO)",
        [
            "Bitola (mm2)", "AWG",
            "Vdrop inicial (V)", "Vdrop inicial (%)",
            "Vdrop T.final (V)", "Vdrop T.final (%)",
            "P. Joule (W/m)", "Temp. regime (C)", "Margem termica (C)",
            "Tempo ate Tmax (min)", "Status queda",
        ],
        linhas_termicas
    )

    secao_resumo = [
        "RESUMO EXECUTIVO",
        f"- Bitola recomendada: {resultado_principal['bitola_recomendada']:.2f} mm2 (AWG {resultado_principal['bitola_awg']})",
        f"- Comprimento total considerado (ida e volta): {resultado_principal['comprimento_total']:.2f} m",
        f"- Vdrop inicial (largada): {resultado_principal['queda_inicial_volts']:.2f} V ({resultado_principal['queda_inicial_percentual']:.2f}%)",
        f"- Vdrop em regime (T final): {resultado_principal['queda_final_volts']:.2f} V ({resultado_principal['queda_final_percentual']:.2f}%)",
        f"- Queda limite: {resultado_principal['queda_maxima_permitida']:.2f} V ({resultado_principal['queda_maxima_percentual']:.2f}%)",
        ""
    ]

    conteudo = []
    conteudo.append("=" * 90)
    conteudo.append("RELATORIO COMPLETO - CALCULO DE BITOLA DE CABO DC")
    conteudo.append(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    conteudo.append("=" * 90)
    conteudo.append("")
    conteudo.extend(secao_entrada)
    conteudo.extend(secao_resumo)
    conteudo.append(tabela_principal)
    conteudo.append("")
    conteudo.append(tabela_termica)

    if incluir_tabela_referencia:
        conteudo.append("")
        conteudo.append(obter_tabela_bitolas_texto())

    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(conteudo) + "\n")

    return caminho_arquivo


def _normalizar_numero_para_nome(valor):
    """Normaliza número para uso em nome de arquivo."""
    if isinstance(valor, float):
        texto = f"{valor:.3f}".rstrip("0").rstrip(".")
    else:
        texto = str(valor)
    return texto.replace("-", "m").replace(".", "p")


def gerar_nome_relatorio_por_inputs(dados_entrada, incluir_tabela_referencia=False):
    """Gera nome de arquivo estável baseado nos inputs e configuração de relatório."""
    base_legivel = (
        "relatorio_bitola_dc"
        f"_d{_normalizar_numero_para_nome(dados_entrada['distancia'])}"
        f"_i{_normalizar_numero_para_nome(dados_entrada['corrente'])}"
        f"_v{_normalizar_numero_para_nome(dados_entrada['tensao'])}"
        f"_q{_normalizar_numero_para_nome(dados_entrada['queda_percentual'])}"
        f"_ta{_normalizar_numero_para_nome(dados_entrada['temp_amb'])}"
        f"_tm{_normalizar_numero_para_nome(dados_entrada['temp_max'])}"
        f"_de{_normalizar_numero_para_nome(dados_entrada['diametro']) if dados_entrada['diametro'] is not None else 'estimado'}"
        f"_ref{'sim' if incluir_tabela_referencia else 'nao'}"
    )

    assinatura = "|".join([
        str(dados_entrada['distancia']),
        str(dados_entrada['corrente']),
        str(dados_entrada['tensao']),
        str(dados_entrada['queda_percentual']),
        str(dados_entrada['temp_amb']),
        str(dados_entrada['temp_max']),
        str(dados_entrada['diametro']),
        str(dados_entrada.get('metodo_instalacao', CFG.instalacao_padrao)),
        str(dados_entrada.get('n_condutores', 1)),
        str(incluir_tabela_referencia)
    ])
    sufixo_hash = hashlib.sha1(assinatura.encode("utf-8")).hexdigest()[:8]

    return f"{base_legivel}_{sufixo_hash}.txt"


def main():
    """Função principal com interface interativa"""
    
    print("\n" + "="*80)
    print("CALCULADORA DE BITOLA IDEAL PARA CABO DC")
    print("="*80 + "\n")
    
    padroes = CFG.padroes
    try:
        # Entradas principais
        distancia_input = input(f"Distância entre a fonte e o equipamento (metros) [padrão {padroes['distancia']:g}]: ").strip()
        distancia = float(distancia_input) if distancia_input else padroes['distancia']

        corrente_input = input(f"Corrente do equipamento (Amperes) [padrão {padroes['corrente']:g}]: ").strip()
        corrente = float(corrente_input) if corrente_input else padroes['corrente']

        tensao_input = input(f"Tensão do sistema (Volts DC) [padrão {padroes['tensao']:g}]: ").strip()
        tensao = float(tensao_input) if tensao_input else padroes['tensao']

        queda_input = input(f"Queda de tensão máxima permitida em % (padrão {padroes['queda_percentual']:g}%): ")
        queda_percentual = float(queda_input) if queda_input else padroes['queda_percentual']

        # Entradas térmicas já no mesmo fluxo
        temp_max_input = input(f"Temperatura máxima suportada pelo cabo (°C) [padrão {padroes['temp_max']:g}]: ").strip()
        temp_max = float(temp_max_input) if temp_max_input else padroes['temp_max']

        temp_amb_input = input(f"Temperatura ambiente (°C) [padrão {padroes['temp_amb']:g}]: ").strip()
        temp_amb = float(temp_amb_input) if temp_amb_input else padroes['temp_amb']

        diametro_input = input("Diâmetro externo do cabo em mm (opcional, Enter para estimar): ")
        diametro = float(diametro_input) if diametro_input else None

        dados_entrada = {
            'distancia': distancia,
            'corrente': corrente,
            'tensao': tensao,
            'queda_percentual': queda_percentual,
            'temp_amb': temp_amb,
            'temp_max': temp_max,
            'diametro': diametro
        }

        salvar_txt = input("Deseja salvar um relatorio completo em TXT? (s/n): ").strip().lower()
        incluir_ref_txt = False
        caminho_relatorio_predefinido = None

        if salvar_txt == 's':
            incluir_ref_txt = input("Incluir tabela de referencia no TXT? (s/n): ").strip().lower() == 's'
            caminho_relatorio_predefinido = gerar_nome_relatorio_por_inputs(dados_entrada, incluir_ref_txt)

            if os.path.exists(caminho_relatorio_predefinido):
                print(f"\nRelatorio ja existente para essa combinacao de inputs: {caminho_relatorio_predefinido}")
                reutilizar = input("Deseja reutilizar e encerrar sem recalcular? (s/n): ").strip().lower()
                if reutilizar == 's':
                    print("\nNenhum calculo executado. Relatorio existente reaproveitado.")
                    return

        h_efetivo = coef_conveccao_efetivo(
            dados_entrada.get('metodo_instalacao', CFG.instalacao_padrao),
            dados_entrada.get('n_condutores', 1),
        )

        # Cálculo principal de bitola
        resultado = calcular_bitola_cb(
            distancia, corrente, tensao, queda_percentual,
            temp_ambiente=temp_amb, coef_conveccao=h_efetivo,
            diametro_externo=diametro, temp_maxima=temp_max,
        )

        # Tabela resumo do cálculo principal
        status_queda = "ADEQUADA" if resultado['queda_final_percentual'] <= resultado['queda_maxima_percentual'] else "ACIMA DO LIMITE"
        linhas_principal = [[
            f"{resultado['secao_calculada']:.2f}",
            f"{resultado['bitola_recomendada']:.2f}",
            f"{resultado['bitola_awg']}",
            f"{resultado['queda_inicial_volts']:.2f}",
            f"{resultado['queda_inicial_percentual']:.2f}",
            f"{resultado['queda_final_volts']:.2f}",
            f"{resultado['queda_final_percentual']:.2f}",
            f"{resultado['queda_maxima_percentual']:.2f}",
            status_queda
        ]]

        imprimir_tabela(
            "RESULTADO PRINCIPAL - DIMENSIONAMENTO",
            [
                "Secao calc. (mm2)", "Bitola recomendada", "AWG",
                "Vdrop inicial (V)", "Vdrop inicial (%)",
                "Vdrop T.final (V)", "Vdrop T.final (%)",
                "Limite (%)", "Status",
            ],
            linhas_principal
        )

        # Análise térmica comparativa: AWG anterior, recomendado e próximo
        bitolas_analise = obter_bitolas_analise_termica(resultado['bitola_recomendada'])
        linhas_termicas = []

        for bitola in bitolas_analise:
            awg = mm2_para_awg(bitola)
            queda = calcular_queda_comparativa(
                bitola, resultado['comprimento_total'], corrente, tensao,
                temp_ambiente=temp_amb, h_conveccao=h_efetivo,
                diametro_externo=diametro, temp_limite=temp_max,
            )
            termico = calcular_tempo_aquecimento(
                bitola, corrente, temp_max, temp_amb, diametro, h_efetivo,
            )

            if queda['queda_final_percentual'] <= resultado['queda_maxima_percentual']:
                status_termico = "OK"
            else:
                status_termico = "QUEDA ALTA"

            margem = termico["margem_termica_celsius"]
            margem_txt = "—" if isinstance(margem, float) and margem == float("-inf") else f"{margem:.1f}"

            linhas_termicas.append([
                f"{bitola:.2f}",
                f"{awg}",
                f"{queda['queda_inicial_volts']:.2f}",
                f"{queda['queda_inicial_percentual']:.2f}",
                f"{queda['queda_final_volts']:.2f}",
                f"{queda['queda_final_percentual']:.2f}",
                f"{termico['potencia_gerada_watts']:.2f}",
                f"{termico['temp_regimen_celsius']}",
                margem_txt,
                f"{termico['tempo_minutos']}",
                status_termico
            ])

        imprimir_tabela(
            "ANALISE TERMICA COMPARATIVA (AWG ANTERIOR, RECOMENDADO E PROXIMO)",
            [
                "Bitola (mm2)", "AWG",
                "Vdrop inicial (V)", "Vdrop inicial (%)",
                "Vdrop T.final (V)", "Vdrop T.final (%)",
                "P. Joule (W/m)", "Temp. regime (C)", "Margem termica (C)",
                "Tempo ate Tmax (min)", "Status queda",
            ],
            linhas_termicas
        )

        print(f"\nParametros termicos: Tamb={temp_amb}C | Tmax={temp_max}C | Diametro externo={diametro if diametro else 'estimado'}")
        
        print("\n" + "="*80 + "\n")
        
        # Mostrar tabela de referência
        mostrar_tabela = input("Deseja ver a tabela de referência de bitolas? (s/n): ")
        if mostrar_tabela.lower() == 's':
            tabela_bitolas()

        if salvar_txt == 's':
            caminho_relatorio = salvar_relatorio_txt(
                dados_entrada=dados_entrada,
                resultado_principal=resultado,
                linhas_principal=linhas_principal,
                linhas_termicas=linhas_termicas,
                incluir_tabela_referencia=incluir_ref_txt,
                caminho_arquivo=caminho_relatorio_predefinido
            )
            print(f"\nRelatorio TXT salvo em: {caminho_relatorio}")
    
    except ValueError:
        print("\n✗ ERRO: Entrada inválida. Por favor, use valores numéricos.")
    except Exception as e:
        print(f"\n✗ ERRO: {e}")


if __name__ == "__main__":
    main()
