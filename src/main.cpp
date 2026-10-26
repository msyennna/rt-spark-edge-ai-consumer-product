// BCA182 Lab 4, Stage 2: FreeRTOS + STM32Cube HAL hardware smoke test.
// This is NOT yet an Edge AI product. No sensors or ML inference yet.
#include <stdint.h>
#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "sensor_probe.h"
#include "aht21_probe.h"

volatile uint32_t g_led_count = 0;
volatile uint32_t g_health_count = 0;
volatile uint32_t g_diag_count = 0;
volatile uint32_t g_last_hal_tick = 0;
volatile uint32_t g_free_heap_bytes = 0;
volatile uint32_t g_min_ever_free_heap_bytes = 0;
volatile uint32_t g_led_stack_free_words = 0;
volatile uint32_t g_boot_error = 0;

static TaskHandle_t g_led_handle = nullptr;

static void LEDTask(void *)
{
    TickType_t wake = xTaskGetTickCount();
    for (;;) {
        HAL_GPIO_TogglePin(GPIOF, GPIO_PIN_12);
        ++g_led_count;
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(500));
    }
}

static void HealthTask(void *)
{
    TickType_t wake = xTaskGetTickCount();
    for (;;) {
        ++g_health_count;
        g_last_hal_tick = HAL_GetTick();
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(1000));
    }
}

static void DiagnosticsTask(void *)
{
    TickType_t wake = xTaskGetTickCount();
    for (;;) {
        ++g_diag_count;
        g_free_heap_bytes = (uint32_t)xPortGetFreeHeapSize();
        g_min_ever_free_heap_bytes = (uint32_t)xPortGetMinimumEverFreeHeapSize();
        if (g_led_handle != nullptr) {
            g_led_stack_free_words = (uint32_t)uxTaskGetStackHighWaterMark(g_led_handle);
        }
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(2000));
    }
}

extern "C" void vApplicationStackOverflowHook(TaskHandle_t, char *)
{
    taskDISABLE_INTERRUPTS();
    g_boot_error = 5;
    for (;;) {}
}

extern "C" void vApplicationMallocFailedHook(void)
{
    taskDISABLE_INTERRUPTS();
    g_boot_error = 6;
    for (;;) {}
}

int main(void)
{
    HAL_Init();
    HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);

    __HAL_RCC_GPIOF_CLK_ENABLE();
    GPIO_InitTypeDef gpio = {};
    gpio.Pin = GPIO_PIN_12;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOF, &gpio);
    HAL_GPIO_WritePin(GPIOF, GPIO_PIN_12, GPIO_PIN_SET);

    if (xTaskCreate(LEDTask, "LED", 192, nullptr, 2, &g_led_handle) != pdPASS) {
        g_boot_error = 1;
        for (;;) {}
    }
    if (xTaskCreate(HealthTask, "Health", 192, nullptr, 1, nullptr) != pdPASS) {
        g_boot_error = 2;
        for (;;) {}
    }
    if (xTaskCreate(DiagnosticsTask, "Diagnostics", 256, nullptr, 1, nullptr) != pdPASS) {
        g_boot_error = 3;
        for (;;) {}
    }

    if (xTaskCreate(SensorProbeTask, "SensorProbe", 384, nullptr, 1, nullptr) != pdPASS) {
        g_boot_error = 7;
        for (;;) {}
    }

    if (xTaskCreate(Aht21Task, "AHT21", 384, nullptr, 1, nullptr) != pdPASS) {
        g_boot_error = 8;
        for (;;) {}
    }

    vTaskStartScheduler();

    g_boot_error = 4;  // The scheduler should never return.
    for (;;) {}
}

extern "C" void xPortSysTickHandler(void);

// HAL's 1 ms timer must continue even before FreeRTOS starts.
// FreeRTOS's Cortex-M4F port owns SVC and PendSV handlers.
extern "C" void SysTick_Handler(void)
{
    HAL_IncTick();

    if (xTaskGetSchedulerState() == taskSCHEDULER_RUNNING) {
        xPortSysTickHandler();
    }
}
