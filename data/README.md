# StudySense real-data collection format (Member 2)

**No synthetic/fabricated measurements should be reported as Lab 4 results.** Wait for Member 1's timestamped serial logger; current branch does not yet have a working StudySense data logger.

## Initial host training format

Create `data/studysense_windows.csv` *after collecting actual sensor data*. Header:

```csv
session_id,trial_id,split,label,proximity_mean,als_mean,temperature_c,humidity_pct
```

- `session_id`: identifies an independent recording session (e.g. `day1_a`). A session must appear in exactly **one** of train/test/final.
- `trial_id`: unique trial/window within a session. For the initial protocol, use one valid **non-overlapping 2-second window per physical trial**.
- `split`: `train`, `test`, or `final`. **Do not** tune the model or its thresholds on `final` trials.
- `label`: `STATION_IDLE`, `STUDY_READY`, `ADJUST_ENVIRONMENT`. Write the true protocol-based state, never the prediction.
- `proximity_mean`: mean **raw AP3216C proximity** reading during window.
- `als_mean`: mean **raw AP3216C ALS** reading during window. Raw value is not automatically lux.
- `temperature_c`: AHT-series temperature in degrees C; `humidity_pct`: relative humidity in percent. Preserve source timestamp and age; stale readings must be flagged in raw logs, not silently accepted.

**Additional raw sample log/metadata required:** timestamps, sensor validity flags, sampling period, firmware version/commit, study-marker geometry and position, room/desk lamp condition, participant code (not personal name), class-2 reason, independent session/trial IDs, and label protocol. Make a file for raw readings and a separate manifest linking to each averaged window.

**Class protocol:** marker absent = `STATION_IDLE`; marker present and study conditions within declared limits = `STUDY_READY`; marker present but genuinely dim light / documented condition needing adjustment = `ADJUST_ENVIRONMENT`. First verify that the white marker does not obstruct the ALS channel. AP3216C cannot detect whether a student is sitting elsewhere at the desk.

**Lab minimum per class:** at least 30 train windows, 10 session-held-out test windows, plus 20 additional independent *final product trials*. Suggested target: 40 train, 15 test, 20 final per class. Collect independently, from actual hardware. No overlapping or near-duplicate windows crossing splits.

**Use:** `ml/train_studysense.py` validates the CSV, checks session separation, prints a confusion matrix/precision/recall, and saves a **host-only** scikit-learn decision tree to `models/`. It will deliberately stop with a clear message until the dataset exists. Model export, a non-ML threshold baseline, and MCU timing/inference are subsequent steps.

**Privacy/safety:** never commit identifying participant information; avoid dangerous light/temperature experiments. Keep the STM32 interface and feature order synchronized with Member 1.
