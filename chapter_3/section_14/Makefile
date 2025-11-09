DIR := $(shell pwd)
GIT_COMMIT := $(shell git rev-parse HEAD)

############ COMMON COMMANDS ############
SRC := $(DIR)/

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make install           - Install dependencies"
	@echo "  make list              - List all available examples"
	@echo ""
	@echo "Running Examples:"
	@echo "  make run EXAMPLE=<name>       - Run a specific example"
	@echo "  make run-simple-user          - Run simple user model example"
	@echo "  make run-product              - Run product with enum example"
	@echo "  make run-optional-fields      - Run book with optional fields example"
	@echo "  make run-array-fields         - Run course with array fields example"
	@echo "  make run-datetime-fields      - Run event with datetime fields example"
	@echo ""
	@echo "Advanced Examples:"
	@echo "  make run-nested-objects       - Run nested user profile example"
	@echo "  make run-complex-article      - Run complex article example"
	@echo "  make run-array-objects        - Run order system example"
	@echo "  make run-deep-nesting         - Run organization structure example"
	@echo "  make run-union-types          - Run payment methods example"
	@echo "  make run-validation           - Run product specification example"
	@echo ""
	@echo "High Reasoning Examples:"
	@echo "  make run-customer-feedback    - Run customer feedback analysis"
	@echo "  make run-meeting-summary      - Run meeting summary extraction"
	@echo "  make run-research-paper       - Run research paper metadata"
	@echo "  make run-job-application      - Run job application evaluation"
	@echo "  make run-financial            - Run financial transaction analysis"
	@echo "  make run-high-reasoning       - Run multi-category review analysis"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean             - Clean outputs and cache"
	@echo "  make lint              - Run ruff linter"
	@echo "  make fmt               - Format code with ruff"
	@echo "  make fix               - Run lint and fmt"
	@echo "  make mypy              - Run mypy type checker"

.PHONY: install
install:
	uv sync

.PHONY: list
list:
	python -m src.main --list-examples

.PHONY: run
run:
	@if [ -z "$(EXAMPLE)" ]; then \
		echo "Error: EXAMPLE not specified"; \
		echo "Usage: make run EXAMPLE=<example_name>"; \
		echo "Run 'make list' to see available examples"; \
		exit 1; \
	fi
	python -m src.main -e $(EXAMPLE)

# Basic Examples
.PHONY: run-simple-user
run-simple-user:
	python -m src.main -e simple_user_model

.PHONY: run-product
run-product:
	python -m src.main -e product_with_enum

.PHONY: run-optional-fields
run-optional-fields:
	python -m src.main -e optional_fields

.PHONY: run-array-fields
run-array-fields:
	python -m src.main -e array_fields

.PHONY: run-datetime-fields
run-datetime-fields:
	python -m src.main -e datetime_fields

# Advanced Examples
.PHONY: run-nested-objects
run-nested-objects:
	python -m src.main -e nested_objects

.PHONY: run-complex-article
run-complex-article:
	python -m src.main -e complex_article

.PHONY: run-array-objects
run-array-objects:
	python -m src.main -e array_of_objects

.PHONY: run-deep-nesting
run-deep-nesting:
	python -m src.main -e deep_nesting

.PHONY: run-union-types
run-union-types:
	python -m src.main -e anyof_union_types

.PHONY: run-validation
run-validation:
	python -m src.main -e validation_constraints

# High Reasoning Examples
.PHONY: run-customer-feedback
run-customer-feedback:
	python -m src.main -e customer_feedback_analysis

.PHONY: run-meeting-summary
run-meeting-summary:
	python -m src.main -e meeting_summary

.PHONY: run-research-paper
run-research-paper:
	python -m src.main -e research_paper_metadata

.PHONY: run-job-application
run-job-application:
	python -m src.main -e job_application_evaluation

.PHONY: run-financial
run-financial:
	python -m src.main -e financial_transaction_analysis

.PHONY: run-high-reasoning
run-high-reasoning:
	python -m src.main -e high_reasoning

.PHONY: clean
clean:
	rm -rf outputs/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

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
