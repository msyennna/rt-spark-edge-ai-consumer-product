#pragma once
#include <stdint.h>

// StudySense Stage 3: five genuine 2-s snapshots per inference feature window.
// No trained model exists in the default generated-model header.
// Status: 0=starting, 1=collecting, 2=trained model prediction,
//         3=complete window but UNTRAINED, 4=waiting for fresh/valid sensors.
extern volatile uint32_t g_ai_status;
extern volatile uint32_t g_ai_model_trained;
extern volatile uint32_t g_ai_prediction;   // 0=READY,1=LIGHT,2=DISTURBANCE,255=none
extern volatile uint32_t g_ai_samples_collected;
extern volatile uint32_t g_ai_window_count;
extern volatile uint32_t g_ai_inference_cycles;
extern volatile uint32_t g_ai_als_sum;
extern volatile uint32_t g_ai_motion_mean_sum;
extern volatile uint32_t g_ai_motion_peak_max;
extern volatile int32_t g_ai_temperature_sum_centi;
extern volatile uint32_t g_ai_humidity_sum_centi;

void StudySenseInferenceTask(void *parameters);
