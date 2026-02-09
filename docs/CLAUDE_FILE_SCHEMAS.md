# Claude Code Data Schemas

This document defines the JSON/JSONL schemas for all data types in a Claude Code data directory.

## Table of Contents

1. [Conversation Messages](#conversation-messages)
2. [History Entries](#history-entries)
3. [Todo Items](#todo-items)
4. [Plan Files](#plan-files)
5. [Stats Cache](#stats-cache)
6. [File History Snapshots](#file-history-snapshots)

---

## Conversation Messages

Conversation files are JSONL (JSON Lines) format where each line is a complete JSON object.

### Base Message Schema

All messages share these common fields:

```typescript
interface BaseMessage {
  type: "user" | "assistant" | "system" | "file-history-snapshot" | "queue-operation" | "summary";
  uuid?: string;                    // Unique message identifier
  parentUuid?: string | null;       // Parent message UUID for threading
  timestamp?: string;               // ISO 8601 format
  sessionId?: string;               // Session UUID
  cwd?: string;                     // Current working directory
  version?: string;                 // Claude Code version (e.g., "2.0.76")
  slug?: string;                    // Human-readable session name
  gitBranch?: string;               // Current git branch
  userType?: string;                // User type (e.g., "external")
  isSidechain?: boolean;            // Whether on conversation sidechain
}
```

### User Message

```typescript
interface UserMessage extends BaseMessage {
  type: "user";
  message: {
    role: "user";
    content: string;               // The user's message text
  };
  thinkingMetadata?: {
    level: "high" | "medium" | "low";
    disabled: boolean;
    triggers: string[];
  };
  todos?: TodoItem[];              // Current todo state
}
```

### Assistant Message

```typescript
interface AssistantMessage extends BaseMessage {
  type: "assistant";
  message: {
    model: string;                 // e.g., "claude-sonnet-4-20250514"
    id: string;                    // Message ID from API
    type: "message";
    role: "assistant";
    content: ContentBlock[];       // Array of content blocks
    stop_reason: string | null;
    stop_sequence: string | null;
    usage: UsageInfo;
  };
  toolUseResult?: ToolResult;      // Result if this follows tool use
}

interface UsageInfo {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens?: number;
  cache_read_input_tokens?: number;
  cache_creation?: {
    ephemeral_5m_input_tokens?: number;
    ephemeral_1h_input_tokens?: number;
  };
}
```

### Content Blocks

Content blocks appear in assistant message `content` arrays:

```typescript
type ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock;

interface TextBlock {
  type: "text";
  text: string;
}

interface ThinkingBlock {
  type: "thinking";
  thinking: string;                // Claude's thinking process
  signature: string;               // Cryptographic signature
}

interface ToolUseBlock {
  type: "tool_use";
  id: string;                      // Tool use ID (e.g., "toolu_bdrk_01...")
  name: string;                    // Tool name
  input: object;                   // Tool-specific input parameters
}

interface ToolResultBlock {
  type: "tool_result";
  tool_use_id: string;
  content: string | ContentItem[];
  is_error?: boolean;
}
```

### Tool Names and Input Schemas

#### Bash Tool
```typescript
interface BashInput {
  command: string;
  timeout?: number;
}
```

#### Read Tool
```typescript
interface ReadInput {
  file_path: string;
  offset?: number;
  limit?: number;
}
```

#### Write Tool
```typescript
interface WriteInput {
  file_path: string;
  content: string;
}
```

#### Edit Tool
```typescript
interface EditInput {
  file_path: string;
  old_string: string;
  new_string: string;
}
```

#### Glob Tool
```typescript
interface GlobInput {
  pattern: string;
  path?: string;
}
```

#### Task (Sub-agent) Tool
```typescript
interface TaskInput {
  subagent_type: "explore" | "task" | "general-purpose" | "code-review";
  description: string;
  prompt: string;
}
```

#### TodoWrite Tool
```typescript
interface TodoWriteInput {
  todos: string;                   // Markdown checklist format
}
```

#### WebFetch Tool
```typescript
interface WebFetchInput {
  url: string;
  max_length?: number;
  raw?: boolean;
}
```

### System Message

```typescript
interface SystemMessage extends BaseMessage {
  type: "system";
  subtype: "compact_boundary" | "info" | "error";
  content: string;
  level: "info" | "warning" | "error";
  isMeta: boolean;
  compactMetadata?: {
    trigger: string;
    preTokens: number;
  };
  logicalParentUuid?: string;
}
```

### File History Snapshot

```typescript
interface FileHistorySnapshot {
  type: "file-history-snapshot";
  messageId: string;               // Associated message UUID
  isSnapshotUpdate: boolean;
  snapshot: {
    messageId: string;
    timestamp: string;
    trackedFileBackups: {
      [filePath: string]: {
        backupFileName: string | null;  // Format: "<hash>@v<version>"
        version: number;
        backupTime: string;
      };
    };
  };
}
```

### Queue Operation

```typescript
interface QueueOperation {
  type: "queue-operation";
  operation: "enqueue" | "dequeue";
  timestamp: string;
  sessionId: string;
  content: string;                 // Queued message content
}
```

### Summary Message

```typescript
interface SummaryMessage {
  type: "summary";
  summary: string;                 // Conversation summary text
  leafUuid: string;                // Last message UUID in summarized section
}
```

### Agent Message Extensions

Sub-agent messages include additional fields:

```typescript
interface AgentMessage extends BaseMessage {
  agentId: string;                 // Agent identifier (short hash)
  // Inherits all other base fields
}
```

---

## History Entries

The `history.jsonl` file contains global command history.

```typescript
interface HistoryEntry {
  display: string;                 // Displayed prompt text
  pastedContents: object;          // Pasted content (usually {})
  timestamp: number;               // Unix timestamp in milliseconds
  project: string;                 // Project path
  sessionId?: string;              // Optional session UUID
}
```

---

## Todo Items

Todo files are JSON arrays containing todo items.

```typescript
interface TodoFile extends Array<TodoItem> {}

interface TodoItem {
  content: string;                 // Todo description
  status: "pending" | "in_progress" | "completed";
  activeForm?: string;             // Current activity description
}
```

**File naming pattern:** `<session-uuid>-agent-<agent-uuid>.json`

---

## Plan Files

Plan files are Markdown documents with a standard structure:

```markdown
# Plan Title

## Problem Statement
Description of the problem being solved.

## Current State Analysis
Analysis of the current state.

## Implementation Plan

### Phase 1: Setup
- [ ] Task 1
- [ ] Task 2

### Phase 2: Implementation
- [ ] Task 3
- [ ] Task 4

## Notes
Additional considerations.
```

**File naming pattern:** `<adjective>-<verb>-<noun>.md` (e.g., `keen-juggling-origami.md`)

---

## Stats Cache

The `stats-cache.json` file contains aggregated usage statistics.

```typescript
interface StatsCache {
  version: number;                 // Schema version (currently 1)
  lastComputedDate: string;        // ISO date (YYYY-MM-DD)
  dailyActivity: DailyStats[];
}

interface DailyStats {
  date: string;                    // ISO date
  messageCount: number;
  sessionCount: number;
  toolCallCount: number;
}
```

---

## DuckDB Table Schemas

Target schemas for the DuckDB extension:

### claude_conversations

```sql
CREATE TABLE claude_conversations (
    session_id VARCHAR,
    project_path VARCHAR,
    message_uuid VARCHAR PRIMARY KEY,
    parent_uuid VARCHAR,
    message_type VARCHAR,          -- 'user', 'assistant', 'system'
    timestamp TIMESTAMP,
    content TEXT,
    model VARCHAR,
    tool_uses JSON,                -- Array of tool use objects
    token_usage JSON,
    slug VARCHAR,
    git_branch VARCHAR,
    cwd VARCHAR
);
```

### claude_plans

```sql
CREATE TABLE claude_plans (
    plan_name VARCHAR PRIMARY KEY,
    slug VARCHAR,
    content TEXT,
    file_size INTEGER,
    created_at TIMESTAMP,
    modified_at TIMESTAMP
);
```

### claude_todos

```sql
CREATE TABLE claude_todos (
    session_id VARCHAR,
    agent_id VARCHAR,
    todo_index INTEGER,
    content TEXT,
    status VARCHAR,                -- 'pending', 'in_progress', 'completed'
    active_form VARCHAR,
    PRIMARY KEY (session_id, agent_id, todo_index)
);
```

### claude_history

```sql
CREATE TABLE claude_history (
    timestamp TIMESTAMP,
    project VARCHAR,
    session_id VARCHAR,
    display TEXT,
    pasted_contents JSON
);
```

### claude_stats

```sql
CREATE TABLE claude_stats (
    date DATE PRIMARY KEY,
    message_count INTEGER,
    session_count INTEGER,
    tool_call_count INTEGER
);
```

---

## Field Value Patterns

### UUIDs
- Format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Example: `be74c085-8d87-49a7-9100-7f0e83f29a10`

### Short Agent IDs
- Format: `a[0-9a-f]{6,7}`
- Example: `a64f14a`

### Timestamps
- ISO 8601 format: `2025-12-26T12:58:17.099Z`
- Unix milliseconds in history: `1760110675230`

### Project Paths
- Original: `/Users/asaucedo/project-name`
- Encoded: `-Users-asaucedo-project-name`

### Slugs
- Pattern: `<adjective>-<verb>-<noun>`
- Examples: `keen-juggling-origami`, `binary-prancing-shore`

### File History Backup Names
- Pattern: `<content-hash>@v<version>`
- Example: `a1a38b086cb7d247@v2`
