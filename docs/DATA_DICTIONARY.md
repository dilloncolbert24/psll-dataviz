# PSLL raw data dictionary

One CSV per table, UTF-8, header row exactly as in `raw_data/templates/`. Leave a cell **blank** for
missing / not applicable (don't type `NA`, `-`, or `0` for "not recorded").
Allowed values are case-sensitive except `condition` (`pre` is accepted and upper-cased).

Shared keys:

| Key | Format | Example |
|---|---|---|
| `site` | `Space A` \| `Space B` | `Space A` |
| `condition` | `PRE` \| `POST` | `POST` |
| `date` | `YYYY-MM-DD` | `2026-10-01` |
| times | 24h `HH:MM` | `15:45` |
| `sheet_id` | one per paper observation sheet | `S07` |
| `participant_id` | stable across all individual files | `AP03` |

---

## Layer 2 · Behavior — source: *Observation / Behavioral Sheet* (owner: Dillon)

### `observation_sessions.csv` — one row per paper sheet (22 rows)
| Column | Type | Notes |
|---|---|---|
| sheet_id | text | Write it on the paper sheet too |
| site, condition | category | |
| observer_id | text | Same observer keeps the same ID PRE and POST |
| date, start_time, end_time | date / time | |
| sheet_version | `short` \| `full` | `short` = first page layout (no sitting / standing / pair-group columns) |
| boundary_confirmed, count_line_confirmed, zones_confirmed | `True` \| `False` | Site-reference checkboxes |

### `movement_counts.csv` — section A, one row per sheet × 5-min interval
| Column | Type | Notes |
|---|---|---|
| sheet_id | text | |
| interval_start_min, interval_end_min | int | `0,5` · `5,10` · `10,15` · `15,20` |
| total_crossing | int | |
| direction_1, direction_2 | int, optional | Only if direction was recorded |

### `snapshots.csv` — section B, one row per sheet × snapshot (5, 10, 15, 20 min)
| Column | Type | Rule checked by the notebook |
|---|---|---|
| snapshot_min | 5 \| 10 \| 15 \| 20 | |
| total_stationary | int | |
| sitting, standing_leaning | int | blank on `short` sheets; sitting + standing ≤ total |
| social_interaction, alone | int | social + alone = total |
| pair_group | int | blank on `short` sheets |
| intervention_use | int | **POST only** — blank for PRE |

### `field_notes.csv` — section D, one row per note
`sheet_id, approx_time, event` — factual events only (rain, delivery vehicle, school group…), no interpretation.

---

## Layer 3 · Context — source: *Environmental and Spatial Coding*

### `frigga_log.csv` — Frigga M2H export, 5-min logging, 09:00–17:00
`timestamp` (`YYYY-MM-DD HH:MM`), `temperature_c`, `relative_humidity_pct`.
Rename the Frigga export's columns to these three names; extra columns are ignored.

### `experimental_windows.csv` — one row per site × exposure window
| Column | Values |
|---|---|
| window | free label, e.g. `PRE Rotation`, `PRE Behavior`, `POST Rotation`, `POST Behavior` |
| phase | `rotation` \| `behavior` |
| condition | `PRE` \| `POST` |
| date, start_time, end_time | the actual clock times used that day |

### `env_manual.csv` — manually coded conditions, one row per site × check
| Column | Coding |
|---|---|
| sun_condition | 0 overcast · 1 mostly cloudy · 2 partly sunny · 3 clear/direct sun |
| wind | 0 calm · 1 light · 2 moderate · 3 strong |
| precipitation | 0 none · 1 light · 2 moderate/heavy |
| ground_condition | 0 dry · 1 damp · 2 wet |
| noise (optional) | 0 low · 1 moderate · 2 high |

### `spatial_conditions.csv` — one row per site × condition (record once before PRE, once after installation)
| Column | Values |
|---|---|
| available_seating, seats_occupied_start | int |
| shade | `None` \| `Partial` \| `Majority` |
| vegetation | `None` \| `Existing` |
| landmark, signage, ground_intervention | `Yes` \| `No` |
| other_temporary | free text |
| photo_file | filename of the standardized photograph |

### `intervention_components.csv` — POST table, one row per site × component
`site, component, installed (Yes|No), units, notes`. Components: Added seating, Shade,
Rug / ground definition, Plants / vegetation, Landmark, Signage, Other.

---

## Layer 1 · Individual — sources: PsyToolkit (Julia), Polar (Julia / Marce)

One row per participant × condition in each file.

### `affect.csv`
`positive_affect`, `negative_affect`, `perceived_restoration` — 1–7 Likert (out-of-range values are flagged).
Derived in the notebook: `affect_balance = positive − negative` (the "PANAS" row of the matrix).

### `physiology.csv`
`rmssd_ms`, `mean_hr_bpm`, `sdnn_ms`, `quality_flag` = `ok` \| `check` (kept, listed in QC) \| `exclude` (blanked).

### `cognition.csv`
`pvt_median_rt_ms`, `pvt_lapses`, `flanker_accuracy` (0–1), `flanker_congruent_rt_ms`, `flanker_incongruent_rt_ms`.
Derived: `flanker_interference_ms = incongruent − congruent`.

Primary metrics for the main presentation are set in the notebook's `PRIMARY_METRICS`
(default: PVT median RT for attention, Flanker interference for inhibition); everything else goes to the *Backup* tab.
