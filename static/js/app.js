(function () {
  "use strict";

  const form = document.getElementById("form-bitola");
  const btnCalcular = document.getElementById("btn-calcular");
  const btnReset = document.getElementById("btn-reset");
  const btnDownload = document.getElementById("btn-download");
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

  function formData() {
    const data = {};
    form.querySelectorAll("input[type=number]").forEach((el) => {
      data[el.name] = el.value;
    });
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
    const ok = status === "OK" || status === "ADEQUADA";
    return `<span class="badge rounded-pill ${ok ? "text-bg-success" : "text-bg-warning"}">${status}</span>`;
  }

  function renderTermica(rows) {
    const body = document.getElementById("termica-body");
    body.innerHTML = rows
      .map(
        (r) => `
      <tr class="${r.recomendada ? "table-primary" : ""}">
        <td>${r.bitola}</td>
        <td>${r.awg}</td>
        <td>${r.queda_volts}</td>
        <td>${r.queda_percentual}</td>
        <td>${r.potencia}</td>
        <td>${r.temp_regime}</td>
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
    document.getElementById("hl-secao").textContent = p.secao_calculada;
    document.getElementById("hl-queda-v").textContent = p.queda_tensao_volts;
    document.getElementById("hl-queda-p").textContent = p.queda_tensao_percentual;
    document.getElementById("hl-limite").textContent = p.queda_maxima_percentual;
    document.getElementById("hl-comp").textContent = p.comprimento_total;

    const badge = document.getElementById("status-badge");
    badge.textContent = p.status;
    badge.className = "badge rounded-pill fs-6 " + (p.adequada ? "text-bg-success" : "text-bg-warning");

    renderTermica(data.termicas);
    renderReferencia(data.referencia);

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
    form.elements["diametro"].value = "";
    clearError();
    resultContent.hidden = true;
    emptyState.hidden = false;
  }

  function toggleRef() {
    const hidden = refWrap.hidden;
    refWrap.hidden = !hidden;
    btnToggleRef.textContent = hidden ? "Ocultar" : "Mostrar";
  }

  form.addEventListener("submit", calcular);
  btnReset.addEventListener("click", resetForm);
  btnDownload.addEventListener("click", baixarRelatorio);
  btnToggleRef.addEventListener("click", toggleRef);
})();
