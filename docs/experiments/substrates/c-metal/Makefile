# Keel on the Metal — Build System
# Targets: arm-none-eabi (Cortex-M4, real hardware)
#           gcc (Linux, simulation mode)

CC_ARM = arm-none-eabi-gcc
CC_NATIVE = gcc

CFLAGS = -Wall -Wextra -O2 -g
CFLAGS_ARM = $(CFLAGS) -mcpu=cortex-m4 -mthumb -nostdlib -ffreestanding
CFLAGS_NATIVE = $(CFLAGS) -DPLATFORM_NATIVE

LDFLAGS_ARM = -T keel.ld -nostartfiles

SRC = /tmp/keel-models/c-metal/src/keel.c
BIN_ARM = build/keel.elf
BIN_NATIVE = build/keel-native

.PHONY: all arm native clean test

all: arm native

arm: $(BIN_ARM)
native: $(BIN_NATIVE)

$(BIN_ARM): $(SRC) keel.ld
	mkdir -p build
	$(CC_ARM) $(CFLAGS_ARM) $(SRC) $(LDFLAGS_ARM) -o $(BIN_ARM)

$(BIN_NATIVE): $(SRC)
	mkdir -p build
	$(CC_NATIVE) $(CFLAGS_NATIVE) $(SRC) -o $(BIN_NATIVE)

test: $(BIN_NATIVE)
	./$(BIN_NATIVE)

clean:
	rm -rf build

flash: $(BIN_ARM)
	openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -c "program $(BIN_ARM) verify reset exit"
