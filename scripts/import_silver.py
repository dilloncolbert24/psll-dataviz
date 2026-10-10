"""Bridge: the team's PSLL pipelines (polar_pipeline / frigga_pipeline "silver" CSVs) -> raw_data/real/.

The pipelines in Data Science Protocols/PSLL_Data turn raw Polar H10 and Frigga M2H exports into
timestamped silver tables in PSLL_Data/_outputs/. This script takes the newest of each and rewrites
them in this dashboard's raw_data schema (docs/DATA_DICTIONARY.md):

    polar_silver_<stamp>.csv + polar_qc_<stamp>.csv  ->  raw_data/real/physiology.csv
    frigga_silver_<stamp>.csv                        ->  raw_data/real/frigga_log.csv

Site comes from a roster CSV (Participant_ID + Space/site column), else from raw_data/real/affect.csv.
quality_flag = "ok" when the pipeline raised no QC flags, otherwise "check" (kept, listed in QC);
nothing is excluded automatically. Previous versions are copied to raw_data/real/_previous/ first.

    python scripts/import_silver.py --outputs "<...>/PSLL_Data/_outputs"
    python scripts/import_silver.py --outputs ... --roster roster.csv --dry-run
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_REAL = PROJECT_DIR / "raw_data" / "real"
STAMP = re.compile(r"_(\d{8}_\d{4})\.csv$")


def latest(outputs: Path, prefix: str) -> Path | None:
    """Newest <prefix>_YYYYMMDD_HHMM.csv (searching subfolders too)."""
    files = [p for p in outputs.rglob(f"{prefix}_*.csv") if STAMP.search(p.name)]
    return max(files, key=lambda p: STAMP.search(p.name).group(1)) if files else None


def normalise_site(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return f"Space {text.upper()}" if len(text) == 1 else text  # "A" -> "Space A"


def site_lookup(roster: Path | None) -> dict:
    if roster:
        df = pd.read_csv(roster, dtype=str)
        site_col = next((c for c in df.columns if c.lower() in ("space", "site")), None)
        id_col = next((c for c in df.columns if c.lower() in ("participant_id", "participant")), None)
        if not (site_col and id_col):
            sys.exit(f"{roster}: needs a Participant_ID column and a Space/site column (has {list(df.columns)})")
        return {r[id_col].strip(): normalise_site(r[site_col]) for _, r in df.iterrows()}
    affect = RAW_REAL / "affect.csv"
    if affect.exists():
        df = pd.read_csv(affect, dtype=str)
        if {"participant_id", "site"} <= set(df.columns):
            return dict(zip(df.participant_id.str.strip(), df.site.map(normalise_site)))
    return {}


def build_physiology(silver: Path, qc: Path | None, sites: dict) -> pd.DataFrame:
    df = pd.read_csv(silver, encoding="utf-8-sig")
    flags = {}
    if qc is not None:
        q = pd.read_csv(qc, encoding="utf-8-sig", dtype={"QC_Flags": str})
        flags = {(r.Participant_ID, r.Condition): (r.QC_Flags if isinstance(r.QC_Flags, str) else "")
                 for r in q.itertuples()}
    out = pd.DataFrame({
        "participant_id": df.Participant_ID.str.strip(),
        "site": df.Participant_ID.str.strip().map(sites),
        "condition": df.Condition.str.strip().str.upper(),
        "rmssd_ms": df.RMSSD_ms.round(1),
        "mean_hr_bpm": df.Mean_HR_bpm.round(1),
        "sdnn_ms": df.SDNN_ms.round(1),
    })
    out["quality_flag"] = [("check" if flags.get((p, c), "") else "ok")
                           for p, c in zip(df.Participant_ID, df.Condition)]
    missing = sorted(out.loc[out.site.isna(), "participant_id"].unique())
    if missing:
        sys.exit(f"No site for {missing}. Pass --roster <csv with Participant_ID, Space> "
                 "or fill raw_data/real/affect.csv first.")
    return out


def build_frigga(silver: Path) -> pd.DataFrame:
    df = pd.read_csv(silver, encoding="utf-8-sig")
    ts = pd.to_datetime(df.Timestamp, errors="coerce")
    out = pd.DataFrame({"timestamp": ts.dt.strftime("%Y-%m-%d %H:%M"),
                        "temperature_c": df.Temperature_C, "relative_humidity_pct": df.RH_pct})
    return out.dropna(subset=["timestamp"])


def write(df: pd.DataFrame, name: str, dry_run: bool):
    target = RAW_REAL / name
    print(f"\n{name}: {len(df)} rows")
    print(df.head(6).to_string(index=False))
    if dry_run:
        return
    if target.exists() and len(target.read_text().strip().splitlines()) > 1:
        backup = RAW_REAL / "_previous" / f"{target.stem}.{datetime.now():%Y%m%d_%H%M%S}.csv"
        backup.parent.mkdir(exist_ok=True)
        shutil.copy2(target, backup)
        print(f"  previous version -> {backup.relative_to(PROJECT_DIR)}")
    df.to_csv(target, index=False)
    print(f"  wrote {target.relative_to(PROJECT_DIR)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outputs", type=Path, required=True, help="PSLL_Data/_outputs folder from the team pipelines")
    ap.add_argument("--roster", type=Path, help="CSV with Participant_ID and Space/site columns")
    ap.add_argument("--dry-run", action="store_true", help="show what would be written, change nothing")
    args = ap.parse_args()
    if not args.outputs.is_dir():
        sys.exit(f"Not a folder: {args.outputs}")

    polar, polar_qc, frigga = (latest(args.outputs, p) for p in ("polar_silver", "polar_qc", "frigga_silver"))
    print("Using:", *(f"  {p.name if p else '(none found)'}" for p in (polar, polar_qc, frigga)), sep="\n")
    if polar:
        write(build_physiology(polar, polar_qc, site_lookup(args.roster)), "physiology.csv", args.dry_run)
    if frigga:
        write(build_frigga(frigga), "frigga_log.csv", args.dry_run)
    if not (polar or frigga):
        sys.exit("No polar_silver_*.csv or frigga_silver_*.csv found.")
    if not args.dry_run:
        print("\nNext: set USE_SAMPLE_DATA = False in the notebook (if not already) and run it.")


if __name__ == "__main__":
    main()
