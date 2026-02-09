# Claude Code DuckDB Extension

A DuckDB extension for parsing and querying Claude Code data directories.

## Overview

This extension provides table functions to query data from Claude Code data directories (typically `~/.claude`), including:

- **Conversations** - JSONL message logs from projects/
- **Plans** - Markdown plan files from plans/
- **Todos** - JSON todo files from todos/
- **History** - Global command history from history.jsonl
- **Stats** - Daily usage statistics from stats-cache.json

## Building

### Prerequisites
- Python3 + venv
- CMake
- Make
- Git
- DuckDB v1.4.4+

### Build Steps

```bash
# Clone extension-ci-tools
git clone --depth 1 -b v1.4.4 https://github.com/duckdb/extension-ci-tools extension-ci-tools

# Build release
make release

# The extension will be at build/release/claude_code.duckdb_extension
```

## Usage

```sql
-- Load extension (requires unsigned flag for custom builds)
LOAD '/path/to/claude_code.duckdb_extension';

-- Query conversations
SELECT session_id, type, message_content 
FROM read_claude_conversations('~/.claude') 
LIMIT 10;

-- Query plans
SELECT plan_name, content 
FROM read_claude_plans('~/.claude');

-- Query todos
SELECT session_id, content, status 
FROM read_claude_todos('~/.claude');

-- Query history
SELECT display, timestamp_ms, project 
FROM read_claude_history('~/.claude');

-- Query stats
SELECT date, message_count, session_count 
FROM read_claude_stats('~/.claude');
```

## Testing

```bash
# Run all tests
make test_release
```

## Technical Notes

- Built using DuckDB C Extension API (more stable than C++ API)
- Uses C_STRUCT_UNSTABLE ABI for v1.4.4 compatibility
- Includes cJSON library for JSON parsing
- Designed for macOS ARM64 (Apple Silicon)

## License

MIT