DIR := $(shell pwd)
GIT_COMMIT := $(shell git rev-parse HEAD)

DOCKER_REPO := shibui/llm-best-practice
DOCKERFILE = $(DIR)/Dockerfile.web
DOCKER_TAG = chapter3_section1
DOCKER_IMAGE_NAME = $(DOCKER_REPO):$(DOCKER_TAG)_$(GIT_COMMIT)

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

############ SERVER COMMANDS ############

.PHONY: run-llm-server
run-llm-server:
	uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 --reload

.PHONY: run-proxy
run-proxy:
	uv run uvicorn src.proxy.proxy_server:app --host 0.0.0.0 --port 8080 --reload

.PHONY: run-all
run-all:
	@echo "Starting LLM API Server on port 8000..."
	@uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 &
	@echo "Starting Proxy Server on port 8080..."
	@uv run uvicorn src.proxy.proxy_server:app --host 0.0.0.0 --port 8080

.PHONY: docker-build
docker-build:
	docker build \
		--platform linux/amd64 \
		-t $(DOCKER_IMAGE_NAME) \
		-f $(DOCKERFILE) \
		.
