# Claude Code DuckDB Extension

A DuckDB extension for parsing and querying Claude Code data directories (typically `~/.claude`).

## Features

This extension provides 5 table functions to query Claude Code data:

| Function | Description |
|----------|-------------|
| `read_claude_conversations(path)` | Parse JSONL conversation files from projects/ |
| `read_claude_plans(path)` | Read markdown plan files from plans/ |
| `read_claude_todos(path)` | Parse JSON todo files from todos/ |
| `read_claude_history(path)` | Parse history.jsonl |
| `read_claude_stats(path)` | Parse stats-cache.json |

## Installation

### Prerequisites
- DuckDB v1.4.4 or later
- macOS ARM64 (Apple Silicon)

### Building from Source

```bash
cd claude_code_ext

# Clone extension-ci-tools if not present
git clone --depth 1 -b v1.4.4 https://github.com/duckdb/extension-ci-tools extension-ci-tools

# Build
make

# The extension will be at build/release/claude_code.duckdb_extension
```

## Usage

```sql
-- Load the extension (unsigned required for custom builds)
LOAD '/path/to/claude_code.duckdb_extension';

-- Query conversations
SELECT * FROM read_claude_conversations('~/.claude') LIMIT 10;

-- Query plans
SELECT plan_name, LENGTH(content) as size 
FROM read_claude_plans('~/.claude');

-- Query todos
SELECT session_id, content, status 
FROM read_claude_todos('~/.claude')
WHERE status = 'in_progress';

-- Query history
SELECT display, timestamp_ms, project 
FROM read_claude_history('~/.claude')
ORDER BY timestamp_ms DESC
LIMIT 20;

-- Query stats
SELECT date, message_count, session_count, tool_call_count
FROM read_claude_stats('~/.claude');

-- Join conversations with todos
SELECT c.session_id, c.slug, t.content as todo
FROM read_claude_conversations('~/.claude') c
JOIN read_claude_todos('~/.claude') t 
  ON c.session_id = t.session_id
LIMIT 10;
```

## Schema Reference

### read_claude_conversations

| Column | Type | Description |
|--------|------|-------------|
| project | VARCHAR | Project path |
| session_id | VARCHAR | Session UUID |
| is_agent | BOOLEAN | True if sub-agent conversation |
| type | VARCHAR | Message type (user, assistant, etc.) |
| uuid | VARCHAR | Message UUID |
| parent_uuid | VARCHAR | Parent message UUID |
| timestamp | VARCHAR | ISO 8601 timestamp |
| version | VARCHAR | Claude version |
| slug | VARCHAR | Session slug |
| git_branch | VARCHAR | Git branch name |
| user_type | VARCHAR | User type |
| message_role | VARCHAR | Role (user/assistant) |
| message_content | VARCHAR | Message content |
| tool_use_id | VARCHAR | Tool use ID |
| tool_name | VARCHAR | Tool name |
| tool_input | VARCHAR | Tool input (JSON) |
| line_number | BIGINT | Line number in source file |

### read_claude_plans

| Column | Type | Description |
|--------|------|-------------|
| plan_name | VARCHAR | Plan name (from filename) |
| file_path | VARCHAR | Full file path |
| content | VARCHAR | Markdown content |

### read_claude_todos

| Column | Type | Description |
|--------|------|-------------|
| session_id | VARCHAR | Session UUID |
| agent_id | VARCHAR | Agent UUID |
| file_path | VARCHAR | Source file path |
| item_index | INTEGER | Todo item index |
| content | VARCHAR | Todo content |
| status | VARCHAR | Status (pending/in_progress/completed) |
| active_form | VARCHAR | Active form text |

### read_claude_history

| Column | Type | Description |
|--------|------|-------------|
| display | VARCHAR | Display text |
| timestamp_ms | BIGINT | Unix timestamp (milliseconds) |
| project | VARCHAR | Project path |
| session_id | VARCHAR | Session UUID |

### read_claude_stats

| Column | Type | Description |
|--------|------|-------------|
| date | VARCHAR | Date (YYYY-MM-DD) |
| message_count | BIGINT | Message count |
| session_count | BIGINT | Session count |
| tool_call_count | BIGINT | Tool call count |

## Project Structure

```
agentic-copilot/
├── claude_code_ext/          # DuckDB extension source
│   ├── src/
│   │   ├── capi_quack.c      # Extension entry point
│   │   ├── conversations.c   # Conversations table function
│   │   ├── plans.c           # Plans table function
│   │   ├── todos.c           # Todos table function
│   │   ├── history.c         # History table function
│   │   ├── stats.c           # Stats table function
│   │   ├── file_utils.c      # File utilities
│   │   └── third_party/      # cJSON library
│   └── CMakeLists.txt
├── docs/
│   ├── CLAUDE_FILE_STRUCTURE.md  # Claude data directory documentation
│   ├── CLAUDE_FILE_SCHEMAS.md    # Data schema documentation
│   └── DUCKDB_EXTENSION_PATTERNS.md  # Extension development patterns
├── scripts/
│   ├── analyze_structure.py   # Analyze Claude data structure
│   ├── generate_test_data.py  # Generate synthetic test data
│   └── verify.sh              # Build and test verification
└── test/
    ├── data/                  # Synthetic test data
    └── sql/                   # SQL test cases
```

## Development

### Running Tests

```bash
./scripts/verify.sh
```

### Regenerating Test Data

```bash
python scripts/generate_test_data.py
```

## Documentation

- [Claude File Structure](docs/CLAUDE_FILE_STRUCTURE.md) - Detailed documentation of Claude data directory
- [Claude File Schemas](docs/CLAUDE_FILE_SCHEMAS.md) - JSON/JSONL schema documentation
- [DuckDB Extension Patterns](docs/DUCKDB_EXTENSION_PATTERNS.md) - Extension development best practices

## License

MIT