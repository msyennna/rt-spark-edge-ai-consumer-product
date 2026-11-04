r"""Train the StudySense lighting-condition model from real independent trials.

Run from the Edge AI repository root:
  .\.venv\Scripts\python.exe ml\build_studysense_dataset.py
  .\.venv\Scripts\python.exe ml\train_studysense.py

Host-side training ONLY. No inference is running on the STM32 yet.
"""
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "studysense_windows.csv"
MODEL_FILE = ROOT / "models" / "studysense_tree.joblib"
LABELS = ["LOW_LIGHT", "MODERATE_LIGHT", "BRIGHT_LIGHT"]
FEATURES = ["proximity_mean", "als_mean", "temperature_c", "humidity_pct"]
REQUIRED = ["session_id", "trial_id", "split", "label", *FEATURES]
MIN_TRAIN = 30
MIN_TEST = 10
MIN_FINAL = 20


def fail(message: str) -> None:
    raise SystemExit("ERROR: " + message)


def report(title: str, true: pd.Series, predicted: np.ndarray) -> None:
    print(f"\n{title}")
    print(f"Accuracy: {accuracy_score(true, predicted):.3f}")
    print(classification_report(true, predicted, labels=LABELS, zero_division=0))
    print("Confusion matrix (true rows, predicted columns):")
    print("Order:", ", ".join(LABELS))
    print(confusion_matrix(true, predicted, labels=LABELS))


def main() -> None:
    if not DATA_FILE.is_file():
        fail(f"Real training data not found: {DATA_FILE}. Record and aggregate physical trials first.")
    df = pd.read_csv(DATA_FILE)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        fail("CSV missing required columns: " + ", ".join(missing))
    if df.empty:
        fail("Dataset contains zero trials")
    df["split"] = df["split"].astype(str).str.strip().str.lower()
    df["label"] = df["label"].astype(str).str.strip()
    if not df["split"].isin(["train", "test", "final"]).all():
        fail("split must be train, test, or final")
    if not df["label"].isin(LABELS).all():
        fail("Unexpected label; expected: " + ", ".join(LABELS))
    if df[["session_id", "trial_id"]].isna().any().any():
        fail("Missing physical trial/session identifier")
    if df.duplicated(["session_id", "trial_id"]).any():
        fail("Duplicate (session_id, trial_id): count each physical trial once")
    if (df.groupby("session_id")["split"].nunique() > 1).any():
        fail("Data leakage: one recording session belongs to multiple splits")
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if not np.isfinite(df[FEATURES].to_numpy(dtype=float)).all():
        fail("Missing/non-finite feature value")

    print("Physical-trial counts by split and class:")
    print(df.groupby(["split", "label"]).size().to_string())
    train = df[df["split"] == "train"]
    test = df[df["split"] == "test"]
    final = df[df["split"] == "final"]
    shortages = []
    for cls in LABELS:
        n_train = int((train["label"] == cls).sum())
        n_test = int((test["label"] == cls).sum())
        n_final = int((final["label"] == cls).sum())
        if n_train < MIN_TRAIN:
            shortages.append(f"{cls}: train {n_train}/{MIN_TRAIN}")
        if n_test < MIN_TEST:
            shortages.append(f"{cls}: test {n_test}/{MIN_TEST}")
        if n_final < MIN_FINAL:
            print(f"FINAL PRODUCT EVALUATION STILL REQUIRED: {cls} {n_final}/{MIN_FINAL}")
    if shortages:
        fail("Minimum independent train/test trials not reached:\n  " + "\n  ".join(shortages))

    model = DecisionTreeClassifier(max_depth=4, min_samples_leaf=3, random_state=42)
    model.fit(train[FEATURES], train["label"])
    report("Multisensor INPUT model (not proof all sensors help)",
           test["label"], model.predict(test[FEATURES]))

    als_model = DecisionTreeClassifier(max_depth=4, min_samples_leaf=3, random_state=42)
    als_model.fit(train[["als_mean"]], train["label"])
    report("Ambient-light-only ablation", test["label"],
           als_model.predict(test[["als_mean"]]))

    print("\nFull-model feature importances:")
    for field, importance in zip(FEATURES, model.feature_importances_):
        print(f" {field}: {importance:.3f}")
    print("CAUTION: Only the lab test conditions are labeled. Mere use of temperature/RH")
    print("as inputs does NOT prove multimodal classification. If the light-only model")
    print("performs equally well, document this and design environmental condition trials.")
    if len(final) > 0:
        print("Final trials intentionally remain untouched: do not tune on these samples.")

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "labels": LABELS,
                 "sample_count_per_trial": 5, "sensor_period_ms": 2000}, MODEL_FILE)
    print(f"\nSaved host-side candidate model: {MODEL_FILE}")
    print("NEXT: export and test the decision tree in STM32 C/C++; confirm the")
    print("same five-sample feature averaging and run >=50 on-MCU timing measurements.")
    print("A joblib model on this laptop does NOT meet the on-MCU inference requirement.")


if __name__ == "__main__":
    main()
