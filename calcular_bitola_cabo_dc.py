#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para calcular a bitola ideal de cabo de energia elétrica DC.
Baseado na queda de tensão máxima permitida e resistividade do condutor.
"""

from datetime import datetime
import hashlib
import os

# Tabela de bitolas comerciais disponíveis (em mm²)
BITOLAS_COMERCIAIS = [
    0.5, 0.75, 1.0, 1.5, 2.5, 4.0, 6.0, 10.0,
    16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0,
    150.0, 185.0, 240.0, 300.0, 400.0, 500.0, 630.0
]


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
    indice = BITOLAS_COMERCIAIS.index(bitola_recomendada)
    indices = [indice - 1, indice, indice + 1]

    bitolas = []
    for i in indices:
        if 0 <= i < len(BITOLAS_COMERCIAIS):
            bitolas.append(BITOLAS_COMERCIAIS[i])

    return bitolas


def calcular_queda_para_bitola(bitola, comprimento_total, corrente, tensao):
    """Calcula queda de tensão para uma bitola específica."""
    resistividade_cobre = 0.0175
    resistencia = (resistividade_cobre * comprimento_total) / bitola
    queda_tensao = corrente * resistencia
    queda_percentual = (queda_tensao / tensao) * 100

    return {
        'resistencia_ohm': resistencia,
        'queda_tensao_volts': queda_tensao,
        'queda_tensao_percentual': queda_percentual
    }

def mm2_para_awg(mm2):
    """
    Converte bitola de mm² para AWG (American Wire Gauge)
    Args:
        mm2 (float): Bitola em mm²
    Returns:
        int or str: Valor AWG ou a bitola em mm² se não houver equivalente direto
    """
    # Tabela de conversão de mm² para AWG (valores comerciais)
    conversao = {
        0.5: 20,
        0.75: 19,
        1.0: 18,
        1.5: 16,
        2.5: 14,
        4.0: 12,
        6.0: 10,
        10.0: 8,
        16.0: 6,
        25.0: 4,
        35.0: 2,
        50.0: 1,
        70.0: '1/0',
        95.0: '2/0',
        120.0: '3/0',
        150.0: '4/0',
        185.0: '250 MCM',
        240.0: '300 MCM',
        300.0: '350 MCM',
        400.0: '400 MCM',
        500.0: '500 MCM',
        630.0: '600 MCM'
    }
    
    return conversao.get(mm2, f"{mm2} mm²")


def calcular_bitola_cb(distancia, corrente, tensao, queda_percentual=3):
    """
    Calcula a bitola ideal do cabo baseado em:
    - Distância entre a fonte e o equipamento
    - Corrente do equipamento
    - Tensão do sistema
    - Queda percentual máxima permitida (padrão: 3%)
    
    Args:
        distancia (float): Distância em metros (ida + volta)
        corrente (float): Corrente em Amperes
        tensao (float): Tensão em Volts (DC)
        queda_percentual (float): Queda de tensão máxima em % (padrão: 3%)
    
    Returns:
        dict: Dicionário com resultados do cálculo
    """
    
    # Resistividade do cobre a 20°C em Ohm.mm²/m
    resistividade_cobre = 0.0175
    
    # Se distância é de ida, considerar ida + volta
    comprimento_total = distancia * 2
    
    # Queda de tensão máxima permitida em volts
    queda_tensao_max = (queda_percentual / 100) * tensao
    
    # Fórmula: S = (ρ × L × I) / V_queda
    # S = seção em mm²
    secao_calculada = (resistividade_cobre * comprimento_total * corrente) / queda_tensao_max
    
    # Encontrar a bitola comercial mais próxima (sempre para cima)
    bitola_ideal = None
    for bitola in BITOLAS_COMERCIAIS:
        if bitola >= secao_calculada:
            bitola_ideal = bitola
            break
    
    if bitola_ideal is None:
        bitola_ideal = BITOLAS_COMERCIAIS[-1]
    
    # Calcular resistência real com a bitola escolhida
    resistencia_real = (resistividade_cobre * comprimento_total) / bitola_ideal
    
    # Calcular queda real com a bitola escolhida
    queda_real = corrente * resistencia_real
    queda_real_percentual = (queda_real / tensao) * 100
    
    # Obter bitola em AWG
    bitola_awg = mm2_para_awg(bitola_ideal)
    
    return {
        'secao_calculada': round(secao_calculada, 2),
        'bitola_recomendada': bitola_ideal,
        'bitola_awg': bitola_awg,
        'comprimento_total': comprimento_total,
        'resistencia_ohm': round(resistencia_real, 4),
        'queda_tensao_volts': round(queda_real, 2),
        'queda_tensao_percentual': round(queda_real_percentual, 2),
        'queda_maxima_permitida': queda_tensao_max,
        'queda_maxima_percentual': queda_percentual
    }


def calcular_tempo_aquecimento(bitola, corrente, temp_maxima, temp_ambiente=25, diametro_externo=None):
    """
    Calcula o tempo para o cabo alcançar a temperatura máxima suportada.
    
    Utiliza modelo de aquecimento com dissipação térmica por convecção.
    
    Args:
        bitola (float): Bitola do cabo em mm²
        corrente (float): Corrente em Amperes
        temp_maxima (float): Temperatura máxima suportada pelo cabo em °C
        temp_ambiente (float): Temperatura ambiente em °C (padrão: 25°C)
        diametro_externo (float): Diâmetro externo do cabo em mm (opcional)
    
    Returns:
        dict: Dicionário com resultados do cálculo térmico
    """
    
    # Propriedades do cobre
    resistividade_cobre = 0.0175  # Ohm.mm²/m
    densidade_cobre = 8900  # kg/m³
    calor_especifico_cobre = 385  # J/(kg·°C)
    
    # Se não informar o diâmetro, estimar baseado na bitola
    if diametro_externo is None:
        # Estimativa: d = √(4×A/π) para condutor equivalente
        diametro_condutor = (4 * bitola / 3.14159) ** 0.5
        # Adicionar isolação (espessura típica 1-1.5mm)
        diametro_externo = diametro_condutor + 2.0
    
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
    
    # Resistência de 1 metro de cabo
    resistencia_1m = (resistividade_cobre * comprimento) / bitola * 1e-6  # em Ohms
    
    # Potência dissipada (efeito Joule)
    potencia_gerada = (corrente ** 2) * resistencia_1m  # em Watts
    
    # Coeficiente de transferência térmica por convecção (ar parado)
    # Valores típicos: 5-25 W/(m²·°C) - usando valor médio de 10
    h_conveccao = 10  # W/(m²·°C)
    
    # Diferença de temperatura a atingir
    delta_temp = temp_maxima - temp_ambiente
    
    # Capacidade térmica total do cobre
    capacidade_termica = massa_cobre * calor_especifico_cobre  # J/°C
    
    # Temperatura que o cabo atingiria em regime permanente (equilíbrio)
    # T_regime = T_amb + (P / (h × A))
    if area_lateral > 0:
        temp_regimen = temp_ambiente + (potencia_gerada / (h_conveccao * area_lateral))
    else:
        temp_regimen = float('inf')
    
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
        'temp_regimen_value': temp_regimen  # valor numérico para comparação
    }


def tabela_bitolas():
    """Exibe uma tabela de referência de bitolas comerciais e suas capacidades"""
    resistividade = 0.0175
    
    # Tabela de referências de corrente máxima (valores aproximados para 30°C)
    capacidades = {
        1.5: 16, 2.5: 20, 4.0: 25, 6.0: 32, 10.0: 44,
        16.0: 60, 25.0: 80, 35.0: 100, 50.0: 125, 70.0: 160,
        95.0: 195, 120.0: 225, 150.0: 260, 185.0: 300, 240.0: 355
    }
    
    linhas = []
    for bitola, corrente_max in capacidades.items():
        resistencia_km = (resistividade / bitola) * 1000
        awg = mm2_para_awg(bitola)
        linhas.append([
            f"{bitola:.1f}",
            str(awg),
            str(corrente_max),
            f"{resistencia_km:.4f}"
        ])

    print(obter_tabela_bitolas_texto(linhas))


def obter_tabela_bitolas_texto(linhas=None):
    """Retorna em texto a tabela de referência de bitolas."""
    resistividade = 0.0175
    capacidades = {
        1.5: 16, 2.5: 20, 4.0: 25, 6.0: 32, 10.0: 44,
        16.0: 60, 25.0: 80, 35.0: 100, 50.0: 125, 70.0: 160,
        95.0: 195, 120.0: 225, 150.0: 260, 185.0: 300, 240.0: 355
    }

    if linhas is None:
        linhas = []
        for bitola, corrente_max in capacidades.items():
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

    secao_entrada = [
        "DADOS DE ENTRADA",
        f"- Distancia (m): {dados_entrada['distancia']}",
        f"- Corrente (A): {dados_entrada['corrente']}",
        f"- Tensao (V): {dados_entrada['tensao']}",
        f"- Queda maxima permitida (%): {dados_entrada['queda_percentual']}",
        f"- Temperatura ambiente (C): {dados_entrada['temp_amb']}",
        f"- Temperatura maxima do cabo (C): {dados_entrada['temp_max']}",
        f"- Diametro externo (mm): {dados_entrada['diametro'] if dados_entrada['diametro'] else 'estimado'}",
        ""
    ]

    tabela_principal = formatar_tabela(
        "RESULTADO PRINCIPAL - DIMENSIONAMENTO",
        ["Secao calc. (mm2)", "Bitola recomendada", "AWG", "Queda real (V)", "Queda real (%)", "Limite (%)", "Status"],
        linhas_principal
    )

    tabela_termica = formatar_tabela(
        "ANALISE TERMICA COMPARATIVA (AWG ANTERIOR, RECOMENDADO E PROXIMO)",
        ["Bitola (mm2)", "AWG", "Queda (V)", "Queda (%)", "P. Joule (W/m)", "Temp. regime (C)", "Tempo ate Tmax (min)", "Status queda"],
        linhas_termicas
    )

    secao_resumo = [
        "RESUMO EXECUTIVO",
        f"- Bitola recomendada: {resultado_principal['bitola_recomendada']:.2f} mm2 (AWG {resultado_principal['bitola_awg']})",
        f"- Comprimento total considerado (ida e volta): {resultado_principal['comprimento_total']:.2f} m",
        f"- Queda real: {resultado_principal['queda_tensao_volts']:.2f} V ({resultado_principal['queda_tensao_percentual']:.2f}%)",
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
        str(incluir_tabela_referencia)
    ])
    sufixo_hash = hashlib.sha1(assinatura.encode("utf-8")).hexdigest()[:8]

    return f"{base_legivel}_{sufixo_hash}.txt"


def main():
    """Função principal com interface interativa"""
    
    print("\n" + "="*80)
    print("CALCULADORA DE BITOLA IDEAL PARA CABO DC")
    print("="*80 + "\n")
    
    try:
        # Entradas principais
        distancia_input = input("Distância entre a fonte e o equipamento (metros) [padrão 10]: ").strip()
        distancia = float(distancia_input) if distancia_input else 10.0

        corrente_input = input("Corrente do equipamento (Amperes) [padrão 5]: ").strip()
        corrente = float(corrente_input) if corrente_input else 5.0

        tensao_input = input("Tensão do sistema (Volts DC) [padrão 12]: ").strip()
        tensao = float(tensao_input) if tensao_input else 12.0

        queda_input = input("Queda de tensão máxima permitida em % (padrão 3%): ")
        queda_percentual = float(queda_input) if queda_input else 3

        # Entradas térmicas já no mesmo fluxo
        temp_max_input = input("Temperatura máxima suportada pelo cabo (°C) [padrão 200]: ").strip()
        temp_max = float(temp_max_input) if temp_max_input else 200.0

        temp_amb_input = input("Temperatura ambiente (°C) [padrão 25]: ").strip()
        temp_amb = float(temp_amb_input) if temp_amb_input else 25

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

        # Cálculo principal de bitola
        resultado = calcular_bitola_cb(distancia, corrente, tensao, queda_percentual)

        # Tabela resumo do cálculo principal
        status_queda = "ADEQUADA" if resultado['queda_tensao_percentual'] <= resultado['queda_maxima_percentual'] else "ACIMA DO LIMITE"
        linhas_principal = [[
            f"{resultado['secao_calculada']:.2f}",
            f"{resultado['bitola_recomendada']:.2f}",
            f"{resultado['bitola_awg']}",
            f"{resultado['queda_tensao_volts']:.2f}",
            f"{resultado['queda_tensao_percentual']:.2f}",
            f"{resultado['queda_maxima_percentual']:.2f}",
            status_queda
        ]]

        imprimir_tabela(
            "RESULTADO PRINCIPAL - DIMENSIONAMENTO",
            ["Secao calc. (mm2)", "Bitola recomendada", "AWG", "Queda real (V)", "Queda real (%)", "Limite (%)", "Status"],
            linhas_principal
        )

        # Análise térmica comparativa: AWG anterior, recomendado e próximo
        bitolas_analise = obter_bitolas_analise_termica(resultado['bitola_recomendada'])
        linhas_termicas = []

        for bitola in bitolas_analise:
            awg = mm2_para_awg(bitola)
            queda = calcular_queda_para_bitola(bitola, resultado['comprimento_total'], corrente, tensao)
            termico = calcular_tempo_aquecimento(bitola, corrente, temp_max, temp_amb, diametro)

            if queda['queda_tensao_percentual'] <= resultado['queda_maxima_percentual']:
                status_termico = "OK"
            else:
                status_termico = "QUEDA ALTA"

            linhas_termicas.append([
                f"{bitola:.2f}",
                f"{awg}",
                f"{queda['queda_tensao_volts']:.2f}",
                f"{queda['queda_tensao_percentual']:.2f}",
                f"{termico['potencia_gerada_watts']:.2f}",
                f"{termico['temp_regimen_celsius']}",
                f"{termico['tempo_minutos']}",
                status_termico
            ])

        imprimir_tabela(
            "ANALISE TERMICA COMPARATIVA (AWG ANTERIOR, RECOMENDADO E PROXIMO)",
            ["Bitola (mm2)", "AWG", "Queda (V)", "Queda (%)", "P. Joule (W/m)", "Temp. regime (C)", "Tempo ate Tmax (min)", "Status queda"],
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
