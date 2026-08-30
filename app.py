# -*- coding: utf-8 -*-
"""Aplicacao web (Flask) para a calculadora de bitola de cabo DC.

Reaproveita as funcoes de calculo do script de linha de comando
`calcular_bitola_cabo_dc.py`, expondo uma interface web e uma API JSON.
"""

import io
import os
import tempfile

from flask import Flask, jsonify, render_template, request, send_file

from calcular_bitola_cabo_dc import (
    CFG,
    bitola_atende_termico_limite,
    calcular_bitola_cb,
    calcular_queda_comparativa,
    calcular_tempo_aquecimento,
    coef_conveccao_efetivo,
    config_para_dict,
    gerar_memorial_calculo,
    texto_rodape_certificacao,
    gerar_nome_relatorio_por_inputs,
    metodos_instalacao,
    mm2_para_awg,
    obter_bitolas_analise_termica,
    salvar_relatorio_txt,
)

app = Flask(__name__)

# Toda a calibração (constantes, tabelas e valores padrão) vem de config.ini,
# via o módulo de cálculo. Assim CLI e web usam exatamente os mesmos números.
PADROES = CFG.padroes


def _status_linha_termica(queda_ok, termico_ok):
    if queda_ok and termico_ok:
        return "OK"
    return "REPROVADO"


def _avaliar_aprovacao(queda_ok, termico_ok, alerta_termico):
    """Consolida queda + térmica em status único para o painel principal."""
    aprovado = queda_ok and termico_ok
    if aprovado:
        return "APROVADO", True, alerta_termico or "ok", None

    motivos = []
    if not queda_ok:
        motivos.append("queda de tensão em regime acima do limite")
    if not termico_ok:
        if alerta_termico == "critico":
            motivos.append("temperatura de regime crítica ou instável (runaway)")
        else:
            motivos.append("temperatura de regime acima do limite térmico (%)")

    msg = "REPROVADO — escolher outros valores"
    if motivos:
        msg += " (" + "; ".join(motivos) + ")"
    return "REPROVADO", False, alerta_termico or "queda", msg


def _montar_sanidade(entradas, resultado, principal, linha_recomendada, instalacao, ok_queda, ok_termico):
    """Checklist resumido para validação rápida do dimensionamento."""
    secao_vdrop = resultado["secao_teorica_vdrop"]
    secao_termica = resultado["secao_teorica_termica"]
    secao_gov = max(secao_vdrop, secao_termica)
    bitola_rec = resultado["bitola_recomendada"]
    criterio = resultado.get("criterio_governante", "—")
    criterio_rotulo = {
        "vdrop": "Queda de tensão",
        "termico": "Limite térmico",
        "igual": "Empate (vdrop = térmico)",
    }.get(criterio, criterio)

    alerta = principal.get("alerta_termico", "ok")
    alerta_ok = alerta == "ok"
    bitola_cobre_gov = bitola_rec >= secao_gov - 0.05

    checks = []
    limite_mm2 = resultado.get("bitola_maxima_frota_mm2")
    if limite_mm2:
        checks.append({
            "id": "limite_frota",
            "rotulo": f"Bitola ≤ AWG {resultado.get('bitola_maxima_frota_awg', '—')}",
            "ok": not resultado.get("limite_frota_excedido"),
            "detalhe": (
                f"limite {limite_mm2:g} mm² · necessária {bitola_rec:g} mm² "
                f"(AWG {resultado['bitola_awg']})"
            ),
        })

    checks.extend([
        {
            "id": "vdrop_regime",
            "rotulo": "Vdrop em regime",
            "ok": ok_queda,
            "detalhe": (
                f"{resultado['queda_final_percentual']:.2f}% "
                f"(limite {resultado['queda_maxima_percentual']:.2f}%)"
            ),
        },
        {
            "id": "termico_limite",
            "rotulo": "T_regime no limite",
            "ok": ok_termico,
            "detalhe": (
                f"{principal['temperatura_operacao']} °C · "
                f"limite {entradas['pct_limite_termico']:.0f}% de T_max"
            ),
        },
        {
            "id": "alerta_termico",
            "rotulo": "Alerta térmico",
            "ok": alerta_ok,
            "detalhe": {"ok": "Dentro da faixa", "atencao": "Atenção", "critico": "Crítico / runaway"}.get(
                alerta, alerta,
            ),
        },
        {
            "id": "bitola_governante",
            "rotulo": "Bitola ≥ seção governante",
            "ok": bitola_cobre_gov,
            "detalhe": f"{bitola_rec:.2f} mm² ≥ {secao_gov:.2f} mm²",
        },
    ])

    resumo = [
        {"rotulo": "Critério governante", "valor": criterio_rotulo},
        {"rotulo": "Cálculo p/ vdrop", "valor": f"{secao_vdrop:.2f} mm²"},
        {"rotulo": "Cálculo p/ T_limite", "valor": f"{secao_termica:.2f} mm²"},
        {"rotulo": "Comprimento (ida+volta)", "valor": f"{resultado['comprimento_total']:.2f} m"},
        {"rotulo": "Instalação", "valor": instalacao["rotulo"]},
        {"rotulo": "h efetivo", "valor": f"{instalacao['h_efetivo']} W/(m²·°C)"},
    ]

    if linha_recomendada:
        resumo.extend([
            {"rotulo": "Margem térmica", "valor": f"{linha_recomendada['margem_termica']} °C"},
            {"rotulo": "P. Joule", "valor": f"{linha_recomendada['potencia']} W/m"},
            {
                "rotulo": "ρ (ini → regime)",
                "valor": (
                    f"{linha_recomendada['resistividade_inicial']} → "
                    f"{linha_recomendada['resistividade_final']} Ω·mm²/m"
                ),
            },
        ])

    return {
        "aprovado": principal.get("aprovado", False),
        "checks": checks,
        "resumo": resumo,
    }


def _to_float(valor, padrao):
    """Converte texto para float aceitando virgula decimal; usa padrao se vazio."""
    if valor is None:
        return padrao
    texto = str(valor).strip().replace(",", ".")
    if texto == "":
        return padrao
    return float(texto)


def _parse_entradas(dados):
    """Extrai e valida as entradas de um dict (form ou JSON)."""
    try:
        distancia = _to_float(dados.get("distancia"), PADROES["distancia"])
        corrente = _to_float(dados.get("corrente"), PADROES["corrente"])
        tensao = _to_float(dados.get("tensao"), PADROES["tensao"])
        queda_percentual = _to_float(dados.get("queda_percentual"), PADROES["queda_percentual"])
        temp_max = _to_float(dados.get("temp_max"), PADROES["temp_max"])
        temp_amb = _to_float(dados.get("temp_amb"), PADROES["temp_amb"])
        pct_limite_termico = _to_float(
            dados.get("pct_limite_termico"), PADROES["pct_limite_termico"],
        )
    except (ValueError, TypeError):
        raise ValueError("Use apenas valores numéricos nos campos.")

    if distancia <= 0 or corrente <= 0 or tensao <= 0 or queda_percentual <= 0:
        raise ValueError("Distância, corrente, tensão e queda devem ser maiores que zero.")
    if not (0 < pct_limite_termico <= 100):
        raise ValueError("Limite térmico (%) deve estar entre 0 e 100.")

    # Método de instalação (validado contra os métodos de config.ini).
    metodo = str(dados.get("metodo_instalacao") or "").strip()
    if metodo not in CFG.instalacao:
        metodo = CFG.instalacao_padrao

    # Número de condutores agrupados lado a lado.
    try:
        n_condutores = int(float(dados.get("n_condutores") or 1))
    except (ValueError, TypeError):
        n_condutores = 1
    n_condutores = max(1, n_condutores)

    return {
        "distancia": distancia,
        "corrente": corrente,
        "tensao": tensao,
        "queda_percentual": queda_percentual,
        "temp_max": temp_max,
        "temp_amb": temp_amb,
        "pct_limite_termico": pct_limite_termico,
        "metodo_instalacao": metodo,
        "n_condutores": n_condutores,
    }


def _tabela_referencia():
    """Retorna as linhas estruturadas da tabela de referencia de bitolas."""
    linhas = []
    for bitola, corrente_max in CFG.capacidade_corrente.items():
        resistencia_km = (CFG.resistividade_cobre / bitola) * 1000
        linhas.append({
            "bitola": f"{bitola:.1f}",
            "awg": str(mm2_para_awg(bitola)),
            "corrente_max": corrente_max,
            "resistencia_km": f"{resistencia_km:.4f}",
        })
    return linhas


def _calcular(entradas):
    """Executa o dimensionamento e a analise termica, retornando dados prontos p/ UI."""
    h_efetivo = coef_conveccao_efetivo(entradas["metodo_instalacao"], entradas["n_condutores"])
    comprimento_termico = entradas["distancia"]

    resultado = calcular_bitola_cb(
        entradas["distancia"],
        entradas["corrente"],
        entradas["tensao"],
        entradas["queda_percentual"],
        temp_ambiente=entradas["temp_amb"],
        coef_conveccao=h_efetivo,
        diametro_externo=None,
        temp_maxima=entradas["temp_max"],
        pct_limite_termico=entradas["pct_limite_termico"],
    )

    adequada_queda = resultado["queda_final_percentual"] <= resultado["queda_maxima_percentual"]
    ok_rec, _ = bitola_atende_termico_limite(
        resultado["bitola_recomendada"],
        entradas["corrente"],
        entradas["temp_max"],
        entradas["temp_amb"],
        h_efetivo,
        None,
        comprimento_termico,
        entradas["pct_limite_termico"],
    )

    principal = {
        "secao_teorica_vdrop": f"{resultado['secao_teorica_vdrop']:.2f}",
        "secao_teorica_termica": f"{resultado['secao_teorica_termica']:.2f}",
        "secao_calculada": f"{resultado['secao_teorica_vdrop']:.2f}",
        "pct_limite_termico": f"{resultado['pct_limite_termico']:.0f}",
        "criterio_governante": resultado["criterio_governante"],
        "bitola_recomendada": f"{resultado['bitola_recomendada']:.2f}",
        "bitola_awg": str(resultado["bitola_awg"]),
        "queda_inicial_volts": f"{resultado['queda_inicial_volts']:.2f}",
        "queda_inicial_percentual": f"{resultado['queda_inicial_percentual']:.2f}",
        "queda_final_volts": f"{resultado['queda_final_volts']:.2f}",
        "queda_final_percentual": f"{resultado['queda_final_percentual']:.2f}",
        "queda_tensao_volts": f"{resultado['queda_final_volts']:.2f}",
        "queda_tensao_percentual": f"{resultado['queda_final_percentual']:.2f}",
        "queda_maxima_percentual": f"{resultado['queda_maxima_percentual']:.2f}",
        "comprimento_total": f"{resultado['comprimento_total']:.2f}",
        "temperatura_operacao": f"{resultado['temperatura_operacao']:.1f}",
    }

    linhas_termicas = []
    alerta_recomendada = None
    linha_recomendada = None
    for bitola in obter_bitolas_analise_termica(resultado["bitola_recomendada"]):
        awg = mm2_para_awg(bitola)
        queda = calcular_queda_comparativa(
            bitola, resultado["comprimento_total"], entradas["corrente"], entradas["tensao"],
            temp_ambiente=entradas["temp_amb"],
            h_conveccao=h_efetivo,
            diametro_externo=None,
            temp_limite=entradas["temp_max"],
        )
        termico = calcular_tempo_aquecimento(
            bitola, entradas["corrente"], entradas["temp_max"],
            entradas["temp_amb"], None, h_efetivo,
            comprimento_termico,
            pct_limite_termico=entradas["pct_limite_termico"],
        )
        ok_queda = queda["queda_final_percentual"] <= resultado["queda_maxima_percentual"]
        ok_termico, _ = bitola_atende_termico_limite(
            bitola, entradas["corrente"], entradas["temp_max"],
            entradas["temp_amb"], h_efetivo, None,
            comprimento_termico, entradas["pct_limite_termico"],
        )
        alerta = termico["alerta_termico"]
        margem = termico["margem_termica_celsius"]
        if isinstance(margem, float) and margem == float("-inf"):
            margem_str = "—"
        else:
            margem_str = f"{margem:.1f}"

        linha = {
            "bitola": f"{bitola:.2f}",
            "awg": str(awg),
            "queda_inicial_volts": f"{queda['queda_inicial_volts']:.2f}",
            "queda_inicial_percentual": f"{queda['queda_inicial_percentual']:.2f}",
            "queda_final_volts": f"{queda['queda_final_volts']:.2f}",
            "queda_final_percentual": f"{queda['queda_final_percentual']:.2f}",
            "potencia": f"{termico['potencia_por_metro_watts']:.2f}",
            "temp_regime": str(termico["temp_regimen_celsius"]),
            "resistividade_inicial": f"{queda['resistividade_inicial']:.4f}",
            "resistividade_final": f"{queda['resistividade_final']:.4f}",
            "margem_termica": margem_str,
            "tempo_minutos": str(termico["tempo_minutos"]),
            "status": _status_linha_termica(ok_queda, ok_termico),
            "alerta_termico": alerta,
            "recomendada": bitola == resultado["bitola_recomendada"],
        }
        linhas_termicas.append(linha)

        if bitola == resultado["bitola_recomendada"]:
            alerta_recomendada = alerta
            linha_recomendada = linha

    status, aprovado, alerta_principal, msg_principal = _avaliar_aprovacao(
        adequada_queda, ok_rec, alerta_recomendada or "ok"
    )
    if resultado.get("limite_frota_excedido"):
        aprovado = False
        status = "REPROVADO"
        frota_msg = resultado["limite_frota_msg"]
        msg_principal = f"{frota_msg} | {msg_principal}" if msg_principal else frota_msg

    principal["status"] = status
    principal["aprovado"] = aprovado
    principal["adequada"] = aprovado
    principal["alerta_termico"] = alerta_principal
    principal["alerta_termico_msg"] = msg_principal
    principal["limite_frota_excedido"] = resultado.get("limite_frota_excedido", False)
    principal["limite_frota_msg"] = resultado.get("limite_frota_msg")

    instalacao = {
        "metodo": entradas["metodo_instalacao"],
        "rotulo": CFG.instalacao_rotulos.get(
            entradas["metodo_instalacao"], entradas["metodo_instalacao"]
        ),
        "n_condutores": entradas["n_condutores"],
        "h_efetivo": f"{h_efetivo:.2f}",
    }

    memorial = gerar_memorial_calculo(entradas, resultado, h_efetivo)
    sanidade = _montar_sanidade(
        entradas, resultado, principal, linha_recomendada, instalacao, adequada_queda, ok_rec,
    )

    return {
        "entradas": entradas,
        "principal": principal,
        "termicas": linhas_termicas,
        "referencia": _tabela_referencia(),
        "instalacao": instalacao,
        "memorial": memorial,
        "sanidade": sanidade,
    }


@app.route("/")
def index():
    return render_template(
        "index.html",
        padroes=PADROES,
        queda_circuito=CFG.queda_circuito,
        metodos=metodos_instalacao(),
        metodo_padrao=CFG.instalacao_padrao,
        rodape_certificacao=texto_rodape_certificacao(),
    )


@app.route("/memorial")
def memorial_page():
    return render_template(
        "memorial.html",
        rodape_certificacao=texto_rodape_certificacao(),
    )


@app.route("/api/memorial", methods=["POST"])
def api_memorial():
    """Recalcula e devolve o memorial de cálculo para validação."""
    dados = request.get_json(silent=True) or request.form
    try:
        entradas = _parse_entradas(dados)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception:  # noqa: BLE001
        return jsonify({"erro": "Entrada invalida. Use valores numericos."}), 400

    payload = _calcular(entradas)
    return jsonify(payload["memorial"])


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/config")
def api_config():
    """Expõe a configuração/calibração ativa (constantes, tabelas, padrões).

    Útil para conferir os números usados: conversão mm²↔AWG, resistividade,
    coeficiente de convecção (W/m²·°C), capacidades de corrente, etc.
    """
    return jsonify(config_para_dict())


@app.route("/api/calcular", methods=["POST"])
def api_calcular():
    dados = request.get_json(silent=True) or request.form
    try:
        entradas = _parse_entradas(dados)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception:  # noqa: BLE001
        return jsonify({"erro": "Entrada invalida. Use valores numericos."}), 400

    return jsonify(_calcular(entradas))


@app.route("/api/relatorio", methods=["POST"])
def api_relatorio():
    dados = request.get_json(silent=True) or request.form
    try:
        entradas = _parse_entradas(dados)
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    except Exception:  # noqa: BLE001
        return jsonify({"erro": "Entrada invalida. Use valores numericos."}), 400

    incluir_ref = str(dados.get("incluir_referencia", "")).lower() in ("1", "true", "s", "on", "sim")

    h_efetivo = coef_conveccao_efetivo(entradas["metodo_instalacao"], entradas["n_condutores"])
    comprimento_termico = entradas["distancia"]
    resultado = calcular_bitola_cb(
        entradas["distancia"], entradas["corrente"],
        entradas["tensao"], entradas["queda_percentual"],
        temp_ambiente=entradas["temp_amb"],
        coef_conveccao=h_efetivo,
        diametro_externo=None,
        temp_maxima=entradas["temp_max"],
        pct_limite_termico=entradas["pct_limite_termico"],
    )
    adequada = resultado["queda_final_percentual"] <= resultado["queda_maxima_percentual"]
    status_queda = "ADEQUADA" if adequada else "ACIMA DO LIMITE"
    linhas_principal = [[
        f"{resultado['secao_calculada']:.2f}",
        f"{resultado['bitola_recomendada']:.2f}",
        f"{resultado['bitola_awg']}",
        f"{resultado['queda_inicial_volts']:.2f}",
        f"{resultado['queda_inicial_percentual']:.2f}",
        f"{resultado['queda_final_volts']:.2f}",
        f"{resultado['queda_final_percentual']:.2f}",
        f"{resultado['queda_maxima_percentual']:.2f}",
        status_queda,
    ]]

    linhas_termicas = []
    for bitola in obter_bitolas_analise_termica(resultado["bitola_recomendada"]):
        awg = mm2_para_awg(bitola)
        queda = calcular_queda_comparativa(
            bitola, resultado["comprimento_total"], entradas["corrente"], entradas["tensao"],
            temp_ambiente=entradas["temp_amb"],
            h_conveccao=h_efetivo,
            diametro_externo=None,
            temp_limite=entradas["temp_max"],
        )
        termico = calcular_tempo_aquecimento(
            bitola, entradas["corrente"], entradas["temp_max"],
            entradas["temp_amb"], None, h_efetivo,
            comprimento_termico,
            pct_limite_termico=entradas["pct_limite_termico"],
        )
        ok_queda = queda["queda_final_percentual"] <= resultado["queda_maxima_percentual"]
        ok_termico, _ = bitola_atende_termico_limite(
            bitola, entradas["corrente"], entradas["temp_max"],
            entradas["temp_amb"], h_efetivo, None,
            comprimento_termico, entradas["pct_limite_termico"],
        )
        status_termico = "OK" if ok_queda and ok_termico else "REPROVADO"
        margem = termico["margem_termica_celsius"]
        if isinstance(margem, float) and margem == float("-inf"):
            margem_txt = "—"
        else:
            margem_txt = f"{margem:.1f}"
        linhas_termicas.append([
            f"{bitola:.2f}", f"{awg}",
            f"{queda['queda_inicial_volts']:.2f}", f"{queda['queda_inicial_percentual']:.2f}",
            f"{queda['queda_final_volts']:.2f}", f"{queda['queda_final_percentual']:.2f}",
            f"{termico['potencia_por_metro_watts']:.2f}", f"{termico['temp_regimen_celsius']}",
            margem_txt,
            f"{termico['tempo_minutos']}", status_termico,
        ])

    nome_arquivo = gerar_nome_relatorio_por_inputs(entradas, incluir_ref)
    with tempfile.TemporaryDirectory() as tmpdir:
        caminho = os.path.join(tmpdir, nome_arquivo)
        salvar_relatorio_txt(
            dados_entrada=entradas,
            resultado_principal=resultado,
            linhas_principal=linhas_principal,
            linhas_termicas=linhas_termicas,
            incluir_tabela_referencia=incluir_ref,
            caminho_arquivo=caminho,
        )
        with open(caminho, "rb") as arquivo:
            conteudo = arquivo.read()

    return send_file(
        io.BytesIO(conteudo),
        mimetype="text/plain",
        as_attachment=True,
        download_name=nome_arquivo,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
