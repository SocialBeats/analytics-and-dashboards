.PHONY: help install install-dev run test lint format clean docker-up docker-down

help:
	@echo "FastAPI MongoDB Template - Available commands:"
	@echo ""
	@echo "  make install         - Install production dependencies"
	@echo "  make install-dev     - Install development dependencies"
	@echo "  make run             - Run the application locally"
	@echo "  make test            - Run tests with coverage"
	@echo "  make lint            - Run code linting"
	@echo "  make format          - Format code with black and isort"
	@echo "  make clean           - Remove generated files and caches"
	@echo "  make docker-up       - Start Docker containers"
	@echo "  make docker-down     - Stop Docker containers"
	@echo "  make pre-commit      - Install pre-commit hooks"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

run:
	uvicorn main:app --reload --host 0.0.0.0 --port 3003

test:
	pytest --cov=app --cov-report=term-missing --cov-report=html

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
