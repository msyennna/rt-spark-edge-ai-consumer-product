# Stage 3D — AHT21 temperature/humidity sensor diagnostic

**Status: code prepared on firmware branch, not yet built or verified on a physical RT-Spark.**

## Reference hardware

Spark-1 HW1.1 official schematic: onboard **AHT21**, 7-bit I2C address **0x38**. Dedicated software-I2C bus uses **PE0 (SCL)** and **PE1 (SDA)**. Check that your kit matches HW1.1 before flashing. This bus is separate from I2C2 used for the ICM20608/AP3216C sensors (PF1/PF0).

## Implementation

- `src/aht21_probe.cpp`: open-drain GPIO software-I2C; short DWT cycle delays; bounded SCL stretch check; status/init command; trigger measurement; 7-byte response; CRC-8 validation; conversion to temperature and RH.
- `include/aht21_probe.h`: debugger observables.
- `src/main.cpp`: adds the fifth FreeRTOS task named `AHT21` with priority 1 and 384 stack **words**, every 2 seconds.
- HAL `SysTick_Handler`, existing I2C2 task and other FreeRTOS tasks are left unchanged.
- This is a diagnostic, not yet a product-ready sensor driver. Its software I2C delays busy-wait briefly while a task is running and require evaluation at the final scheduling rates.

## Local verification (in this order)

1. Stop PIO Debug **completely** (Shift+F5) before building; VS Code debug can lock `firmware.elf` on Windows.
2. `git switch feature/firmware-rtos`, then `git pull --ff-only origin feature/firmware-rtos`.
3. `pio run -e rt_spark_f407zg`. **Do not upload if build fails.**
4. If build succeeds and board matches the HW1.1 reference, `pio run -e rt_spark_f407zg -t upload`.
5. Start PIO Debug, continue 5–10 seconds, pause, observe:
   - `g_aht_probe_count`: should increase every ~2 s.
   - `g_aht_present`: 1 when status command succeeded.
   - `g_aht_status`: sensor status byte (255 means unread).
   - `g_aht_calibrated`: status bit 3 from latest status reply.
   - `g_aht_sample_valid`: 1 only for a successful, CRC-checked, in-range measurement.
   - `g_aht_crc_ok`: 1 if valid CRC and measurement accepted.
   - `g_aht_sample_count`: number of validated readings.
   - `g_aht_temperature_centi_c`: divide by 100 for Celsius; e.g., 2675 means 26.75 C.
   - `g_aht_humidity_centi_pct`: divide by 100 for %RH; e.g., 6225 means 62.25 %RH.
   - `g_aht_error_code`: 0 OK; 1 bus stuck; 2 status error; 3 calibration-init command error; 4 trigger error; 5 data read error; 6 busy; 7 CRC; 8 out-of-range.
   - `g_boot_error`: should remain zero.
6. Compare room measurement with gently warming the sensor area (hand close but not touching) or a modest humidity change. No breath/condensation directly on exposed circuitry.
7. Stop debugger completely before next build.

**Do not claim this sensor works until measured debug values are supplied.** A successful build or I2C ACK alone is insufficient. Avoid merging the experimental task to main without a code review and hardware evidence.
