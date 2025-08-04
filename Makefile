.PHONY: help setup install-backend install-frontend dev-backend dev-frontend dev test test-unit test-integration test-e2e test-all format lint type-check quality-check clean docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  setup              - Set up the entire project"
	@echo "  install-backend    - Install backend dependencies"
	@echo "  install-frontend   - Install frontend dependencies"
	@echo "  dev-backend        - Run backend in development mode"
	@echo "  dev-frontend       - Run frontend in development mode"
	@echo "  dev                - Run both backend and frontend"
	@echo "  test               - Run all tests"
	@echo "  test-unit          - Run unit tests only"
	@echo "  test-integration   - Run integration tests only"
	@echo "  test-e2e           - Run end-to-end tests"
	@echo "  test-all           - Run all tests with coverage"
	@echo "  format             - Format code (black, prettier)"
	@echo "  lint               - Run linting (flake8, eslint)"
	@echo "  type-check         - Run type checking (mypy, tsc)"
	@echo "  quality-check      - Run all quality checks"
	@echo "  docker-up          - Start all services with Docker"
	@echo "  docker-down        - Stop all Docker services"
	@echo "  clean              - Clean build artifacts"

setup: install-backend install-frontend
	@echo "Project setup complete!"

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend and frontend..."
	make -j2 dev-backend dev-frontend

# Testing commands
test: test-unit test-integration
	@echo "All tests completed!"

test-unit:
	@echo "Running unit tests..."
	cd backend && python -m pytest tests/unit/ -v
	cd frontend && npm run test:ci

test-integration:
	@echo "Running integration tests..."
	cd backend && python -m pytest tests/integration/ -v

test-e2e:
	@echo "Running end-to-end tests..."
	npx playwright test

test-all:
	@echo "Running all tests with coverage..."
	cd backend && python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term
	cd frontend && npm run test:coverage
	make test-e2e

# Code quality commands
format:
	@echo "Formatting code..."
	cd backend && black .
	cd backend && isort .
	cd frontend && npx prettier --write .

lint:
	@echo "Running linting..."
	cd backend && flake8 .
	cd frontend && npm run lint

type-check:
	@echo "Running type checking..."
	cd backend && mypy .
	cd frontend && npm run type-check

quality-check: format lint type-check
	@echo "All quality checks completed!"

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	cd frontend && rm -rf .next node_modules
	cd backend && rm -rf __pycache__