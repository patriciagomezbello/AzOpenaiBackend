.DEFAULT_GOAL := help
SHELL := /bin/sh

USE_POETRY := $(shell command -v poetry 2> /dev/null)
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
	@echo '  General targets automate the workflow for the application and scripts.'
	@echo '  Specific targets manage environments and testing, and should not be used directly without understanding.'
	@echo ''
	@echo 'Variables:'
	@echo '  DIR               - Target directory (default: app/backend)'
	@echo '  VENV_DIR          - Virtual environment directory name (default: .venv)'
	@echo '  START_SCRIPT      - Startup script name (default: start.sh)'
	@echo '  FRONTEND_BRANCH   - Branch to pull for the frontend (default: main)'
	@echo ''
	@echo 'General targets:'
	@echo '  dev               - Run the mate application and frontend'
	@echo '  mate              - Run the mate application'
	@echo '  scripts           - Run the scripts'
	@echo '  frontend          - Run the frontend'
	@echo '  bot               - Run the jira ticket bot'
	@echo '  test              - Run all tests'
	@echo '  mate-test         - Run tests for the mate application'
	@echo '  scripts-test      - Run tests for the scripts'
	@echo '  cleanup           - Clean up the virtual environments and cache directories'
	@echo '  lint              - Run pre-commit hooks'
	@echo '  help              - Display this help message'
	@echo ''
	@echo 'Specific targets:'
	@echo '  start                 - Start the application/script in [DIR]/[START_SCRIPT]'
	@echo '  run-test              - Run tests in [DIR]'
	@echo '  create-venv           - Create a python virtual environment in [DIR] with the name [VENV_DIR]'
	@echo '  create-venv-pip       - Create a python virtual environment using pip'
	@echo '  create-venv-poetry    - Create a python virtual environment using poetry'
	@echo '  remove-venv           - Remove the python virtual environment in [DIR] with the name [VENV_DIR]'
	@echo '  restore-packages      - Restore python packages in [DIR]'
	@echo '  restore-packages-pip  - Restore python packages using pip'
	@echo '  restore-packages-poetry - Restore python packages using poetry'
	@echo '  cleanup-mate          - Clean up the virtual environment and cache directories for the mate application'
	@echo '  cleanup-scripts       - Clean up the virtual environment and cache directories for the scripts'
	@echo '  remove-pycache        - Remove __pycache__ and .pytest_cache directories except in [VENV_DIR]'
	@echo '  update-submodules     - Update git submodules and checkout [FRONTEND_BRANCH]'
	@echo '  update-frontend       - Check out [FRONTEND_BRANCH]'
	@echo '  install-frontend-deps - Install frontend dependencies'
	@echo '  gen-deps              - Generate the requirements.txt file in [DIR] using poetry'

.PHONY: dev
dev:
	@$(MAKE) -s -j 2 mate frontend

.PHONY: mate
mate:
	@$(MAKE) -s DIR=app/backend start

.PHONY: scripts
scripts:
	@$(MAKE) -s DIR=scripts START_SCRIPT=prepdocs-local.sh start

.PHONY: bot
bot:
	@$(MAKE) -s DIR=app/ticket-bot start

.PHONY: test
test: mate-test scripts-test

.PHONY: mate-test
mate-test: 
	@$(MAKE) -s DIR=app/backend run-test

.PHONY: scripts-test
scripts-test:
	@$(MAKE) -s DIR=scripts run-test

.PHONY: cleanup
cleanup: cleanup-mate cleanup-scripts

.PHONY: cleanup-mate
cleanup-mate: 
	@$(MAKE) -s DIR=app/backend remove-venv remove-pycache

.PHONY: cleanup-scripts
cleanup-scripts:
	@$(MAKE) -s DIR=scripts remove-venv remove-pycache

.PHONY: start
start: create-venv restore-packages
	@echo 'Starting $(DIR)/$(START_SCRIPT)'
	@cd $(DIR) && ./$(START_SCRIPT)
	@if [ $$? -ne 0 ]; then \
		echo "Failed to run ./$(DIR)/$(START_SCRIPT)"; \
		exit $$?; \
	fi

.PHONY: frontend
frontend: update-submodules install-frontend-deps
	@echo 'Starting frontend'
	@cd app/frontend && npm run dev -- --host 0.0.0.0

.PHONY: run-test
run-test: create-venv restore-packages
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

.PHONY: create-venv
create-venv:
	@if [ -z "$(USE_POETRY)" ]; then \
		$(MAKE) -s create-venv-pip; \
	else \
		$(MAKE) -s create-venv-poetry; \
	fi

.PHONY: create-venv-pip
create-venv-pip:
	@if [ -d $(DIR)/$(VENV_DIR) ]; then \
		echo 'Virtual environment "$(DIR)/$(VENV_DIR)" already exists'; \
		exit 0; \
	else \
		echo 'Creating virtual environment "$(DIR)/$(VENV_DIR)"'; \
		python3 -m venv $(DIR)/$(VENV_DIR); \
	fi

.PHONY: create-venv-poetry
create-venv-poetry:
	@if [ -d $(DIR)/$(VENV_DIR) ]; then \
		echo 'Virtual environment "$(DIR)/$(VENV_DIR)" already exists'; \
		exit 0; \
	else \
		echo 'Creating virtual environment "$(DIR)/$(VENV_DIR)"'; \
		poetry config virtualenvs.in-project true; \
		cd $(DIR) && poetry install; \
	fi

.PHONY: remove-venv
remove-venv:
	@echo 'Removing python virtual environment in $(DIR)'
	@if [ -d $(DIR)/$(VENV_DIR) ]; then \
		rm -rf $(DIR)/$(VENV_DIR); \
		echo 'Virtual environment "$(DIR)/$(VENV_DIR)" removed'; \
	else \
		echo 'Virtual environment "$(DIR)/$(VENV_DIR)" does not exist'; \
	fi

.PHONY: restore-packages
restore-packages: create-venv
	@if [ -z "$(USE_POETRY)" ]; then \
		$(MAKE) -s restore-packages-pip; \
	else \
		$(MAKE) -s restore-packages-poetry; \
	fi

.PHONY: restore-packages-pip
restore-packages-pip:
	@echo "Restoring python packages in $(DIR)"
	@cd $(DIR) && ./$(VENV_DIR)/bin/python -m pip install -q -r requirements.txt
	@if [ $$? -ne 0 ]; then \
		echo "Failed to restore python packages in $(DIR)"; \
		exit $$?; \
	fi

.PHONY: restore-packages-poetry
restore-packages-poetry:
	@echo "Restoring python packages in $(DIR)"
	@cd $(DIR) && poetry install
	@if [ $$? -ne 0 ]; then \
		echo "Failed to restore python packages in $(DIR)"; \
		exit $$?; \
	fi

.PHONY: lint
lint:
	@pre-commit run --hook-stage pre-commit -a

.PHONY: remove-pycache
remove-pycache:
	@echo 'Removing __pycache__ and .pytest_cache directories'
	@find . -type d -path '*/$(VENV_DIR)/*' -prune -o \( -name __pycache__ -o -name .pytest_cache \) -exec rm -rf {} +

.PHONY: update-submodules
update-submodules:
	@echo 'Updating git submodules'
	@git submodule update --init --recursive
	@$(MAKE) -s update-frontend

.PHONY: update-frontend
update-frontend:
	@echo 'Checking out frontend branch $(FRONTEND_BRANCH)'
	@git submodule update --remote --merge
	@git -C app/frontend checkout $(FRONTEND_BRANCH)

.PHONY: install-frontend-deps
install-frontend-deps:
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
update-deps:
	@if [ -z "$(USE_POETRY)" ]; then \
		echo "poetry is not installed. Please install poetry to update dependencies"; \
		exit 1; \
	else \
		echo "Updating dependencies..."; \
		cd $(DIR); \
		poetry update; \
		echo "Dependencies updated"; \
	fi

.PHONY: gen-deps
gen-deps:
	@if [ -z "$(USE_POETRY)" ]; then \
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