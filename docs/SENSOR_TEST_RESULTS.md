# RT-Spark Laboratory Activity 4 — Sensor Bring-Up Evidence

**Date:** 2026-10-26
**Branch:** `feature/firmware-rtos`
**Source:** User-observed ST-LINK/VS Code WATCH readings on physical RT-Spark board (shared screenshots). These results are not automated tests.

## Previously verified platform bring-up

- STM32Cube + FreeRTOS firmware compiled, flashed and blinked the onboard PF12 red LED.
- Three scheduled FreeRTOS task counters advanced at their designed periods.
- `g_boot_error = 0` during observed tests.

## ICM20608

- Detected over I2C2 at address 0x68; `WHO_AM_I = 0xAF` (175 decimal).
- After wake-up, 14-byte read produced plausible raw acceleration/gyroscope values, including `accel_z_raw = 16848` in one mostly level orientation.
- **Status:** Identity and basic data acquisition verified; no calibration or motion classifier dataset yet.

## AP3216C

- Detected over I2C2 at address 0x1E.
- Initial multi-byte register reads generated mirrored/fabricated channel patterns and were **not** accepted as valid ALS/PS evidence.
- Code was corrected to read optical registers `0x0A..0x0F` **individually**.
- Experimental proximity hysteresis thresholds: **lower 60, upper 120 raw units**, configuration readback matches and `g_ap3216c_ps_interrupt_mode = 1`.
- One observed full cycle (white paper approximately 1 cm away vs removed):
  - No paper: proximity raw **8**, near flag **0**, ALS raw **61**.
  - Paper close: proximity raw **1023**, near flag **1**, ALS raw **0**. Reading is at the 10-bit sensor maximum (saturated).
  - Paper removed: proximity raw **0**, near flag **0**, ALS raw **62**.
- For the final removal screenshot: `g_ap3216c_sample_valid = 1`, `g_ap3216c_ps_valid = 1`, `g_ap3216c_ps_thresholds_match = 1`, `g_i2c2_last_error = 0`, `g_boot_error = 0`.
- **Status:** One near/away transition successfully demonstrated. Not yet statistically validated or calibrated.

## Limitations / follow-up

1. Repeat near/away test with at least several cycles, varied ambient light, and different reflective surfaces; inspect noise / false transitions.
2. Current proximity thresholds are **temporary test values**, not a final product calibration.
3. Do not treat saturated `1023` as distance or use raw ALS readings as lux without correct range conversion.
4. Validate the AHT21 temperature/humidity sensor at 7-bit address `0x38`, using its *separate* software-I2C pins after checking the board schematic/revision.
5. Define the consumer-product application and required sample rates before replacing these low-rate diagnostic probes with sensor acquisition + queues + on-device ML inference.
6. Save original WATCH screenshots locally for lab evidence and upload copies separately if requested. This document records the observed values only.
