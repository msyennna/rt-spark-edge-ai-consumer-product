// StudySense Stage 0: serial sensor bring-up (NOT the final ML dataset sampler).
// Spark-1 reference board CubeMX configuration: USART1 PA9 TX / PA10 RX.
// Verify your actual board's ST-LINK VCP routing before relying on COM3.
// Deliberately low rate: existing sensor probe tasks acquire every ~2 seconds.
#include <stdio.h>
#include <string.h>
#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "sensor_probe.h"
#include "aht21_probe.h"

// Boot diagnostics defined by src/main.cpp (shared across translation units).
extern volatile uint32_t g_boot_error;

volatile uint32_t g_studysense_uart_initialized = 0;
volatile uint32_t g_studysense_log_count = 0;
volatile uint32_t g_studysense_uart_errors = 0;

namespace {
UART_HandleTypeDef uart = {};

bool initializeSerial() {
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_USART1_CLK_ENABLE();
    GPIO_InitTypeDef gpio = {};
    gpio.Pin = GPIO_PIN_9 | GPIO_PIN_10;
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_PULLUP;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = GPIO_AF7_USART1;
    HAL_GPIO_Init(GPIOA, &gpio);

    uart.Instance = USART1;
    uart.Init.BaudRate = 115200;
    uart.Init.WordLength = UART_WORDLENGTH_8B;
    uart.Init.StopBits = UART_STOPBITS_1;
    uart.Init.Parity = UART_PARITY_NONE;
    uart.Init.Mode = UART_MODE_TX_RX;
    uart.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    uart.Init.OverSampling = UART_OVERSAMPLING_16;
    return HAL_UART_Init(&uart) == HAL_OK;
}

void writeLine(const char *str) {
    const uint16_t len = static_cast<uint16_t>(strlen(str));
    if (HAL_UART_Transmit(&uart,
                          reinterpret_cast<uint8_t *>(const_cast<char *>(str)),
                          len, 100u) != HAL_OK) {
        ++g_studysense_uart_errors;
    }
}
}

void StudySenseLoggerTask(void *) {
    g_studysense_uart_initialized = initializeSerial() ? 1u : 0u;
    if (!g_studysense_uart_initialized) {
        ++g_studysense_uart_errors;
        vTaskDelete(nullptr);
    }
    // Wait for the existing probe tasks to initialize their sensors.
    vTaskDelay(pdMS_TO_TICKS(1200));
    writeLine("# StudySense diagnostic logger v0; NOT final training dataset\r\n");
    writeLine("timestamp_ms,ps_raw,als_raw,near,ps_valid,optical_valid,optical_seq,"
              "temperature_centi_c,humidity_centi_pct,aht_valid,aht_crc_ok,"
              "aht_seq,imu_valid,imu_seq,boot_error\r\n");

    TickType_t wake = xTaskGetTickCount();
    for (;;) {
        // Read diagnostic snapshots. They are updated asynchronously by two
        // existing 2-second tasks. Sequence columns flag stale/repeated data.
        // A future logger must create synchronized sensor windows and queues.
        const uint32_t timeMs = HAL_GetTick();
        const uint32_t ps = g_ap3216c_ps_raw;
        const uint32_t als = g_ap3216c_als_raw;
        const uint32_t nearFlag = g_ap3216c_object_near;
        const uint32_t psValid = g_ap3216c_ps_valid;
        const uint32_t opticalValid = g_ap3216c_sample_valid;
        const uint32_t opticalSeq = g_ap3216c_sample_count;
        const int32_t tempCenti = g_aht_temperature_centi_c;
        const uint32_t rhCenti = g_aht_humidity_centi_pct;
        const uint32_t ahtValid = g_aht_sample_valid;
        const uint32_t crcOk = g_aht_crc_ok;
        const uint32_t ahtSeq = g_aht_sample_count;
        const uint32_t imuValid = g_imu_sample_valid;
        const uint32_t imuSeq = g_imu_sample_count;
        const uint32_t bootError = g_boot_error;

        char line[200] = {};
        const int n = snprintf(
            line, sizeof(line),
            "%lu,%lu,%lu,%lu,%lu,%lu,%lu,%ld,%lu,%lu,%lu,%lu,%lu,%lu,%lu\r\n",
            static_cast<unsigned long>(timeMs),
            static_cast<unsigned long>(ps),
            static_cast<unsigned long>(als),
            static_cast<unsigned long>(nearFlag),
            static_cast<unsigned long>(psValid),
            static_cast<unsigned long>(opticalValid),
            static_cast<unsigned long>(opticalSeq),
            static_cast<long>(tempCenti),
            static_cast<unsigned long>(rhCenti),
            static_cast<unsigned long>(ahtValid),
            static_cast<unsigned long>(crcOk),
            static_cast<unsigned long>(ahtSeq),
            static_cast<unsigned long>(imuValid),
            static_cast<unsigned long>(imuSeq),
            static_cast<unsigned long>(bootError));
        if (n > 0 && n < static_cast<int>(sizeof(line))) {
            writeLine(line);
            ++g_studysense_log_count;
        } else {
            ++g_studysense_uart_errors;
        }
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(2000));
    }
}
