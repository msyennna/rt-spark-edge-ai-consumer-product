# Stage 3A: Onboard sensor detection (experimental, not yet validated)

Reference: RT-Spark Spark-1 schematic and board support documentation. Verify actual kit revision against schematic before flashing. On this board reference, I2C2 is on PF1 (SCL), PF0 (SDA); ICM20608 address 0x68 and AP3216C address 0x1E. The AHT-series sensor uses a separate software I2C bus and is **not** tested yet.

After running `git pull --ff-only origin feature/firmware-rtos`, compile using `pio run -e rt_spark_f407zg`. Confirm build before uploading with the previously verified ST-LINK programming setup.

Firmware adds SensorProbeTask (priority 1, 384 stack words, period 2 seconds) alongside LEDTask, HealthTask, DiagnosticsTask. ST-LINK debugger WATCH variables:
- `g_i2c2_initialized` = 1 if HAL_I2C_Init() succeeded
- `g_sensor_probe_count` = increases every ~2 seconds
- `g_icm20608_detected` = 1 if device ACKs at 0x68
- `g_icm20608_whoami` = expected 175 decimal (0xAF), or 255 if unreadable
- `g_icm20608_id_valid` = 1 if identity register is 0xAF
- `g_ap3216c_detected` = 1 if the 0x1E address ACKs; not enough to certify sensor functionality
- `g_i2c2_last_error` = HAL I2C error bits
- Check existing task counters and `g_boot_error` (=0 when no recorded boot errors)

A failed probe is *not* proof the sensor is missing; confirm board version, pin mux, pull-ups, bus availability and pin conflicts. An ACK is *not* a functional sensor measurement.

Do NOT commit the firmware to main until this diagnostic build and physical board bring-up are reviewed. Later implement real timed acquisition, validation, queues and two relevant sensing modalities, then MCU inference.
