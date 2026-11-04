"""Capture one real StudySense lighting + desk-motion physical trial (23-column MCU UART).

This is a host acquisition utility, NOT MCU inference.
Use one real separately prepared setup per trial, five distinct ~2 s snapshots.
Preserves earlier lighting data: writes to data/trials_motion_raw/ instead.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("Install pyserial into your project venv: .\\.venv\\Scripts\\python.exe -m pip install pyserial")

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "timestamp_ms", "ps_raw", "als_raw", "near", "ps_valid", "optical_valid",
    "optical_seq", "temperature_centi_c", "humidity_centi_pct", "aht_valid",
    "aht_crc_ok", "aht_seq", "imu_valid", "imu_seq", "boot_error",
    "motion_valid", "motion_window_seq", "motion_samples", "motion_mean_delta",
    "motion_peak_delta", "motion_failed", "motion_elapsed_ms", "motion_max_gap_ms",
]
VALID_FIELDS = ["ps_valid", "optical_valid", "aht_valid", "aht_crc_ok", "imu_valid", "motion_valid"]
COUNT = 5
LABELS = {"READY": "STUDY_READY", "LOW": "IMPROVE_LIGHTING", "TAPPING": "DESK_DISTURBANCE"}
PROTOCOLS = {
    "READY": "Lamp on in your agreed study-light position; desk still; paper removed.",
    "LOW": "Lamp off/lower-light setup; desk still; paper removed.",
    "TAPPING": "Same lamp position as READY; gently tap TABLE BESIDE board through recording; no touching electronics.",
}


def safe_id(s: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", s):
        raise ValueError("Use 1-80 letters, numbers, underscores, hyphens (begin with letter or number)")
    return s


def parse_line(line: str) -> dict[str, int] | None:
    vals = line.strip().split(",")
    if len(vals) != len(FIELDS):
        return None
    try:
        numbers = [int(v.strip()) for v in vals]
    except ValueError:
        return None
    d = dict(zip(FIELDS, numbers))
    if d["boot_error"] != 0 or any(d[k] != 1 for k in VALID_FIELDS):
        return None
    if not (0 <= d["ps_raw"] <= 1023 and 0 <= d["als_raw"] <= 65535):
        return None
    if not (-4000 <= d["temperature_centi_c"] <= 8500 and 0 <= d["humidity_centi_pct"] <= 10000):
        return None
    if not (90 <= d["motion_samples"] <= 100 and 0 <= d["motion_failed"] <= 10):
        return None
    if not (1800 <= d["motion_elapsed_ms"] <= 2600 and 0 <= d["motion_max_gap_ms"] <= 100):
        return None
    if d["motion_mean_delta"] < 0 or d["motion_peak_delta"] < d["motion_mean_delta"]:
        return None
    # Paper marker is not used; a near detection would introduce ALS occlusion.
    if d["near"] != 0:
        return None
    return d


def main() -> None:
    p = argparse.ArgumentParser(description="Capture 5 valid 23-column motion+light windows for ONE physical trial")
    p.add_argument("--split", choices=("train", "test", "final"), required=True)
    p.add_argument("--session", required=True, help="A real session used in exactly one data split")
    p.add_argument("--condition", choices=tuple(LABELS), required=True)
    p.add_argument("--trial", required=True, help="Unique ID for this independently prepared setup")
    p.add_argument("--setup-note", required=True, help="Describe physical lamp and desk condition, not a sensor prediction")
    p.add_argument("--port", default="COM3")
    args = p.parse_args()
    try:
        session, trial = safe_id(args.session), safe_id(args.trial)
    except ValueError as ex:
        p.error(str(ex))
    if not args.setup_note.strip():
        p.error("setup-note must describe the actual physical setup")
    target = ROOT / "data" / "trials_motion_raw" / args.split / session / f"{trial}_{args.condition}.csv"
    if target.exists():
        p.error(f"Refusing to overwrite existing trial: {target}")
    print("ONE separately prepared setup = ONE physical trial (5 consecutive 2-second windows).")
    print(f"Label: {LABELS[args.condition]} | split: {args.split} | session: {session} | trial: {trial}")
    print("Protocol:", PROTOCOLS[args.condition])
    print("Close PlatformIO monitor; sensor must be running Motion Stage 1 (23 columns).")
    print("Setup-note:", args.setup_note)

    rows: list[dict[str, object]] = []
    previous: dict[str, int] | None = None
    end = time.monotonic() + 90.0
    first_line_seen = False
    try:
        with serial.Serial(args.port, 115200, timeout=2) as port:
            port.reset_input_buffer()
            while len(rows) < COUNT and time.monotonic() < end:
                line = port.readline().decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line[0].isdigit() and not first_line_seen:
                    first_line_seen = True
                    if len(line.split(",")) == 15:
                        sys.exit("ERROR: old 15-column STM32 logger detected. Upload Motion Stage 1 before capturing.")
                reading = parse_line(line)
                if reading is None:
                    continue
                if previous is not None:
                    seq_cols = ["optical_seq", "aht_seq", "imu_seq", "motion_window_seq", "timestamp_ms"]
                    if any(reading[k] <= previous[k] for k in seq_cols):
                        continue
                    if not (1000 <= reading["timestamp_ms"] - previous["timestamp_ms"] <= 5000):
                        print("Skipping row after unusual timing gap")
                        # Don't blend non-contiguous windows into the same trial.
                        rows.clear()
                        previous = None
                        continue
                previous = reading
                reading["captured_at_utc"] = datetime.now(timezone.utc).isoformat()
                reading["session_id"] = session
                reading["trial_id"] = trial
                reading["split"] = args.split
                reading["condition"] = args.condition
                reading["setup_note"] = args.setup_note.strip()
                rows.append(reading)
                print(f"{len(rows)}/5: light={reading['als_raw']}, motion_mean={reading['motion_mean_delta']}, "
                      f"motion_peak={reading['motion_peak_delta']}, samples={reading['motion_samples']}, "
                      f"temp={reading['temperature_centi_c']/100:.2f} C")
    except (serial.SerialException, OSError) as ex:
        sys.exit(f"COM port error: {ex}. Close 'pio device monitor' first.")
    except KeyboardInterrupt:
        sys.exit("Cancelled: no trial file saved")
    if len(rows) != COUNT:
        sys.exit(f"ERROR: only {len(rows)} valid motion windows obtained. No trial saved.")
    target.parent.mkdir(parents=True, exist_ok=True)
    columns = ["captured_at_utc", "session_id", "trial_id", "split", "condition", "setup_note", *FIELDS]
    with target.open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)
    print("\nSAVED one genuine motion trial:", target)
    print("Before another trial, physically reset the setup; don't just change the trial ID.")


if __name__ == "__main__":
    main()
