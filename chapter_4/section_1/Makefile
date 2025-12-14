DIR := $(shell pwd)
GIT_COMMIT := $(shell git rev-parse HEAD)

DOCKER_REPO := shibui/llm-best-practice
DOCKERFILE = $(DIR)/Dockerfile.web
DOCKER_TAG = chapter4_section1

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

.PHONY: docker-build-web
docker-build-web:
	docker build \
		--platform linux/amd64 \
		-t $(DOCKER_REPO):$(DOCKER_TAG)_web \
		-f Dockerfile.web \
		.

.PHONY: docker-build
docker-build: docker-build-web

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
