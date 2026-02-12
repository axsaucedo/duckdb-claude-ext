#!/bin/bash
# Test runner for agent_data DuckDB extension
# Runs SQLLogicTest .test files via duckdb_sqllogictest
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
EXT_PATH="$PROJECT_DIR/build/debug/agent_data.duckdb_extension"
TEST_SQL_DIR="$PROJECT_DIR/test/sql"
PYTHON_BIN="$PROJECT_DIR/configure/venv/bin/python3"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ ! -f "$EXT_PATH" ]; then
    echo -e "${RED}Extension not found at $EXT_PATH${NC}"
    echo "Run 'make debug' first."
    exit 1
fi

echo "Running SQLLogicTest suite..."
START_TIME=$(date +%s)

$PYTHON_BIN -m duckdb_sqllogictest \
    --test-dir "$TEST_SQL_DIR" \
    --external-extension "$EXT_PATH"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}All SQLLogicTest tests passed!${NC} (${ELAPSED}s)"
