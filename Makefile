.PHONY: help api-venv api-install api-dev api-test web-install web-dev

help:
	@echo "Targets:"
	@echo "  api-venv     - create venv in project root .venv"
	@echo "  api-install  - install API deps"
	@echo "  api-dev      - run FastAPI dev server"
	@echo "  api-test     - run pytest"
	@echo "  web-install  - install web deps"
	@echo "  web-dev      - run Next.js dev server"

api-venv:
	python3 -m venv .venv
	./.venv/bin/python -m pip install --upgrade pip

api-install: api-venv
	./.venv/bin/pip install -r apps/api/requirements.txt

api-dev:
	cd apps/api && ../../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

api-test:
	cd apps/api && ../../.venv/bin/pytest -q

web-install:
	cd apps/web && npm install

web-dev:
	cd apps/web && npm run dev

