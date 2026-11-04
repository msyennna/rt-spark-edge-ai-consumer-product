# StudySense — Stage 3 on-device inference integration (safe scaffold)

This stage adds a separate FreeRTOS `SS_AI` task that acquires five distinct ~2 s motion, light and AHT diagnostic snapshots and calculates features **on the STM32**. The default model header is explicitly **UNTRAINED**: it never claims valid classification, accuracy, or latency. This is **not a trained MCU model yet**.

The five ML features must match `ml/build_studysense_motion_dataset.py` exactly and in order:

1. `als_mean` = sum of 5 optical `als_raw` / 5.
2. `motion_mean_delta_mean` = sum of five 2-second `motion_mean_delta` / 5.
3. `motion_peak_delta_max` = maximum of five 2-second `motion_peak_delta`.
4. `temperature_c` = sum of five AHT21 centi-degree values / 500.
5. `humidity_pct` = sum of five AHT21 centi-percent values / 500.

**Sampling quality:** the task requires new optical, AHT and motion sequence numbers and all flags valid, near=0, motion sampling >=90/100, etc. A rejected sample resets the partial 5-window average. A sensor snapshot copied under an RTOS critical section is a diagnostic snapshot, not hardware-synchronized acquisition across sensors.

The existing CSV logger remains **exactly 23 numeric columns**. Every ~10 seconds it additionally outputs a human-readable `# AI_STATUS,...` line. The working Python trial collector ignores lines beginning with `#`. These notes are not training data.

`g_ai_status`: 0 starting, 1 collecting, 2 trained prediction, 3 five features ready but no model, 4 sensor/data quality gate not met. `g_ai_prediction=255` means *invalid/no trained prediction*. Other class indices: 0=STUDY_READY, 1=IMPROVE_LIGHTING, 2=DESK_DISTURBANCE. `g_ai_inference_cycles=0` while no model. Watch the `# AI_STATUS` lines or debugger globals.

After real >=30 train and >=10 test independent trials per class are collected and train script succeeds, use `ml/export_studysense_motion_cpp.py` to generate a replacement for `include/studysense_model_generated.h`. The exporter validates the feature and label order and refuses to export if held-out counts are insufficient. Review and commit the generated header separately. Rebuild and upload the firmware, then compare host versus STM32 predictions on held-out and repeated physical trials, measure >=50 MCU inference timings, and finish the 20 final product trials/class on the finished device.

The original 14 training trials and initial calibration evidence should be preserved. Do not report laboratory compliance from this scaffold.
