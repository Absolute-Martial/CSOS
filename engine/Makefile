# Personal Engineering OS - Scheduler Engine
# Makefile for C compilation

CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -O2
DEBUG_FLAGS = -g -DDEBUG
TARGET = scheduler
SOURCES = scheduler.c
HEADERS = scheduler.h
DATA_FILES = schedule.dat labs.dat

# Default target
all: $(TARGET)

# Production build
$(TARGET): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCES)
	@echo "Build complete: ./$(TARGET)"

# Debug build
debug: $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) $(DEBUG_FLAGS) -o $(TARGET)_debug $(SOURCES)
	@echo "Debug build complete: ./$(TARGET)_debug"

# Clean build artifacts
clean:
	rm -f $(TARGET) $(TARGET)_debug $(TARGET).exe $(TARGET)_debug.exe
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

# Install to /usr/local/bin (Unix)
install: $(TARGET)
	cp $(TARGET) /usr/local/bin/
	@echo "Installed to /usr/local/bin/"

.PHONY: all debug clean clean-all test install
