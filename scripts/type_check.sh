#!/bin/bash
# Type checking script using mypy
# This helps identify areas where type hints should be added

set -e

echo "Running type checking with mypy..."

# Install mypy if not present
if ! command -v mypy &> /dev/null; then
    echo "Installing mypy..."
    pip install mypy
fi

# Run mypy on key modules
mypy app.py \
    scraper/ \
    auth/ \
    models/ \
    cache/ \
    --ignore-missing-imports \
    --no-strict-optional \
    --show-error-codes \
    || echo "Type checking completed with some issues (expected for gradual typing)"

echo "Type checking complete. Review output above for areas needing type hints."

