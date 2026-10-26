// BCA182 Laboratory 4 — Stage 1: RT-Spark hardware LED smoke test.
// HAL only. FreeRTOS, sensors and AI have NOT been integrated yet.
// RT-Thread Spark-1 BSP identifies the onboard red LED as PF12.
// No external wiring is required. Do not use this as final lab firmware.
#include <stdint.h>
#include "stm32f4xx_hal.h"

volatile uint32_t g_hal_heartbeat = 0;

int main(void)
{
    HAL_Init();                 // Default internal clock / HAL SysTick timebase.
    __HAL_RCC_GPIOF_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {};
    gpio.Pin = GPIO_PIN_12;    // RT-Spark onboard red LED (LED_R).
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOF, &gpio);

    // Spark-1 onboard LED is commonly active LOW; toggle works either way.
    HAL_GPIO_WritePin(GPIOF, GPIO_PIN_12, GPIO_PIN_SET);

    while (1) {
        HAL_GPIO_TogglePin(GPIOF, GPIO_PIN_12);
        ++g_hal_heartbeat;     // Optional watch expression in debugger.
        HAL_Delay(500);        // Expected ~0.5 s change per toggle.
    }
}

// HAL_Init() configures the SysTick timer, but this bare-metal project must
// provide an IRQ handler to advance the HAL millisecond timebase.
// FreeRTOS integration will later require coordinated tick/interrupt ownership.
extern "C" void SysTick_Handler(void)
{
    HAL_IncTick();
}
