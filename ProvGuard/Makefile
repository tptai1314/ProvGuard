.PHONY: install test demo bounds plots clean

install:
	python -m pip install -e '.[dev]'

test:
	pytest -q

demo:
	python scripts/run_synthetic_demo.py --config configs/synthetic_demo.yaml

bounds:
	python -m provguard.cli bounds --config configs/default.yaml

plots:
	python scripts/make_plots.py --input outputs/synthetic_demo/results.json --output outputs/synthetic_demo

clean:
	python -c "from pathlib import Path; [p.unlink() for p in Path('.').rglob('*.pyc')]"

