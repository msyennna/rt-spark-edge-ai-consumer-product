# StudySense Motion AI Stage 2 — separate data workflow

The tests on 2026-11-04 established that a stationary desk had mean acceleration-change values roughly 56-87 and peaks 128-378; gentle repeated tapping had means 129-562 and peaks 1,543-9,908 in the supplied recordings. The exact units are raw changes in ICM20608 accelerometer counts, **not calibrated m/s²**. These are **pilot observations**, not a final false-alarm/accuracy test.

This package **adds only three Python files** to `ml/`, does not overwrite the existing light-only dataset, and makes no Git commit. It needs the **23-column Motion Stage 1 firmware** already uploaded. COM3 monitor must be closed before running any capture script.

## Labels are actual experimental actions, not machine predictions

| `--condition` | ML label | Reproducible setup |
| --- | --- | --- |
| READY | STUDY_READY | Study-lamp position calibrated in your workspace; desk still, marker removed |
| LOW | IMPROVE_LIGHTING | Lamp off / lower light condition, desk still, marker removed |
| TAPPING | DESK_DISTURBANCE | Same lighting as READY; gently tap tabletop beside board for the whole 10s collection, marker removed |

Keep the board on a stationary, stable part of the tabletop, not in hand. No hitting the electronics. These labels are **operational states defined by the setup**, not guarantees of optimum study lighting or human distraction. Samples with near=1 are rejected because the marker may occlude ALS. If poor lighting and tapping occur together, they are outside this first three-class protocol; define priority and test combined cases before release.

## One pilot per state

Run from `C:\Users\Yena\rt-spark-edge-ai-consumer-product` using its venv; with the PlatformIO serial monitor closed:

```powershell
.\.venv\Scripts\python.exe ml\capture_studysense_motion_trial.py --split train --session motion_train_day1 --condition READY --trial R001 --setup-note "lamp at study position; desk still"
.\.venv\Scripts\python.exe ml\capture_studysense_motion_trial.py --split train --session motion_train_day1 --condition LOW --trial L001 --setup-note "lamp off; desk still"
.\.venv\Scripts\python.exe ml\capture_studysense_motion_trial.py --split train --session motion_train_day1 --condition TAPPING --trial D001 --setup-note "lamp at study position; gently tapped desk continuously"
```

Wait approximately 10 seconds after changing the lamp setup before starting the command. Restart/physically prepare each setup independently and record practical setup notes/photos; changing only trial ID cannot create independence. The `TAPPING` trial should have tap activity *during* the collector's 10-second window.

```powershell
.\.venv\Scripts\python.exe ml\build_studysense_motion_dataset.py
```

This creates `data/studysense_motion_windows.csv`, separate from `data/studysense_windows.csv`. The new raw files go to `data/trials_motion_raw/{train|test|final}/{session_id}`. Five 2-second snapshots = ONE 10-second averaged feature window/trial. The builder verifies flags, strictly growing optical/AHT/IMU/motion sequence IDs, freshness, timing, and label integrity.

**Only after sufficient independently prepared trials** (at least 30 per class train, 10 per class session-held-out test, 20 per class additional final product trials) run:

```powershell
.\.venv\Scripts\python.exe ml\train_studysense_motion.py
```

Collect `--split test --session motion_test_day2`, and `--split final --session motion_final_day3` in genuinely new sessions. Don't tune on final trials. Rotate condition order and tap strength for diverse train/test data. Photos, environmental setup and timestamp metadata remain important. No test/model accuracy is claimed yet. Do not count the 14 logging windows from initial tapping as independent product trials.

This package is **host-side acquisition and training**, not STM32 inference. The final product still needs on-MCU feature extraction, actual inference, a user interface, FreeRTOS scheduling QA and duration/offline/per-class evaluation evidence.

### Safe Git staging

Keep the old data and calibration files in place. Stage **only** the new `ml` scripts and this documentation; do not stage `data/trials_motion_raw/` by default or use `git add .` with unintended files. Git author should be set to `msyennna` with the verified email for the local commit. Review file contents before committing.
