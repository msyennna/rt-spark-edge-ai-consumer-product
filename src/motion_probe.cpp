// StudySense: experimental ~50 Hz accelerometer sampler and 2-second motion
// diagnostic feature. This does NOT yet perform ML inference on the STM32.
// Uses a lock-protected read interface owned by SensorProbeTask (I2C2).
#include <stdint.h>
#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "sensor_probe.h"
#include "motion_probe.h"

volatile uint32_t g_motion_window_seq = 0;
volatile uint32_t g_motion_valid = 0;
volatile uint32_t g_motion_samples = 0;
volatile uint32_t g_motion_mean_delta = 0;
volatile uint32_t g_motion_peak_delta = 0;
volatile uint32_t g_motion_failed = 0;
volatile uint32_t g_motion_elapsed_ms = 0;
volatile uint32_t g_motion_max_gap_ms = 0;
volatile uint32_t g_motion_total_ok = 0;

namespace {
constexpr uint32_t kAttempts = 100; // nominal 2 seconds at 50 Hz
uint32_t absDelta(int16_t current, int16_t previous)
{
    int32_t d = static_cast<int32_t>(current) - static_cast<int32_t>(previous);
    return static_cast<uint32_t>(d < 0 ? -d : d);
}
}

void MotionSamplerTask(void *)
{
    // Let the existing owner initialize the I2C peripheral and wake the IMU.
    vTaskDelay(pdMS_TO_TICKS(800));
    const TickType_t period = pdMS_TO_TICKS(20);
    TickType_t wake = xTaskGetTickCount();
    uint32_t beginMs = HAL_GetTick();
    uint32_t priorMs = beginMs;
    uint32_t maxGapMs = 0;
    uint32_t count = 0;
    uint32_t success = 0;
    uint32_t failures = 0;
    uint32_t pairs = 0;
    uint32_t peak = 0;
    uint64_t deltaSum = 0;
    int16_t priorX = 0, priorY = 0, priorZ = 0;
    bool havePrior = false;

    for (;;) {
        const uint32_t nowMs = HAL_GetTick();
        if (count != 0) {
            const uint32_t gap = nowMs - priorMs;
            if (gap > maxGapMs) maxGapMs = gap;
        }
        priorMs = nowMs;

        int16_t x = 0, y = 0, z = 0;
        if (SensorReadMotionAcceleration(&x, &y, &z)) {
            ++success;
            if (havePrior) {
                const uint32_t delta = absDelta(x, priorX)
                                     + absDelta(y, priorY)
                                     + absDelta(z, priorZ);
                deltaSum += delta;
                if (delta > peak) peak = delta;
                ++pairs;
            }
            priorX = x;
            priorY = y;
            priorZ = z;
            havePrior = true;
        } else {
            ++failures;
            havePrior = false; // do not bridge a missing measurement
        }
        ++count;

        if (count == kAttempts) {
            const uint32_t elapsedMs = HAL_GetTick() - beginMs;
            const uint32_t mean = pairs ? static_cast<uint32_t>(deltaSum / pairs) : 0u;
            // Minimum quality gate: no fabricated zero-motion window on I2C failure.
            const uint32_t valid = (success >= 90 && pairs >= 85 &&
                maxGapMs <= 100 && elapsedMs >= 1800 && elapsedMs <= 2600) ? 1u : 0u;
            taskENTER_CRITICAL();
            g_motion_valid = valid;
            g_motion_samples = success;
            g_motion_mean_delta = mean;
            g_motion_peak_delta = peak;
            g_motion_failed = failures;
            g_motion_elapsed_ms = elapsedMs;
            g_motion_max_gap_ms = maxGapMs;
            g_motion_total_ok += success;
            ++g_motion_window_seq; // publish last; serial task snapshots under critical
            taskEXIT_CRITICAL();
            count = success = failures = pairs = peak = maxGapMs = 0;
            deltaSum = 0;
            havePrior = false;
            beginMs = HAL_GetTick();
            priorMs = beginMs;
        }
        vTaskDelayUntil(&wake, period);
    }
}
