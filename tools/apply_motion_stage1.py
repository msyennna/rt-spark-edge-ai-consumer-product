"""Apply StudySense IMU Stage 1 to the firmware worktree, without rewriting git history.

Run from C:\\Users\\Yena\\rt-spark-studysense-logger:
    python tools\\apply_motion_stage1.py

Preflight checks all expected source snippets BEFORE writing any file.
It refuses to patch unexpected/partially modified files.
"""
from __future__ import annotations

from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one matching anchor, found {count}; no files patched")
    return source.replace(old, new, 1)


def patch_sensor(s: str) -> str:
    s = replace_once(s, '#include "task.h"\n',
        '#include "task.h"\n#include "semphr.h"\n', "sensor include")
    s = replace_once(s, 'static I2C_HandleTypeDef s_i2c2 = {};',
        'static I2C_HandleTypeDef s_i2c2 = {};\n'
        'static SemaphoreHandle_t s_i2c2_mutex = nullptr;', "I2C handle")
    s = replace_once(s, 'void SensorProbeTask(void *)\n{',
        '''// Called only by the motion task; the legacy SensorProbeTask owns I2C2.
// Locking prevents interleaved transactions on the same STM32 peripheral.
bool SensorReadMotionAcceleration(int16_t *x, int16_t *y, int16_t *z)
{
    if (x == nullptr || y == nullptr || z == nullptr ||
        !g_i2c2_initialized || !g_imu_configured || s_i2c2_mutex == nullptr) {
        return false;
    }
    if (xSemaphoreTake(s_i2c2_mutex, pdMS_TO_TICKS(15)) != pdTRUE) return false;
    uint8_t raw[6] = {};
    const HAL_StatusTypeDef status = HAL_I2C_Mem_Read(
        &s_i2c2, static_cast<uint16_t>(0x68u << 1), 0x3Bu,
        I2C_MEMADD_SIZE_8BIT, raw, sizeof(raw), 15);
    xSemaphoreGive(s_i2c2_mutex);
    if (status != HAL_OK) return false;
    *x = DecodeSigned16(&raw[0]);
    *y = DecodeSigned16(&raw[2]);
    *z = DecodeSigned16(&raw[4]);
    return true;
}

void SensorProbeTask(void *)
{''', "inserting motion I2C read")
    s = replace_once(s, '    g_i2c2_initialized = InitializeI2C2() ? 1u : 0u;',
        '''    s_i2c2_mutex = xSemaphoreCreateMutex();
    g_i2c2_initialized =
        (s_i2c2_mutex != nullptr && InitializeI2C2()) ? 1u : 0u;''',
        "mutex initialization")
    s = replace_once(s, '        if (g_i2c2_initialized) {\n',
        '''        if (g_i2c2_initialized && s_i2c2_mutex != nullptr &&
            xSemaphoreTake(s_i2c2_mutex, pdMS_TO_TICKS(30)) == pdTRUE) {
''', "protect legacy I2C loop")
    s = replace_once(s,
        '            g_i2c2_last_error = HAL_I2C_GetError(&s_i2c2);\n',
        '''            g_i2c2_last_error = HAL_I2C_GetError(&s_i2c2);
            xSemaphoreGive(s_i2c2_mutex);
''', "release I2C mutex")
    return s


def patch_header(s: str) -> str:
    return replace_once(s, 'void SensorProbeTask(void *parameters);',
        '''// Returns one fresh accel sample with a protected I2C2 transaction.
// False means no valid sample: DO NOT treat as zero motion.
bool SensorReadMotionAcceleration(int16_t *x, int16_t *y, int16_t *z);
void SensorProbeTask(void *parameters);''', "sensor header")


def patch_main(s: str) -> str:
    s = replace_once(s, '#include "studysense_logger.h"',
        '#include "studysense_logger.h"\n#include "motion_probe.h"', "main include")
    s = replace_once(s, '    vTaskStartScheduler();',
        '''    // Experimental fast motion task (~50 Hz) owns no other I2C peripheral.
    if (xTaskCreate(MotionSamplerTask, "Motion", 384, nullptr, 2, nullptr) != pdPASS) {
        g_boot_error = 10;
        for (;;) {}
    }

    vTaskStartScheduler();''', "create motion task")
    return s


def patch_logger(s: str) -> str:
    s = replace_once(s, '#include "aht21_probe.h"',
        '#include "aht21_probe.h"\n#include "motion_probe.h"', "logger include")
    s = replace_once(s, '"aht_seq,imu_valid,imu_seq,boot_error\\r\\n");',
        '''"aht_seq,imu_valid,imu_seq,boot_error,"
              "motion_valid,motion_window_seq,motion_samples,motion_mean_delta,"
              "motion_peak_delta,motion_failed,motion_elapsed_ms,motion_max_gap_ms\\r\\n");''',
        "logger CSV header")
    s = replace_once(s,
        '        const uint32_t bootError = g_boot_error;',
        '''        const uint32_t bootError = g_boot_error;
        // Coherent published 2-second IMU diagnostic snapshot.
        taskENTER_CRITICAL();
        const uint32_t motionValid = g_motion_valid;
        const uint32_t motionWindowSeq = g_motion_window_seq;
        const uint32_t motionSamples = g_motion_samples;
        const uint32_t motionMeanDelta = g_motion_mean_delta;
        const uint32_t motionPeakDelta = g_motion_peak_delta;
        const uint32_t motionFailed = g_motion_failed;
        const uint32_t motionElapsedMs = g_motion_elapsed_ms;
        const uint32_t motionMaxGapMs = g_motion_max_gap_ms;
        taskEXIT_CRITICAL();''', "logger snapshot")
    s = replace_once(s, 'char line[200] = {};', 'char line[320] = {};', "logger buffer")
    s = replace_once(s,
        '"%lu,%lu,%lu,%lu,%lu,%lu,%lu,%ld,%lu,%lu,%lu,%lu,%lu,%lu,%lu\\r\\n",',
        '''"%lu,%lu,%lu,%lu,%lu,%lu,%lu,%ld,%lu,%lu,%lu,%lu,%lu,%lu,%lu,"
            "%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu\\r\\n",''',
        "logger format")
    s = replace_once(s,
        '            static_cast<unsigned long>(bootError));',
        '''            static_cast<unsigned long>(bootError),
            static_cast<unsigned long>(motionValid),
            static_cast<unsigned long>(motionWindowSeq),
            static_cast<unsigned long>(motionSamples),
            static_cast<unsigned long>(motionMeanDelta),
            static_cast<unsigned long>(motionPeakDelta),
            static_cast<unsigned long>(motionFailed),
            static_cast<unsigned long>(motionElapsedMs),
            static_cast<unsigned long>(motionMaxGapMs));''', "logger format args")
    return s


def main() -> None:
    transformations = {
        "src/sensor_probe.cpp": patch_sensor,
        "include/sensor_probe.h": patch_header,
        "src/main.cpp": patch_main,
        "src/studysense_logger.cpp": patch_logger,
    }
    outputs = {}
    try:
        for rel, transform in transformations.items():
            path = root / rel
            if not path.is_file():
                raise RuntimeError(f"Missing {path} - run from the logger firmware worktree")
            outputs[path] = transform(path.read_text(encoding="utf-8"))
        if not (root / "src/motion_probe.cpp").exists():
            raise RuntimeError("Copy the entire zip into the firmware worktree first")
        if not (root / "include/motion_probe.h").exists():
            raise RuntimeError("Copy the entire zip into the firmware worktree first")
    except Exception as exc:
        sys.exit(f"FAILED PREFLIGHT, no files patched: {exc}")
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print("Patched", path.relative_to(root))
    print("Motion Stage 1 patch applied. Build with: pio run -e rt_spark_f407zg")
    print("Do NOT run the old Python CSV collectors on the new 23-column logger yet.")


if __name__ == "__main__":
    main()
