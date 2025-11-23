#!/bin/bash
# Code quality checks script
# Runs various code quality tools

set -e

echo "Running code quality checks..."

# Install tools if needed
pip install black flake8 isort pylint --quiet

echo "1. Formatting check with black..."
black --check . || echo "Code formatting issues found. Run 'black .' to fix."

echo "2. Import sorting check with isort..."
isort --check-only . || echo "Import sorting issues found. Run 'isort .' to fix."

echo "3. Linting with flake8..."
flake8 . --max-line-length=120 --exclude=venv,__pycache__,migrations || echo "Linting issues found."

echo "4. Code complexity with pylint..."
pylint app.py scraper/ auth/ --max-line-length=120 --disable=C0111 || echo "Pylint issues found."

echo "Code quality checks complete!"

