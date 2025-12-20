# Personal Engineering OS - Scheduler Engine
# Makefile for C compilation

CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -O2
SHARED_FLAGS = -shared -fPIC
DEBUG_FLAGS = -g -DDEBUG

# Targets
TARGET = scheduler
SHARED_TARGET = scheduler_engine

# Sources
SOURCES = scheduler.c
ENGINE_SOURCES = scheduler_engine.c
HEADERS = scheduler.h

# Data files
DATA_FILES = schedule.dat labs.dat

# Platform detection for shared library extension
ifeq ($(OS),Windows_NT)
    SHARED_EXT = .dll
    SHARED_FLAGS = -shared
else
    UNAME := $(shell uname)
    ifeq ($(UNAME),Darwin)
        SHARED_EXT = .dylib
        SHARED_FLAGS = -shared -fPIC
    else
        SHARED_EXT = .so
        SHARED_FLAGS = -shared -fPIC
    endif
endif

# Default target - build both CLI and shared library
all: $(TARGET) shared

# CLI executable (original scheduler)
$(TARGET): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCES)
	@echo "Build complete: ./$(TARGET)"

# Shared library for Python ctypes
shared: $(ENGINE_SOURCES)
	$(CC) $(CFLAGS) $(SHARED_FLAGS) -o $(SHARED_TARGET)$(SHARED_EXT) $(ENGINE_SOURCES)
	@echo "Shared library built: $(SHARED_TARGET)$(SHARED_EXT)"

# Debug build
debug: $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) $(DEBUG_FLAGS) -o $(TARGET)_debug $(SOURCES)
	@echo "Debug build complete: ./$(TARGET)_debug"

# Debug shared library
debug-shared: $(ENGINE_SOURCES)
	$(CC) $(CFLAGS) $(DEBUG_FLAGS) $(SHARED_FLAGS) -o $(SHARED_TARGET)_debug$(SHARED_EXT) $(ENGINE_SOURCES)
	@echo "Debug shared library built: $(SHARED_TARGET)_debug$(SHARED_EXT)"

# Clean build artifacts
clean:
	rm -f $(TARGET) $(TARGET)_debug $(TARGET).exe $(TARGET)_debug.exe
	rm -f $(SHARED_TARGET)$(SHARED_EXT) $(SHARED_TARGET)_debug$(SHARED_EXT)
	rm -f $(SHARED_TARGET).dll $(SHARED_TARGET).so $(SHARED_TARGET).dylib
	@echo "Cleaned build artifacts"

# Clean everything including data
clean-all: clean
	rm -f $(DATA_FILES)
	@echo "Cleaned all files including data"

# Run tests
test: $(TARGET)
	@echo "=== Running Scheduler Tests ==="
	./$(TARGET) --help
	./$(TARGET) --analyze-gaps
	./$(TARGET) --list-schedule
	./$(TARGET) --list-queue
	./$(TARGET) --analyze-gaps --json

# Test shared library
test-shared: shared
	@echo "=== Shared Library Built ==="
	@echo "Test from Python:"
	@echo "  from ctypes import CDLL"
	@echo "  lib = CDLL('./$(SHARED_TARGET)$(SHARED_EXT)')"
	@echo "  print(lib.get_engine_version())"

# Install to /usr/local/bin (Unix)
install: $(TARGET)
	cp $(TARGET) /usr/local/bin/
	@echo "Installed to /usr/local/bin/"

# Install shared library
install-shared: shared
ifeq ($(OS),Windows_NT)
	@echo "Copy $(SHARED_TARGET).dll to your Python project or system PATH"
else
	sudo cp $(SHARED_TARGET)$(SHARED_EXT) /usr/local/lib/
	sudo ldconfig
	@echo "Installed shared library to /usr/local/lib/"
endif

.PHONY: all shared debug debug-shared clean clean-all test test-shared install install-shared

