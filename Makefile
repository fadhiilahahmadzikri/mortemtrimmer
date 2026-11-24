.PHONY: bootstrap lint format test readiness check notices stage-models package-win clean-install bump-dry-run

bootstrap:
	python -m pip install -r requirements.txt
	pre-commit install -t pre-commit -t commit-msg -t pre-push

lint:
	ruff check .

format:
	ruff format --check .

test:
	pytest tests/unit tests/integration -v

readiness:
	python main.py --check

notices:
	python packaging/manifests/notices_generator.py

stage-models:
	python scripts/stage_offline_models.py

package-win: notices stage-models
	python -m PyInstaller --noconfirm packaging/pyinstaller/shim.spec
	python -m PyInstaller --noconfirm packaging/pyinstaller/core.spec
	"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging/windows/installer.iss

clean-install:
	python scripts/clean_install.py

bump-dry-run:
	cz bump --dry-run

check: lint format test readiness
