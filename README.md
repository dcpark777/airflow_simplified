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
- `tests/` - Test files for the project

## Waiter Plugin

This project includes a custom plugin for waiting on tasks from other DAGs.

### Quick Example

```python
from waiter import wait_for_task, dags

# Wait for a task from another DAG
wait_task = wait_for_task(task=dags.my_dag.my_task_id)
```

See `plugins/waiter/README.md` for full documentation and `dags/example_wait_dag.py` for a complete example.

## Testing

Tests are dockerized and can be run in containers (recommended) or locally.

### Dockerized Tests (Recommended)

```bash
# Run all tests in container
make test

# Run only unit tests
make test-unit

# Test DAG imports
make test-dags

# Build test container
make test-build

# Open shell in test container
make test-shell
```

### Local Tests

For local testing, install dependencies first:

```bash
pip install -r requirements-test.txt
make test-local
```

The dockerized tests ensure a consistent environment and don't require local Python setup.

## Troubleshooting

If the webserver isn't responding:

1. Check resources: `make check-resources`
2. Increase memory if needed: `make fix-resources`
3. Restart: `make restart`
