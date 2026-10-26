// RT-Spark Spark-1 HW1.1 AHT21 diagnostic driver (GPIO software I2C).
// Board schematic: PE0=SCL, PE1=SDA; AHT21 7-bit address 0x38.
// This bus is separate from the working I2C2 sensor-probe bus (PF0/PF1).
// Initial diagnostic only, NOT a calibrated product acquisition driver.
#include "aht21_probe.h"
#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"

volatile uint32_t g_aht_probe_count = 0;
volatile uint32_t g_aht_present = 0;
volatile uint32_t g_aht_status = 0xFF;
volatile uint32_t g_aht_calibrated = 0;
volatile uint32_t g_aht_sample_valid = 0;
volatile uint32_t g_aht_sample_count = 0;
volatile uint32_t g_aht_crc_ok = 0;
volatile int32_t g_aht_temperature_centi_c = 0;
volatile uint32_t g_aht_humidity_centi_pct = 0;
volatile uint32_t g_aht_error_code = 0;

namespace {
constexpr uint16_t SCL = GPIO_PIN_0;
constexpr uint16_t SDA = GPIO_PIN_1;
constexpr uint8_t AHT_WRITE = 0x70;
constexpr uint8_t AHT_READ = 0x71;

inline void sclLow() { HAL_GPIO_WritePin(GPIOE, SCL, GPIO_PIN_RESET); }
inline void sclRelease() { HAL_GPIO_WritePin(GPIOE, SCL, GPIO_PIN_SET); }
inline void sdaLow() { HAL_GPIO_WritePin(GPIOE, SDA, GPIO_PIN_RESET); }
inline void sdaRelease() { HAL_GPIO_WritePin(GPIOE, SDA, GPIO_PIN_SET); }
inline bool sdaHigh() { return HAL_GPIO_ReadPin(GPIOE, SDA) == GPIO_PIN_SET; }
inline bool sclHigh() { return HAL_GPIO_ReadPin(GPIOE, SCL) == GPIO_PIN_SET; }

void delayUs(uint32_t us) {
    const uint32_t clocksPerUs = SystemCoreClock / 1000000u;
    const uint32_t start = DWT->CYCCNT;
    const uint32_t cycles = us * (clocksPerUs ? clocksPerUs : 1u);
    while ((uint32_t)(DWT->CYCCNT - start) < cycles) {}
}
void busPause() { delayUs(8); }

bool clockHigh() {
    sclRelease();
    // Bounded wait accommodates clock stretching / pull-up rise.
    for (unsigned i = 0; i < 100; ++i) {
        if (sclHigh()) { busPause(); return true; }
        delayUs(5);
    }
    return false;
}

void startCondition() {
    sdaRelease(); sclRelease(); busPause();
    sdaLow(); busPause(); sclLow(); busPause();
}
void stopCondition() {
    sdaLow(); busPause(); (void)clockHigh();
    sdaRelease(); busPause();
}
bool writeByte(uint8_t value) {
    for (unsigned i=0; i<8; ++i) {
        if (value & 0x80u) sdaRelease(); else sdaLow();
        busPause();
        if (!clockHigh()) return false;
        sclLow(); busPause();
        value <<= 1;
    }
    sdaRelease(); busPause();
    if (!clockHigh()) return false;
    const bool ack = !sdaHigh();
    sclLow(); busPause();
    return ack;
}
bool readByte(uint8_t &value, bool ack) {
    sdaRelease();
    value = 0;
    for (unsigned i=0; i<8; ++i) {
        busPause();
        if (!clockHigh()) return false;
        value = static_cast<uint8_t>((value << 1) | (sdaHigh() ? 1u : 0u));
        sclLow(); busPause();
    }
    if (ack) sdaLow(); else sdaRelease();
    busPause();
    if (!clockHigh()) return false;
    sclLow(); busPause();
    sdaRelease();
    return true;
}
bool command(const uint8_t *bytes, unsigned count) {
    startCondition();
    bool ok = writeByte(AHT_WRITE);
    for (unsigned i=0; i<count && ok; ++i) ok=writeByte(bytes[i]);
    stopCondition();
    return ok;
}
bool readData(uint8_t *out, unsigned count) {
    startCondition();
    bool ok=writeByte(AHT_READ);
    for (unsigned i=0; i<count && ok; ++i) ok=readByte(out[i], i+1<count);
    stopCondition();
    return ok;
}
uint8_t crc8(const uint8_t *bytes, unsigned count) {
    uint8_t crc=0xFF;
    for (unsigned i=0; i<count; ++i) {
        crc ^= bytes[i];
        for (unsigned bit=0; bit<8; ++bit)
            crc = (crc & 0x80u) ? static_cast<uint8_t>((crc<<1)^0x31u)
                                : static_cast<uint8_t>(crc<<1);
    }
    return crc;
}
void initBus() {
    __HAL_RCC_GPIOE_CLK_ENABLE();
    GPIO_InitTypeDef gpio = {};
    gpio.Pin = SCL | SDA;
    gpio.Mode = GPIO_MODE_OUTPUT_OD;
    gpio.Pull = GPIO_PULLUP; // Board external pullups are preferable.
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOE, &gpio);
    sclRelease(); sdaRelease();
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}
}

void Aht21Task(void *) {
    initBus();
    vTaskDelay(pdMS_TO_TICKS(50));
    TickType_t wake = xTaskGetTickCount();
    for (;;) {
        ++g_aht_probe_count;
        g_aht_sample_valid = 0;
        g_aht_crc_ok = 0;
        g_aht_error_code = 0;
        g_aht_present = 0;
        if (!sclHigh() || !sdaHigh()) {
            g_aht_error_code = 1;
        } else {
            uint8_t status = 0xFFu;
            const uint8_t statusCommand = 0x71u;
            // AHT21 status command 0x71 is a standalone read-status operation
            // (not a register on a generic I2C memory-device protocol).
            if (!command(&statusCommand, 1) || !readData(&status, 1)) {
                g_aht_error_code = 2;
            } else {
                g_aht_present = 1;
                g_aht_status = status;
                if (!(status & 0x08u)) {
                    const uint8_t initialize[3] = {0xBEu, 0x08u, 0x00u};
                    if (!command(initialize, 3)) g_aht_error_code = 3;
                    vTaskDelay(pdMS_TO_TICKS(20));
                }
                const uint8_t measure[3] = {0xACu, 0x33u, 0x00u};
                if (!g_aht_error_code && !command(measure, 3)) g_aht_error_code = 4;
                if (!g_aht_error_code) {
                    vTaskDelay(pdMS_TO_TICKS(100));
                    uint8_t data[7] = {};
                    if (!readData(data, 7)) {
                        g_aht_error_code = 5;
                    } else if (data[0] & 0x80u) {
                        g_aht_error_code = 6;
                    } else if (crc8(data,6) != data[6]) {
                        g_aht_error_code = 7;
                    } else {
                        const uint32_t rhRaw = ((uint32_t)data[1]<<12) |
                            ((uint32_t)data[2]<<4) | ((uint32_t)data[3]>>4);
                        const uint32_t tempRaw = (((uint32_t)data[3]&0x0Fu)<<16) |
                            ((uint32_t)data[4]<<8) | data[5];
                        const uint32_t rh100 = (uint32_t)(((uint64_t)rhRaw*10000u + 524288u) >> 20);
                        const int32_t c100 = (int32_t)(((uint64_t)tempRaw*20000u + 524288u)>>20) - 5000;
                        if (rh100 > 10000u || c100 < -4000 || c100 > 8500) {
                            g_aht_error_code = 8;
                        } else {
                            g_aht_humidity_centi_pct = rh100;
                            g_aht_temperature_centi_c = c100;
                            g_aht_crc_ok = 1;
                            g_aht_sample_valid = 1;
                            ++g_aht_sample_count;
                        }
                    }
                }
            }
        }
        g_aht_calibrated = (g_aht_status & 0x08u) ? 1u : 0u;
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(2000));
    }
}
