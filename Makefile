.PHONY: bootstrap lint format test readiness check notices package-win

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

package-win: notices
	python -m PyInstaller --noconfirm packaging/pyinstaller/shim.spec
	python -m PyInstaller --noconfirm packaging/pyinstaller/core.spec
	"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging/windows/installer.iss

check: lint format test readiness
