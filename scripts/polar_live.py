"""Record a Polar H10 live over Bluetooth: HR + RR intervals -> CSV, with a running HR/RMSSD readout.

Built on bleakheart (MPL-2.0, https://github.com/fsmeraldi/bleakheart), which reads the standard BLE
heart-rate service on top of Bleak. Works on macOS, Windows and Linux; no phone app needed.

The CSV uses the column names the team's polar_pipeline already reads
("Phone timestamp" = epoch ms, "HR [bpm]", "RR-interval [ms]", one row per beat), and is named
<participant>.csv, so a live recording can go straight into PSLL_Data/PolarH10/prePolar or postPolar.
Rows are flushed as they arrive, so a dropped connection keeps everything recorded so far.

    pip install bleakheart                     # once (pulls in bleak)
    python scripts/polar_live.py P001 PRE --minutes 5
    python scripts/polar_live.py P001 POST --out "<...>/PSLL_Data/PolarH10/postPolar"
    python scripts/polar_live.py P001 PRE --simulate --speed 20   # no strap: synthetic beats, fast
    python scripts/polar_live.py P001 PRE --live-json web/data/live/polar.json  # rolling summary file

The readout is for checking signal quality during the session only. Reported HRV values come from
polar_pipeline (same Task Force definitions, plus its QC flags).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import random
import sys
import time
from collections import deque
from pathlib import Path
from statistics import median

PROJECT_DIR = Path(__file__).resolve().parent.parent
HEADER = ["Phone timestamp", "HR [bpm]", "RR-interval [ms]"]
WINDOW_S = 60          # rolling window for the live readout
REPORT_EVERY_S = 10


def valid_mask(rr: list[float], lo=300.0, hi=2000.0, dev=0.20, window=11) -> list[bool]:
    """Same rule as polar_pipeline.clean_rr: physiologic range + within 20% of the local median."""
    ok = [lo <= x <= hi for x in rr]
    half = window // 2
    out = []
    for i, x in enumerate(rr):
        neighbours = [rr[j] for j in range(max(0, i - half), min(len(rr), i + half + 1)) if ok[j]]
        local = median(neighbours) if len(neighbours) >= 3 else None
        out.append(ok[i] and (local is None or abs(x - local) / local <= dev))
    return out


def summarise(rr: list[float]) -> dict:
    if len(rr) < 3:
        return {"beats": len(rr)}
    ok = valid_mask(rr)
    nn = [x for x, v in zip(rr, ok) if v]
    diffs = [b - a for a, b, va, vb in zip(rr, rr[1:], ok, ok[1:]) if va and vb]
    return {"beats": len(rr), "artifact_pct": round(100 * (1 - len(nn) / len(rr)), 1),
            "hr_bpm": round(60000 / (sum(nn) / len(nn)), 1) if nn else None,
            "rmssd_ms": round(math.sqrt(sum(d * d for d in diffs) / len(diffs)), 1) if len(diffs) >= 2 else None}


class Recorder:
    def __init__(self, path: Path, live_json: Path | None, speed: float):
        self.path, self.live_json, self.speed = path, live_json, speed
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        self.fh = path.open("a", newline="")
        self.writer = csv.writer(self.fh)
        if new:
            self.writer.writerow(HEADER)
        self.window: deque[tuple[float, float]] = deque()  # (t_seconds, rr_ms)
        self.all_rr: list[float] = []
        self.last_report = time.monotonic()

    def beat(self, epoch_ms: int, bpm: float, rr_ms: float | None):
        self.writer.writerow([epoch_ms, bpm, "" if rr_ms is None else round(rr_ms)])
        self.fh.flush()
        if rr_ms is None:
            return
        t = epoch_ms / 1000
        self.all_rr.append(rr_ms)
        self.window.append((t, rr_ms))
        while self.window and self.window[0][0] < t - WINDOW_S:
            self.window.popleft()
        if time.monotonic() - self.last_report >= REPORT_EVERY_S / self.speed:
            self.last_report = time.monotonic()
            self.report()

    def report(self):
        s = summarise([rr for _, rr in self.window])
        total = summarise(self.all_rr)
        flag = "  ⚠ check strap contact" if (s.get("artifact_pct") or 0) > 5 else ""
        print(f"  last {WINDOW_S}s: HR {s.get('hr_bpm', '–')} bpm · RMSSD {s.get('rmssd_ms', '–')} ms · "
              f"artifacts {s.get('artifact_pct', '–')}% · {total['beats']} beats total{flag}", flush=True)
        if self.live_json:
            self.live_json.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.live_json.with_suffix(".tmp")
            tmp.write_text(json.dumps({"updated": time.strftime("%Y-%m-%dT%H:%M:%S"), "window_s": WINDOW_S,
                                       "window": s, "session": total,
                                       "recent_rr_ms": [round(rr) for _, rr in self.window][-120:]}))
            tmp.replace(self.live_json)  # atomic, so a polling page never reads half a file

    def close(self):
        self.fh.close()
        s = summarise(self.all_rr)
        print(f"\nSaved {self.path}  ({s['beats']} beats; session HR {s.get('hr_bpm', '–')} bpm, "
              f"RMSSD {s.get('rmssd_ms', '–')} ms, artifacts {s.get('artifact_pct', '–')}%)")


async def run_device(rec: Recorder, seconds: float, name_filter: str):
    from bleak import BleakClient, BleakScanner
    from bleakheart import HeartRate

    print(f"Scanning for a device whose name contains '{name_filter}'…")
    device = await BleakScanner.find_device_by_filter(
        lambda d, adv: bool(d.name) and name_filter.lower() in d.name.lower(), timeout=20)
    if device is None:
        sys.exit("No strap found. Wet the electrodes, snap it on, and close Polar apps on nearby phones "
                 "(a strap only streams to one device at a time).")
    queue: asyncio.Queue = asyncio.Queue()
    done = asyncio.Event()
    async with BleakClient(device, disconnected_callback=lambda _: done.set()) as client:
        print(f"Connected to {device.name}. Recording {seconds / 60:g} min — Ctrl+C to stop early.")
        hr = HeartRate(client, queue=queue, instant_rate=True, unpack=True)
        await hr.start_notify()
        deadline = time.monotonic() + seconds
        while not done.is_set() and time.monotonic() < deadline:
            try:
                _, tstamp_ns, (bpm, rr), _ = await asyncio.wait_for(queue.get(), timeout=1)
            except asyncio.TimeoutError:
                continue
            rec.beat(int(tstamp_ns / 1e6), bpm, rr)
        if done.is_set():
            print("Strap disconnected — data so far is saved.")
        elif client.is_connected:
            await hr.stop_notify()


async def run_simulated(rec: Recorder, seconds: float, speed: float):
    """Synthetic beats (~72 bpm, RMSSD ~35 ms, occasional artifacts) to test the workflow without a strap."""
    print(f"Simulating {seconds / 60:g} min at {speed:g}× speed…")
    t_ms, rr, elapsed = time.time() * 1000, 830.0, 0.0
    while elapsed < seconds * 1000:
        rr = 830 + 0.6 * (rr - 830) + random.gauss(0, 30)
        beat = rr * 1.9 if random.random() < 0.02 else rr  # ~2% missed beats
        t_ms += beat
        elapsed += beat
        rec.beat(int(t_ms), round(60000 / rr), beat)
        await asyncio.sleep(beat / 1000 / speed)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("participant", help="participant ID, used as the file name (e.g. P001)")
    ap.add_argument("condition", type=str.upper, choices=["PRE", "POST"])
    ap.add_argument("--minutes", type=float, default=5, help="recording length (default 5)")
    ap.add_argument("--out", type=Path, help="output folder (default raw_data/polar_live/<pre|post>Polar)")
    ap.add_argument("--device", default="Polar", help="part of the strap's Bluetooth name, e.g. its ID")
    ap.add_argument("--live-json", type=Path, help="also keep a rolling summary JSON updated (for a live view)")
    ap.add_argument("--simulate", action="store_true", help="no strap: generate synthetic beats")
    ap.add_argument("--speed", type=float, default=1, help="simulation speed-up factor")
    args = ap.parse_args()

    out = args.out or PROJECT_DIR / "raw_data" / "polar_live" / f"{args.condition.lower()}Polar"
    path = out / f"{args.participant}.csv"
    if path.exists():
        sys.exit(f"{path} already exists — use another ID/folder, or move the old file first.")
    rec = Recorder(path, args.live_json, args.speed if args.simulate else 1)
    try:
        coro = (run_simulated(rec, args.minutes * 60, args.speed) if args.simulate
                else run_device(rec, args.minutes * 60, args.device))
        asyncio.run(coro)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        rec.close()


if __name__ == "__main__":
    main()
