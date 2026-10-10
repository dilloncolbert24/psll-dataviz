// Data access layer: everything the page knows comes from web/data/*.json written by the notebook.
const DATA_ROOT = "data";
const figureCache = new Map();

async function getJSON(path) {
  const res = await fetch(`${DATA_ROOT}/${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${DATA_ROOT}/${path}`);
  return res.json();
}

export const loadManifest = () => getJSON("manifest.json");

export async function loadFigure(id) {
  if (!figureCache.has(id)) figureCache.set(id, getJSON(`figures/${id}.json`));
  return figureCache.get(id);
}

export function clearCache() {
  figureCache.clear();
}

// Poll the manifest; call onChange when the notebook has re-exported (generated_at changed).
// Skips ticks while the tab is hidden (phone locked / backgrounded) and checks immediately on return.
export function watchManifest(current, onChange, intervalMs = 10000) {
  let stamp = current.generated_at;
  const check = async () => {
    if (document.hidden) return;
    try {
      const m = await loadManifest();
      if (m.generated_at !== stamp) {
        stamp = m.generated_at;
        clearCache();
        onChange(m);
      }
    } catch {
      /* data folder mid-write; try again next tick */
    }
  };
  document.addEventListener("visibilitychange", check);
  return setInterval(check, intervalMs);
}
