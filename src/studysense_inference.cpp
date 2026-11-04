// StudySense Stage 3: on-device feature aggregation and safe model hook.
// Genuine on-device predictions are disabled until a trained tree is exported.
// Mirrors ml/build_studysense_motion_dataset.py: FIVE 2-s snapshots -> ONE row.
// IMPORTANT: optical, AHT and motion are still asynchronously acquired, not
// an atomic synchronized sensor frame. Compare actual MCU windows with host data.
#include <stdint.h>
#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "sensor_probe.h"
#include "aht21_probe.h"
#include "motion_probe.h"
#include "studysense_inference.h"
#include "studysense_model_generated.h"

extern volatile uint32_t g_boot_error;

volatile uint32_t g_ai_status = 0;
volatile uint32_t g_ai_model_trained = studysense_ml::kTrained ? 1u : 0u;
volatile uint32_t g_ai_prediction = 255u;
volatile uint32_t g_ai_samples_collected = 0;
volatile uint32_t g_ai_window_count = 0;
volatile uint32_t g_ai_inference_cycles = 0;
volatile uint32_t g_ai_als_sum = 0;
volatile uint32_t g_ai_motion_mean_sum = 0;
volatile uint32_t g_ai_motion_peak_max = 0;
volatile int32_t g_ai_temperature_sum_centi = 0;
volatile uint32_t g_ai_humidity_sum_centi = 0;

namespace {
struct Snapshot {
    uint32_t als, opticalSeq, ahtSeq, motionSeq;
    int32_t tempCenti;
    uint32_t humidityCenti, motionMean, motionPeak;
    uint32_t valid;
};

Snapshot readSnapshot() {
    Snapshot s = {};
    // Keep copy short: do not perform any I2C operation in this section.
    taskENTER_CRITICAL();
    s.als = g_ap3216c_als_raw;
    s.opticalSeq = g_ap3216c_sample_count;
    s.ahtSeq = g_aht_sample_count;
    s.motionSeq = g_motion_window_seq;
    s.tempCenti = g_aht_temperature_centi_c;
    s.humidityCenti = g_aht_humidity_centi_pct;
    s.motionMean = g_motion_mean_delta;
    s.motionPeak = g_motion_peak_delta;
    s.valid = (
        g_ap3216c_ps_valid == 1u &&
        g_ap3216c_sample_valid == 1u &&
        g_ap3216c_object_near == 0u &&
        g_aht_sample_valid == 1u &&
        g_aht_crc_ok == 1u &&
        g_imu_sample_valid == 1u &&
        g_motion_valid == 1u &&
        g_motion_samples >= 90u && g_motion_samples <= 100u &&
        g_motion_failed <= 10u &&
        g_motion_elapsed_ms >= 1800u && g_motion_elapsed_ms <= 2600u &&
        g_motion_max_gap_ms <= 100u &&
        g_ap3216c_als_raw <= 65535u &&
        g_aht_temperature_centi_c >= -4000 &&
        g_aht_temperature_centi_c <= 8500 &&
        g_aht_humidity_centi_pct <= 10000u &&
        g_boot_error == 0u
    ) ? 1u : 0u;
    taskEXIT_CRITICAL();
    return s;
}
}

void StudySenseInferenceTask(void *) {
    // Start after other tasks have initialized their respective sensors.
    vTaskDelay(pdMS_TO_TICKS(1500));
    if (studysense_ml::kTrained) {
        CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
        DWT->CYCCNT = 0u;
        DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    }

    TickType_t wake = xTaskGetTickCount();
    uint32_t oldOpt = 0, oldAht = 0, oldMotion = 0;
    uint32_t collected = 0, lightSum = 0, motionMeanSum = 0, peakMax = 0;
    int32_t temperatureSum = 0;
    uint32_t humiditySum = 0;
    for (;;) {
        Snapshot s = readSnapshot();
        const bool fresh = s.opticalSeq > oldOpt && s.ahtSeq > oldAht &&
                           s.motionSeq > oldMotion;
        oldOpt = s.opticalSeq;
        oldAht = s.ahtSeq;
        oldMotion = s.motionSeq;
        if (!s.valid || !fresh) {
            collected = lightSum = motionMeanSum = peakMax = humiditySum = 0u;
            temperatureSum = 0;
            g_ai_samples_collected = 0u;
            g_ai_status = 4u;
            vTaskDelayUntil(&wake, pdMS_TO_TICKS(2000));
            continue;
        }
        lightSum += s.als;
        motionMeanSum += s.motionMean;
        if (s.motionPeak > peakMax) peakMax = s.motionPeak;
        temperatureSum += s.tempCenti;
        humiditySum += s.humidityCenti;
        ++collected;
        g_ai_samples_collected = collected;
        g_ai_status = 1u;

        if (collected == 5u) {
            // Equal to Python: five-point average of ALS and IMU mean,
            // maximum of IMU peaks, five-point average of temp/RH centi-units.
            const float features[5] = {
                static_cast<float>(lightSum) / 5.0f,
                static_cast<float>(motionMeanSum) / 5.0f,
                static_cast<float>(peakMax),
                static_cast<float>(temperatureSum) / 500.0f,
                static_cast<float>(humiditySum) / 500.0f
            };
            uint8_t prediction = 255u;
            uint32_t cycles = 0u;
            if (studysense_ml::kTrained) {
                const uint32_t begin = DWT->CYCCNT;
                prediction = studysense_ml::Predict(features);
                cycles = DWT->CYCCNT - begin;
                if (prediction > 2u) prediction = 255u;
            }
            taskENTER_CRITICAL();
            g_ai_als_sum = lightSum;
            g_ai_motion_mean_sum = motionMeanSum;
            g_ai_motion_peak_max = peakMax;
            g_ai_temperature_sum_centi = temperatureSum;
            g_ai_humidity_sum_centi = humiditySum;
            g_ai_prediction = prediction;
            g_ai_inference_cycles = cycles;
            g_ai_status = (prediction == 255u) ? 3u : 2u;
            ++g_ai_window_count;
            taskEXIT_CRITICAL();
            collected = lightSum = motionMeanSum = peakMax = humiditySum = 0u;
            temperatureSum = 0;
        }
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(2000));
    }
}
