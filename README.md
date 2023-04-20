# airflow_simplified

- Docker/Local Airflow server setup
    - Use docker compose
        - SQL Lite server

## Getting Started
- Follow [these instructions](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html) to get Docker compose running
    - `curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.5.3/docker-compose.yaml'`

- Run these commands before doing docker compose
```
mkdir -p ./dags ./logs ./plugins
<!-- echo -e "AIRFLOW_UID=$(id -u)" > .env --> Only needed for Linux
```

### Running Docker Compose

1. Run database migrations and create user account
`docker compose up airflow-init`

2. Run Airflow
`docker compose up`

3. Loging via web UI at `http://localhost:8080` with username:password `airflow:airflow`

To clean up all containers and images:
`docker compose down --volumes --rmi all`