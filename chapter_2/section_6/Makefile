DIR := $(shell pwd)
GIT_COMMIT := $(shell git rev-parse HEAD)

############ COMMON COMMANDS ############
SRC := $(DIR)/

.PHONY: lint
lint:
	uvx ruff check --extend-select I --fix $(SRC)

.PHONY: fmt
fmt:
	uvx ruff format $(SRC)

.PHONY: fix
fix: lint fmt

.PHONY: mypy
mypy:
	uvx mypy $(SRC) --namespace-packages --explicit-package-bases

############ PYTEST TESTING ############

.PHONY: pytest
pytest:
	uv run pytest

.PHONY: pytest-verbose
pytest-verbose:
	uv run pytest -vv

.PHONY: pytest-cov
pytest-cov:
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

.PHONY: pytest-watch
pytest-watch:
	uv run pytest-watch

.PHONY: pytest-unit
pytest-unit:
	uv run pytest tests/test_template_engine.py tests/test_prompt.py

.PHONY: pytest-failed
pytest-failed:
	uv run pytest --lf

############ TEMPLATE TESTING ############

.PHONY: test-basic
test-basic:
	uv run python test_template.py

.PHONY: test-all
test-all:
	uv run python test_all_templates.py

.PHONY: test-templates
test-templates: test-basic test-all

.PHONY: test
test: pytest test-templates

############ LLM EXECUTION ############

.PHONY: run-openai
run-openai:
	uv run python -m src.main --llm-provider openai --model gpt-4o

.PHONY: run-gemini
run-gemini:
	uv run python -m src.main --llm-provider gemini --model gemini-2.0-flash-exp

############ SETUP ############

.PHONY: install
install:
	uv sync

.PHONY: help
help:
	@echo "Available commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install         - Install dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests (pytest + template tests)"
	@echo "  make pytest          - Run pytest unit tests"
	@echo "  make pytest-verbose  - Run pytest with verbose output"
	@echo "  make pytest-cov      - Run pytest with coverage report"
	@echo "  make pytest-unit     - Run specific unit tests"
	@echo "  make pytest-failed   - Re-run only failed tests"
	@echo "  make test-basic      - Run basic template test"
	@echo "  make test-all        - Run comprehensive template tests"
	@echo "  make test-templates  - Run all template tests"
	@echo ""
	@echo "LLM Execution:"
	@echo "  make run-openai      - Run with OpenAI"
	@echo "  make run-gemini      - Run with Gemini"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint            - Run linter"
	@echo "  make fmt             - Format code"
	@echo "  make fix             - Run linter and formatter"
	@echo "  make mypy            - Run type checker"
