.DEFAULT_GOAL := help
SHELL := /bin/sh

HAS_POETRY := $(shell command -v poetry 2> /dev/null)
HAS_PIPX := $(shell command -v pipx 2> /dev/null)
DIR := app/backend
VENV_DIR := .venv
START_SCRIPT := start.sh
FRONTEND_BRANCH := main

.PHONY: help
help:
	@echo 'Usage: make [VARIABLES] [TARGET]'
	@echo ''
	@echo 'Description:'
	@echo '  This Makefile provides a set of targets to run the mate application and scripts.'
	@echo ''
	@echo 'Variables:'
	@echo '  DIR               - Target directory (default: app/backend)'
	@echo '  VENV_DIR          - Virtual environment directory name (default: .venv)'
	@echo '  START_SCRIPT      - Startup script name (default: start.sh)'
	@echo '  FRONTEND_BRANCH   - Branch to pull for the frontend (default: main)'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?### "} /^[a-zA-Z_-]+:.*?### / {printf "  %-30s - %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: dev
dev: ### Run the mate application and frontend
	@$(MAKE) -s -j 2 mate frontend

.PHONY: mate
mate: ### Run the mate application
	@$(MAKE) -s DIR=app/backend start

.PHONY: scripts
scripts: ### Run the scripts
	@$(MAKE) -s DIR=scripts START_SCRIPT=prepdocs-local.sh start

.PHONY: bot
bot: ### Run the jira ticket bot
	@$(MAKE) -s DIR=app/ticket-bot start

.PHONY: data-loader
data-loader: ### Run the data loader
	@$(MAKE) -s DIR=app/dataloader start

.PHONY: test
test: mate-test scripts-test ### Run tests for the mate application and scripts

.PHONY: mate-test
mate-test: ### Run tests for the mate application
	@$(MAKE) -s DIR=app/backend run-test

.PHONY: scripts-test
scripts-test: ### Run tests for the scripts
	@$(MAKE) -s DIR=scripts run-test

.PHONY: data-loader-test
data-loader-test: ### Run tests for the data loader
	@$(MAKE) -s DIR=app/dataloader run-test

.PHONY: cleanup
cleanup: cleanup-mate cleanup-scripts ### Clean up the virtual environments and cache directories

.PHONY: cleanup-mate
cleanup-mate: ### Clean up the virtual environment and cache directories for the mate application
	@$(MAKE) -s DIR=app/backend remove-venv remove-pycache

.PHONY: cleanup-scripts
cleanup-scripts: ### Clean up the virtual environment and cache directories for the scripts
	@$(MAKE) -s DIR=scripts remove-venv remove-pycache

.PHONY: start
start: restore-packages ### Start the application/script in [DIR]/[START_SCRIPT]
	@echo 'Starting $(DIR)/$(START_SCRIPT)'
	@cd $(DIR) && ./$(START_SCRIPT)
	@if [ $$? -ne 0 ]; then \
		echo "Failed to run ./$(DIR)/$(START_SCRIPT)"; \
		exit $$?; \
	fi

.PHONY: frontend
frontend: update-submodules install-frontend-deps ### Run the frontend
	@echo 'Starting frontend'
	@cd app/frontend && npm run dev -- --host 0.0.0.0

.PHONY: run-test
run-test: create-venv restore-packages ### Run tests in [DIR]
	@echo 'Running tests in $(DIR)'
	@if ! command -v pytest &> /dev/null; then \
		echo "pytest is not installed. Installing pytest"; \
		cd $(DIR) && ./$(VENV_DIR)/bin/python3 -m pip install -q pytest; \
		if [ $$? -ne 0 ]; then \
			echo "Failed to install pytest"; \
			exit $$?; \
		fi; \
	fi
	@cd $(DIR) && ./$(VENV_DIR)/bin/python3 -m pytest
	@if [ $$? -ne 0 ]; then \
		echo "Failed to run scripts tests"; \
		exit $$?; \
	fi

VENV_PATH := $(DIR)/$(VENV_DIR)

$(VENV_PATH):
	@if [ -z "$(HAS_POETRY)" ]; then \
		echo "poetry is not installed. Please install poetry to create a virtual environment"; \
		exit 1; \
	fi
	@echo 'Creating virtual environment "$(VENV_PATH)"'; \
	cd $(DIR) && poetry install
	
create-venv: $(VENV_PATH) ### Create a python virtual environment in [DIR] with the name [VENV_DIR]

.PHONY: remove-venv
remove-venv: ### Remove the python virtual environment in [DIR] with the name [VENV_DIR]
	@echo 'Removing python virtual environment in $(DIR)'
	@if [ -d $(DIR)/$(VENV_DIR) ]; then \
		rm -rf $(DIR)/$(VENV_DIR); \
		echo 'Virtual environment "$(DIR)/$(VENV_DIR)" removed'; \
	else \
		echo 'Virtual environment "$(DIR)/$(VENV_DIR)" does not exist'; \
	fi

.PHONY: restore-packages
restore-packages: create-venv ### Restore python packages in [DIR]
	@if [ -z "$(HAS_POETRY)" ]; then \
		echo "poetry is not installed. Please install poetry to restore packages"; \
		exit 1; \
	fi
	@echo "Restoring python packages in $(DIR)"
	@cd $(DIR) && poetry install
	@if [ $$? -ne 0 ]; then \
		echo "Failed to restore python packages in $(DIR)"; \
		exit $$?; \
	fi

.PHONY: setup-base
setup-base: ### Minimal setup in order to start development or a CI run (installs poetry and restores packages)
	@if [ -z "$(HAS_PIPX)" ]; then \
		pip install poetry pre-commit; \
	else \
		pipx install poetry pre-commit; \
	fi
	@$(MAKE) restore-packages

	
.PHONY: setup-pre-commit
setup-pre-commit: ### Setup pre-commit (a commit linting tool) in this repository
	@cd app/backend; poetry run pre-commit install

.PHONY: setup
setup: setup-base setup-pre-commit ### Setup you development environment

.PHONY: lint
lint: setup-base ### Lint all projects manually
	@pre-commit run -a

.PHONY: format
format: ### Format all code
	@find . -type f -not -path "*.venv*" -not -path "*node_modules*" -name '*.py' | xargs -I {} reorder-python-imports --py38-plus {} || true
	@black ./ --config pyproject.toml
	@find . -type f -not -path "*.venv*" -not -path "*node_modules*" -name '*.py' | xargs -I {} autoflake -v {} --in-place --remove-all-unused-imports

.PHONY: remove-pycache
remove-pycache: ### Remove __pycache__ and .pytest_cache directories except in [VENV_DIR]
	@echo 'Removing __pycache__ and .pytest_cache directories'
	@find . -type d -path '*/$(VENV_DIR)/*' -prune -o \( -name __pycache__ -o -name .pytest_cache \) -exec rm -rf {} +

.PHONY: update-submodules
update-submodules: ### Update git submodules and checkout [FRONTEND_BRANCH]
	@echo 'Updating git submodules'
	@git submodule update --init --recursive
	@$(MAKE) -s update-frontend

.PHONY: update-frontend
update-frontend: ### Check out [FRONTEND_BRANCH]
	@echo 'Checking out frontend branch $(FRONTEND_BRANCH)'
	@git submodule update --remote --merge
	@git -C app/frontend checkout $(FRONTEND_BRANCH)

.PHONY: install-frontend-deps
install-frontend-deps: ### Install frontend dependencies
	@if [ -d app/frontend/node_modules ]; then \
		echo 'Frontend dependencies already installed'; \
	else \
		echo 'Installing frontend dependencies'; \
		cd app/frontend && npm install; \
	fi
	@if [ -f frontend.env ]; then \
		cp frontend.env app/frontend/.env; \
	fi
	
.PHONY: update-deps
update-deps: ### Update dependencies in [DIR]
	@if [ -z "$(HAS_POETRY)" ]; then \
		echo "poetry is not installed. Please install poetry to update dependencies"; \
		exit 1; \
	fi
	@echo "Updating dependencies in $(DIR)"
	@cd $(DIR) && poetry update
	@if [ $$? -ne 0 ]; then \
		echo "Failed to update dependencies in $(DIR)"; \
		exit $$?; \
	fi
	@echo "Dependencies updated in $(DIR)"

.PHONY: gen-deps
gen-deps: ### Generate the requirements.txt file in [DIR] using poetry
	@if [ -z "$(HAS_POETRY)" ]; then \
		echo "poetry is not installed. Please install poetry to generate dependencies"; \
		exit 1; \
	else \
		echo "Generating dependencies..."; \
		cd $(DIR); \
		echo "# AUTOMATICALLY GENERATED FILE. DO NOT EDIT." > requirements.txt; \
		echo "#" >> requirements.txt; \
		echo "# This file is autogenerated. Do not edit manually." >> requirements.txt; \
		echo "# To generate this file, run the following command:" >> requirements.txt; \
		echo "#\n# make DIR=$(DIR) gen-deps" >> requirements.txt; \
		poetry export -f requirements.txt --without-hashes >> requirements.txt; \
		echo "Dependencies generated"; \
	fi
