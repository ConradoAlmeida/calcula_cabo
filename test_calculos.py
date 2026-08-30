# -*- coding: utf-8 -*-
"""Testes de verificação dos cálculos e do carregamento de config.ini."""

import textwrap

import pytest

import calcular_bitola_cabo_dc as m


# --------------------------------------------------------------------------
# Dimensionamento (queda de tensão) — conferido à mão
# --------------------------------------------------------------------------
def test_dimensionamento_exemplo_readme():
    """7 m, 7 A, 12 V DC, 5%: S = (0.0175 * 14 * 7) / 0.6 = 2.86 mm² -> 4.0 mm²."""
    r = m.calcular_bitola_cb(distancia=7, corrente=7, tensao=12, queda_percentual=5)
    assert r["secao_calculada"] == 2.86
    assert r["bitola_recomendada"] == 4.0
    assert r["bitola_awg"] == 12
    assert r["queda_tensao_volts"] == 0.43
    assert r["queda_tensao_percentual"] == 3.57


def test_queda_para_bitola_bate_com_formula():
    """R = rho*L/S; V = I*R. Para 4 mm², 14 m, 7 A: R=0.061250, V=0.4288 V."""
    q = m.calcular_queda_para_bitola(bitola=4.0, comprimento_total=14.0, corrente=7, tensao=12)
    assert q["resistencia_ohm"] == pytest.approx(0.06125, abs=1e-5)
    assert q["queda_tensao_volts"] == pytest.approx(0.42875, abs=1e-5)
    assert q["queda_tensao_percentual"] == pytest.approx(3.5729, abs=1e-3)


def test_queda_comparativa_final_maior_que_inicial():
    """Com aquecimento, Vdrop em regime deve ser maior que na largada."""
    q = m.calcular_queda_comparativa(
        bitola=4.0, comprimento_total=2.0, corrente=49, tensao=12,
        temp_ambiente=25, h_conveccao=m.CFG.coef_conveccao,
    )
    assert q["queda_final_volts"] > q["queda_inicial_volts"]
    assert q["queda_final_percentual"] > q["queda_inicial_percentual"]


def test_bitola_selecionada_e_sempre_para_cima():
    r = m.calcular_bitola_cb(distancia=1, corrente=1, tensao=12, queda_percentual=3)
    assert r["bitola_recomendada"] >= r["secao_calculada"]


def test_dimensionamento_com_rho_t_pode_aumentar_bitola():
    """Com ρ(T), a bitola pode subir em relação ao cálculo só a 20 °C."""
    r20 = m.calcular_bitola_cb(distancia=1, corrente=49, tensao=12, queda_percentual=5)
    r_t = m.calcular_bitola_cb(
        distancia=1, corrente=49, tensao=12, queda_percentual=5,
        temp_ambiente=25, coef_conveccao=m.CFG.coef_conveccao, temp_maxima=200,
    )
    assert r_t["bitola_recomendada"] >= r20["bitola_recomendada"]
    assert r_t["queda_final_volts"] >= r_t["queda_inicial_volts"]


# --------------------------------------------------------------------------
# Conversão mm² -> AWG (vem de config.ini)
# --------------------------------------------------------------------------
@pytest.mark.parametrize("mm2,awg", [
    (2.5, 14), (4.0, 12), (6.0, 10), (50.0, 1), (70.0, "1/0"), (185.0, "250 MCM"),
])
def test_conversao_awg(mm2, awg):
    assert m.mm2_para_awg(mm2) == awg


def test_conversao_awg_sem_equivalente():
    assert m.mm2_para_awg(3.3) == "3.3 mm²"


# --------------------------------------------------------------------------
# Análise térmica — potência Joule e ρ(T)
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Resistividade dependente da temperatura
# --------------------------------------------------------------------------
def test_resistividade_em_temperatura_t0():
    """ρ(T₀) deve ser igual a ρ₀."""
    assert m.resistividade_em_temperatura(m.CFG.temperatura_referencia) == pytest.approx(
        m.CFG.resistividade_cobre
    )


def test_resistividade_aumenta_com_temperatura():
    assert m.resistividade_em_temperatura(140) > m.resistividade_em_temperatura(25)


def test_equilibrio_termico_maior_que_modelo_fixo():
    """Com ρ(T), T de regime deve ser maior que com ρ₀ fixo (corrente moderada)."""
    bitola, corrente, temp_amb = 6.0, 20.0, 25.0
    h = m.CFG.coef_conveccao
    diam = (4 * bitola / 3.14159) ** 0.5 + m.CFG.espessura_isolacao
    area = 2 * 3.14159 * (diam / 2 / 1000) * 1.0

    conv = m.calcular_equilibrio_termico(bitola, corrente, temp_amb, h, area)
    rho_fixo = m.CFG.resistividade_cobre
    p_fixo = corrente ** 2 * (rho_fixo / bitola)
    t_fixo = temp_amb + p_fixo / (h * area)

    assert conv["temp_regimen"] > t_fixo


def test_potencia_joule_correta():
    """Runaway térmico: P usa ρ(T_max), maior que o valor a 20 °C (70 W/m)."""
    t = m.calcular_tempo_aquecimento(bitola=2.5, corrente=100, temp_maxima=200, temp_ambiente=25)
    assert t["potencia_gerada_watts"] > 70.0
    assert t["potencia_gerada_watts"] == pytest.approx(119.52, abs=0.5)


def test_margem_termica_exemplo_usuario():
    """Cenário com T_regime ~140 °C e T_max 200 → margem ~60 °C."""
    t = m.calcular_tempo_aquecimento(bitola=4.0, corrente=49, temp_maxima=200, temp_ambiente=25)
    assert 135 <= t["temp_regimen_value"] <= 145
    assert t["margem_termica_celsius"] == pytest.approx(200 - t["temp_regimen_value"], abs=0.1)
    assert t["alerta_termico"] == "atencao"


def test_corrente_alta_atinge_tmax():
    """Com 100 A em 2.5 mm² o cabo ultrapassa o regime e atinge Tmax em tempo finito."""
    t = m.calcular_tempo_aquecimento(bitola=2.5, corrente=100, temp_maxima=200, temp_ambiente=25)
    assert t["tempo_minutos"] != "Nunca atingirá"
    assert t["temp_regimen_value"] > 200


def test_corrente_baixa_nao_atinge_tmax():
    """Com corrente baixa o cabo se estabiliza abaixo de Tmax e nunca a atinge."""
    t = m.calcular_tempo_aquecimento(bitola=6.0, corrente=7, temp_maxima=200, temp_ambiente=25)
    assert t["tempo_minutos"] == "Nunca atingirá"


# --------------------------------------------------------------------------
# config.ini — calibração / override
# --------------------------------------------------------------------------
def test_carregar_config_padrao_bate_com_embutido():
    cfg = m.carregar_config()
    assert cfg.resistividade_cobre == 0.0175
    assert cfg.temperatura_referencia == 20.0
    assert cfg.coef_temp_cobre == 0.00393
    assert cfg.coef_conveccao == 10.0
    assert len(cfg.bitolas_comerciais) == 22


def test_override_resistividade_muda_resultado(tmp_path):
    """Dobrar a resistividade no config deve dobrar a seção calculada."""
    ini = tmp_path / "config.ini"
    ini.write_text(textwrap.dedent("""
        [fisica]
        resistividade_cobre = 0.0350
    """), encoding="utf-8")

    cfg_original = m.CFG
    try:
        m.CFG = m.carregar_config(str(ini))
        assert m.CFG.resistividade_cobre == 0.0350
        r = m.calcular_bitola_cb(distancia=7, corrente=7, tensao=12, queda_percentual=5)
        # S dobra: 2.86 -> 5.72 mm² -> próxima bitola comercial 6.0 mm²
        assert r["secao_calculada"] == pytest.approx(5.72, abs=0.01)
        assert r["bitola_recomendada"] == 6.0
    finally:
        m.CFG = cfg_original


def test_override_tabela_awg(tmp_path):
    ini = tmp_path / "config.ini"
    ini.write_text(textwrap.dedent("""
        [conversao_awg]
        4.0 = TESTE
    """), encoding="utf-8")

    cfg_original = m.CFG
    try:
        m.CFG = m.carregar_config(str(ini))
        assert m.mm2_para_awg(4.0) == "TESTE"
    finally:
        m.CFG = cfg_original


# --------------------------------------------------------------------------
# Instalação + agrupamento (novos)
# --------------------------------------------------------------------------
def test_metodos_instalacao_carregados():
    ids = {mt["id"] for mt in m.metodos_instalacao()}
    assert {"ar_livre", "eletroduto_embutido", "enterrado"}.issubset(ids)


def test_fator_agrupamento():
    assert m.fator_agrupamento(1) == 1.0
    assert m.fator_agrupamento(3) < 1.0
    # acima do maior n definido, usa o último fator
    assert m.fator_agrupamento(999) == m.fator_agrupamento(max(m.CFG.agrupamento))


def test_coef_efetivo_pior_instalacao_menor_h():
    ar = m.coef_conveccao_efetivo("ar_livre", 1)
    enterrado = m.coef_conveccao_efetivo("enterrado", 1)
    assert enterrado < ar


def test_coef_efetivo_agrupamento_reduz_h():
    h1 = m.coef_conveccao_efetivo("ar_livre", 1)
    h4 = m.coef_conveccao_efetivo("ar_livre", 4)
    assert h4 < h1


def test_instalacao_pior_aquece_mais():
    """Mesma corrente: eletroduto embutido deve resultar em T maior que ar livre."""
    h_ar = m.coef_conveccao_efetivo("ar_livre", 1)
    h_enc = m.coef_conveccao_efetivo("eletroduto_embutido", 1)
    t_ar = m.calcular_tempo_aquecimento(2.5, 20, 200, 25, None, h_ar)
    t_enc = m.calcular_tempo_aquecimento(2.5, 20, 200, 25, None, h_enc)
    assert t_enc["temp_regimen_value"] > t_ar["temp_regimen_value"]


def test_agrupamento_aquece_mais():
    h1 = m.coef_conveccao_efetivo("ar_livre", 1)
    h6 = m.coef_conveccao_efetivo("ar_livre", 6)
    t1 = m.calcular_tempo_aquecimento(2.5, 20, 200, 25, None, h1)
    t6 = m.calcular_tempo_aquecimento(2.5, 20, 200, 25, None, h6)
    assert t6["temp_regimen_value"] > t1["temp_regimen_value"]


def test_memorial_contem_secoes_principais():
    entradas = {
        "distancia": 1.0, "corrente": 49.0, "tensao": 12.0, "queda_percentual": 5.0,
        "temp_amb": 25.0, "temp_max": 200.0, "diametro": None,
        "metodo_instalacao": "ar_livre", "n_condutores": 1,
    }
    h = m.coef_conveccao_efetivo("ar_livre", 1)
    resultado = m.calcular_bitola_cb(
        entradas["distancia"], entradas["corrente"], entradas["tensao"],
        entradas["queda_percentual"], temp_ambiente=25, coef_conveccao=h, temp_maxima=200,
    )
    memorial = m.gerar_memorial_calculo(entradas, resultado, h)
    ids = {s["id"] for s in memorial["secoes"]}
    assert ids == {"entradas", "constantes", "dimensionamento", "queda", "termico", "comparativo"}
    assert memorial["titulo"]
    assert len(memorial.get("diagramas", [])) >= 2
    assert "mermaid" in memorial["diagramas"][0]


def test_coef_conveccao_default_sem_argumento():
    """Sem coef_conveccao explícito, usa o valor base de config.ini."""
    t = m.calcular_tempo_aquecimento(2.5, 20, 200, 25)
    esperado = m.calcular_tempo_aquecimento(2.5, 20, 200, 25, None, m.CFG.coef_conveccao)
    assert t["temp_regimen_value"] == esperado["temp_regimen_value"]
