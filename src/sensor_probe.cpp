// BCA182 Laboratory 4, Stage 3A: on-board I2C2 sensor presence checks.
// Hardware verification only; this does not yet stream or classify data.
// Spark-1 HW1.1 schematic: PF1 I2C2_SCL, PF0 I2C2_SDA.
// ICM20608 = I2C address 0x68, WHO_AM_I register 0x75, expected 0xAF.
// AP3216C = I2C address 0x1E. An I2C ACK alone is NOT a full sensor test.
// AHT21/AHT-series is on a separate software I2C bus; not probed here.
#include "sensor_probe.h"
#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

volatile uint32_t g_i2c2_initialized = 0;
volatile uint32_t g_sensor_probe_count = 0;
volatile uint32_t g_icm20608_detected = 0;
volatile uint32_t g_icm20608_whoami = 0xFF;
volatile uint32_t g_icm20608_id_valid = 0;
volatile uint32_t g_ap3216c_detected = 0;
volatile uint32_t g_ap3216c_configured = 0;
volatile uint32_t g_ap3216c_sample_valid = 0;
volatile uint32_t g_ap3216c_sample_count = 0;
volatile uint32_t g_ap3216c_als_raw = 0;
volatile uint32_t g_ap3216c_ps_raw = 0;
volatile uint32_t g_ap3216c_ir_raw = 0;
volatile uint32_t g_ap3216c_object_near = 0;
volatile uint32_t g_ap3216c_ps_valid = 0;
volatile uint32_t g_ap3216c_ps_settings_valid = 0;
volatile uint32_t g_ap3216c_ps_config_reg = 0;
volatile uint32_t g_ap3216c_led_control_reg = 0;
volatile uint32_t g_ap3216c_ps_low_threshold = 0;
volatile uint32_t g_ap3216c_ps_high_threshold = 0;
volatile uint32_t g_i2c2_last_error = 0;
volatile uint32_t g_imu_configured = 0;
volatile uint32_t g_imu_sample_valid = 0;
volatile uint32_t g_imu_sample_count = 0;
volatile int32_t g_accel_x_raw = 0;
volatile int32_t g_accel_y_raw = 0;
volatile int32_t g_accel_z_raw = 0;
volatile int32_t g_gyro_x_raw = 0;
volatile int32_t g_gyro_y_raw = 0;
volatile int32_t g_gyro_z_raw = 0;

static int16_t DecodeSigned16(const uint8_t* b)
{
    return (int16_t)((uint16_t)((uint16_t)b[0] << 8) | b[1]);
}

static I2C_HandleTypeDef s_i2c2 = {};

static bool InitializeI2C2()
{
    __HAL_RCC_GPIOF_CLK_ENABLE();
    __HAL_RCC_I2C2_CLK_ENABLE();

    GPIO_InitTypeDef pins = {};
    pins.Pin = GPIO_PIN_0 | GPIO_PIN_1;
    pins.Mode = GPIO_MODE_AF_OD;
    pins.Pull = GPIO_PULLUP;
    pins.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    pins.Alternate = GPIO_AF4_I2C2;
    HAL_GPIO_Init(GPIOF, &pins);

    s_i2c2.Instance = I2C2;
    s_i2c2.Init.ClockSpeed = 100000;
    s_i2c2.Init.DutyCycle = I2C_DUTYCYCLE_2;
    s_i2c2.Init.OwnAddress1 = 0;
    s_i2c2.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    s_i2c2.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    s_i2c2.Init.OwnAddress2 = 0;
    s_i2c2.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    s_i2c2.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

    return HAL_I2C_Init(&s_i2c2) == HAL_OK;
}

void SensorProbeTask(void *)
{
    // Start after FreeRTOS is active and the sensors have had time to power up.
    vTaskDelay(pdMS_TO_TICKS(100));
    g_i2c2_initialized = InitializeI2C2() ? 1u : 0u;

    // Wake the IMU from sleep using PWR_MGMT_1 = 0x00.
    // This is intentionally one-time initialization; do not reset it each probe.
    const uint16_t icmAddr = (uint16_t)(0x68u << 1);
    if (g_i2c2_initialized &&
        HAL_I2C_IsDeviceReady(&s_i2c2, icmAddr, 2, 20) == HAL_OK) {
        uint8_t wake = 0x00u;
        if (HAL_I2C_Mem_Write(&s_i2c2, icmAddr, 0x6Bu,
                              I2C_MEMADD_SIZE_8BIT, &wake, 1u, 30) == HAL_OK) {
            g_imu_configured = 1;
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }

    // AP3216C mode 0x03 enables ALS + PS/IR functions.
    // Datasheet system config 0x00, measurement registers 0x0A..0x0F.
    const uint16_t apsAddr = (uint16_t)(0x1Eu << 1);
    if (g_i2c2_initialized &&
        HAL_I2C_IsDeviceReady(&s_i2c2, apsAddr, 2, 20) == HAL_OK) {
        uint8_t mode = 0x03u;
        g_ap3216c_configured =
            (HAL_I2C_Mem_Write(&s_i2c2, apsAddr, 0x00u,
                               I2C_MEMADD_SIZE_8BIT, &mode, 1, 30) == HAL_OK) ? 1u : 0u;
    }
    // TEMPORARY diagnostic thresholds only. Observed away ~2, close ~17.
    // Hysteresis: near when PS > 12; away when PS < 5. These values are
    // NOT calibrated and must be revisited after repeated controlled trials.
    // AP3216C registers: 0x2A low-L, 0x2B low-H, 0x2C high-L, 0x2D high-H.
    // Low threshold 5 -> {1, 1}; high threshold 12 -> {0, 3}.
    if (g_ap3216c_configured) {
        uint8_t diagnosticThresholds[4] = {1u, 1u, 0u, 3u};
        if (HAL_I2C_Mem_Write(&s_i2c2, apsAddr, 0x2Au,
                              I2C_MEMADD_SIZE_8BIT,
                              diagnosticThresholds, 4u, 40) != HAL_OK) {
            // A failed threshold write is reported by the readback diagnostics.
            g_ap3216c_configured = 0u;
        }
    }
    if (g_ap3216c_configured) {
        vTaskDelay(pdMS_TO_TICKS(200)); // Allow initial optical measurements to settle.
    }

    TickType_t lastWake = xTaskGetTickCount();
    for (;;) {
        ++g_sensor_probe_count;

        if (g_i2c2_initialized) {
            const uint16_t icmAddr = (uint16_t)(0x68u << 1);
            const uint16_t apsAddr = (uint16_t)(0x1Eu << 1);

            g_icm20608_detected =
                (HAL_I2C_IsDeviceReady(&s_i2c2, icmAddr, 2, 20) == HAL_OK) ? 1u : 0u;
            g_icm20608_whoami = 0xFFu;
            g_icm20608_id_valid = 0;

            if (g_icm20608_detected) {
                uint8_t whoami = 0xFFu;
                if (HAL_I2C_Mem_Read(&s_i2c2, icmAddr, 0x75u,
                                     I2C_MEMADD_SIZE_8BIT, &whoami, 1u, 30) == HAL_OK) {
                    g_icm20608_whoami = whoami;
                    g_icm20608_id_valid = (whoami == 0xAFu) ? 1u : 0u;
                }
            }
            // Read consecutive accel, temperature, and gyro registers (0x3B..0x48).
            // Only update six-axis values after a complete successful transfer.
            g_imu_sample_valid = 0;
            if (g_icm20608_id_valid && g_imu_configured) {
                uint8_t raw[14] = {};
                if (HAL_I2C_Mem_Read(&s_i2c2, icmAddr, 0x3Bu,
                                     I2C_MEMADD_SIZE_8BIT, raw, 14u, 40) == HAL_OK) {
                    g_accel_x_raw = DecodeSigned16(&raw[0]);
                    g_accel_y_raw = DecodeSigned16(&raw[2]);
                    g_accel_z_raw = DecodeSigned16(&raw[4]);
                    g_gyro_x_raw = DecodeSigned16(&raw[8]);
                    g_gyro_y_raw = DecodeSigned16(&raw[10]);
                    g_gyro_z_raw = DecodeSigned16(&raw[12]);
                    ++g_imu_sample_count;
                    g_imu_sample_valid = 1;
                }
            }
            g_ap3216c_detected =
                (HAL_I2C_IsDeviceReady(&s_i2c2, apsAddr, 2, 20) == HAL_OK) ? 1u : 0u;
            g_ap3216c_sample_valid = 0;
            g_ap3216c_ps_valid = 0;
            if (g_ap3216c_detected && g_ap3216c_configured) {
                uint8_t optical[6] = {};
                if (HAL_I2C_Mem_Read(&s_i2c2, apsAddr, 0x0Au,
                                     I2C_MEMADD_SIZE_8BIT, optical, 6u, 40) == HAL_OK) {
                    // 0x0A/0x0B: IR, lower two bits of IR low are data;
                    // bit 7 of IR low indicates IR overflow.
                    // 0x0C/0x0D: 16-bit ALS raw count.
                    // 0x0E/0x0F: PS (10 bit), status/overflow bits also encoded.
                    const uint32_t irOverflow = (optical[0] & 0x80u) ? 1u : 0u;
                    const uint32_t psOverflow =
                        ((optical[4] | optical[5]) & 0x40u) ? 1u : 0u;
                    g_ap3216c_ir_raw =
                        ((uint32_t)optical[1] << 2) | (optical[0] & 0x03u);
                    g_ap3216c_als_raw =
                        ((uint32_t)optical[3] << 8) | (uint32_t)optical[2];
                    g_ap3216c_ps_raw =
                        ((uint32_t)(optical[5] & 0x3Fu) << 4) | (optical[4] & 0x0Fu);
                    g_ap3216c_object_near = (optical[4] & 0x80u) ? 1u : 0u;
                    g_ap3216c_ps_valid = (!irOverflow && !psOverflow) ? 1u : 0u;
                    g_ap3216c_sample_valid = 1u; // Successful transfer; PS has separate validity flag.
                    ++g_ap3216c_sample_count;
                }
            }
            // Read-only proximity configuration and near/far thresholds.
            // No settings are changed by this diagnostic.
            g_ap3216c_ps_settings_valid = 0u;
            if (g_ap3216c_detected && g_ap3216c_configured) {
                uint8_t configRegs[2] = {};
                uint8_t thresholdRegs[4] = {};
                if (HAL_I2C_Mem_Read(&s_i2c2, apsAddr, 0x20u,
                                     I2C_MEMADD_SIZE_8BIT,
                                     configRegs, sizeof(configRegs), 40) == HAL_OK &&
                    HAL_I2C_Mem_Read(&s_i2c2, apsAddr, 0x2Au,
                                     I2C_MEMADD_SIZE_8BIT,
                                     thresholdRegs, sizeof(thresholdRegs), 40) == HAL_OK) {
                    g_ap3216c_ps_config_reg = configRegs[0];
                    g_ap3216c_led_control_reg = configRegs[1];
                    g_ap3216c_ps_low_threshold =
                        ((uint32_t)thresholdRegs[1] << 2) |
                        ((uint32_t)thresholdRegs[0] & 0x03u);
                    g_ap3216c_ps_high_threshold =
                        ((uint32_t)thresholdRegs[3] << 2) |
                        ((uint32_t)thresholdRegs[2] & 0x03u);
                    g_ap3216c_ps_settings_valid = 1u;
                }
            }
            g_i2c2_last_error = HAL_I2C_GetError(&s_i2c2);
        }

        vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(2000));
    }
}
