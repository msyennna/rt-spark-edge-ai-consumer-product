# StudySense — Stage 1 IMU motion bring-up (experimental)

## Purpose

This incremental firmware update aims to detect gentle movement of the desk **on which the RT-Spark rests**. It does not measure concentration, productivity, or human presence. No ML runs on-device yet.

- `MotionSamplerTask`: nominal 50-Hz reads, 100 attempts / 2 seconds.
- The acceleration feature is raw L1 successive-sample difference: `abs(dx)+abs(dy)+abs(dz)`. Published `motion_mean_delta` and `motion_peak_delta` are raw ICM20608 units, not calibrated accelerations.
- An I2C2 mutex protects the fast IMU reads from the existing optical/IMU diagnostic task, since ICM20608 and AP3216C share that peripheral.
- `motion_valid`, `motion_samples`, `motion_failed`, `motion_elapsed_ms`, and `motion_max_gap_ms` help detect unreliable sampling. These should be checked before accepting motion features.
- The existing 15-field serial logger gains EIGHT fields after `boot_error`:
  `motion_valid,motion_window_seq,motion_samples,motion_mean_delta,motion_peak_delta,motion_failed,motion_elapsed_ms,motion_max_gap_ms`.
- Existing serial observation on COM3 continues at 115200 baud, but the old **15-field PC calibration/trial collector does not parse the new 23-field output**. Do NOT capture training data with that old collector until it is upgraded.

## Applying safely

Use the existing separate worktree at `C:\Users\Yena\rt-spark-studysense-logger`, branch `feature/studysense-logger`. Extract the ZIP **there**. This bundle does not contain `main.cpp` or `sensor_probe.cpp` replacements; `tools/apply_motion_stage1.py` patches their currently checked-out contents only if expected anchors match.

```powershell
cd C:\Users\Yena\rt-spark-studysense-logger
Expand-Archive "$env:USERPROFILE\Downloads\StudySense_Motion_Stage1.zip" -DestinationPath . -Force
python tools\apply_motion_stage1.py
pio run -e rt_spark_f407zg
```

If Python is not on PATH use `C:\Users\Yena\rt-spark-edge-ai-consumer-product\.venv\Scripts\python.exe` to invoke the patcher.

If the build fails, DO NOT flash. Send the first compiler error to the assistant. The patcher does not push/commit under the wrong account. Review `git diff` before making your own commit as `msyennna`.

## After successful build

With permission already granted to replace the firmware on your second board, flash with `pio run -e rt_spark_f407zg -t upload`. This will overwrite the current 15-field StudySense diagnostic image. Then monitor COM3 with `pio device monitor -p COM3 -b 115200`.

A sample **23-value** line will end in eight motion diagnostic fields. Verify the `motion_window_seq` increases, `motion_valid=1`, `motion_samples` about 100, `motion_failed` near 0, `motion_elapsed_ms` about 2,000 and that the mean/peak motion delta differ between a still desk and gentle tapping beside the board. Do not hit or shake the board directly.

Do not treat one row as an independent product trial. This is sensor calibration and feature verification; true training/test/final capture and dataset versioning will follow after this stage.

## Limitations and next phase

The existing AHT21 and optical tasks still operate at ~2s, and their values are not acquired simultaneously with every motion sample. The motion summary may also repeat across adjacent UART rows due to separately scheduled 2-second tasks. Host processing must use window sequence IDs and reject stale/invalid rows. A later revision will add a defined timestamped multi-modal feature window / queue, versioned host collector, and the three proposed classes `STUDY_READY`, `IMPROVE_LIGHTING`, and `DESK_DISTURBANCE`. The final classifier must be exported from actual independent training data and executed on the STM32 with timing evidence.
