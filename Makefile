# Airflow Simplified - Makefile
# This Makefile provides convenient commands to manage the Airflow Podman Compose setup

.PHONY: help run stop clean restart logs status init shell test check-resources fix-resources

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Airflow Simplified - Available Commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

init: ## Initialize Airflow database and create admin user
	@echo "$(YELLOW)Initializing Airflow...$(NC)"
	podman-compose up airflow-init
	@echo "$(GREEN)Airflow initialization complete!$(NC)"

run: ## Build and launch Airflow containers in detached mode
	@echo "$(YELLOW)Building and starting Airflow containers...$(NC)"
	podman-compose up --build -d
	@echo "$(GREEN)Airflow is starting up!$(NC)"
	@echo "$(BLUE)Access the web UI at: http://localhost:8080$(NC)"
	@echo "$(BLUE)Default credentials: airflow / airflow$(NC)"

stop: ## Stop running containers without removing them
	@echo "$(YELLOW)Stopping Airflow containers...$(NC)"
	podman-compose stop
	@echo "$(GREEN)Containers stopped.$(NC)"

restart: ## Restart all containers
	@echo "$(YELLOW)Restarting Airflow containers...$(NC)"
	podman-compose restart
	@echo "$(GREEN)Containers restarted.$(NC)"

clean: ## Stop and remove containers, networks, and volumes
	@echo "$(YELLOW)Cleaning up Airflow containers and resources...$(NC)"
	podman-compose down
	@echo "$(GREEN)Cleanup complete.$(NC)"

clean-all: ## Stop and remove containers, networks, volumes, and images
	@echo "$(YELLOW)Performing full cleanup (containers, networks, volumes, and images)...$(NC)"
	podman-compose down --volumes --rmi all
	@echo "$(GREEN)Full cleanup complete.$(NC)"

logs: ## View logs from all containers (use LOGS_SERVICE=<service> for specific service)
	@if [ -z "$(LOGS_SERVICE)" ]; then \
		podman-compose logs -f; \
	else \
		podman-compose logs -f $(LOGS_SERVICE); \
	fi

status: ## Show status of all containers
	@echo "$(BLUE)Container Status:$(NC)"
	@podman-compose ps

shell: ## Open an interactive shell in the Airflow CLI container
	@echo "$(YELLOW)Opening Airflow CLI shell...$(NC)"
	podman-compose run --rm airflow-cli bash

test: ## Run Airflow tests (example - customize as needed)
	@echo "$(YELLOW)Running Airflow tests...$(NC)"
	podman-compose run --rm airflow-cli airflow dags list
	@echo "$(GREEN)Tests complete.$(NC)"

check-resources: ## Check Podman machine resources
	@echo "$(BLUE)Checking Podman machine resources...$(NC)"
	@echo ""
	@podman machine list
	@echo ""
	@echo "$(YELLOW)Note: Airflow recommends at least 4GB RAM.$(NC)"
	@echo "$(YELLOW)If you have less, the webserver workers may crash.$(NC)"
	@echo "$(YELLOW)Run 'make fix-resources' for instructions to increase memory.$(NC)"

fix-resources: ## Show instructions to increase Podman machine memory
	@echo "$(BLUE)To increase Podman machine memory on macOS:$(NC)"
	@echo ""
	@echo "$(GREEN)1. Stop the current machine:$(NC)"
	@echo "   podman machine stop"
	@echo ""
	@echo "$(GREEN)2. Set memory to 4GB (4096MB) or more:$(NC)"
	@echo "   podman machine set --memory 4096"
	@echo ""
	@echo "$(GREEN)3. Start the machine:$(NC)"
	@echo "   podman machine start"
	@echo ""
	@echo "$(YELLOW)Alternatively, the webserver is configured to use 2 workers$(NC)"
	@echo "$(YELLOW)instead of 4 to reduce memory usage.$(NC)"

