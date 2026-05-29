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

############ RAG COMMANDS ############

.PHONY: index
index:
	uv run python -m src.main index -d data

.PHONY: query
query:
	@if [ -z "$(Q)" ]; then \
		echo "Error: Please provide a question using Q='your question'"; \
		echo "Example: make query Q='What are the benefits of structured output?'"; \
		exit 1; \
	fi
	uv run python -m src.main query -d data -q "$(Q)"

.PHONY: query-example
query-example:
	uv run python -m src.main query -d data -q "What are the main benefits of structured output for LLM systems?"
