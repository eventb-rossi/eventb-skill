.PHONY: help check validate check-models build

# A bare `make` should say what is available, not run the slow model checks.
.DEFAULT_GOAL := help

PYTHON ?= python3

# The gate to run before every commit: spec conformance, repository conventions, and
# catalog freshness. Needs nothing but a Python interpreter.
check:
	$(PYTHON) scripts/validate.py --no-tools
	$(PYTHON) scripts/build_index.py --check

# Everything `check` covers, plus the Event-B gates over the bundled examples. Warns
# and skips those if rossi/eventb-animate are missing; use check-models to require them.
validate:
	$(PYTHON) scripts/validate.py

# The full gate: format, validate, build, model-check and WD-check every example at
# every refinement level. Fails if rossi or eventb-animate is not on PATH.
check-models:
	$(PYTHON) scripts/validate.py --require-tools

# Regenerate the derived catalogs. Never edit skills/index.json or llms.txt by hand.
build:
	$(PYTHON) scripts/build_index.py

help:
	@echo "Targets:"
	@echo "  check         spec + convention rules, then catalog drift (no external tools)"
	@echo "  validate      check, plus the Event-B gates when rossi/eventb-animate exist"
	@echo "  check-models  the full gate; fails if rossi or eventb-animate is missing"
	@echo "  build         regenerate skills/index.json and llms.txt"
