# Claude Code File Structure Documentation

This document describes the file and folder structure of a Claude Code data directory (typically `~/.claude`).

## Overview

Claude Code stores all conversation data, file backups, and metadata in a central data directory. The structure is designed to support multiple projects, conversation sessions, and agent instances.

## Root Directory Structure

```
~/.claude/
├── CLAUDE.md                 # Global Claude configuration/instructions
├── history.jsonl             # Global command/prompt history
├── stats-cache.json          # Aggregated usage statistics
├── projects/                 # Per-project conversation data
├── plans/                    # Implementation plans (markdown)
├── todos/                    # Todo items (JSON)
├── file-history/             # File version backups
├── session-env/              # Session environment data
├── debug/                    # Debug logs
├── telemetry/                # Telemetry data
├── shell-snapshots/          # Shell state snapshots
├── statsig/                  # Feature flag data
└── plugins/                  # Plugin storage
```

## Detailed Structure

### Projects Directory (`projects/`)

Contains per-project conversation data. Each project is identified by its filesystem path with `/` replaced by `-`.

```
projects/
├── -Users-username-project-name/
│   ├── <session-uuid>.jsonl      # Main conversation (user-initiated session)
│   ├── agent-<short-id>.jsonl    # Sub-agent conversations
│   └── ...
└── -Users-username-another-project/
    └── ...
```

**File Naming Patterns:**
- `<uuid>.jsonl` - Main conversation sessions (full UUID like `463678c9-ccb0-4ecf-ab27-97899863c508`)
- `agent-<short-id>.jsonl` - Sub-agent sessions (short hash like `agent-a64f14a`)

**Relationships:**
- Main sessions can spawn sub-agents via the `task` tool
- Sub-agents reference parent session via `sessionId` field
- Sub-agents have their own `agentId` field

### Plans Directory (`plans/`)

Contains implementation plans created via the `update_plan` or planning tools.

```
plans/
├── binary-prancing-shore.md
├── keen-juggling-origami.md
└── ...
```

**File Naming:**
- Named with human-readable slugs (adjective-verb-noun pattern)
- Same slug appears in conversation messages (`slug` field)

**Content Structure:**
- Standard markdown format
- Typically contains problem statement, phases, and TODO lists

### Todos Directory (`todos/`)

Contains todo item lists managed via the `update_todo` tool.

```
todos/
├── <session-uuid>-agent-<agent-uuid>.json
└── ...
```

**File Naming:**
- Pattern: `<session-id>-agent-<agent-id>.json`
- Links todo state to specific agent within session

**Content Structure:**
```json
[
  {
    "content": "Task description",
    "status": "completed|in_progress|pending",
    "activeForm": "Current activity description"
  }
]
```

### File History Directory (`file-history/`)

Contains versioned backups of files modified during sessions.

```
file-history/
├── <session-uuid>/
│   ├── <content-hash>@v<version>
│   └── ...
└── ...
```

**File Naming:**
- Pattern: `<content-hash>@v<version-number>`
- Hash is based on original file path
- Version increments with each backup

### History File (`history.jsonl`)

Global command/prompt history across all projects.

**Fields:**
- `display` - The displayed prompt/command text
- `pastedContents` - Any pasted content (object)
- `timestamp` - Unix timestamp in milliseconds
- `project` - Project path
- `sessionId` - Optional session UUID

### Stats Cache (`stats-cache.json`)

Aggregated usage statistics.

```json
{
  "version": 1,
  "lastComputedDate": "2026-01-06",
  "dailyActivity": [
    {
      "date": "2025-11-15",
      "messageCount": 1272,
      "sessionCount": 1,
      "toolCallCount": 373
    }
  ]
}
```

## Conversation JSONL Message Types

Each line in a `.jsonl` conversation file is a message object with a `type` field.

### Message Types

| Type | Description | Key Fields |
|------|-------------|------------|
| `user` | User message | `message.content`, `uuid`, `timestamp`, `todos` |
| `assistant` | Claude's response | `message.content`, `uuid`, `parentUuid`, `toolUseResult` |
| `system` | System message | `subtype`, `content`, `level`, `compactMetadata` |
| `file-history-snapshot` | File backup snapshot | `messageId`, `snapshot`, `isSnapshotUpdate` |
| `queue-operation` | Async queue operation | `operation`, `content` |
| `summary` | Conversation summary | `summary`, `leafUuid` |

### Common Message Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Message type identifier |
| `uuid` | string | Unique message identifier |
| `parentUuid` | string\|null | Parent message UUID (for threading) |
| `timestamp` | string | ISO 8601 timestamp |
| `sessionId` | string | Session UUID |
| `cwd` | string | Current working directory |
| `version` | string | Claude Code version |
| `slug` | string | Human-readable session name |
| `gitBranch` | string | Current git branch |
| `userType` | string | User type (e.g., "external") |
| `isSidechain` | boolean | Whether message is on a sidechain |

### Agent-Specific Fields

| Field | Type | Description |
|-------|------|-------------|
| `agentId` | string | Agent identifier (for sub-agents) |
| `toolUseResult` | object | Result of tool execution |

### User Message Structure

```json
{
  "type": "user",
  "uuid": "...",
  "parentUuid": null,
  "timestamp": "2025-12-26T12:58:17.099Z",
  "sessionId": "...",
  "cwd": "/path/to/project",
  "message": {
    "role": "user",
    "content": "User's message text"
  },
  "thinkingMetadata": {
    "level": "...",
    "disabled": false,
    "triggers": [...]
  },
  "todos": []
}
```

### Assistant Message Structure

```json
{
  "type": "assistant",
  "uuid": "...",
  "parentUuid": "...",
  "timestamp": "2025-12-26T12:58:23.319Z",
  "sessionId": "...",
  "cwd": "/path/to/project",
  "message": {
    "model": "claude-sonnet-4-20250514",
    "id": "msg_...",
    "type": "message",
    "role": "assistant",
    "content": [...]
  }
}
```

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Data Directory                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  history.jsonl ──────────────┐                                  │
│  (global command history)    │                                  │
│                              ▼                                  │
│  projects/                   │                                  │
│  ├── <project-path>/         │                                  │
│  │   ├── <session>.jsonl ◄───┤                                  │
│  │   │   ├── user messages   │                                  │
│  │   │   ├── assistant msgs ─┼─────► plans/<slug>.md            │
│  │   │   │   (tool calls)    │       (via update_plan tool)     │
│  │   │   │                   │                                  │
│  │   │   └── spawns ─────────┼─────► todos/<session-agent>.json │
│  │   │                       │       (via update_todo tool)     │
│  │   ├── agent-<id>.jsonl ◄──┘                                  │
│  │   │   (sub-agent)                                            │
│  │   └── ...                                                    │
│  │                                                              │
│  file-history/                                                  │
│  ├── <session>/                                                 │
│  │   └── <hash>@v<version>   ◄──── file-history-snapshot msgs   │
│  │       (file backups)                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Relationships

1. **Session → Project**: Each session file lives under a project directory
2. **Session → Sub-agents**: Main sessions spawn agent-* files
3. **Session → Plans**: Conversations reference plans via `slug` field
4. **Session → Todos**: Todo tool creates files named by session+agent
5. **Session → File History**: file-history-snapshot messages link to backup files
6. **History → Sessions**: History entries optionally reference sessionId
