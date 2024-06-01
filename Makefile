# Makefile

# Variables
VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip

# Default target
.PHONY: all
all: help

# Help target
.PHONY: help
help:
	@echo "Usage:"
	@echo "  make venv           Create a virtual environment and install dependencies"
	@echo "  make dev            Run the bot in development mode"
	@echo "  make docker-build   Build the Docker image (TODO)"
	@echo "  make docker-run     Run the Docker container (TODO)"

# Create a virtual environment and install dependencies
.PHONY: venv
venv:
	python3 -m venv $(VENV_DIR)
	$(PIP) install -r requirements.txt

# Run the bot in development mode
.PHONY: run
run:
	$(PYTHON) bot.py

# Build the Docker image
.PHONY: docker-build
docker-build:
	docker build -t breast-feeding-bot .

# Run the Docker container
.PHONY: docker-run
docker-run:
	docker run -d --name breast-feeding-bot breast-feeding-bot
