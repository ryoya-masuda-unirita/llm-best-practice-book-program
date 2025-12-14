DIR := $(shell pwd)
GIT_COMMIT := $(shell git rev-parse HEAD)

############ COMMON COMMANDS ############
SRC := $(DIR)/

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
