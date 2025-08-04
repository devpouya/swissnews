.PHONY: help setup install-backend install-frontend dev-backend dev-frontend dev test clean docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  setup              - Set up the entire project"
	@echo "  install-backend    - Install backend dependencies"
	@echo "  install-frontend   - Install frontend dependencies"
	@echo "  dev-backend        - Run backend in development mode"
	@echo "  dev-frontend       - Run frontend in development mode"
	@echo "  dev                - Run both backend and frontend"
	@echo "  test               - Run tests"
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

test:
	cd backend && python -m pytest tests/
	cd frontend && npm test

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	cd frontend && rm -rf .next node_modules
	cd backend && rm -rf __pycache__