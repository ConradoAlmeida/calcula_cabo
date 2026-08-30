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
    calcular_bitola_cb,
    calcular_queda_comparativa,
    calcular_tempo_aquecimento,
    coef_conveccao_efetivo,
    config_para_dict,
    gerar_memorial_calculo,
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


def _to_float(valor, padrao):
    """Converte texto para float aceitando virgula decimal; usa padrao se vazio."""
    if valor is None:
        return padrao
    texto = str(valor).strip().replace(",", ".")
    if texto == "":
        return padrao
    return float(texto)


def _to_float_opcional(valor):
    """Converte para float ou retorna None quando vazio (diametro externo)."""
    if valor is None:
        return None
    texto = str(valor).strip().replace(",", ".")
    if texto == "":
        return None
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
        diametro = _to_float_opcional(dados.get("diametro"))
    except (ValueError, TypeError):
        raise ValueError("Use apenas valores numéricos nos campos.")

    if distancia <= 0 or corrente <= 0 or tensao <= 0 or queda_percentual <= 0:
        raise ValueError("Distância, corrente, tensão e queda devem ser maiores que zero.")

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
        "diametro": diametro,
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

    resultado = calcular_bitola_cb(
        entradas["distancia"],
        entradas["corrente"],
        entradas["tensao"],
        entradas["queda_percentual"],
        temp_ambiente=entradas["temp_amb"],
        coef_conveccao=h_efetivo,
        diametro_externo=entradas["diametro"],
        temp_maxima=entradas["temp_max"],
    )

    adequada = resultado["queda_final_percentual"] <= resultado["queda_maxima_percentual"]
    status_queda = "ADEQUADA" if adequada else "ACIMA DO LIMITE"

    principal = {
        "secao_calculada": f"{resultado['secao_calculada']:.2f}",
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
        "status": status_queda,
        "adequada": adequada,
    }

    linhas_termicas = []
    alerta_recomendada = None
    for bitola in obter_bitolas_analise_termica(resultado["bitola_recomendada"]):
        awg = mm2_para_awg(bitola)
        queda = calcular_queda_comparativa(
            bitola, resultado["comprimento_total"], entradas["corrente"], entradas["tensao"],
            temp_ambiente=entradas["temp_amb"],
            h_conveccao=h_efetivo,
            diametro_externo=entradas["diametro"],
            temp_limite=entradas["temp_max"],
        )
        termico = calcular_tempo_aquecimento(
            bitola, entradas["corrente"], entradas["temp_max"],
            entradas["temp_amb"], entradas["diametro"], h_efetivo,
        )
        ok = queda["queda_final_percentual"] <= resultado["queda_maxima_percentual"]
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
            "potencia": f"{termico['potencia_gerada_watts']:.2f}",
            "temp_regime": str(termico["temp_regimen_celsius"]),
            "margem_termica": margem_str,
            "tempo_minutos": str(termico["tempo_minutos"]),
            "status": "OK" if ok else "QUEDA ALTA",
            "alerta_termico": alerta,
            "recomendada": bitola == resultado["bitola_recomendada"],
        }
        linhas_termicas.append(linha)

        if bitola == resultado["bitola_recomendada"]:
            alerta_recomendada = alerta

    if adequada and alerta_recomendada in ("atencao", "critico"):
        principal["alerta_termico"] = alerta_recomendada
        principal["alerta_termico_msg"] = (
            "Queda de tensão adequada, mas a temperatura de regime está elevada. "
            "Considere aumentar a bitola ou melhorar a instalação."
        )
    else:
        principal["alerta_termico"] = alerta_recomendada or "ok"
        principal["alerta_termico_msg"] = None

    instalacao = {
        "metodo": entradas["metodo_instalacao"],
        "rotulo": CFG.instalacao_rotulos.get(
            entradas["metodo_instalacao"], entradas["metodo_instalacao"]
        ),
        "n_condutores": entradas["n_condutores"],
        "h_efetivo": f"{h_efetivo:.2f}",
    }

    memorial = gerar_memorial_calculo(entradas, resultado, h_efetivo)

    return {
        "entradas": entradas,
        "principal": principal,
        "termicas": linhas_termicas,
        "referencia": _tabela_referencia(),
        "instalacao": instalacao,
        "memorial": memorial,
    }


@app.route("/")
def index():
    return render_template(
        "index.html",
        padroes=PADROES,
        metodos=metodos_instalacao(),
        metodo_padrao=CFG.instalacao_padrao,
    )


@app.route("/memorial")
def memorial_page():
    return render_template("memorial.html")


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
    resultado = calcular_bitola_cb(
        entradas["distancia"], entradas["corrente"],
        entradas["tensao"], entradas["queda_percentual"],
        temp_ambiente=entradas["temp_amb"],
        coef_conveccao=h_efetivo,
        diametro_externo=entradas["diametro"],
        temp_maxima=entradas["temp_max"],
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
            diametro_externo=entradas["diametro"],
            temp_limite=entradas["temp_max"],
        )
        termico = calcular_tempo_aquecimento(
            bitola, entradas["corrente"], entradas["temp_max"],
            entradas["temp_amb"], entradas["diametro"], h_efetivo,
        )
        status_termico = "OK" if queda["queda_final_percentual"] <= resultado["queda_maxima_percentual"] else "QUEDA ALTA"
        margem = termico["margem_termica_celsius"]
        if isinstance(margem, float) and margem == float("-inf"):
            margem_txt = "—"
        else:
            margem_txt = f"{margem:.1f}"
        linhas_termicas.append([
            f"{bitola:.2f}", f"{awg}",
            f"{queda['queda_inicial_volts']:.2f}", f"{queda['queda_inicial_percentual']:.2f}",
            f"{queda['queda_final_volts']:.2f}", f"{queda['queda_final_percentual']:.2f}",
            f"{termico['potencia_gerada_watts']:.2f}", f"{termico['temp_regimen_celsius']}",
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
