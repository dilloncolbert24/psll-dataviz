// One renderer per figure "kind" emitted by the notebook: plotly | table | matrix.
import { themeFigure } from "./theme.js";

const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) if (c != null) node.append(c);
  return node;
};

const fmt = (v) => {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(2);
  return String(v);
};

export function renderTable(tbl) {
  if (!tbl) return el("p", { class: "subtitle", text: "No data table." });
  const thead = el("thead", {}, el("tr", {}, ...tbl.columns.map((c) => el("th", { scope: "col", text: c }))));
  const tbody = el("tbody", {}, ...tbl.rows.map((r) => el("tr", {}, ...r.map((v) => el("td", { text: fmt(v) })))));
  return el("div", { class: "table-wrap" }, el("table", {}, thead, tbody));
}

function renderMatrix({ sites, rows }) {
  const thead = el("thead", {}, el("tr", {},
    el("th", { scope: "col", text: "Evidence stream" }),
    ...sites.map((s) => el("th", { scope: "col", text: s }))));
  const tbody = el("tbody");
  for (const row of rows) {
    const isContext = /Environmental|Spatial/.test(row.stream);
    const tr = el("tr", { class: isContext ? "context" : "" },
      el("th", { scope: "row" }, row.stream, el("span", { class: "detail", text: row.metric })));
    for (const s of sites) {
      const c = row.cells[s];
      const tag = c.favorability ? el("span", { class: `tag ${c.favorability}`, text: c.favorability }) : null;
      tr.append(el("td", { class: "cell" },
        el("span", { class: "arrow", "aria-label": c.arrow, text: c.arrow }), tag,
        el("span", { class: "detail", text: c.detail })));
    }
    tbody.append(tr);
  }
  return el("div", { class: "table-wrap matrix" }, el("table", {}, thead, tbody));
}

// Text cards (stage 4): blocks are {h} | {p} | {list}; references are listed under the text.
function renderArticle({ blocks }) {
  const body = el("div", { class: "article" });
  for (const b of blocks) {
    if (b.h) body.append(el("h4", { text: b.h }));
    else if (b.p) body.append(el("p", { text: b.p }));
    else if (b.list) body.append(el("ul", {}, ...b.list.map((t) => el("li", { text: t }))));
  }
  return body;
}

function renderReferences(refs) {
  const items = refs.map((r) => {
    const href = r.doi ? `https://doi.org/${r.doi}` : r.url;
    const link = href ? el("a", { href, target: "_blank", rel: "noopener", text: r.doi ? `doi:${r.doi}` : "link" }) : null;
    const lib = r.in_library ? el("span", { class: "chip", text: "In team library" }) : null;
    return el("li", {}, `${r.cite} `, link, lib);
  });
  return el("details", { class: "refs" }, el("summary", { text: `References (${refs.length})` }), el("ol", {}, ...items));
}

// Plotly charts are tracked so they can be re-themed / resized without refetching.
const livePlots = new Map(); // node -> figure spec

// Phones: drag-to-zoom would swallow the page's scroll gesture, and desktop margins waste the narrow width.
const narrow = window.matchMedia("(max-width: 700px)");
const touch = window.matchMedia("(pointer: coarse)");

function mobileLayout(layout) {
  if (touch.matches) {
    layout.dragmode = false;
    for (const key of Object.keys(layout)) {
      if (/^[xy]axis\d*$/.test(key)) layout[key] = { ...layout[key], fixedrange: true };
    }
  }
  if (narrow.matches) {
    layout.margin = { ...layout.margin, r: 8 };
    layout.font = { ...layout.font, size: 11 };
  }
  return layout;
}

function drawPlot(node, figure) {
  const themed = themeFigure(figure);
  const layout = mobileLayout({ ...themed.layout, autosize: true, height: figure.layout.height });
  Plotly.react(node, themed.data, layout,
    { responsive: true, displaylogo: false, displayModeBar: narrow.matches ? false : "hover",
      scrollZoom: false, modeBarButtonsToRemove: ["select2d", "lasso2d"] });
}

// Rotating a phone or resizing a window across the breakpoint re-applies the layout tweaks.
narrow.addEventListener("change", () => rethemeAll());
touch.addEventListener("change", () => rethemeAll());

export function rethemeAll() {
  for (const [node, fig] of livePlots) {
    if (!node.isConnected) livePlots.delete(node);
    else drawPlot(node, fig);
  }
}

export function renderCard(spec) {
  const chips = el("div", { class: "chips" }, el("span", { class: "chip", text: spec.layer }));
  if (spec.exploratory) chips.append(el("span", { class: "chip exploratory", text: "Exploratory" }));
  if (spec.backup) chips.append(el("span", { class: "chip", text: "Backup" }));

  const card = el("article", { class: "card", id: `fig-${spec.id}` },
    chips, el("h3", { text: spec.title }),
    spec.subtitle ? el("p", { class: "subtitle", text: spec.subtitle }) : null);

  if (spec.kind === "plotly") {
    const plot = el("div", { class: "plot", role: "img", "aria-label": spec.title });
    card.append(plot);
    livePlots.set(plot, spec.figure);
    requestAnimationFrame(() => drawPlot(plot, spec.figure));
  } else if (spec.kind === "matrix") {
    card.classList.add("wide");
    card.append(renderMatrix(spec.payload));
  } else if (spec.kind === "article") {
    card.append(renderArticle(spec.payload));
    if (spec.payload.references?.length) card.append(renderReferences(spec.payload.references));
  } else {
    card.append(renderTable(spec.table));
  }

  if (spec.notes?.length) card.append(el("ul", { class: "notes" }, ...spec.notes.map((n) => el("li", { text: n }))));
  if (spec.kind !== "table" && spec.table) {
    card.append(el("details", {}, el("summary", { text: "Show data" }), renderTable(spec.table)));
  }
  return card;
}

export function renderQC(items) {
  if (!items.length) return el("p", { class: "empty", text: "No QC messages — all inputs passed validation." });
  const order = { error: 0, warning: 1, info: 2 };
  const sorted = [...items].sort((a, b) => order[a.level] - order[b.level]);
  return el("ul", { class: "qc-list" }, ...sorted.map((q) =>
    el("li", { class: q.level }, el("span", { class: "lvl", text: q.level }), `${q.layer}: ${q.message}`)));
}

export { el };
