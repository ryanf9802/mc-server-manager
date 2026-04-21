APP_MODULE := mc_server_manager.main
RUNTIME_DIR := .run
PID_FILE := $(RUNTIME_DIR)/mc-server-manager.pid
LOG_FILE := $(RUNTIME_DIR)/mc-server-manager.log
UV_CACHE_DIR := $(RUNTIME_DIR)/uv-cache

.PHONY: up down status logs

up:
	@mkdir -p $(RUNTIME_DIR) $(UV_CACHE_DIR)
	@if [ -f "$(PID_FILE)" ] && kill -0 "$$(cat "$(PID_FILE)")" 2>/dev/null; then \
		echo "mc-server-manager is already running with PID $$(cat "$(PID_FILE)")"; \
		exit 0; \
	fi
	@if [ -f "$(PID_FILE)" ]; then rm -f "$(PID_FILE)"; fi
	@nohup env UV_CACHE_DIR="$(UV_CACHE_DIR)" uv run python -m $(APP_MODULE) >"$(LOG_FILE)" 2>&1 & echo $$! >"$(PID_FILE)"
	@sleep 1
	@if kill -0 "$$(cat "$(PID_FILE)")" 2>/dev/null; then \
		echo "mc-server-manager started with PID $$(cat "$(PID_FILE)")"; \
		echo "Logs: $(LOG_FILE)"; \
	else \
		echo "mc-server-manager exited during startup. Check $(LOG_FILE)"; \
		rm -f "$(PID_FILE)"; \
		exit 1; \
	fi

down:
	@if [ ! -f "$(PID_FILE)" ]; then \
		echo "mc-server-manager is not running"; \
		exit 0; \
	fi
	@pid="$$(cat "$(PID_FILE)")"; \
	if kill -0 "$$pid" 2>/dev/null; then \
		kill "$$pid"; \
		sleep 1; \
		if kill -0 "$$pid" 2>/dev/null; then \
			echo "mc-server-manager is still running with PID $$pid"; \
			echo "Stop it manually or retry after checking the app state."; \
			exit 1; \
		fi; \
		echo "mc-server-manager stopped"; \
	else \
		echo "Removing stale PID file for PID $$pid"; \
	fi
	@rm -f "$(PID_FILE)"

status:
	@if [ -f "$(PID_FILE)" ] && kill -0 "$$(cat "$(PID_FILE)")" 2>/dev/null; then \
		echo "mc-server-manager is running with PID $$(cat "$(PID_FILE)")"; \
	else \
		echo "mc-server-manager is not running"; \
	fi

logs:
	@if [ -f "$(LOG_FILE)" ]; then \
		tail -n 50 "$(LOG_FILE)"; \
	else \
		echo "No log file found at $(LOG_FILE)"; \
	fi
