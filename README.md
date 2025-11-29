# Airflow Simplified

Local Airflow development environment using Podman Compose.

## Prerequisites

- Podman installed and running
- Podman machine with at least 4GB RAM (check with `make check-resources`)

## Quick Start

1. **Initialize Airflow** (first time only):

   ```bash
   make init
   ```

2. **Start Airflow**:

   ```bash
   make run
   ```

3. **Access the web UI**:

   - URL: <http://localhost:8080>
   - Username: `airflow`
   - Password: `airflow`

## Available Commands

Run `make` or `make help` to see all available commands:

- `make run` - Start all containers
- `make stop` - Stop containers
- `make clean` - Stop and remove containers
- `make logs` - View logs (use `LOGS_SERVICE=<name>` for specific service)
- `make status` - Show container status
- `make check-resources` - Check Podman machine resources
- `make fix-resources` - Show instructions to increase memory

## Directory Structure

- `dags/` - Place your DAG files here
- `logs/` - Airflow logs
- `plugins/` - Airflow plugins

## Troubleshooting

If the webserver isn't responding:

1. Check resources: `make check-resources`
2. Increase memory if needed: `make fix-resources`
3. Restart: `make restart`
