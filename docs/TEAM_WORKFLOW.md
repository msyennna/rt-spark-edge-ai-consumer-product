# Group collaboration and ownership (draft)

**Status:** Initial proposal; the team must assign actual owners before starting feature work.

## Branch rules

- `main` is the shared, approved integration branch. Never push feature code directly to `main`.
- `setup/firmware-foundation` holds the initial unverified build scaffold. Review and test before merging.
- After the foundation is merged, each member branches **from the updated main**:
  - `feature/sensors` — board inventory, sensor drivers, sampling, diagnostics.
  - `feature/ml-pipeline` — labeled data, DSP, training, baseline, exported model.
  - `feature/local-ui` — LCD, buttons, LEDs, buzzer and feedback.
  - `feature/rtos-integration` — FreeRTOS configuration, task ownership, queues and fault handling.
- Branch examples are workstreams, not necessarily one branch per person; assign them according to group size.
- Members who need to change common startup, clock, pin, interrupt, linker, FreeRTOS configuration or `platformio.ini` must coordinate first with the integration owner.

## Ownership table — fill in GitHub usernames

| Workstream | GitHub owner | Reviewer | Current status |
|---|---|---|---|
| STM32Cube / FreeRTOS integration | TBD | TBD | Not started |
| Onboard sensor drivers & diagnostics | TBD | TBD | Not started |
| Data, DSP, training & on-device inference | TBD | TBD | Not started |
| LCD / buttons / local feedback | TBD | TBD | Not started |
| Test evidence / report / reproducibility | TBD | TBD | Not started |

**Shared contract:** One firmware image, one PlatformIO config, central peripheral pin map, a single scheduler, one owner of interrupt vectors, and clearly defined interfaces between modules. Do not paste multiple independent `main()` programs together.

## Branch and pull-request flow

1. Clone: `git clone https://github.com/msyennna/rt-spark-edge-ai-consumer-product.git`
2. Enter the repo: `cd rt-spark-edge-ai-consumer-product`
3. Update: `git switch main && git pull --ff-only origin main`
4. Create your branch: `git switch -c feature/sensors` (use your assigned name).
5. Implement only the agreed workstream. Use `git status` and `git diff` before committing.
6. Stage selected files: `git add src/sensors.cpp include/sensors.h` (example only; replace with actual paths).
7. Commit: `git commit -m "feat: add sensor readout"`
8. Publish: `git push -u origin feature/sensors`
9. Open a pull request to `main`; request a review. Do not merge until code review and applicable build/board tests pass.
10. After merge, everyone updates local `main`. Create the next branch from that updated `main`.

For an existing feature branch that needs new `main` changes: commit or stash work first, then `git fetch origin` and `git merge origin/main` while on the feature branch. Resolve conflicts with the integration owner. Do not force-push shared branches.

## Integration checklist

- [ ] Compiles with `pio run -e rt_spark_f407zg` using STM32Cube.
- [ ] FreeRTOS actually integrated and scheduler starts (NOT complete in the initial smoke test).
- [ ] Only one interrupt vector / SysTick/HAL timebase implementation.
- [ ] Board clock, actual pin map, DMA, RAM/Flash linker layout checked against RT-Spark hardware.
- [ ] Sensors, model, feedback, and diagnostics all run in one firmware.
- [ ] Model inference continues without Wi-Fi.
- [ ] No keys, personal data, binaries or generated `.pio` files committed.
- [ ] Test results and limitations stated honestly.

## First milestones

**Stage 0 (this PR):** Agree on teamwork policy and test a basic STM32Cube PlatformIO build / HAL startup. There is **no FreeRTOS yet** and no verified peripherals.

**Stage 1 (next PR):** Validate schematic, UART/pins/clock/debugger, integrate exactly one compatible FreeRTOS kernel and ARM_CM4F portable layer with correct HAL timebase and interrupts. Demonstrate scheduler startup and at least three tasks.

**Stage 2:** Bring up sensors and UI as separate modules with a consolidated diagnostic mode.

**Stage 3:** Collect actual board data, train/validate compact model, integrate it on STM32, test offline.

**Stage 4:** Run specified trials, latency/memory/soak tests, finalize evidence and report.
