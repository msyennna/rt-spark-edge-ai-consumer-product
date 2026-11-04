# StudySense Stage 0: serial logger bring-up

This is an **experimental diagnostic** task layered on top of Member 1's existing FreeRTOS sensor probes. It is **not yet the final synchronized dataset capture** and not an AI classifier.

## Confirmed source reference
- RT-Spark STM32F407 reference CubeMX project configures USART1_TX on PA9 and USART1_RX on PA10. Actual second-board ST-LINK VCP routing still needs physical testing.
- Existing sensor probe tasks sample every ~2 seconds.
- The output includes time and validity/sequence counters so duplicate/stale readings can be identified; it is NOT synchronized across sensors.
- The logger writes to USART1 at **115200 baud**, expected at the corresponding ST-LINK virtual COM port (COM3 on Member 2's laptop), if that route is wired.
- It does not change GPIO pins used by AP3216C/IMU (PF0/PF1), AHT21 (PE0/PE1), or onboard LED PF12.

## Member 2: compile before flashing
From the separate worktree at `C:\Users\Yena\rt-spark-studysense-logger`, stop serial monitoring and debugging first.

```powershell
git fetch origin
git pull --ff-only origin feature/studysense-logger
pio run -e rt_spark_f407zg
```

If the build fails, **do not upload**. Report the full tail of the build log. If it succeeds, check that the second board matches RT-Spark STM32F407 reference pinout, and then arrange upload after confirming with the group. Flashing **replaces** the existing second-board MQTT firmware; its binary has not been backed up.

## After upload
Expected serial header:

```csv
timestamp_ms,ps_raw,als_raw,near,ps_valid,optical_valid,optical_seq,temperature_centi_c,humidity_centi_pct,aht_valid,aht_crc_ok,aht_seq,imu_valid,imu_seq,boot_error
```

The first line is a `#` diagnostic banner. Sensor values are raw integer measurements; temperature and humidity are *centi*-units (divide by 100). The logger outputs a row every ~2 seconds and tracks `g_studysense_uart_initialized`, `g_studysense_log_count` and `g_studysense_uart_errors` under debugger.

**IMPORTANT**:
1. Do not treat 2-second asynchronous snapshots as independent ML windows or as synchronized sampling.
2. Before any dataset capture, verify that marker-near/away changes `ps_raw`, and that `als_raw` still changes with lamp on/off *while the marker is near*. Previous Member 1 tests had ALS 0 with a near white paper marker.
3. Compare `optical_seq` and `aht_seq` each row, reject invalid or duplicate samples, and inspect errors.
4. For full lab compliance, migrate to timestamped sensor acquisition/queues, a frozen AI feature contract and independent recording sessions.
5. If COM3 stays blank despite successful flashing, do not change pins at random: validate the USART1 routing on that hardware revision, UART init counters, and cable wiring using debugger.
