#!/bin/bash
# Test runner for agent_data DuckDB extension
# Runs all SQL test files and checks for PASS/FAIL assertions
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
EXT_PATH="$PROJECT_DIR/build/debug/agent_data.duckdb_extension"
TEST_SQL_DIR="$PROJECT_DIR/test/sql"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -f "$EXT_PATH" ]; then
    echo -e "${RED}Extension not found at $EXT_PATH${NC}"
    echo "Run 'make debug' first."
    exit 1
fi

TOTAL_PASS=0
TOTAL_FAIL=0
FAILED_TESTS=""
START_TIME=$(date +%s)

for sql_file in "$TEST_SQL_DIR"/test_*.sql; do
    test_name=$(basename "$sql_file" .sql)
    echo -e "${YELLOW}Running $test_name...${NC}"

    output=$(duckdb -unsigned -noheader -csv -cmd "LOAD '$EXT_PATH';" -c ".read $sql_file" 2>&1) || true

    while IFS= read -r line; do
        [ -z "$line" ] && continue
        result=$(echo "$line" | xargs)
        if [[ "$result" == PASS* ]]; then
            TOTAL_PASS=$((TOTAL_PASS + 1))
            echo -e "  ${GREEN}✓ $result${NC}"
        elif [[ "$result" == FAIL* ]]; then
            TOTAL_FAIL=$((TOTAL_FAIL + 1))
            FAILED_TESTS="$FAILED_TESTS\n  $test_name: $result"
            echo -e "  ${RED}✗ $result${NC}"
        fi
    done <<< "$output"
done

# Benchmark timing check: full test suite should complete in under 10 seconds
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

if [ $ELAPSED -gt 10 ]; then
    echo -e "${RED}⚠ Benchmark warning: test suite took ${ELAPSED}s (threshold: 10s)${NC}"
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
    FAILED_TESTS="$FAILED_TESTS\n  benchmark: test suite exceeded 10s threshold (${ELAPSED}s)"
fi

echo ""
echo "========================================"
echo -e "Results: ${GREEN}$TOTAL_PASS passed${NC}, ${RED}$TOTAL_FAIL failed${NC} (${ELAPSED}s)"
echo "========================================"

if [ $TOTAL_FAIL -gt 0 ]; then
    echo -e "${RED}Failed tests:${NC}"
    echo -e "$FAILED_TESTS"
    exit 1
fi

echo -e "${GREEN}All tests passed!${NC}"
