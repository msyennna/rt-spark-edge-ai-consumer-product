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
volatile uint32_t g_i2c2_last_error = 0;

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
            g_ap3216c_detected =
                (HAL_I2C_IsDeviceReady(&s_i2c2, apsAddr, 2, 20) == HAL_OK) ? 1u : 0u;
            g_i2c2_last_error = HAL_I2C_GetError(&s_i2c2);
        }

        vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(2000));
    }
}
