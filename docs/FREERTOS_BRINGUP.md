# Lab 4 Stage 2 — FreeRTOS bring-up

## Status

**Not yet validated on hardware.** This stage replaces the HAL delay loop with
three independently scheduled tasks. Only merge after a successful PlatformIO
build, ST-LINK flash, and visible FreeRTOS LED test.

## Kernel source and reproducibility

`tools/add_freertos.py` compiles the FreeRTOS kernel **bundled with** the
PlatformIO-installed `framework-stm32cubef4` package (observed on the
developer's machine as STM32CubeF4 1.28.3). Selected sources:
`tasks.c`, `queue.c`, `list.c`, `event_groups.c`, `timers.c`,
`stream_buffer.c`, `portable/GCC/ARM_CM4F/port.c` and
`portable/MemMang/heap_4.c`. No Arduino FreeRTOS / extra port / second
heap implementation should be present.

## Tasks (initial test only)

| Task | Priority | Stack (words) | Period | Proof |
|---|---:|---:|---:|---|
| LEDTask | 2 | 192 | 500 ms | PF12 red LED toggles |
| HealthTask | 1 | 192 | 1000 ms | `g_health_count` increases in debugger |
| DiagnosticsTask | 1 | 256 | 2000 ms | `g_diag_count`, heap and stack watermark variables update |

The **later product architecture** will replace these provisional tasks with
SensorTask, InferenceTask and FeedbackTask plus the required queues/synchronization.

## Build and hardware test

1. `git switch feature/firmware-rtos`
2. `git pull --ff-only origin feature/firmware-rtos`
3. `pio run -e rt_spark_f407zg`
4. If successful, use the previously **verified** ST-LINK path:
   `pio run -e rt_spark_f407zg -t upload`.
5. Expect the onboard red PF12 LED to alternate every 500 ms.
6. If debugging, watch `g_led_count`, `g_health_count`,
   `g_diag_count`, `g_last_hal_tick`, `g_free_heap_bytes`,
   `g_min_ever_free_heap_bytes`, `g_led_stack_free_words`.
7. Preserve the build/upload output and record test observations.

## Cortex-M4F FPU build configuration

The FreeRTOS `ARM_CM4F` port includes floating-point register context-save
instructions. The initial build failed at `port.o` with `vstmdbeq` and
`vldmiaeq` assembler errors because the PlatformIO STM32Cube configuration
had not selected the floating-point instruction set. The project now sets
`-mfpu=fpv4-sp-d16` and `-mfloat-abi=softfp` in `platformio.ini`. These
allow hardware FP instructions while preserving the soft-float calling
convention for compatibility. Rebuild the **entire** firmware with these flags.
This fix is not validated until a local clean build passes and the scheduler
runs on the physical board.

## Interrupt/clock notes

- `HAL_Init()` sets up the initial HAL millisecond tick (internal
  oscillator/default system clock for this smoke test).
- `SysTick_Handler()` calls `HAL_IncTick()` on each tick and forwards
  the tick to FreeRTOS **after** scheduler startup.
- GCC CM4F `port.c` owns `SVC_Handler` and `PendSV_Handler`.
- All shared peripheral IRQ priorities must be reviewed before adding
  any ISR that uses a FreeRTOS `...FromISR` API.
- The generic `black_f407zg` board manifest is still provisional for
  the RT-Spark kit; confirm actual oscillator, peripheral pins and SRAM
  mapping before treating this as an RT-Spark-specific build.
- No board sensor, UART console, Wi-Fi, on-device ML model or full
  integration is included in this stage.

## Failure indicators

If task creation fails, `g_boot_error` is set to 1, 2 or 3 and
the code stops before starting the scheduler. If the scheduler returns,
`g_boot_error` is set to 4. Stack overflow and failed kernel allocation
set values 5 and 6. These flags can be examined with a debugger.

Build success alone does not prove runtime operation; report actual evidence.
