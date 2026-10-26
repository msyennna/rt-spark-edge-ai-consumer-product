# Group collaboration and ownership (draft)

**Status:** Initial proposal; the team must assign actual owners before starting feature work.

## Branch rules

- `main` is the shared, approved integration branch. Never push feature code directly to `main`.
- `setup/firmware-foundation` holds the initial unverified build scaffold. Review and test before merging.
- This is a **three-member group**. After the foundation is reviewed, tested and merged, each member branches **from the updated main**:
  - `feature/firmware-rtos` — Member 1: verified board config, STM32Cube/FreeRTOS foundation, sensor drivers, sampling and integration.
  - `feature/edge-ai` — Member 2: board-data collection plan, DSP/features, labeled dataset, baseline, model training/validation, exported on-device inference.
  - `feature/local-ui` — Member 3: LCD, buttons, LEDs/buzzer, diagnostics UI, local feedback and logging.
- These assignments are proposals until each team member confirms their GitHub username and workstream. All three participate in board testing, validation, documentation and final demonstration. The firmware and ML owners coordinate the captured data format; the UI and integration owners coordinate status messages and task interfaces.
- Members who need to change common startup, clock, pin, interrupt, linker, FreeRTOS configuration or `platformio.ini` must coordinate first with the integration owner.

## Three-member ownership — fill in actual GitHub usernames

| Member | Proposed branch | Primary work | Peer reviewer | Status |
|---|---|---|---|---|
| Member 1 (suggested: firmware lead) | `feature/firmware-rtos` | PlatformIO + FreeRTOS, board config, drivers, sensor acquisition, system integration | Member 3 | Unassigned |
| Member 2 (suggested: Edge AI lead) | `feature/edge-ai` | Data capture protocol, labels, DSP, train/test split, baseline, model evaluation and MCU inference | Member 1 | Unassigned |
| Member 3 (suggested: feedback lead) | `feature/local-ui` | LCD, buttons, alarms, diagnostic/service UI, local output and event logs | Member 2 | Unassigned |

**Shared responsibilities:** real hardware inventory, data collection sessions, code reviews, offline demonstration, 20+ trials per classification state, inference latency runs, 15-minute soak test, evidence, report, and individual explanation. Every member reviews at least one other member's Pull Request. The integration lead may coordinate release builds, but does not merge without review.

**Shared contract:** One firmware image, one PlatformIO config, central peripheral pin map, a single scheduler, one owner of interrupt vectors, and clearly defined interfaces between modules. Do not paste multiple independent `main()` programs together.

## Branch and pull-request flow

1. Clone: `git clone https://github.com/msyennna/rt-spark-edge-ai-consumer-product.git`
2. Enter the repo: `cd rt-spark-edge-ai-consumer-product`
3. Update: `git switch main && git pull --ff-only origin main`
4. Create your branch: `git switch -c feature/firmware-rtos` (replace with your assigned branch).
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
