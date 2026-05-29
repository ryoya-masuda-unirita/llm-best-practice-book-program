DIR := $(shell pwd)
GIT_COMMIT := $(shell git rev-parse HEAD)

DOCKER_REPO := shibui/llm-best-practice
DOCKERFILE = $(DIR)/Dockerfile
DOCKER_TAG = chapter2_section5

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

############ DOCKER COMMANDS ############

.PHONY: help
help:
	@echo "Docker Commands:"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-up       - Start services with docker-compose"
	@echo "  make docker-down     - Stop services"
	@echo "  make docker-logs     - View service logs"
	@echo "  make docker-restart  - Restart services (down + up)"

.PHONY: docker-build
docker-build:
	docker build \
		--platform linux/amd64 \
		-t $(DOCKER_REPO):$(DOCKER_TAG) \
		-f Dockerfile \
		.

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
