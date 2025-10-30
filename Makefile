DOCKER ?= docker
IMAGE_NAME ?= productcard-ai-bot
TAG ?= v1
CONTAINER_NAME ?= productcard-ai-bot
ENV_FILE ?= .env

.PHONY: build run run-hostnet logs stop restart sh clean help

help:
	@echo "Make targets:"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z0-9_\-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker image
	$(DOCKER) build -t $(IMAGE_NAME):$(TAG) .

run: stop ## Run container (host.docker.internal)
	$(DOCKER) run -d \
		--name $(CONTAINER_NAME) \
		--env-file $(ENV_FILE) \
		--add-host=host.docker.internal:host-gateway \
		$(IMAGE_NAME):$(TAG)

run-hostnet: stop ## Linux: host network
	$(DOCKER) run -d \
		--name $(CONTAINER_NAME) \
		--env-file $(ENV_FILE) \
		--network host \
		$(IMAGE_NAME):$(TAG)

logs: ## Tail logs
	$(DOCKER) logs -f $(CONTAINER_NAME)

stop: ## Stop and remove container
	-$(DOCKER) stop $(CONTAINER_NAME) 2>/dev/null || true
	-$(DOCKER) rm $(CONTAINER_NAME) 2>/dev/null || true

restart: stop run ## Restart container

sh: ## Shell into container
	$(DOCKER) exec -it $(CONTAINER_NAME) /bin/bash

clean: ## Remove image
	-$(DOCKER) rmi $(IMAGE_NAME):$(TAG) 2>/dev/null || true

