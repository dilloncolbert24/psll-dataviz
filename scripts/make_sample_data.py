"""Generate SYNTHETIC sample data matching raw_data/templates/*.csv.

These numbers are invented so the notebook and dashboard can be built and
tested before the real field data is transcribed. Never present them as results.

Usage:  python scripts/make_sample_data.py
Output: raw_data/sample/*.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "raw_data" / "sample"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)

DATE = "2026-10-01"
SITES = {"Space A": 6, "Space B": 5}  # observers per site -> 22 sheets total
CONDITIONS = ["PRE", "POST"]
OBS_START = {"PRE": "11:20", "POST": "15:45"}
OBS_END = {"PRE": "11:40", "POST": "16:05"}

# --- Behavior: observation sheets -------------------------------------------
sessions, movement, snaps, notes = [], [], [], []
sheet_n = 0
for site, n_obs in SITES.items():
    base_occ = 7 if site == "Space A" else 5
    for cond in CONDITIONS:
        lift = (1.5 if site == "Space A" else 1.25) if cond == "POST" else 1.0
        true_occ = [rng.poisson(base_occ * lift) for _ in range(4)]
        true_flow = [rng.poisson(40) for _ in range(4)]
        for o in range(1, n_obs + 1):
            sheet_n += 1
            sid = f"S{sheet_n:02d}"
            sessions.append(dict(
                sheet_id=sid, site=site, condition=cond,
                observer_id=f"{site[-1]}{o:02d}", date=DATE,
                start_time=OBS_START[cond], end_time=OBS_END[cond],
                # first protocol page had the short snapshot table
                sheet_version="short" if o == n_obs and cond == "PRE" else "full",
                boundary_confirmed=True, count_line_confirmed=True, zones_confirmed=True,
            ))
            for i, flow in enumerate(true_flow):
                tot = max(0, flow + rng.integers(-4, 5))
                d1 = int(tot * rng.uniform(0.4, 0.6))
                movement.append(dict(sheet_id=sid, interval_start_min=i * 5,
                                     interval_end_min=i * 5 + 5, total_crossing=tot,
                                     direction_1=d1, direction_2=tot - d1))
            short = sessions[-1]["sheet_version"] == "short"
            for i, occ in enumerate(true_occ):
                tot = max(0, occ + rng.integers(-1, 2))
                sit = int(round(tot * (0.6 if cond == "POST" else 0.45)))
                social = int(round(tot * (0.55 if cond == "POST" else 0.4)))
                alone = tot - social
                snaps.append(dict(
                    sheet_id=sid, snapshot_min=(i + 1) * 5, total_stationary=tot,
                    sitting=None if short else sit,
                    standing_leaning=None if short else tot - sit,
                    social_interaction=social, alone=alone,
                    pair_group=None if short else social,
                    intervention_use=(int(round(tot * 0.5)) if cond == "POST" else None),
                ))
            if cond == "POST" and site == "Space A" and o <= 3:
                notes.append(dict(sheet_id=sid, approx_time="15:55",
                                  event="Delivery van parked near count line (~3 min)"))
            if cond == "PRE" and site == "Space B" and o <= 2:
                notes.append(dict(sheet_id=sid, approx_time="11:30",
                                  event="School group crossed the site"))

pd.DataFrame(sessions).to_csv(OUT / "observation_sessions.csv", index=False)
pd.DataFrame(movement).to_csv(OUT / "movement_counts.csv", index=False)
pd.DataFrame(snaps).to_csv(OUT / "snapshots.csv", index=False)
pd.DataFrame(notes).to_csv(OUT / "field_notes.csv", index=False)

# --- Environment: Frigga 5-min log 09:00-17:00 ------------------------------
ts = pd.date_range(f"{DATE} 09:00", f"{DATE} 17:00", freq="5min")
hours = (ts.hour + ts.minute / 60).to_numpy()
temp = 20 + 5.5 * np.clip((hours - 9) / 7, 0, 1) + rng.normal(0, 0.15, len(ts))
rh = 64 - 20 * np.clip((hours - 9) / 7, 0, 1) + rng.normal(0, 0.8, len(ts))
pd.DataFrame(dict(timestamp=ts.strftime("%Y-%m-%d %H:%M"),
                  temperature_c=temp.round(1),
                  relative_humidity_pct=rh.round(0))).to_csv(OUT / "frigga_log.csv", index=False)

windows = []
for site in SITES:
    windows += [
        dict(site=site, date=DATE, window="PRE Rotation", phase="rotation", condition="PRE", start_time="09:20", end_time="10:20"),
        dict(site=site, date=DATE, window="PRE Behavior", phase="behavior", condition="PRE", start_time="11:20", end_time="11:45"),
        dict(site=site, date=DATE, window="POST Rotation", phase="rotation", condition="POST", start_time="13:45", end_time="14:45"),
        dict(site=site, date=DATE, window="POST Behavior", phase="behavior", condition="POST", start_time="15:45", end_time="16:10"),
    ]
pd.DataFrame(windows).to_csv(OUT / "experimental_windows.csv", index=False)

env_manual = []
for site in SITES:
    for t, sun, wind in [("09:30", 1, 1), ("11:30", 2, 1), ("14:00", 3, 2), ("16:00", 3, 1)]:
        env_manual.append(dict(site=site, date=DATE, time=t, sun_condition=sun, wind=wind,
                               precipitation=0, ground_condition=0, noise=1))
pd.DataFrame(env_manual).to_csv(OUT / "env_manual.csv", index=False)

# --- Spatial ----------------------------------------------------------------
spatial = []
for site in SITES:
    spatial.append(dict(site=site, condition="PRE", available_seating=7, seats_occupied_start=2,
                        shade="None", vegetation="Existing", landmark="No", signage="No",
                        ground_intervention="No", other_temporary="", photo_file=f"{site[-1]}_pre.jpg"))
    spatial.append(dict(site=site, condition="POST", available_seating=13, seats_occupied_start=4,
                        shade="Partial", vegetation="Existing", landmark="Yes",
                        signage="Yes" if site == "Space A" else "No",
                        ground_intervention="Yes", other_temporary="", photo_file=f"{site[-1]}_post.jpg"))
pd.DataFrame(spatial).to_csv(OUT / "spatial_conditions.csv", index=False)

comps = []
for site in SITES:
    comps += [
        dict(site=site, component="Added seating", installed="Yes", units=6, notes=""),
        dict(site=site, component="Shade", installed="Yes", units="", notes="Sail over seating"),
        dict(site=site, component="Rug / ground definition", installed="Yes", units="", notes=""),
        dict(site=site, component="Plants / vegetation", installed="Yes" if site == "Space A" else "No", units=4 if site == "Space A" else "", notes=""),
        dict(site=site, component="Landmark", installed="Yes", units="", notes=""),
        dict(site=site, component="Signage", installed="Yes" if site == "Space A" else "No", units="", notes=""),
        dict(site=site, component="Other", installed="No", units="", notes=""),
    ]
pd.DataFrame(comps).to_csv(OUT / "intervention_components.csv", index=False)

# --- Individual measures ----------------------------------------------------
affect, phys, cog = [], [], []
for site, n in {"Space A": 12, "Space B": 12}.items():
    for p in range(1, n + 1):
        pid = f"{site[-1]}P{p:02d}"
        resp = rng.normal(0.8 if site == "Space A" else 0.2, 0.6)  # latent "restoration response"
        pa0, na0, r0 = rng.normal(4.2, 0.7), rng.normal(2.6, 0.6), rng.normal(3.8, 0.8)
        hr0, rm0 = rng.normal(78, 8), rng.normal(38, 10)
        pvt0, fc0 = rng.normal(320, 30), rng.normal(480, 40)
        dtemp_hr = 3.0  # warmer afternoon nudges HR up
        for cond in CONDITIONS:
            k = 1 if cond == "POST" else 0
            affect.append(dict(participant_id=pid, site=site, condition=cond,
                               positive_affect=np.clip(pa0 + k * resp * 0.6 + rng.normal(0, .2), 1, 7).round(2),
                               negative_affect=np.clip(na0 - k * resp * 0.3 + rng.normal(0, .2), 1, 7).round(2),
                               perceived_restoration=np.clip(r0 + k * resp + rng.normal(0, .3), 1, 7).round(2)))
            phys.append(dict(participant_id=pid, site=site, condition=cond,
                             rmssd_ms=max(8, rm0 + k * resp * 4 + rng.normal(0, 3)).__round__(1),
                             mean_hr_bpm=(hr0 + k * (dtemp_hr - resp) + rng.normal(0, 1.5)).__round__(1),
                             sdnn_ms=max(10, rm0 * 1.3 + rng.normal(0, 4)).__round__(1),
                             quality_flag="check" if (pid == "BP07" and cond == "POST") else "ok"))
            inc_extra = 60 - k * resp * 8
            cog.append(dict(participant_id=pid, site=site, condition=cond,
                            pvt_median_rt_ms=(pvt0 - k * resp * 10 + rng.normal(0, 8)).__round__(0),
                            pvt_lapses=int(rng.poisson(max(0.2, 1.5 - k * resp * 0.5))),
                            flanker_accuracy=float(np.clip(rng.normal(0.94 + k * 0.01, 0.02), 0.7, 1)).__round__(3),
                            flanker_congruent_rt_ms=(fc0 + rng.normal(0, 10)).__round__(0),
                            flanker_incongruent_rt_ms=(fc0 + inc_extra + rng.normal(0, 10)).__round__(0)))

pd.DataFrame(affect).to_csv(OUT / "affect.csv", index=False)
pd.DataFrame(phys).to_csv(OUT / "physiology.csv", index=False)
pd.DataFrame(cog).to_csv(OUT / "cognition.csv", index=False)
print(f"Wrote synthetic sample data to {OUT}")
