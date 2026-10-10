// App shell: reads the manifest, builds stage tabs (Day 3 flow), and renders figures for the active tab.
import { loadManifest, loadFigure, watchManifest } from "./api.js";
import { initTheme, onThemeChange } from "./theme.js";
import { renderCard, renderQC, rethemeAll, el } from "./renderers.js";

const $ = (id) => document.getElementById(id);
let manifest;

function tabsFor(m) {
  const tabs = m.stages.map((s) => ({
    key: `stage-${s.id}`, label: `${s.id} · ${s.title}`, stage: s,
    figures: m.figures.filter((f) => f.stage === s.id && !f.backup),
  }));
  tabs.push({ key: "backup", label: "Backup metrics", figures: m.figures.filter((f) => f.backup),
    stage: { title: "Backup metrics", prompt: "Secondary metrics kept out of the main presentation." } });
  const issues = m.qc.filter((q) => q.level !== "info").length;
  tabs.push({ key: "qc", label: "Data quality", qc: true, count: issues,
    stage: { title: "Data quality", prompt: "Validation messages from the notebook. Resolve errors before presenting." } });
  return tabs;
}

function renderHeader(m) {
  $("project-title").textContent = m.project;
  $("research-question").textContent = m.research_question;
  $("synthetic-banner").hidden = !m.synthetic;
  const c = m.counts;
  $("meta-line").textContent =
    `Generated ${new Date(m.generated_at).toLocaleString()} · ${c.participants} participants · ` +
    `${c.observation_sheets} observation sheets · ${c.frigga_readings} Frigga readings · ${m.sites.join(" / ")}`;
}

async function showTab(tab) {
  document.querySelectorAll(".tab").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.key === tab.key)));
  // On phones the tab strip scrolls sideways; keep the active tab visible.
  document.querySelector(`.tab[data-key="${tab.key}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
  const intro = $("stage-intro");
  intro.replaceChildren(el("h2", { text: tab.stage.title }), el("p", { class: "prompt", text: tab.stage.prompt }));

  const grid = $("figure-grid");
  if (tab.qc) {
    grid.replaceChildren(el("div", { class: "card wide" }, renderQC(manifest.qc)));
    return;
  }
  if (!tab.figures.length) {
    grid.replaceChildren(el("p", { class: "empty", text: "No figures in this section yet." }));
    return;
  }
  grid.replaceChildren(el("p", { class: "empty", text: "Loading…" }));
  const specs = await Promise.all(tab.figures.map((f) => loadFigure(f.id)));
  grid.replaceChildren(...specs.map(renderCard));
}

function render(m) {
  manifest = m;
  renderHeader(m);
  const tabs = tabsFor(m);
  const nav = $("stage-tabs");
  nav.replaceChildren(...tabs.map((t) => {
    const b = el("button", { class: "tab", role: "tab", type: "button", "data-key": t.key }, t.label);
    const n = t.count ?? t.figures?.length;
    if (n) b.append(el("span", { class: "count", text: `(${n})` }));
    b.addEventListener("click", () => { location.hash = t.key; });
    return b;
  }));
  const route = () => showTab(tabs.find((t) => t.key === location.hash.slice(1)) ?? tabs[0]);
  window.onhashchange = route;
  route();
}

async function boot() {
  initTheme($("theme-toggle"));
  onThemeChange(rethemeAll);
  try {
    const m = await loadManifest();
    render(m);
    watchManifest(m, render);
  } catch (err) {
    $("figure-grid").replaceChildren(el("div", { class: "error-state" },
      el("p", { text: "Could not load data/manifest.json." }),
      el("p", { text: "Run the notebook (it writes web/data/), and serve the web/ folder over http — opening index.html as a file:// URL blocks fetch()." }),
      el("code", { text: String(err.message) })));
  }
}

boot();
