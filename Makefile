.PHONY: bootstrap lint format readiness check

bootstrap:
	python -m pip install -r requirements.txt
	python -m pip install pre-commit ruff
	pre-commit install -t pre-commit -t commit-msg -t pre-push

lint:
	ruff check .

format:
	ruff format --check .

readiness:
	python main.py --check

check: lint format readiness
