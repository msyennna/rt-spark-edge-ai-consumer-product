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
// Stage 3C: AP3216C ambient-light and proximity measurements.
// Values are raw ADC counts; do not describe them as lux or distance.
extern volatile uint32_t g_ap3216c_configured;
extern volatile uint32_t g_ap3216c_sample_valid;
extern volatile uint32_t g_ap3216c_sample_count;
extern volatile uint32_t g_ap3216c_als_raw;
extern volatile uint32_t g_ap3216c_ps_raw;
extern volatile uint32_t g_ap3216c_ir_raw;
extern volatile uint32_t g_ap3216c_object_near;
extern volatile uint32_t g_ap3216c_ps_valid;

extern volatile uint32_t g_i2c2_last_error;

// Stage 3B: real IMU sample diagnostics (raw 16-bit sensor counts, not calibrated).
// g_imu_sample_valid becomes 1 only after a successful 14-byte ICM20608 read.
extern volatile uint32_t g_imu_configured;
extern volatile uint32_t g_imu_sample_valid;
extern volatile uint32_t g_imu_sample_count;
extern volatile int32_t g_accel_x_raw;
extern volatile int32_t g_accel_y_raw;
extern volatile int32_t g_accel_z_raw;
extern volatile int32_t g_gyro_x_raw;
extern volatile int32_t g_gyro_y_raw;
extern volatile int32_t g_gyro_z_raw;


// FreeRTOS task entry point. RT-Spark reference schematic HW1.1:
// I2C2: PF1=SCL, PF0=SDA; ICM20608 @ 0x68; AP3216C @ 0x1E.
void SensorProbeTask(void *parameters);
