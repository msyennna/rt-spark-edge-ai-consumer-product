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

## AHT21 temperature / humidity — initial readout

- On-board AHT21 software-I2C diagnostic on PE0 (SCL) / PE1 (SDA) was observed running with the FreeRTOS scheduler.
- VS Code ST-LINK WATCH evidence (2026-10-26):
  - `g_aht_probe_count = 10`, `g_aht_present = 1`, `g_aht_status = 24` (0x18).
  - `g_aht_calibrated = 1`, `g_aht_sample_valid = 1`, `g_aht_sample_count = 10`, `g_aht_crc_ok = 1`.
  - `g_aht_temperature_centi_c = 3144` => **31.44 °C**.
  - `g_aht_humidity_centi_pct = 8338` => **83.38 % RH**.
  - `g_aht_error_code = 0`, `g_boot_error = 0`.
- **Status:** Initial CRC-checked temperature and humidity measurement demonstrated on hardware. Accuracy, response, and longer-duration reliability remain unvalidated.

## Limitations / follow-up

1. Repeat near/away test with at least several cycles, varied ambient light, and different reflective surfaces; inspect noise / false transitions.
2. Current proximity thresholds are **temporary test values**, not a final product calibration.
3. Do not treat saturated `1023` as distance or use raw ALS readings as lux without correct range conversion.
4. Repeat AHT21 measurements over time and compare with a reference thermometer/hygrometer; verify response to moderate environmental changes.
5. Define the consumer-product application and required sample rates before replacing these low-rate diagnostic probes with sensor acquisition + queues + on-device ML inference.
6. Save original WATCH screenshots locally for lab evidence and upload copies separately if requested. This document records the observed values only.
