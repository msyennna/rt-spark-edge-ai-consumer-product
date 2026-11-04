#pragma once
#include <stdint.h>

// Diagnostic IMU motion feature. An acquired 2-second window comprises
// 100 scheduled 20-ms attempts; real success count and max gap are reported.
// Mean/peak delta = sum(abs(ax[i]-ax[i-1]),abs(ay[i]-ay[i-1]),abs(az[i]-az[i-1]))
// over successive valid acceleration reads, in ICM20608 raw LSB units.
// NOT calibrated physical units or an ML classification.
extern volatile uint32_t g_motion_window_seq;
extern volatile uint32_t g_motion_valid;
extern volatile uint32_t g_motion_samples;
extern volatile uint32_t g_motion_mean_delta;
extern volatile uint32_t g_motion_peak_delta;
extern volatile uint32_t g_motion_failed;
extern volatile uint32_t g_motion_elapsed_ms;
extern volatile uint32_t g_motion_max_gap_ms;
extern volatile uint32_t g_motion_total_ok;
void MotionSamplerTask(void *parameters);
