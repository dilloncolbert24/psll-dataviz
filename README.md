# PSLL data-viz workflow

Python (Colab or VS Code) does all the analysis and **writes the charts as JSON**; a static JavaScript page
served by Vite reads that JSON and renders it with Plotly.js — on your computer and on your phone (same Wi-Fi).

```
 raw_data/real/*.csv          notebooks/psll_pipeline.ipynb              web/ (Vite :8000)
 ───────────────────   ──►   ───────────────────────────────   ──►   ─────────────────────────
 12 CSVs, 3 layers           validate → consensus → deltas           index.html + js/main.js
 (see docs/DATA_DICTIONARY)  → evidence matrix → Plotly figs          fetches data/manifest.json
                             writes web/data/manifest.json            and data/figures/<id>.json
                                    web/data/figures/*.json           re-checks every 10 s
                                    web/data/*.csv (for stats)
```

## Layout

| Path | What |
|---|---|
| `raw_data/templates/` | Empty CSVs with the exact headers (`raw_data/real/` starts as a copy — fill those in) |
| `raw_data/sample/` | **Synthetic** test data (`scripts/make_sample_data.py`) so everything runs before fieldwork data exists |
| `notebooks/psll_pipeline.ipynb` | The pipeline. Runs unchanged in Colab or VS Code |
| `web/` | Dashboard: `index.html`, `css/`, `js/api.js` (data), `js/theme.js`, `js/renderers.js`, `js/main.js` |
| `web/data/` | Notebook output — don't edit by hand |
| `package.json`, `vite.config.js` | Vite dev server for `web/` (port 8000). `npm run publish:site` → personal site `/psll/` |
| `content/so_what_next.json` | Text + references for the *So what next?* tab |
| `scripts/polar_live.py`, `scripts/import_silver.py` | Live H10 recording; team-pipeline silver → `raw_data/real/` |
| `scripts/publish_site.mjs` | Copies `web/` into `~/Developer/personalSite/public/psll/` (blocks real data by default) |
| `.vscode/` | Tasks: serve dashboard, run notebook, regenerate sample data |

## Run it in VS Code

One-time: install [Node.js](https://nodejs.org) (18+), then `npm install` at the project root
(or `Terminal → Run Task → Install dashboard dependencies`).

1. Install recommended extensions when prompted (Python, Jupyter).
2. `Terminal → Run Task → Run pipeline notebook (local)` (or open the notebook and **Run All**).
3. `Terminal → Run Build Task` (⇧⌘B) → runs `npm run dev`.

Equivalent from a terminal at the project root:

```bash
npm run dev          # = vite --host; prints a Local and a Network URL
```

## View it on your phone (published to the personal site)

The study Wi-Fi blocks phone ↔ laptop connections, so the phone version lives on the personal website at
**`<your site>/psll/`** (unlisted, `noindex`). `web/` is copied into `~/Developer/personalSite/public/psll/`:

```bash
npm run publish:site            # copies web/ → personalSite/public/psll/ (synthetic data only)
cd ~/Developer/personalSite && git add public/psll && git commit -m "Update PSLL dashboard" && git push
```

- The personal site's repo and website are **public**. The script refuses to copy real study data
  (`manifest.synthetic = false`) unless run with `-- --allow-real`; only do that once public release is cleared.
- The site doesn't see Drive updates live: re-run the notebook → `publish:site` → push to update it.
- On touch screens charts don't drag-zoom (the page scrolls normally); tap a point for its value.
  Set `PSLL_SITE_DIR` if the site lives somewhere else.

`npm run dev` still serves the dashboard on this computer (and on the LAN, on networks that allow it).
`npm run dev:local` binds to localhost only. Without Node:
`python3 -m http.server 8000 --directory web`.

## Run it in Colab (connecting the two workflows)

**Recommended:** keep this whole folder in Google Drive at `My Drive/PSLL Dataviz` and install
Google Drive for Desktop so the same folder is open in VS Code on your laptop.

1. Open `notebooks/psll_pipeline.ipynb` in Colab (Drive → right-click → Open with → Colaboratory).
2. Run all. The first cell mounts Drive; outputs are written to `My Drive/PSLL Dataviz/web/data/`.
3. Drive syncs to your laptop → the dashboard (desktop and phone) notices the new `generated_at` and redraws within ~10 s.

Without Drive sync: the last cell also downloads `psll_web_data.zip` — unzip it into `web/data/`.

## Automated data flow

```
 Polar H10 ──(live, Bluetooth)──► scripts/polar_live.py ──► P###.csv ─┐
 Polar H10 ──(phone app export)───────────────────────────────────────┤
                                                                      ├─► team pipelines (PSLL_Data:
 Frigga M2H ──(USB → .xlsx report)────────────────────────────────────┤    polar_pipeline, frigga_pipeline,
 PsyToolkit / observation sheets ─────────────────────────────────────┘    psytoolkit, obs) → *_silver_*.csv
                                                                              │
 scripts/import_silver.py ◄───────────────────────────────────────────────────┘
        ▼
 raw_data/real/physiology.csv, frigga_log.csv ──► notebook ──► web/data ──► dashboard
```

| Step | Command | Notes |
|---|---|---|
| Live H10 recording | `python3 scripts/polar_live.py P001 PRE --minutes 5` | Needs `pip install bleakheart`. Streams HR + RR over Bluetooth (no phone app), prints HR / RMSSD / artifact % every 10 s, saves in the format `polar_pipeline` reads. `--simulate` tests without a strap; `--live-json` keeps a rolling summary file. |
| Team pipelines | see `PSLL_Data` (franzloza) | Raw exports → bronze → silver CSVs + QC flags. |
| Bridge | `python3 scripts/import_silver.py --outputs ".../PSLL_Data/_outputs" [--roster roster.csv]` | Newest silver → `raw_data/real/`. Site from roster (`Participant_ID, Space`) or `affect.csv`. QC flags → `quality_flag = check`. Old files backed up to `raw_data/real/_previous/`. `--dry-run` previews. |
| Notebook | VS Code task *Run pipeline notebook (local)* | Set `USE_SAMPLE_DATA = False` for real data. |

**Device notes**
- **Polar H10** streams live (standard BLE heart-rate service; ECG/accelerometer via Polar's PMD service).
  The official PolarBleSDK is Android/iOS only; on a laptop use `bleakheart` (MPL-2.0) on top of Bleak.
  A strap streams to one device at a time, so close Polar apps on nearby phones.
- **Frigga M2H** has no live link or API: it is a USB logger that writes PDF/CSV/.xlsx reports, handled by
  `frigga_pipeline`. Frigga's 4G models (V5 series) report to Frigga Cloud, but no public API was found.
  For live temperature and humidity, an open BLE sensor such as RuuviTag (`ruuvitag-sensor` Python package)
  can sit next to the Frigga, with the Frigga kept as the reference.
- **Live data on the website** would need a small backend, because the site is static (Cloudflare Pages).
  Only aggregated values should go there, and only once ethics approval covers it; see the *So what next?* tab.

## Stage 4 · So what next?

Text cards come from `content/so_what_next.json`, with references from the team library in Drive
(*Data Science Protocols → dashboards → literature*) plus newer citizen-science and wearables work. Edit the
JSON, re-run the notebook, and the tab updates.

## Going from sample to real data

1. Transcribe sheets into `raw_data/real/` using the templates (rules in `docs/DATA_DICTIONARY.md`).
2. In the notebook's config cell set `USE_SAMPLE_DATA = False`.
3. Run, then open the **Data quality** tab — fix any *errors* in the CSVs and re-run.
   The yellow "synthetic data" banner disappears automatically.

## Adding a figure

In the notebook, build a Plotly figure and call
`register(id, stage, layer, title, subtitle, fig, data_table)`. Tag each trace with
`meta={"color": "series-1"}` (or `series-2`, `muted`) instead of relying on the hex — the page swaps in the
light/dark palette. `kind="table"` (a `table(df)` payload) and `kind="matrix"` are also supported.
The page needs no changes: it renders whatever the manifest lists.

## Open questions for the team

- The observation protocol says "continuously for **25** minutes" in *What you will record* but the sheet has 4×5-min
  intervals (20 min). The pipeline assumes 20.
- Are the two field-sheet layouts (with/without sitting · standing · pair/group) both in use? The pipeline handles both
  via `sheet_version`.
- Is there one Frigga for both spaces or one each? Windows are per site; the log is currently a single file.
- PANAS scale: the doc says 7-point Likert; standard PANAS is 5-point. Range checks assume 1–7.
