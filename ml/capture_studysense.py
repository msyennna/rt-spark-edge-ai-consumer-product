r"""Capture REAL StudySense calibration readings from the STM32 UART logger.

Run from the Edge AI repository root, with the PlatformIO monitor CLOSED:
  .\.venv\Scripts\python.exe ml\capture_studysense.py --condition LOW --trial L01

Only for calibration; do NOT count 10 adjacent rows as 10 independent ML trials.
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
    sys.exit("Missing pyserial. Install: .\\.venv\\Scripts\\python.exe -m pip install pyserial")

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "timestamp_ms", "ps_raw", "als_raw", "near", "ps_valid", "optical_valid",
    "optical_seq", "temperature_centi_c", "humidity_centi_pct", "aht_valid",
    "aht_crc_ok", "aht_seq", "imu_valid", "imu_seq", "boot_error",
]
VALID_FLAGS = ("ps_valid", "optical_valid", "aht_valid", "aht_crc_ok", "imu_valid")


def safe_name(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", text.strip())
    if not cleaned or cleaned == "_":
        raise ValueError("Session/trial ID must contain a letter or digit")
    return cleaned


def parse_reading(line: str) -> dict[str, int] | None:
    pieces = line.strip().split(",")
    if len(pieces) != len(FIELDS):
        return None  # Banner, header, debug line or incomplete serial message
    try:
        values = [int(value.strip()) for value in pieces]
    except ValueError:
        return None
    reading = dict(zip(FIELDS, values))
    if reading["boot_error"] != 0 or any(reading[name] != 1 for name in VALID_FLAGS):
        return None
    if not (0 <= reading["ps_raw"] <= 1023 and 0 <= reading["als_raw"] <= 65535):
        return None
    if not (-4000 <= reading["temperature_centi_c"] <= 8500
            and 0 <= reading["humidity_centi_pct"] <= 10000):
        return None
    return reading


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture StudySense calibration data from COM3")
    parser.add_argument("--condition", choices=["LOW", "MEDIUM", "BRIGHT"], required=True)
    parser.add_argument("--trial", required=True, help="Unique ID for this recording, e.g. L01")
    parser.add_argument("--session", default=None, help="Recording-session ID; defaults to today's date")
    parser.add_argument("--port", default="COM3")
    parser.add_argument("--samples", type=int, default=10)
    args = parser.parse_args()
    if not (2 <= args.samples <= 100):
        parser.error("--samples must be between 2 and 100")
    session = safe_name(args.session or datetime.now().strftime("calibration_%Y%m%d"))
    trial = safe_name(args.trial)
    output = ROOT / "data" / "calibration_auto" / f"{session}_{trial}_{args.condition}.csv"
    if output.exists():
        sys.exit(f"File already exists (refusing to overwrite): {output}\nChoose a new --trial ID.")

    print(f"Condition: {args.condition} | session: {session} | trial: {trial}")
    print(f"Keep the lamp/board stationary. Collecting {args.samples} fresh valid rows.")
    print(f"Opening {args.port} at 115200 baud. Close 'pio device monitor' first.")
    results: list[dict[str, object]] = []
    last_seq: tuple[int, int, int] | None = None
    deadline = time.monotonic() + max(90, 6 * args.samples)
    try:
        with serial.Serial(port=args.port, baudrate=115200, timeout=2) as port:
            port.reset_input_buffer()
            while len(results) < args.samples and time.monotonic() < deadline:
                line = port.readline().decode("utf-8", errors="replace").strip()
                reading = parse_reading(line)
                if reading is None:
                    continue
                seq = (reading["optical_seq"], reading["aht_seq"], reading["imu_seq"])
                if last_seq is not None and any(new <= old for new, old in zip(seq, last_seq)):
                    continue  # Reject repeated / out-of-order sensor values
                last_seq = seq
                reading["captured_at_utc"] = datetime.now(timezone.utc).isoformat()
                reading["session_id"] = session
                reading["trial_id"] = trial
                reading["condition"] = args.condition
                results.append(reading)
                print(f"  {len(results):>2}/{args.samples}: ps={reading['ps_raw']}, "
                      f"als={reading['als_raw']}, "
                      f"temp={reading['temperature_centi_c'] / 100:.2f} C, "
                      f"humidity={reading['humidity_centi_pct'] / 100:.2f}%")
    except (serial.SerialException, OSError) as error:
        sys.exit(f"Could not read {args.port}: {error}\nCheck USB connection and close the PlatformIO monitor.")
    except KeyboardInterrupt:
        sys.exit("Capture cancelled; no data saved.")

    if len(results) != args.samples:
        sys.exit(f"Only {len(results)} valid rows received. No file saved. Check board/COM port.")
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["captured_at_utc", "session_id", "trial_id", "condition", *FIELDS]
    try:
        with output.open("x", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    except FileExistsError:
        sys.exit(f"File already exists: {output}")
    print(f"\nSaved {len(results)} genuine UART readings to:\n  {output}")
    print("Note: these 10 adjacent samples form ONE calibration recording, not 10 independent trials.")


if __name__ == "__main__":
    main()
