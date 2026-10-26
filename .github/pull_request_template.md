## What changed?

Explain what you added and which workstream owns it.

## Verification (check only what you actually ran)

- [ ] `pio run -e rt_spark_f407zg` succeeded
- [ ] Tested on actual RT-Spark board (list board revision, evidence/logs)
- [ ] Relevant FreeRTOS task/heap/stack checks passed
- [ ] Confirmed no pin/clock/interrupt conflicts
- [ ] No secrets or generated build artifacts committed
- [ ] Another group member reviewed the change

## Evidence / limitations

Paste a short test log, screenshots/links to evidence, or explain why something remains untested.

## Integration impact

Does this change `main.cpp`, `platformio.ini`, startup/clock, interrupt handlers, FreeRTOS config, shared pin assignments or ML input shape? If yes, confirm the integration owner reviewed it.
