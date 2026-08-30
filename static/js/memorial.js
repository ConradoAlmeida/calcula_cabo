(function () {
  "use strict";

  const STORAGE_KEY = "calc_memorial_payload";

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderItens(itens) {
    return (
      '<dl class="row mb-0 memorial-dl">' +
      itens
        .map(
          (item) =>
            '<dt class="col-sm-5 text-body-secondary">' +
            escapeHtml(item.rotulo) +
            "</dt>" +
            '<dd class="col-sm-7">' +
            escapeHtml(item.valor) +
            "</dd>"
        )
        .join("") +
      "</dl>"
    );
  }

  function renderPassos(passos) {
    return passos
      .map(
        (p, i) => `
      <div class="memorial-passo">
        <div class="memorial-passo-num">${i + 1}</div>
        <div class="memorial-passo-body">
          <h3 class="h6 mb-1">${escapeHtml(p.titulo)}</h3>
          <div class="memorial-formula"><code>${escapeHtml(p.formula)}</code></div>
          <div class="memorial-calculo">${escapeHtml(p.calculo)}</div>
          ${p.nota ? '<p class="text-body-secondary small mb-0 mt-2">' + escapeHtml(p.nota) + "</p>" : ""}
        </div>
      </div>`
      )
      .join("");
  }

  function renderTabelaComparativo(linhas) {
    const rows = linhas
      .map(
        (r) => `
      <tr class="${r.recomendada ? "table-primary" : ""}">
        <td>${escapeHtml(r.bitola)}</td>
        <td>${escapeHtml(r.awg)}</td>
        <td>${escapeHtml(r.vdrop_ini)}</td>
        <td>${escapeHtml(r.vdrop_fin)}</td>
        <td>${escapeHtml(r.temp_regime)}</td>
      </tr>`
      )
      .join("");

    return `
      <div class="table-responsive">
        <table class="table table-dark table-sm align-middle mb-0">
          <thead>
            <tr class="text-body-secondary">
              <th>Bitola</th><th>AWG</th><th>Vdrop inicial</th><th>Vdrop T. final</th><th>T regime (°C)</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function renderDiagramas(diagramas) {
    if (!diagramas || !diagramas.length) return "";

    return diagramas
      .map(
        (d) => `
      <section class="card shadow-sm memorial-secao memorial-diagrama" id="diag-${escapeHtml(d.id)}">
        <div class="card-body">
          <h2 class="h5 mb-2">${escapeHtml(d.titulo)}</h2>
          ${d.descricao ? '<p class="text-body-secondary small mb-3">' + escapeHtml(d.descricao) + "</p>" : ""}
          <div class="memorial-mermaid-wrap">
            <pre class="mermaid">${escapeHtml(d.mermaid)}</pre>
          </div>
        </div>
      </section>`
      )
      .join("");
  }

  function renderSecao(secao) {
    let body = "";
    if (secao.itens) {
      body = renderItens(secao.itens);
    } else if (secao.passos) {
      body = '<div class="memorial-passos">' + renderPassos(secao.passos) + "</div>";
    } else if (secao.tabela) {
      body = renderTabelaComparativo(secao.tabela);
    }

    return `
      <section class="card shadow-sm memorial-secao" id="sec-${escapeHtml(secao.id)}">
        <div class="card-body">
          <h2 class="h5 mb-3">${escapeHtml(secao.titulo)}</h2>
          ${body}
        </div>
      </section>`;
  }

  async function renderMemorial(memorial, principal) {
    document.title = memorial.titulo + " — Bitola DC";
    const subtitulo = principal
      ? "Bitola recomendada: " +
        principal.bitola_recomendada +
        " mm² (AWG " +
        principal.bitola_awg +
        ") · Vdrop T. final: " +
        principal.queda_final_volts +
        " V"
      : "";
    document.getElementById("memorial-subtitulo").textContent = subtitulo;

    const diagContainer = document.getElementById("memorial-diagramas");
    if (memorial.diagramas && memorial.diagramas.length) {
      diagContainer.innerHTML = renderDiagramas(memorial.diagramas);
      diagContainer.hidden = false;
    } else {
      diagContainer.innerHTML = "";
      diagContainer.hidden = true;
    }

    const container = document.getElementById("memorial-secoes");
    container.innerHTML = memorial.secoes.map(renderSecao).join("");

    if (typeof mermaid !== "undefined" && memorial.diagramas && memorial.diagramas.length) {
      mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        securityLevel: "strict",
        flowchart: { htmlLabels: true, curve: "basis" },
      });
      await mermaid.run({ querySelector: ".mermaid" });
    }
  }

  async function loadMemorial() {
    const empty = document.getElementById("memorial-empty");
    const content = document.getElementById("memorial-content");
    const raw = sessionStorage.getItem(STORAGE_KEY);

    if (!raw) {
      empty.hidden = false;
      content.hidden = true;
      return;
    }

    try {
      const payload = JSON.parse(raw);
      if (!payload.memorial) {
        throw new Error("sem memorial");
      }
      await renderMemorial(payload.memorial, payload.principal);
      empty.hidden = true;
      content.hidden = false;
    } catch (err) {
      empty.hidden = false;
      content.hidden = true;
    }
  }

  document.getElementById("btn-print").addEventListener("click", () => window.print());
  loadMemorial();
})();
