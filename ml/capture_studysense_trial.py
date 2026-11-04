r"""Capture ONE real, independently prepared StudySense trial via STM32 COM3.

Usage from repository root (PlatformIO monitor must be closed):
  .\.venv\Scripts\python.exe ml\capture_studysense_trial.py --split train --session train_day1 --condition LOW --trial L001

Five fresh 2-second sensor snapshots make ONE 10-second trial/window.
This script intentionally reuses parse_reading() from the proven calibration logger.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

from capture_studysense import FIELDS, parse_reading, safe_name, serial

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_PER_TRIAL = 5


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture one physical StudySense lighting trial")
    parser.add_argument("--condition", choices=["LOW", "MEDIUM", "BRIGHT"], required=True)
    parser.add_argument("--split", choices=["train", "test", "final"], required=True)
    parser.add_argument("--session", required=True, help="An independent session ID used for only ONE split")
    parser.add_argument("--trial", required=True, help="Unique trial ID within session, e.g. L001")
    parser.add_argument("--port", default="COM3")
    parser.add_argument("--setup-note", default="", help="Non-identifying physical setup notes")
    args = parser.parse_args()

    session = safe_name(args.session)
    trial = safe_name(args.trial)
    out_dir = ROOT / "data" / "trials_raw" / args.split / session
    out = out_dir / f"{trial}_{args.condition}.csv"
    if out.exists():
        parser.error(f"Refusing to overwrite an existing trial: {out}")

    print(f"Split={args.split} | session={session} | trial={trial} | label={args.condition}")
    print("IMPORTANT: one separately prepared lighting setup = ONE trial.")
    print("Do not reuse five adjacent samples as five trials.")
    print("Keep lamp and board steady during the recording; remove the paper marker.")
    print(f"Collecting {SAMPLES_PER_TRIAL} fresh valid serial readings on {args.port}...")
    last_seq = None
    rows: list[dict[str, object]] = []
    deadline = time.monotonic() + 90.0

    try:
        with serial.Serial(port=args.port, baudrate=115200, timeout=2) as port:
            port.reset_input_buffer()
            while len(rows) < SAMPLES_PER_TRIAL and time.monotonic() < deadline:
                line = port.readline().decode("utf-8", errors="replace").strip()
                reading = parse_reading(line)
                if reading is None:
                    continue
                seq = (reading["optical_seq"], reading["aht_seq"], reading["imu_seq"])
                if last_seq is not None and any(new <= old for new, old in zip(seq, last_seq)):
                    continue
                last_seq = seq
                reading.update({
                    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                    "session_id": session,
                    "trial_id": trial,
                    "split": args.split,
                    "condition": args.condition,
                    "setup_note": args.setup_note,
                })
                rows.append(reading)
                print(f" {len(rows)}/{SAMPLES_PER_TRIAL}: "
                      f"ps={reading['ps_raw']}, als={reading['als_raw']}, "
                      f"temp={reading['temperature_centi_c'] / 100:.2f} C, "
                      f"RH={reading['humidity_centi_pct'] / 100:.2f}%")
    except (serial.SerialException, OSError) as exc:
        sys.exit(f"COM port failure: {exc}. Close the PlatformIO monitor and try again.")
    except KeyboardInterrupt:
        sys.exit("Cancelled; trial not saved.")

    if len(rows) != SAMPLES_PER_TRIAL:
        sys.exit(f"Only {len(rows)} valid readings received; trial NOT saved.")
    out_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = ["captured_at_utc", "session_id", "trial_id", "split", "condition", "setup_note", *FIELDS]
    with out.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSAVED ONE independent physical trial (five readings):\n  {out}")
    print("Reset/reposition the lamp for the next physical trial. Never relabel sensor values.")


if __name__ == "__main__":
    main()
