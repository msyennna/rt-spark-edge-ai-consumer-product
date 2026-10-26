#pragma once
#include <stdint.h>

// AHT21 environmental sensor on the dedicated software-I2C bus.
// Official Spark-1 HW1.1 schematic: PE0=SCL, PE1=SDA, address 0x38.
// Diagnostic values for the VS Code ST-LINK WATCH pane.
//
// Only g_aht_sample_valid=1 + g_aht_crc_ok=1 indicates a validated result.
// Temperature: degrees C * 100 (2534 = 25.34 C).
// Humidity: percent RH * 100 (5678 = 56.78% RH).
extern volatile uint32_t g_aht_probe_count;
extern volatile uint32_t g_aht_present;
extern volatile uint32_t g_aht_status;
extern volatile uint32_t g_aht_calibrated;
extern volatile uint32_t g_aht_sample_valid;
extern volatile uint32_t g_aht_sample_count;
extern volatile uint32_t g_aht_crc_ok;
extern volatile int32_t g_aht_temperature_centi_c;
extern volatile uint32_t g_aht_humidity_centi_pct;
extern volatile uint32_t g_aht_error_code;

// Error codes: 0=OK, 1=bus not idle, 2=status read failed,
// 3=not calibrated, 4=trigger failed, 5=data read failed,
// 6=sensor busy, 7=CRC mismatch, 8=out-of-range value.
void Aht21Task(void *parameters);
