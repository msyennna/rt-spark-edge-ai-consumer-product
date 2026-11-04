"""StudySense: first supervised model using real RT-Spark capture windows.

Run from repository root:
    .\\.venv\\Scripts\\python.exe ml\\train_studysense.py

This is a host-side training/validation starter, NOT MCU inference.
Do not generate synthetic measurements for the laboratory submission.
"""
from pathlib import Path
import sys

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "studysense_windows.csv"
MODEL_FILE = ROOT / "models" / "studysense_tree.joblib"

LABELS = ["STATION_IDLE", "STUDY_READY", "ADJUST_ENVIRONMENT"]
FEATURES = ["proximity_mean", "als_mean", "temperature_c", "humidity_pct"]
REQUIRED = ["session_id", "trial_id", "split", "label", *FEATURES]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not DATA_FILE.is_file():
        fail(
            f"Real sensor dataset not found: {DATA_FILE}\n"
            "First collect labeled RT-Spark measurements using the agreed "
            "StudySense capture protocol. See data/README.md."
        )

    df = pd.read_csv(DATA_FILE)
    missing = [name for name in REQUIRED if name not in df.columns]
    if missing:
        fail(f"CSV missing required columns: {', '.join(missing)}")
    if df.empty:
        fail("CSV contains no observations.")

    df["split"] = df["split"].astype(str).str.strip().str.lower()
    df["label"] = df["label"].astype(str).str.strip()
    if not df["split"].isin(["train", "test", "final"]).all():
        fail("split must be train, test, or final.")
    if not df["label"].isin(LABELS).all():
        fail("Unexpected label. Expected: " + ", ".join(LABELS))
    if df[["session_id", "trial_id"]].isna().any().any():
        fail("session_id and trial_id are required for every row.")
    if df[FEATURES].isna().any().any():
        fail("One or more sensor features are blank or invalid.")

    for feature in FEATURES:
        try:
            df[feature] = pd.to_numeric(df[feature], errors="raise")
        except (ValueError, TypeError) as err:
            fail(f"Non-numeric feature {feature}: {err}")
    # Non-finite input is invalid for the first MCU-friendly model.
    import numpy as np

    if not np.isfinite(df[FEATURES].to_numpy(dtype=float)).all():
        fail("Sensor feature values must all be finite.")

    # Every recording session belongs to exactly one split.
    session_splits = df.groupby("session_id")["split"].nunique()
    if (session_splits > 1).any():
        fail("Data leakage: at least one session_id appears in multiple splits.")
    if df.duplicated(["session_id", "trial_id"]).any():
        fail("Duplicate (session_id, trial_id) detected. Use one window per trial.")

    train = df.loc[df["split"] == "train"]
    test = df.loc[df["split"] == "test"]
    if train.empty or test.empty:
        fail("Both training and held-out test sessions are required.")

    print("\nActual window counts by split/class:")
    print(df.groupby(["split", "label"]).size().to_string())
    missing_train = sorted(set(LABELS) - set(train["label"]))
    missing_test = sorted(set(LABELS) - set(test["label"]))
    if missing_train or missing_test:
        fail(f"Each class must appear in both splits. Missing: train={missing_train}, test={missing_test}")

    for label in LABELS:
        n_train = int((train["label"] == label).sum())
        n_test = int((test["label"] == label).sum())
        if n_train < 30 or n_test < 10:
            print(f"WARNING: {label} has {n_train} train and {n_test} test windows; "
                  "the Lab 4 minimum is 30 train and 10 held-out per class.")

    model = DecisionTreeClassifier(max_depth=4, min_samples_leaf=3, random_state=42)
    model.fit(train[FEATURES], train["label"])
    prediction = model.predict(test[FEATURES])

    print("\nSession-held-out test accuracy:", f"{accuracy_score(test['label'], prediction):.3f}")
    print("\nClassification report:")
    print(classification_report(test["label"], prediction, labels=LABELS, zero_division=0))
    print("Confusion matrix (rows=true, columns=predicted):")
    print("Label order:", ", ".join(LABELS))
    print(confusion_matrix(test["label"], prediction, labels=LABELS))

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "labels": LABELS}, MODEL_FILE)
    print(f"\nHost-side model saved to: {MODEL_FILE}")
    print("NEXT: Compare to threshold baseline; export tested decision rules into "
          "STM32 C/C++; verify on-device inference. This .joblib is NOT MCU firmware.")


if __name__ == "__main__":
    main()
