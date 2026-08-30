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


def test_bitola_recomendada_exige_queda_e_termico():
    """Menor bitola aprovada: queda dentro do limite e alerta térmico ok."""
    h = m.coef_conveccao_efetivo("ar_livre", 1)
    r = m.calcular_bitola_cb(
        distancia=4, corrente=300, tensao=100, queda_percentual=3,
        temp_ambiente=25, coef_conveccao=h, temp_maxima=200,
    )
    assert r["bitola_recomendada"] == 70.0
    assert r["queda_final_percentual"] <= 3
    termico = m.calcular_tempo_aquecimento(
        r["bitola_recomendada"], 300, 200, 25, None, h, comprimento=4,
    )
    assert termico["alerta_termico"] == "ok"


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


def test_runaway_termico_classificado_critico():
    """Runaway térmico (T regime infinita) deve ser alerta crítico, não ok."""
    h = m.coef_conveccao_efetivo("ar_livre", 1)
    t = m.calcular_tempo_aquecimento(25, 300, 200, 25, None, h)
    assert t["temp_regimen_value"] == float("inf")
    assert t["alerta_termico"] == "critico"


def test_avaliar_aprovacao_reprova_runaway_mesmo_com_queda_ok():
    from app import _avaliar_aprovacao

    status, aprovado, alerta, msg = _avaliar_aprovacao(True, "critico")
    assert status == "REPROVADO"
    assert not aprovado
    assert alerta == "critico"
    assert "escolher outros valores" in msg
    assert "runaway" in msg.lower()


def test_avaliar_aprovacao_aprovado_queda_e_termico_ok():
    from app import _avaliar_aprovacao

    status, aprovado, alerta, msg = _avaliar_aprovacao(True, "ok")
    assert status == "APROVADO"
    assert aprovado
    assert alerta == "ok"
    assert msg is None


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
    assert m.fator_agrupamento(20) == 0.50
    assert m.fator_agrupamento(25) == 0.45
    # acima do maior n definido, usa o último fator
    assert m.fator_agrupamento(999) == m.fator_agrupamento(max(m.CFG.agrupamento))


def test_fator_agrupamento_interpolacao_entre_chaves():
    """Entre chaves definidas, usa o fator da maior chave <= n (não volta a 1.0)."""
    cfg = m.Config(
        resistividade_cobre=0.0175,
        temperatura_referencia=20.0,
        coef_temp_cobre=0.00393,
        densidade_cobre=8900.0,
        calor_especifico_cobre=385.0,
        coef_conveccao=10.0,
        espessura_isolacao=2.0,
        padroes=dict(m.CFG.padroes),
        bitolas_comerciais=list(m.CFG.bitolas_comerciais),
        conversao_awg=dict(m.CFG.conversao_awg),
        capacidade_corrente=dict(m.CFG.capacidade_corrente),
        instalacao=dict(m.CFG.instalacao),
        instalacao_rotulos=dict(m.CFG.instalacao_rotulos),
        instalacao_padrao=m.CFG.instalacao_padrao,
        agrupamento={1: 1.0, 10: 0.5, 20: 0.5},
    )
    assert m.fator_agrupamento(15, cfg) == 0.5
    assert m.fator_agrupamento(9, cfg) == 1.0


def test_agrupamento_20_muito_pior_que_1():
    """20 condutores devem reduzir h bem mais que 8 (faixa 10–20 = 50%)."""
    h1 = m.coef_conveccao_efetivo("ar_livre", 1)
    h20 = m.coef_conveccao_efetivo("ar_livre", 20)
    assert h20 == pytest.approx(h1 * 0.50, rel=1e-6)
    assert h20 < m.coef_conveccao_efetivo("ar_livre", 8)


def test_cenario_baixa_corrente_agrupamento():
    """Com carga térmica baixa, ΔT absoluto é pequeno mas n=20 aquece mais que n=1."""
    h1 = m.coef_conveccao_efetivo("ar_livre", 1)
    h20 = m.coef_conveccao_efetivo("ar_livre", 20)
    t1 = m.calcular_tempo_aquecimento(2.5, 3, 200, 25, None, h1)
    t20 = m.calcular_tempo_aquecimento(2.5, 3, 200, 25, None, h20)
    assert 25.4 <= t1["temp_regimen_value"] <= 25.6
    assert t20["temp_regimen_value"] > t1["temp_regimen_value"]
    assert t20["temp_regimen_value"] - t1["temp_regimen_value"] > 0.4


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
    assert ids == {"resumo", "entradas", "constantes", "dimensionamento", "queda", "termico", "comparativo"}
    assert memorial["titulo"]
    assert len(memorial.get("diagramas", [])) >= 2
    assert "mermaid" in memorial["diagramas"][0]


def test_comprimento_termico_escala_potencia_total():
    """Potência total escala com o comprimento; W/m e T_regime permanecem constantes."""
    h = m.coef_conveccao_efetivo("ar_livre", 1)
    t4 = m.calcular_tempo_aquecimento(25, 100, 200, 25, None, h, comprimento=4)
    t10 = m.calcular_tempo_aquecimento(25, 100, 200, 25, None, h, comprimento=10)
    assert t4["temp_regimen_value"] == pytest.approx(t10["temp_regimen_value"])
    assert t4["potencia_por_metro_watts"] == pytest.approx(t10["potencia_por_metro_watts"])
    assert t10["potencia_gerada_watts"] == pytest.approx(t4["potencia_gerada_watts"] * 2.5, rel=0.01)


def test_comprimento_condutor_metade_do_loop():
    assert m.comprimento_condutor(8) == 4


def test_queda_comparativa_usa_comprimento_condutor_na_termica():
    h = m.coef_conveccao_efetivo("ar_livre", 1)
    q = m.calcular_queda_comparativa(
        25, 8, 100, 100, temp_ambiente=25, h_conveccao=h, temp_limite=200,
    )
    t = m.calcular_tempo_aquecimento(25, 100, 200, 25, None, h, comprimento=4)
    assert q["temperatura_final"] == pytest.approx(t["temp_regimen_value"])


def test_coef_conveccao_default_sem_argumento():
    """Sem coef_conveccao explícito, usa o valor base de config.ini."""
    t = m.calcular_tempo_aquecimento(2.5, 20, 200, 25)
    esperado = m.calcular_tempo_aquecimento(2.5, 20, 200, 25, None, m.CFG.coef_conveccao)
    assert t["temp_regimen_value"] == esperado["temp_regimen_value"]
