DIR := $(shell pwd)
GIT_COMMIT := $(shell git rev-parse HEAD)

DOCKER_REPO := shibui/llm-best-practice
DOCKERFILE = $(DIR)/Dockerfile.web
DOCKER_TAG = chapter3_section4

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

.PHONY: run-api-gateway
run-api-gateway:
	uv run uvicorn src.api_gateway.gateway_server:app --host 0.0.0.0 --port 8080 --reload

.PHONY: run-gateway-client
run-gateway-client:
	uv run python -m src.api_gateway.example_client

.PHONY: run-all
run-all:
	@echo "Starting LLM API Server on port 8000..."
	@uv run uvicorn src.api.llm_server:app --host 0.0.0.0 --port 8000 &
	@echo "Starting API Gateway Server on port 8080..."
	@uv run uvicorn src.api_gateway.gateway_server:app --host 0.0.0.0 --port 8080

############ DOCKER COMMANDS ############

.PHONY: docker-build-web
docker-build-web:
	docker build \
		--platform linux/amd64 \
		-t $(DOCKER_REPO):$(DOCKER_TAG)_web \
		-f Dockerfile.web \
		.

.PHONY: docker-build-api-gateway
docker-build-api-gateway:
	docker build \
		--platform linux/amd64 \
		-t $(DOCKER_REPO):$(DOCKER_TAG)_api_gateway \
		-f Dockerfile.api_gateway \
		.

.PHONY: docker-build
docker-build: docker-build-web docker-build-api-gateway

.PHONY: docker-up
docker-up:
	docker-compose up -d

.PHONY: docker-down
docker-down:
	docker-compose down

.PHONY: docker-logs
docker-logs:
	docker-compose logs -f

.PHONY: docker-restart
docker-restart: docker-down docker-up
