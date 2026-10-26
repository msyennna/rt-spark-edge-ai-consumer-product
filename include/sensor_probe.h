#pragma once

#include <stdint.h>

// Hardware diagnostics visible in the ST-LINK debugger.
// status: 0 = failed/not detected; 1 = detected/initialized.
extern volatile uint32_t g_i2c2_initialized;
extern volatile uint32_t g_sensor_probe_count;
extern volatile uint32_t g_icm20608_detected;
extern volatile uint32_t g_icm20608_whoami; // 0xFF means not read
extern volatile uint32_t g_icm20608_id_valid;
extern volatile uint32_t g_ap3216c_detected;
extern volatile uint32_t g_i2c2_last_error;

// FreeRTOS task entry point. RT-Spark reference schematic HW1.1:
// I2C2: PF1=SCL, PF0=SDA; ICM20608 @ 0x68; AP3216C @ 0x1E.
void SensorProbeTask(void *parameters);
