#!/bin/bash
# Quick code quality check script
# Run this before committing to catch issues early

set -e

echo "🔍 Running code quality checks..."
echo ""

# Activate virtualenv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "1️⃣ Checking code formatting with Ruff..."
ruff format --check .
echo "✅ Formatting check passed"
echo ""

echo "2️⃣ Running Ruff linter..."
ruff check .
echo "✅ Linting passed"
echo ""

echo "3️⃣ Running tests..."
pytest tests/ -m "not api_health" -q
echo "✅ Tests passed"
echo ""

echo "🎉 All checks passed! Ready to commit."
