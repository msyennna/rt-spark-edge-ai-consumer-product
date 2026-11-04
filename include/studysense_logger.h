#pragma once
#include <stdint.h>
// Stage 0 diagnostic serial logger. NOT synchronized final ML sampling.
extern volatile uint32_t g_studysense_uart_initialized;
extern volatile uint32_t g_studysense_log_count;
extern volatile uint32_t g_studysense_uart_errors;
void StudySenseLoggerTask(void *parameters);
