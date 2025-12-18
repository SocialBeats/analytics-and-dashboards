.PHONY: help install install-dev run test lint format clean docker-up docker-down test-dashboards test-dashboards-unit test-dashboards-integration test-dashboards-docker test-widgets test-widgets-unit test-widgets-integration test-widgets-docker test-beat-metrics test-beat-metrics-unit test-beat-metrics-integration test-beat-metrics-docker

help:
	@echo "FastAPI MongoDB Template - Available commands:"
	@echo ""
	@echo "  make install                  - Install production dependencies"
	@echo "  make install-dev              - Install development dependencies"
	@echo "  make run                      - Run the application locally"
	@echo "  make test                     - Run all tests with coverage"
	@echo "  make test-dashboards          - Run Dashboard tests (unit + integration)"
	@echo "  make test-dashboards-unit     - Run Dashboard unit tests only"
	@echo "  make test-dashboards-integration - Run Dashboard integration tests only"
	@echo "  make test-dashboards-docker   - Run Dashboard tests inside Docker container"
	@echo "  make test-widgets             - Run Widget tests (unit + integration)"
	@echo "  make test-widgets-unit        - Run Widget unit tests only"
	@echo "  make test-widgets-integration - Run Widget integration tests only"
	@echo "  make test-widgets-docker      - Run Widget tests inside Docker container"
	@echo "  make test-beat-metrics        - Run Beat Metrics tests (unit + integration)"
	@echo "  make test-beat-metrics-unit   - Run Beat Metrics unit tests only"
	@echo "  make test-beat-metrics-integration - Run Beat Metrics integration tests only"
	@echo "  make test-beat-metrics-docker - Run Beat Metrics tests inside Docker container"
	@echo "  make lint                     - Run code linting"
	@echo "  make format                   - Format code with black and isort"
	@echo "  make clean                    - Remove generated files and caches"
	@echo "  make docker-up                - Start Docker containers"
	@echo "  make docker-down              - Stop Docker containers"
	@echo "  make pre-commit               - Install pre-commit hooks"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	uvicorn main:app --reload --host 0.0.0.0 --port 3003

test:
	pytest --cov=app --cov-report=term-missing --cov-report=html

test-dashboards:
	pytest tests/test_dashboard_service.py tests/test_dashboard_endpoints.py -v --cov=app.services.dashboard_service --cov=app.endpoints.dashboards --cov-report=term-missing --cov-report=html

test-dashboards-unit:
	pytest tests/test_dashboard_service.py -v

test-dashboards-integration:
	pytest tests/test_dashboard_endpoints.py -v

test-dashboards-docker:
	docker-compose exec api pytest tests/test_dashboard_service.py tests/test_dashboard_endpoints.py -v --cov=app.services.dashboard_service --cov=app.endpoints.dashboards --cov-report=term-missing

test-widgets:
	pytest tests/test_widget_service.py tests/test_widget_endpoints.py -v --cov=app.services.widget_service --cov=app.endpoints.widgets --cov-report=term-missing --cov-report=html

test-widgets-unit:
	pytest tests/test_widget_service.py -v

test-widgets-integration:
	pytest tests/test_widget_endpoints.py -v

test-widgets-docker:
	docker-compose exec api pytest tests/test_widget_service.py tests/test_widget_endpoints.py -v --cov=app.services.widget_service --cov=app.endpoints.widgets --cov-report=term-missing

test-beat-metrics:
	pytest tests/test_beat_metrics_service.py tests/test_beat_metrics_endpoints.py -v --cov=app.services.beat_metrics_service --cov=app.endpoints.beat_metrics --cov-report=term-missing --cov-report=html

test-beat-metrics-unit:
	pytest tests/test_beat_metrics_service.py -v

test-beat-metrics-integration:
	pytest tests/test_beat_metrics_endpoints.py -v

test-beat-metrics-docker:
	docker-compose exec api pytest tests/test_beat_metrics_service.py tests/test_beat_metrics_endpoints.py -v --cov=app.services.beat_metrics_service --cov=app.endpoints.beat_metrics --cov-report=term-missing

lint:
	ruff check app/ tests/
	mypy app/

format:
	black app/ tests/
	isort app/ tests/
	ruff check --fix app/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

pre-commit:
	pre-commit install
	pre-commit run --all-files
