"""Compile the FreeRTOS kernel included with the installed STM32CubeF4 package.

This project intentionally uses the CMSIS/HAL-compatible kernel bundled with
framework-stm32cubef4, NOT the Arduino FreeRTOS library. Exactly one GCC
Cortex-M4F port and one heap allocator (heap_4.c) are selected.
"""
from pathlib import Path

Import("env")  # Provided by PlatformIO/SCons.

framework_dir = env.PioPlatform().get_package_dir("framework-stm32cubef4")
if not framework_dir:
    raise RuntimeError("framework-stm32cubef4 package not available.")

kernel = Path(framework_dir) / "Middlewares" / "Third_Party" / "FreeRTOS" / "Source"
port = kernel / "portable" / "GCC" / "ARM_CM4F"
heap = kernel / "portable" / "MemMang" / "heap_4.c"

files = [
    "tasks.c",
    "queue.c",
    "list.c",
    "event_groups.c",
    "timers.c",
    "stream_buffer.c",
    "portable/GCC/ARM_CM4F/port.c",
    "portable/MemMang/heap_4.c",
]

for relative in files:
    if not (kernel / relative).is_file():
        raise RuntimeError("Missing STM32CubeF4 FreeRTOS source: " + str(kernel / relative))

env.AppendUnique(CPPPATH=[
    str(kernel / "include"),
    str(port),
    str(Path(env.subst("$PROJECT_DIR")) / "include"),
])

# Pre-build scripts may use BuildSources to append external object files to the
# firmware build. A selective filter prevents compiling all the other ports,
# heap implementations, or CMSIS-RTOS compatibility wrappers.
env.BuildSources(
    "$BUILD_DIR/freertos_kernel",
    str(kernel),
    src_filter=["+<{}>".format(filename) for filename in files],
)

print("BCA182: using STM32CubeF4 bundled FreeRTOS (ARM_CM4F + heap_4).")
