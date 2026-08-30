(function () {
  "use strict";

  const form = document.getElementById("form-bitola");
  const btnCalcular = document.getElementById("btn-calcular");
  const btnReset = document.getElementById("btn-reset");
  const btnDownload = document.getElementById("btn-download");
  const btnMemorial = document.getElementById("btn-memorial");
  const btnToggleRef = document.getElementById("btn-toggle-ref");
  const errorBox = document.getElementById("error-box");
  const emptyState = document.getElementById("empty-state");
  const resultContent = document.getElementById("result-content");
  const refWrap = document.getElementById("ref-wrap");
  const spinner = btnCalcular.querySelector(".spinner");
  const btnLabel = btnCalcular.querySelector(".btn-label");

  const defaults = {};
  form.querySelectorAll("input[type=number]").forEach((el) => {
    defaults[el.name] = el.value;
  });
  const metodoEl = form.elements["metodo_instalacao"];
  const metodoDefault = metodoEl ? metodoEl.value : null;
  const MEMORIAL_KEY = "calc_memorial_payload";

  function formData() {
    const data = {};
    form.querySelectorAll("input[type=number]").forEach((el) => {
      data[el.name] = el.value;
    });
    const metodo = form.elements["metodo_instalacao"];
    if (metodo) data["metodo_instalacao"] = metodo.value;
    const nCond = form.elements["n_condutores"];
    if (nCond) data["n_condutores"] = nCond.value;
    return data;
  }

  function setLoading(loading) {
    btnCalcular.disabled = loading;
    spinner.hidden = !loading;
    btnLabel.textContent = loading ? "Calculando..." : "Calcular bitola";
  }

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.hidden = false;
  }

  function clearError() {
    errorBox.hidden = true;
  }

  function pill(status) {
    if (status === "OK" || status === "APROVADO") {
      return `<span class="badge rounded-pill text-bg-success">${status}</span>`;
    }
    if (status === "REPROVADO") {
      return `<span class="badge rounded-pill text-bg-danger">${status}</span>`;
    }
    return `<span class="badge rounded-pill text-bg-warning">${status}</span>`;
  }

  function termicaRowClass(alerta) {
    if (alerta === "critico") return "termica-critico";
    if (alerta === "atencao") return "termica-atencao";
    return "";
  }

  function renderTermica(rows) {
    const body = document.getElementById("termica-body");
    body.innerHTML = rows
      .map(
        (r) => `
      <tr class="${r.recomendada ? "row-recomendada" : ""} ${termicaRowClass(r.alerta_termico)}">
        <td>${r.bitola}</td>
        <td>${r.awg}</td>
        <td>${r.queda_inicial_volts} V (${r.queda_inicial_percentual}%)</td>
        <td>${r.queda_final_volts} V (${r.queda_final_percentual}%)</td>
        <td>${r.potencia}</td>
        <td>${r.temp_regime}</td>
        <td>${r.resistividade_inicial}</td>
        <td>${r.resistividade_final}</td>
        <td>${r.tempo_minutos}</td>
        <td>${pill(r.status)}</td>
      </tr>`
      )
      .join("");
  }

  function renderReferencia(rows) {
    const body = document.getElementById("referencia-body");
    body.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.bitola}</td>
        <td>${r.awg}</td>
        <td>${r.corrente_max}</td>
        <td>${r.resistencia_km}</td>
      </tr>`
      )
      .join("");
  }

  function renderResult(data) {
    const p = data.principal;
    document.getElementById("hl-bitola").textContent = p.bitola_recomendada;
    document.getElementById("hl-awg").textContent = p.bitola_awg;
    document.getElementById("hl-secao-vdrop").textContent = p.secao_teorica_vdrop;
    document.getElementById("hl-secao-termica").textContent = p.secao_teorica_termica;
    document.getElementById("hl-queda-ini-v").textContent = p.queda_inicial_volts;
    document.getElementById("hl-queda-ini-p").textContent = p.queda_inicial_percentual;
    document.getElementById("hl-queda-fin-v").textContent = p.queda_final_volts;
    document.getElementById("hl-queda-fin-p").textContent = p.queda_final_percentual;
    document.getElementById("hl-limite").textContent = p.queda_maxima_percentual;
    document.getElementById("hl-limite-termico").textContent = p.pct_limite_termico;
    document.getElementById("hl-comp").textContent = p.comprimento_total;

    const badge = document.getElementById("status-badge");
    badge.textContent = p.status;
    badge.className =
      "badge rounded-pill fs-6 " +
      (p.aprovado || p.status === "APROVADO" ? "text-bg-success" : "text-bg-danger");

    const alertaBox = document.getElementById("alerta-termico-box");
    if (alertaBox) {
      if (p.alerta_termico_msg) {
        alertaBox.textContent = p.alerta_termico_msg;
        alertaBox.className =
          "alert py-2 px-3 mt-3 mb-0 small " +
          (p.aprovado || p.status === "APROVADO" ? "alert-success" : "alert-danger");
        alertaBox.hidden = false;
      } else {
        alertaBox.hidden = true;
      }
    }

    const info = document.getElementById("instalacao-info");
    if (info && data.instalacao) {
      const i = data.instalacao;
      info.innerHTML =
        'Instalação: <strong>' + i.rotulo + '</strong> · ' +
        'condutores agrupados: <strong>' + i.n_condutores + '</strong> · ' +
        'convecção efetiva: <strong>' + i.h_efetivo + ' W/(m²·°C)</strong>';
      info.hidden = false;
    }

    renderTermica(data.termicas);
    renderReferencia(data.referencia);

    const memorialPayload = {
      memorial: data.memorial,
      principal: data.principal,
      entradas: data.entradas,
    };
    try {
      sessionStorage.setItem(MEMORIAL_KEY, JSON.stringify(memorialPayload));
    } catch (err) {
      console.warn("sessionStorage indisponível; memorial recarregará via API.", err);
    }
    if (btnMemorial) btnMemorial.hidden = false;

    emptyState.hidden = true;
    resultContent.hidden = false;
  }

  async function calcular(evt) {
    evt.preventDefault();
    clearError();
    setLoading(true);
    try {
      const resp = await fetch("/api/calcular", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData()),
      });
      const data = await resp.json();
      if (!resp.ok) {
        showError(data.erro || "Erro ao calcular.");
        return;
      }
      renderResult(data);
    } catch (err) {
      showError("Falha de comunicação com o servidor.");
    } finally {
      setLoading(false);
    }
  }

  async function baixarRelatorio() {
    clearError();
    const payload = formData();
    payload.incluir_referencia = document.getElementById("incluir-ref").checked;
    try {
      const resp = await fetch("/api/relatorio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        showError(data.erro || "Erro ao gerar o relatório.");
        return;
      }
      const blob = await resp.blob();
      const disposition = resp.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : "relatorio_bitola_dc.txt";

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      showError("Falha ao baixar o relatório.");
    }
  }

  function resetForm() {
    Object.keys(defaults).forEach((name) => {
      const el = form.elements[name];
      if (el) el.value = defaults[name];
    });
    if (metodoEl && metodoDefault !== null) metodoEl.value = metodoDefault;
    syncVdropPresetActive();
    if (btnMemorial) btnMemorial.hidden = true;
    sessionStorage.removeItem(MEMORIAL_KEY);
    clearError();
    resultContent.hidden = true;
    emptyState.hidden = false;
  }

  function toggleRef() {
    const hidden = refWrap.hidden;
    refWrap.hidden = !hidden;
    btnToggleRef.textContent = hidden ? "Ocultar" : "Mostrar";
  }

  function syncVdropPresetActive() {
    const quedaInput = form.elements["queda_percentual"];
    if (!quedaInput) return;
    const val = parseFloat(quedaInput.value);
    document.querySelectorAll(".vdrop-preset").forEach((btn) => {
      const preset = parseFloat(btn.dataset.quedaPreset);
      btn.classList.toggle("active", !Number.isNaN(val) && val === preset);
    });
  }

  document.querySelectorAll(".vdrop-preset").forEach((btn) => {
    btn.addEventListener("click", () => {
      const quedaInput = form.elements["queda_percentual"];
      if (quedaInput) quedaInput.value = btn.dataset.quedaPreset;
      syncVdropPresetActive();
    });
  });
  const quedaInputEl = form.elements["queda_percentual"];
  if (quedaInputEl) {
    quedaInputEl.addEventListener("input", syncVdropPresetActive);
    syncVdropPresetActive();
  }

  form.addEventListener("submit", calcular);
  btnReset.addEventListener("click", resetForm);
  btnDownload.addEventListener("click", baixarRelatorio);
  btnToggleRef.addEventListener("click", toggleRef);

  if (btnMemorial) {
    btnMemorial.addEventListener("click", (evt) => {
      evt.preventDefault();
      window.location.href = "/memorial";
    });
  }
})();
