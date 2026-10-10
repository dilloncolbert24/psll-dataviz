// Light/dark handling. Python tags each trace with meta.color = a palette role ("series-1", "muted", ...);
// here roles are resolved to the current theme's CSS custom properties.
const STORAGE_KEY = "psll-theme";
const listeners = new Set();

export const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();

export function initTheme(button) {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) document.documentElement.dataset.theme = saved;
  } catch { /* storage blocked */ }

  button.addEventListener("click", () => {
    const next = isDark() ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* ignore */ }
    notify();
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", notify);
}

export const isDark = () => cssVar("page").toLowerCase() === "#0d0d0d";
export const onThemeChange = (fn) => listeners.add(fn);
const notify = () => listeners.forEach((fn) => fn());

// Return a themed deep copy of a Plotly {data, layout} spec.
export function themeFigure(figure) {
  const fig = structuredClone(figure);
  const ink = cssVar("text-secondary");
  const muted = cssVar("text-muted");
  const grid = cssVar("grid");
  const axis = cssVar("axis");
  const surface = cssVar("surface-1");

  for (const trace of fig.data) {
    const role = trace.meta?.color;
    if (!role) continue;
    const color = cssVar(role);
    if (trace.line) trace.line.color = color;
    if (trace.marker) {
      trace.marker.color = color;
      if (trace.marker.line) trace.marker.line.color = surface;
    }
    if (trace.error_y) trace.error_y.color = color;
  }

  const L = fig.layout;
  L.font = { ...L.font, color: ink };
  L.paper_bgcolor = "rgba(0,0,0,0)";
  L.plot_bgcolor = "rgba(0,0,0,0)";
  L.hoverlabel = { bgcolor: surface, bordercolor: axis, font: { color: cssVar("text-primary") } };
  for (const key of Object.keys(L)) {
    if (/^[xy]axis\d*$/.test(key)) {
      L[key] = { ...L[key], gridcolor: grid, linecolor: axis, tickfont: { color: muted } };
    }
  }
  for (const a of L.annotations ?? []) a.font = { ...a.font, color: ink };
  for (const s of L.shapes ?? []) {
    if (s.type === "rect") s.fillcolor = grid;
    if (s.type === "line" && s.line) s.line.color = axis;
  }
  return fig;
}
