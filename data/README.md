# StudySense real sensor dataset — lighting calibration phase

This is a **provisional LOW/MEDIUM/BRIGHT study-desk lighting classifier**. It is not the previous paper-marker presence classifier. The marker blocked AP3216C ambient-light sensing in actual tests. The model's labels describe *controlled light setups*, **not** evidence of healthy illumination, glare, student occupancy or attention.

The FreeRTOS UART logger is running on the STM32 and sends valid sensor snapshots about every 2 s. Do not make up or backfill sensor values. Current Python scripts collect, aggregate and train on a PC; **on-MCU inference has not yet been implemented**.

## Keep calibration separate

- Existing `data/calibration/` and `data/calibration_auto/` recordings are valuable real hardware evidence.
- The training-data builder deliberately ignores those folders. Do not relabel calibration runs as independent final trials.
- Preserve actual photos and notes for the lamp-off / lamp-angled / lamp-toward-desk positions. Avoid a paper marker covering AP3216C.

## One genuine physical trial

1. Choose a lighting condition **before** reading the sensor. Label from the lamp setup, not from a sensor threshold or classifier prediction.
2. Set a reproducible lamp/board arrangement; mark locations with removable tape. Document setup differences and any relevant ambient daylight. Let the setup stabilize.
3. Record **five fresh snapshots (about 10 seconds)** in ONE file. The five rows produce ONE averaged window, NOT five independent trials.
4. For the next trial, actually reset/reposition the setup and repeat the physical procedure. Changing only the `--trial` name while keeping the same continuous sensor stream is not independent replication.
5. Mix the order of conditions within training sessions, if practical, to reduce time/temperature confounding. Never force readings into an expected range by relabeling them. Record unexpected cases too.

From the repository root, with COM3 monitor closed:

```powershell
.\.venv\Scripts\python.exe ml\capture_studysense_trial.py --split train --session train_day1 --condition LOW --trial L001 --setup-note "lamp off board fixed"
```

This creates `data/trials_raw/train/train_day1/L001_LOW.csv`. For a different physically prepared trial use another ID such as `L002`; use `--condition MEDIUM --trial M001` or `--condition BRIGHT --trial B001` as appropriate.

To aggregate the **actual** raw captures:

```powershell
.\.venv\Scripts\python.exe ml\build_studysense_dataset.py
```

This creates `data/studysense_windows.csv`. It checks timestamps, sensor validity, sample sequences, session separation and duplicate trial IDs. It cannot verify physical independence; your written protocol and photos must support that.

## Split design and counts

`session_id` is a real collection session, and **a session must belong to a single split**. For example:

| Split | Example session | Minimum independent trials per class |
| --- | --- | ---: |
| train | `train_day1` | 30 |
| test | `test_day2` | 10 |
| final | `final_day3` | 20 |

Those are **60 separate physical trials per class**, or **180 total**, across all splits. Arrange genuinely separate sessions/lighting variations as much as feasible. A different CSV filename is not an independent trial. Never train/tune on held-out final samples; keep the test session held out until the model settings are fixed.

The builder produces exactly one row per trial with the feature header:

```csv
session_id,trial_id,split,label,proximity_mean,als_mean,temperature_c,humidity_pct,sample_count,first_timestamp_ms,last_timestamp_ms,raw_file
```

- Labels: `LOW_LIGHT`, `MODERATE_LIGHT`, `BRIGHT_LIGHT`.
- `als_mean` and `proximity_mean` are uncalibrated AP3216C raw units.
- `temperature_c` and `humidity_pct` are AHT21 engineering units (raw centi-units divided by 100).
- The logger's optical, AHT and IMU probes run asynchronously; each snapshot is diagnostic, not an atomic acquisition. The reader checks validity and strictly increasing sensor sequence numbers, but **precise cross-sensor synchrony is not established**.
- Feature extraction for the eventual MCU inference must use the **same five samples**, measured on the same periods and with matching conversion/scaling. Only after validating should timing/memory/product metrics be claimed.

Training (after sufficient genuine trials):

```powershell
.\.venv\Scripts\python.exe ml\train_studysense.py
```

Training compares a four-feature decision tree against an ambient-light-only tree on session-held-out test data. **Multisensor inputs alone are not evidence of multisensor *decision value*.** If temperature/humidity do not improve classification, report that honestly. A three-class lighting-only AI model may be insufficient to demonstrate the laboratory's multimodal Edge AI objective. A revised study-environment classifier needs actual independent temperature/humidity condition trials, distinct ground-truth labels and verified added value before claiming compliance.

Keep raw files and identifying personal information out of public commits until reviewed for privacy and repository size. Stage only intended source files for your first commit.
