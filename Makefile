# Makefile

# Variables
VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip
IMAGE_NAME = breast-feeding-bot

# Default target
.PHONY: all
all: help

# Help target
.PHONY: help
help:
	@echo "Usage:"
	@echo "  make venv           Create a virtual environment and install dependencies"
	@echo "  make run            Run the bot in development mode"
	@echo "  make docker-build   Build the Docker image"
	@echo "  make docker-run     Run the Docker container"
	@echo "  make init-db        Initialize the database"
	@echo "  make migrate-db     Migrate the database to the new setup"

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
	docker build -t $(IMAGE_NAME) .

# Run the Docker container
.PHONY: docker-run
docker-run:
	docker run -d --name $(IMAGE_NAME) --env-file .env $(IMAGE_NAME)

# Initialize the database
.PHONY: init-db
init-db: venv
	$(PYTHON) create_tables.py
