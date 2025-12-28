# ============================================================
# Makefile
# Steam ML Platform
#
# This Makefile is the single entry point for:
# - environment setup
# - dependency management
# - code quality checks
# - project initialization
#
# IMPORTANT (Windows):
# - venv creation must NOT run while VS Code is open
# - dependency sync is always safe inside VS Code
# ============================================================

# ------------------------------------------------------------
# Virtual environment configuration
# ------------------------------------------------------------
VENV := .venv

ifeq ($(OS),Windows_NT)
	PYTHON := $(VENV)\Scripts\python.exe
	PIP := $(VENV)\Scripts\pip.exe
	RUFF := $(VENV)\Scripts\ruff.exe
	BLACK := $(VENV)\Scripts\black.exe
	PRECOMMIT := $(VENV)\Scripts\pre-commit.exe
else
	PYTHON := $(VENV)/bin/python
	PIP := $(VENV)/bin/pip
	RUFF := $(VENV)/bin/ruff
	BLACK := $(VENV)/bin/black
	PRECOMMIT := $(VENV)/bin/pre-commit
endif

.PHONY: help venv setup deps init lint format check ingest ingest-sample clean

# ------------------------------------------------------------
# Help
# ------------------------------------------------------------
help:
	@echo ""
	@echo "Steam ML Platform - Available commands:"
	@echo ""
	@echo "  make venv            Create virtual environment (run once, VS Code closed)"
	@echo "  make setup           Sync dependencies from pyproject.toml"
	@echo "  make init            Initialize repository (install git hooks)"
	@echo ""
	@echo "  make lint            Run Ruff linter"
	@echo "  make format          Format code with Black"
	@echo "  make check           Run all pre-commit hooks"
	@echo ""
	@echo "  make ingest          Run full ingestion pipeline"
	@echo "  make ingest-sample   Run ingestion on a small sample"
	@echo ""
	@echo "  make clean           Remove generated data artifacts"
	@echo ""

# ------------------------------------------------------------
# Environment setup (RUN ONCE)
# ------------------------------------------------------------
venv:
	@echo "Creating virtual environment..."
	python -m venv $(VENV)
	@echo "Upgrading pip..."
	$(PYTHON) -m pip install --upgrade pip
	@echo "Virtual environment ready."

# ------------------------------------------------------------
# Dependency management (SAFE TO RUN IN VS CODE)
# ------------------------------------------------------------
deps:
	@echo "Installing / updating project dependencies..."
	$(PYTHON) -m pip install -e .
	@echo "Dependencies are up to date."

setup: deps

# ------------------------------------------------------------
# Repository initialization (RUN ONCE)
# ------------------------------------------------------------
init:
	@echo "Installing pre-commit hooks..."
	$(PRECOMMIT) install
	@echo "Pre-commit hooks installed."

# ------------------------------------------------------------
# Code quality
# ------------------------------------------------------------
lint:
	@echo "Running Ruff linter..."
	$(RUFF) check src

format:
	@echo "Formatting code with Black..."
	$(BLACK) src

check:
	@echo "Running all pre-commit checks..."
	$(PRECOMMIT) run --all-files

# ------------------------------------------------------------
# Data ingestion
# ------------------------------------------------------------
ingest:
	@echo "Running full ingestion pipeline..."
	$(PYTHON) src/pipelines/ingest_all.py

ingest-sample:
	@echo "Running ingestion pipeline on sample data..."
	$(PYTHON) src/pipelines/ingest_all.py --limit 100

# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------
clean:
	@echo "Cleaning generated data..."
ifeq ($(OS),Windows_NT)
	powershell -Command "Remove-Item -Recurse -Force data\\bronze\\* -ErrorAction SilentlyContinue"
	powershell -Command "Remove-Item -Recurse -Force data\\silver\\* -ErrorAction SilentlyContinue"
	powershell -Command "Remove-Item -Recurse -Force data\\gold\\* -ErrorAction SilentlyContinue"
else
	rm -rf data/bronze/* data/silver/* data/gold/*
endif
	@echo "Cleanup complete."
