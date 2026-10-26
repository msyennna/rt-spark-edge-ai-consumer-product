# RT-Spark physical inventory — complete before pin assignment

The lab requires every **physically available, functioning** onboard sensor / module to be included in the integrated application or a meaningful diagnostic mode. A connector alone does not mean an accessory is installed.

| Resource to inspect | Fitted? | Tested? | Pins/bus from schematic | Role or exception |
|---|---|---|---|---|
| STM32F407ZGT6 / board revision / oscillator | TBD | TBD | TBD | Core platform |
| ICM20608 6-axis IMU | TBD | TBD | TBD | To decide |
| AHT10 temperature/humidity | TBD | TBD | TBD | To decide |
| AP3216C light/proximity | TBD | TBD | TBD | To decide |
| LCD | TBD | TBD | TBD | Feedback/diagnostics |
| Buttons | TBD | TBD | TBD | Input |
| LED or LED matrix | TBD | TBD | TBD | Feedback/diagnostics |
| Buzzer | TBD | TBD | TBD | Feedback/diagnostics |
| Wi-Fi module | TBD | TBD | TBD | Optional communication/diagnostics |
| RTC | TBD | TBD | TBD | If fitted |
| External flash / microSD | TBD | TBD | TBD | If fitted |
| IR/CAN/RS485/other modules | TBD | TBD | TBD | Only if fitted |

Record RT-Spark schematic revision, ST-LINK connection, USB UART routing, oscillator source, HAL timebase choice and memory/linker evidence. Do **not** assume the generic `black_f407zg` board manifest represents the complete RT-Spark hardware. Obtain instructor-verified exceptions for absent/inoperative components where necessary.

Minimum for the primary consumer product: two distinct relevant onboard sensing modalities when available, at least one user input, and at least one local output.

Do not finalize feature selection or model design until this checklist is verified on the physical kit.
