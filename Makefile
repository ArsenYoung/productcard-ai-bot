DOCKER ?= docker
IMAGE_NAME ?= productcard-ai-bot
TAG ?= latest
CONTAINER_NAME ?= productcard-ai-bot
ENV_FILE ?= .env

.PHONY: help build run run-hostnet logs stop restart sh clean

help: ## Show this help message with targets
	@echo "Make targets:"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z0-9_\-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo
	@echo "Variables:"
	@echo "  IMAGE_NAME=$(IMAGE_NAME) TAG=$(TAG) CONTAINER_NAME=$(CONTAINER_NAME)"
	@echo "  ENV_FILE=$(ENV_FILE)"

build: ## Build Docker image
	$(DOCKER) build -t $(IMAGE_NAME):$(TAG) .

# Default run: make container see host's Ollama via host.docker.internal
# On Linux this requires Docker 20.10+ (host-gateway). On Mac/Windows it's built-in.
run: stop ## Run container (uses host.docker.internal)
	$(DOCKER) run -d \
		--name $(CONTAINER_NAME) \
		--env-file $(ENV_FILE) \
		--add-host=host.docker.internal:host-gateway \
		$(IMAGE_NAME):$(TAG)

# Linux-only convenience: use the host network (no need to change LLM_BASE_URL)
run-hostnet: stop ## Run container with host network (Linux)
	$(DOCKER) run -d \
		--name $(CONTAINER_NAME) \
		--env-file $(ENV_FILE) \
		--network host \
		$(IMAGE_NAME):$(TAG)

logs: ## Tail container logs
	$(DOCKER) logs -f $(CONTAINER_NAME)

stop: ## Stop and remove container
	-$(DOCKER) stop $(CONTAINER_NAME) 2>/dev/null || true
	-$(DOCKER) rm $(CONTAINER_NAME) 2>/dev/null || true

restart: stop run ## Rebuild and run container

sh: ## Open an interactive shell in the container
	$(DOCKER) exec -it $(CONTAINER_NAME) /bin/bash

clean: ## Remove built image
	-$(DOCKER) rmi $(IMAGE_NAME):$(TAG) 2>/dev/null || true
