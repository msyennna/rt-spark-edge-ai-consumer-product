"""Build one feature row per real motion+light trial, without using older lighting-only data."""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "trials_motion_raw"
OUTPUT = ROOT / "data" / "studysense_motion_windows.csv"
LABELS = {"READY": "STUDY_READY", "LOW": "IMPROVE_LIGHTING", "TAPPING": "DESK_DISTURBANCE"}
FLAGS = ["ps_valid", "optical_valid", "aht_valid", "aht_crc_ok", "imu_valid", "motion_valid"]
NUMERIC = ["timestamp_ms", "ps_raw", "als_raw", "near", "optical_seq", "aht_seq",
           "imu_seq", "boot_error", "temperature_centi_c", "humidity_centi_pct",
           "motion_window_seq", "motion_samples", "motion_mean_delta", "motion_peak_delta",
           "motion_failed", "motion_elapsed_ms", "motion_max_gap_ms", *FLAGS]
REQUIRED = ["session_id", "trial_id", "split", "condition", "setup_note", *NUMERIC]


def fail(s: str) -> None:
    sys.exit("ERROR: " + s)


def single(df: pd.DataFrame, field: str, path: Path) -> str:
    v = df[field].astype(str).str.strip().unique()
    if len(v) != 1 or not v[0]:
        fail(f"{path}: not exactly one {field} value")
    return v[0]


def main() -> None:
    files = sorted(RAW.rglob("*.csv")) if RAW.exists() else []
    if not files:
        fail(f"No motion trials recorded yet: {RAW}")
    rows = []
    seen = set()
    splits = {}
    for file in files:
        frame = pd.read_csv(file)
        missing = [c for c in REQUIRED if c not in frame.columns]
        if missing:
            fail(f"{file}: missing {missing}")
        if len(frame) != 5:
            fail(f"{file}: expected 5 windows, got {len(frame)}")
        session, trial, split, condition = [single(frame, c, file) for c in
                                            ("session_id", "trial_id", "split", "condition")]
        if condition not in LABELS or split not in {"train", "test", "final"}:
            fail(f"{file}: invalid split or condition")
        if file.parent.name != session or file.parent.parent.name != split:
            fail(f"{file}: inconsistent folder/session/split")
        if file.stem != f"{trial}_{condition}":
            fail(f"{file}: inconsistent filename/trial ID")
        if session in splits and splits[session] != split:
            fail(f"Session reused across splits: {session}")
        splits[session] = split
        if (session, trial) in seen:
            fail(f"Duplicate trial: {session}/{trial}")
        seen.add((session, trial))
        for f in NUMERIC:
            frame[f] = pd.to_numeric(frame[f], errors="coerce")
        if not np.isfinite(frame[NUMERIC].to_numpy(dtype=float)).all():
            fail(f"{file}: nonfinite/nonnumeric reading")
        if (frame[FLAGS] != 1).any().any() or (frame["boot_error"] != 0).any():
            fail(f"{file}: invalid sensor flags or boot errors")
        if (frame["near"] != 0).any():
            fail(f"{file}: marker might obstruct light sensor (near=1)")
        if not frame["als_raw"].between(0,65535).all() or not frame["ps_raw"].between(0,1023).all():
            fail(f"{file}: raw optical out of range")
        if not frame["motion_samples"].between(90,100).all() or (frame["motion_failed"]>10).any():
            fail(f"{file}: poor motion samples")
        if not frame["motion_elapsed_ms"].between(1800,2600).all() or (frame["motion_max_gap_ms"]>100).any():
            fail(f"{file}: poor motion timing")
        if (frame["motion_mean_delta"] < 0).any() or (frame["motion_peak_delta"] < frame["motion_mean_delta"]).any():
            fail(f"{file}: invalid motion feature")
        if not frame["temperature_centi_c"].between(-4000,8500).all() or not frame["humidity_centi_pct"].between(0,10000).all():
            fail(f"{file}: temperature/humidity out of range")
        for key in ("optical_seq","aht_seq","imu_seq","motion_window_seq","timestamp_ms"):
            if not (frame[key].diff().iloc[1:] > 0).all():
                fail(f"{file}: duplicate or out-of-order {key}")
        if not frame["timestamp_ms"].diff().iloc[1:].between(1000,5000).all():
            fail(f"{file}: unexpected sample gaps")
        rows.append({
            "session_id":session,"trial_id":trial,"split":split,"label":LABELS[condition],
            "als_mean":float(frame["als_raw"].mean()),
            "motion_mean_delta_mean":float(frame["motion_mean_delta"].mean()),
            "motion_peak_delta_max":int(frame["motion_peak_delta"].max()),
            "proximity_mean":float(frame["ps_raw"].mean()),
            "temperature_c":float(frame["temperature_centi_c"].mean()/100),
            "humidity_pct":float(frame["humidity_centi_pct"].mean()/100),
            "sample_count":len(frame),
            "first_timestamp_ms":int(frame["timestamp_ms"].iloc[0]),
            "last_timestamp_ms":int(frame["timestamp_ms"].iloc[-1]),
            "raw_file":file.relative_to(ROOT).as_posix(),
        })
    out = pd.DataFrame(rows).sort_values(["split","session_id","trial_id"])
    OUTPUT.parent.mkdir(exist_ok=True, parents=True)
    out.to_csv(OUTPUT,index=False,float_format="%.5f")
    print(f"Saved {len(rows)} physical motion+light trials to {OUTPUT}")
    print(out.groupby(["split","label"]).size().to_string())
    print("Five sensor windows = ONE physical trial; photo/setup records support independence.")

if __name__ == "__main__":
    main()
