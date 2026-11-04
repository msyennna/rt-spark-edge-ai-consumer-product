"""Aggregate real UART trial files into one genuine feature row per physical trial.

Input: data/trials_raw/{train|test|final}/{session_id}/{trial_id}_{condition}.csv
Output: data/studysense_windows.csv

Only aggregate files recorded using ml/capture_studysense_trial.py.
Calibration recordings are deliberately excluded. No synthetic data is generated.
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "trials_raw"
OUTPUT = ROOT / "data" / "studysense_windows.csv"
SAMPLES_PER_TRIAL = 5
LABELS = {"LOW": "LOW_LIGHT", "MEDIUM": "MODERATE_LIGHT", "BRIGHT": "BRIGHT_LIGHT"}
VALID_FIELDS = ["ps_valid", "optical_valid", "aht_valid", "aht_crc_ok", "imu_valid"]
NUMERIC_FIELDS = [
    "timestamp_ms", "ps_raw", "als_raw", "optical_seq", "aht_seq", "imu_seq",
    "temperature_centi_c", "humidity_centi_pct", "near", "boot_error", *VALID_FIELDS,
]
REQUIRED = ["session_id", "trial_id", "split", "condition", *NUMERIC_FIELDS]


def fail(message: str) -> None:
    raise SystemExit("ERROR: " + message)


def one_value(df: pd.DataFrame, field: str, path: Path) -> str:
    values = df[field].astype(str).str.strip().unique()
    if len(values) != 1 or not values[0]:
        fail(f"{path}: inconsistent {field} within one trial")
    return values[0]


def main() -> None:
    files = sorted(RAW_DIR.rglob("*.csv")) if RAW_DIR.exists() else []
    if not files:
        fail(f"No recorded physical trials in {RAW_DIR}. Capture trials first.")

    aggregated: list[dict[str, object]] = []
    seen_trials: set[tuple[str, str]] = set()
    session_splits: dict[str, str] = {}
    for path in files:
        df = pd.read_csv(path)
        missing = [col for col in REQUIRED if col not in df.columns]
        if missing:
            fail(f"{path}: missing columns: {', '.join(missing)}")
        if len(df) != SAMPLES_PER_TRIAL:
            fail(f"{path}: expected exactly {SAMPLES_PER_TRIAL} genuine snapshots; got {len(df)}")
        session = one_value(df, "session_id", path)
        trial = one_value(df, "trial_id", path)
        split = one_value(df, "split", path)
        condition = one_value(df, "condition", path)
        if split not in {"train", "test", "final"} or condition not in LABELS:
            fail(f"{path}: invalid split or condition")
        if path.parent.name != session or path.parent.parent.name != split:
            fail(f"{path}: folder split/session does not match CSV metadata")
        if session in session_splits and session_splits[session] != split:
            fail(f"{session}: one session spans multiple splits (data leakage)")
        session_splits[session] = split
        key = (session, trial)
        if key in seen_trials:
            fail(f"Duplicate physical trial key {key}")
        seen_trials.add(key)

        for field in NUMERIC_FIELDS:
            df[field] = pd.to_numeric(df[field], errors="coerce")
        values = df[NUMERIC_FIELDS].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            fail(f"{path}: invalid/non-numeric/non-finite sensor reading")
        if (df[VALID_FIELDS] != 1).any().any() or (df["boot_error"] != 0).any():
            fail(f"{path}: invalid sensor flags or boot error")
        if not df["ps_raw"].between(0, 1023).all() or not df["als_raw"].between(0, 65535).all():
            fail(f"{path}: optical data outside hardware range")
        if not df["temperature_centi_c"].between(-4000, 8500).all():
            fail(f"{path}: temperature outside valid acquisition range")
        if not df["humidity_centi_pct"].between(0, 10000).all():
            fail(f"{path}: RH outside valid acquisition range")
        for col in ("timestamp_ms", "optical_seq", "aht_seq", "imu_seq"):
            if not (df[col].diff().iloc[1:] > 0).all():
                fail(f"{path}: stale, repeated or out-of-order {col}")
        intervals = df["timestamp_ms"].diff().iloc[1:]
        if not intervals.between(1000, 5000).all():
            fail(f"{path}: unexpected timestamp interval; investigate missing/stale data")

        aggregated.append({
            "session_id": session, "trial_id": trial, "split": split,
            "label": LABELS[condition],
            "proximity_mean": float(df["ps_raw"].mean()),
            "als_mean": float(df["als_raw"].mean()),
            "temperature_c": float(df["temperature_centi_c"].mean() / 100),
            "humidity_pct": float(df["humidity_centi_pct"].mean() / 100),
            "sample_count": len(df),
            "first_timestamp_ms": int(df["timestamp_ms"].iloc[0]),
            "last_timestamp_ms": int(df["timestamp_ms"].iloc[-1]),
            "raw_file": path.relative_to(ROOT).as_posix(),
        })

    out = pd.DataFrame(aggregated).sort_values(["split", "session_id", "trial_id"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False, float_format="%.5f")
    print(f"Saved {len(out)} REAL trial windows to {OUTPUT}")
    print("\nPhysical-trial counts (not sample counts):")
    print(out.groupby(["split", "label"]).size().to_string())
    print("\nIMPORTANT: Software cannot verify that you physically reset each setup.")
    print("Record your lamp/board placement, recording session and photos separately.")
    print("Only trial_raw files are counted; calibration_auto files are excluded.")


if __name__ == "__main__":
    main()
