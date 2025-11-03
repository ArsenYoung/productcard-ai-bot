DOCKER            ?= docker
IMAGE_NAME        ?= productcard-ai-bot
TAG               ?= v1
CONTAINER_NAME    ?= productcard-ai-bot
ENV_FILE          ?= .env
VENV_DIR          ?= .venv
PYTHON            ?= $(VENV_DIR)/bin/python
PIP               ?= $(VENV_DIR)/bin/pip
OLLAMA_MODEL      ?= phi3:mini

.PHONY: help ## Show this help
help:
	@echo "Make targets:"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z0-9_\-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo "\nVariables (override as needed):"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)  TAG=$(TAG)  CONTAINER_NAME=$(CONTAINER_NAME)"
	@echo "  ENV_FILE=$(ENV_FILE)  VENV_DIR=$(VENV_DIR)  OLLAMA_MODEL=$(OLLAMA_MODEL)"

# ----------------------------
# Docker lifecycle
# ----------------------------
.PHONY: build run up logs stop down restart sh ps clean

build: ## Build Docker image
	$(DOCKER) build -t $(IMAGE_NAME):$(TAG) .

run: stop ## Run container (Linux host network, mounts ./data for live DB)
	@mkdir -p ./data
	$(DOCKER) run -d \
		--name $(CONTAINER_NAME) \
		--env-file $(ENV_FILE) \
		--network host \
		-v "$(PWD)/data:/app/data" \
		$(IMAGE_NAME):$(TAG)

up: build run ## Build image and start container (host network)

logs: ## Tail logs
	$(DOCKER) logs -f $(CONTAINER_NAME)

ps: ## List container state
	$(DOCKER) ps -a --filter name=$(CONTAINER_NAME)

stop: ## Stop and remove container
	-$(DOCKER) stop $(CONTAINER_NAME) 2>/dev/null || true
	-$(DOCKER) rm $(CONTAINER_NAME) 2>/dev/null || true

down: stop ## Alias for stop

restart: stop run ## Restart container

sh: ## Shell into container
	$(DOCKER) exec -it $(CONTAINER_NAME) /bin/bash

clean: ## Remove image
	-$(DOCKER) rmi $(IMAGE_NAME):$(TAG) 2>/dev/null || true

# ----------------------------
# Local development
# ----------------------------
.PHONY: venv install cli bot test sql-up sql-down sql

venv: ## Create virtualenv in .venv
	python3 -m venv $(VENV_DIR)
	$(PYTHON) -m pip install --upgrade pip

install: venv ## Install Python dependencies into venv
	$(PIP) install -r requirements.txt

# Use either ARGS or individual variables for CLI
# Example: make cli TEXT="Мышь Logitech" FEATURES="тихие клики" PLATFORM=ozon TONE=neutral
cli: install ## Run CLI locally (use TEXT/FEATURES/PLATFORM/TONE/AUDIENCE or ARGS)
	@if [ -n "$(ARGS)" ]; then \
		$(PYTHON) -m cli $(ARGS); \
	else \
		[ -n "$(TEXT)" ] || (echo "Set TEXT=... for CLI input or pass ARGS=..." && exit 1); \
		set -e; CMD="$(PYTHON) -m cli '$(TEXT)'"; \
		[ -n "$(FEATURES)" ] && CMD="$$CMD --features '$(FEATURES)'" || true; \
		[ -n "$(PLATFORM)" ] && CMD="$$CMD --platform $(PLATFORM)" || true; \
		[ -n "$(TONE)" ] && CMD="$$CMD --tone $(TONE)" || true; \
		[ -n "$(AUDIENCE)" ] && CMD="$$CMD --audience '$(AUDIENCE)'" || true; \
		echo $$CMD; eval $$CMD; \
	fi

bot: install ## Run Telegram bot locally
	$(PYTHON) -m bot.main

test: install ## Run tests
	$(PYTHON) -m pytest -q

# ----------------------------
# Environment and tooling
# ----------------------------
.PHONY: env-init env-set env-print ollama-pull ollama-run doctor

env-init: ## Create .env from example if missing
	@[ -f $(ENV_FILE) ] && echo "$(ENV_FILE) exists" || cp .env.example $(ENV_FILE)

env-set: ## Set one key in .env: make env-set KEY=NAME VALUE=val
	@[ -n "$(KEY)" ] || (echo "KEY is required" && exit 1)
	@[ -n "$(VALUE)" ] || (echo "VALUE is required" && exit 1)
	@touch $(ENV_FILE)
	@if grep -qE '^$(KEY)=' $(ENV_FILE); then \
		sed -i "s|^$(KEY)=.*|$(KEY)=$(VALUE)|" $(ENV_FILE); \
	else \
		echo "$(KEY)=$(VALUE)" >> $(ENV_FILE); \
	fi
	@echo "Updated $(KEY) in $(ENV_FILE)"

env-print: ## Print current .env (safe)
	@sed 's/\(TELEGRAM_BOT_TOKEN=\).*/\1***REDACTED***/' $(ENV_FILE) 2>/dev/null || echo "$(ENV_FILE) not found"

ollama-pull: ## Pull default model with Ollama
	@which ollama >/dev/null 2>&1 || (echo "Ollama not found. Install from https://ollama.ai" && exit 1)
	ollama pull $(OLLAMA_MODEL)

ollama-run: ## Run a prompt via Ollama (use PROMPT or ARGS)
	@which ollama >/dev/null 2>&1 || (echo "Ollama not found. Install from https://ollama.ai" && exit 1)
	@if [ -n "$(ARGS)" ]; then \
		ollama run $(OLLAMA_MODEL) $(ARGS); \
	else \
		[ -n "$(PROMPT)" ] || (echo "Set PROMPT=... for prompt text or pass ARGS=..." && exit 1); \
		ollama run $(OLLAMA_MODEL) "$(PROMPT)"; \
	fi

doctor: ## Check local prerequisites and configuration
	@echo "Python:"; python3 --version || true
	@echo "Virtualenv:"; test -x $(PYTHON) && echo "$(PYTHON) exists" || echo "Run: make install"
	@echo "Docker:"; $(DOCKER) --version || true
	@echo "Ollama:"; (which ollama >/dev/null 2>&1 && echo ok) || echo missing
	@echo "Model $(OLLAMA_MODEL):"; (ollama list 2>/dev/null | grep -q "$(OLLAMA_MODEL)" && echo present) || echo "not found; run: make ollama-pull"
	@echo ".env:"; [ -f $(ENV_FILE) ] && echo present || echo "missing; run: make env-init"

# ----------------------------
# SQLite viewer (Datasette)
# ----------------------------
sql-up: install ## Launch SQLite web UI (Datasette) in background. Use PORT=8001
	@set -e; \
	DBP=$$(awk -F= '/^DB_PATH=/{print $$2}' $(ENV_FILE) 2>/dev/null | tail -n1); \
	[ -n "$$DBP" ] || DBP=./data/bot.db; \
	echo "DB_PATH=$$DBP"; \
	mkdir -p "$$(dirname "$$DBP")"; \
	if [ ! -f "$$DBP" ]; then \
		echo "DB not found locally. Will try to copy from container $(CONTAINER_NAME)..."; \
		IN_CONTAINER="$$DBP"; case "$$IN_CONTAINER" in /*) ;; *) IN_CONTAINER="/app/$$IN_CONTAINER" ;; esac; \
		$(DOCKER) cp $(CONTAINER_NAME):"$$IN_CONTAINER" "$$DBP" 2>/dev/null || true; \
	fi; \
	if [ ! -f "$$DBP" ]; then \
		echo "DB still not found, creating empty at $$DBP"; \
		DBP="$$DBP" python3 -c "import os,sqlite3; p=os.environ.get('DBP'); os.makedirs(os.path.dirname(p) or '.', exist_ok=True); sqlite3.connect(p).close(); print('Created', p)"; \
	fi; \
	$(PIP) show datasette >/dev/null 2>&1 || $(PIP) install datasette; \
	PORT=$${PORT:-8001}; echo "Open http://127.0.0.1:$$PORT"; \
	$(PYTHON) -m datasette "$$DBP" -p "$$PORT" -h 127.0.0.1 & echo $$! > .datasette.pid; \
	echo "Datasette started with PID $$(cat .datasette.pid)"

sql-down: ## Stop SQLite web UI (Datasette) started by sql-up
	@if [ -f .datasette.pid ]; then \
		PID=$$(cat .datasette.pid); \
		if kill $$PID >/dev/null 2>&1; then \
			echo "Stopped datasette (PID $$PID)"; \
		else \
			echo "Process $$PID not running"; \
		fi; \
		rm -f .datasette.pid; \
	else \
		echo ".datasette.pid not found (is it running?)"; \
	fi

# Backward-compatible alias
sql: sql-up ## (deprecated) Use `make sql-up` instead
