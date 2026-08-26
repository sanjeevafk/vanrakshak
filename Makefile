.PHONY: all start eval run-cli install test test-backend test-frontend typecheck build clean

all: test build

start:
	./scripts/start_app.sh

run-cli:
	./backend/.venv/bin/python scripts/run_drone_mission.py $(VIDEO)

eval:
	./scripts/run_evals.sh

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd frontend && npm install

test: test-backend test-frontend

test-backend:
	cd backend && .venv/bin/pytest -v

test-frontend:
	cd frontend && npm test

typecheck:
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

clean:
	rm -rf .mypy_cache .pytest_cache frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
