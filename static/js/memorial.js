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
      <tr class="${r.recomendada ? "row-recomendada" : ""}">
        <td>${escapeHtml(r.bitola)}</td>
        <td>${escapeHtml(r.awg)}</td>
        <td>${escapeHtml(r.vdrop_ini)}</td>
        <td>${escapeHtml(r.vdrop_fin)}</td>
        <td>${escapeHtml(r.temp_regime)}</td>
        <td>${renderStatusBadge(r.status)}</td>
      </tr>`
      )
      .join("");

    return `
      <div class="table-responsive">
        <table class="table table-dark table-sm align-middle mb-0">
          <thead>
            <tr class="text-body-secondary">
              <th>Bitola</th><th>AWG</th><th>Vdrop inicial</th><th>Vdrop T. final</th><th>T regime (°C)</th><th>Status</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function renderStatusBadge(status) {
    if (status === "APROVADO") {
      return '<span class="badge rounded-pill text-bg-success">APROVADO</span>';
    }
    if (status === "REPROVADO") {
      return '<span class="badge rounded-pill text-bg-danger">REPROVADO</span>';
    }
    return escapeHtml(status || "—");
  }

  function renderTextos(textos) {
    return (
      '<ul class="memorial-resumo mb-0">' +
      textos.map((t) => "<li>" + escapeHtml(t) + "</li>").join("") +
      "</ul>"
    );
  }

  function renderDiagramas(diagramas) {
    if (!diagramas || !diagramas.length) return { html: "", nodes: [] };

    const nodes = [];
    const parts = diagramas.map((d) => {
      const id = "mermaid-" + d.id;
      nodes.push({ id: id, source: d.mermaid });
      return `
      <section class="card shadow-sm memorial-secao memorial-diagrama" id="diag-${escapeHtml(d.id)}">
        <div class="card-body">
          <h2 class="h5 mb-2">${escapeHtml(d.titulo)}</h2>
          ${d.descricao ? '<p class="text-body-secondary small mb-3">' + escapeHtml(d.descricao) + "</p>" : ""}
          <div class="memorial-mermaid-wrap">
            <pre class="mermaid" id="${escapeHtml(id)}"></pre>
          </div>
        </div>
      </section>`;
    });

    return { html: parts.join(""), nodes: nodes };
  }

  function renderSecao(secao) {
    let body = "";
    if (secao.textos) {
      body = renderTextos(secao.textos);
    } else if (secao.itens) {
      body = renderItens(secao.itens);
    } else if (secao.passos) {
      body = '<div class="memorial-passos">' + renderPassos(secao.passos) + "</div>";
    } else if (secao.tabela) {
      body = renderTabelaComparativo(secao.tabela);
    }

    return `
      <section class="card shadow-sm memorial-secao${secao.id === "resumo" ? " memorial-resumo-card" : ""}" id="sec-${escapeHtml(secao.id)}">
        <div class="card-body">
          <h2 class="h5 mb-3">${escapeHtml(secao.titulo)}</h2>
          ${body}
        </div>
      </section>`;
  }

  async function renderMermaidDiagrams(nodes) {
    if (!nodes.length) return;

    const preElements = nodes
      .map((n) => {
        const el = document.getElementById(n.id);
        if (el) el.textContent = n.source;
        return el;
      })
      .filter(Boolean);

    if (!preElements.length) return;

    if (typeof mermaid === "undefined") {
      preElements.forEach((el) => {
        el.classList.add("memorial-mermaid-fallback");
      });
      return;
    }

    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "loose",
      flowchart: { htmlLabels: true, curve: "basis" },
    });

    for (const el of preElements) {
      try {
        await mermaid.run({ nodes: [el] });
      } catch (err) {
        console.warn("Mermaid indisponível; exibindo texto do diagrama.", err);
        el.classList.add("memorial-mermaid-fallback");
      }
    }
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
    const diagramPack = renderDiagramas(memorial.diagramas);
    if (diagramPack.html) {
      diagContainer.innerHTML = diagramPack.html;
      diagContainer.hidden = false;
    } else {
      diagContainer.innerHTML = "";
      diagContainer.hidden = true;
    }

    const container = document.getElementById("memorial-secoes");
    container.innerHTML = memorial.secoes.map(renderSecao).join("");

    const footerCert = document.querySelector(".app-footer-cert");
    if (footerCert && memorial.rodape_certificacao) {
      footerCert.textContent = memorial.rodape_certificacao;
    }

    // Mermaid mede o DOM; precisa estar visível antes do render.
    showContent();
    await renderMermaidDiagrams(diagramPack.nodes);
  }

  function readStoredPayload() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (err) {
      console.warn("Falha ao ler sessionStorage do memorial.", err);
      return null;
    }
  }

  function savePayload(payload) {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch (err) {
      console.warn("Falha ao gravar sessionStorage; memorial usará API.", err);
    }
  }

  async function fetchPayloadFromApi(entradas) {
    const resp = await fetch("/api/calcular", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(entradas),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.erro || "Erro ao recarregar o memorial.");
    }
    return data;
  }

  function showEmpty(message) {
    const empty = document.getElementById("memorial-empty");
    const content = document.getElementById("memorial-content");
    const msg = empty.querySelector("p.text-body-secondary");
    if (msg && message) msg.textContent = message;
    empty.hidden = false;
    content.hidden = true;
  }

  function showContent() {
    document.getElementById("memorial-empty").hidden = true;
    document.getElementById("memorial-content").hidden = false;
  }

  async function loadMemorial() {
    let payload = readStoredPayload();

    if (!payload || !payload.entradas) {
      showEmpty("Execute um dimensionamento na calculadora para gerar o memorial.");
      return;
    }

    if (!payload.memorial || !payload.principal) {
      try {
        payload = await fetchPayloadFromApi(payload.entradas);
        savePayload({
          memorial: payload.memorial,
          principal: payload.principal,
          entradas: payload.entradas,
        });
      } catch (err) {
        showEmpty(err.message || "Não foi possível carregar o memorial.");
        return;
      }
    }

    if (!payload.memorial) {
      showEmpty("O servidor não retornou dados de memorial para este cálculo.");
      return;
    }

    try {
      await renderMemorial(payload.memorial, payload.principal);
    } catch (err) {
      console.error(err);
      showEmpty("Erro ao renderizar o memorial. Tente calcular novamente.");
    }
  }

  document.getElementById("btn-print").addEventListener("click", () => window.print());
  loadMemorial();
})();
