// Stage 0: STM32Cube HAL smoke test, NOT the final FreeRTOS application.
// Watch g_hal_heartbeat in a debugger to confirm the MCU reaches main().
// No RT-Spark peripheral pins are configured until the hardware audit.
#include <stdint.h>
#include "stm32f4xx_hal.h"

volatile uint32_t g_hal_heartbeat = 0;

int main(void) {
    HAL_Init();

    while (1) {
        HAL_Delay(1000);
        ++g_hal_heartbeat;
    }
}
