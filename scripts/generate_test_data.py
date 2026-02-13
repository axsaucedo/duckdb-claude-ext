#!/usr/bin/env python3
"""
Generate deterministic test data for the agent_data DuckDB extension.

Produces both Claude Code (data_claude/) and Copilot CLI (data_copilot/)
test fixtures with fixed seeds for full reproducibility. Re-running this
script always produces byte-identical output.

Usage:
    python scripts/generate_test_data.py          # regenerate all
"""

import json
import random
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

# ─── deterministic RNG ───────────────────────────────────────────────
SEED = 42
_rng = random.Random(SEED)
_uuid_counter = 0


def _uuid() -> str:
    """Deterministic UUID v4 using seeded RNG."""
    global _uuid_counter
    _uuid_counter += 1
    r = random.Random(SEED + _uuid_counter)
    return str(uuid.UUID(int=r.getrandbits(128), version=4))


def _short_id() -> str:
    global _uuid_counter
    _uuid_counter += 1
    r = random.Random(SEED + _uuid_counter)
    return "a" + uuid.UUID(int=r.getrandbits(128), version=4).hex[:7]


# ─── Claude configuration ────────────────────────────────────────────
CLAUDE_DIR = Path("test/data_claude")
NUM_PROJECTS = 3
SESSIONS_PER_PROJECT = 2
MESSAGES_PER_SESSION = 10
AGENTS_PER_SESSION = 1
NUM_PLANS = 4
NUM_TODOS = 5
NUM_HISTORY_ENTRIES = 20
NUM_STATS_DAYS = 7

ADJECTIVES = ["keen", "binary", "bright", "cozy", "swift", "quiet"]
VERBS = ["juggling", "prancing", "exploring", "napping", "coding", "testing"]
NOUNS = ["origami", "shore", "wolf", "hippo", "stream", "dolphin"]

PROJECT_PATHS = [
    "/Users/testuser/project-alpha",
    "/Users/testuser/project-beta",
    "/Users/testuser/project-gamma",
]

TOOLS = [
    ("Bash", {"command": "ls -la"}),
    ("Read", {"file_path": "src/main.py"}),
    ("Write", {"file_path": "output.txt", "content": "test content"}),
    ("Edit", {"file_path": "config.json", "old_string": "old", "new_string": "new"}),
    ("Glob", {"pattern": "**/*.py"}),
    ("TodoWrite", {"todos": "- [ ] Task 1\n- [x] Task 2"}),
]

SAMPLE_PROMPTS = [
    "Create a new Python project with a basic structure",
    "Add unit tests for the main module",
    "Fix the bug in the authentication handler",
    "Refactor the database connection logic",
    "Add error handling to the API endpoints",
    "Document the public functions",
    "Optimize the search algorithm",
    "Set up CI/CD pipeline",
]

# Fixed base time for determinism
BASE_TIME = datetime(2026, 1, 8, 10, 0, 0)


# ─── Claude generators ───────────────────────────────────────────────

def encode_project_path(path: str) -> str:
    return path.replace("/", "-")


def generate_slug() -> str:
    return f"{_rng.choice(ADJECTIVES)}-{_rng.choice(VERBS)}-{_rng.choice(NOUNS)}"


def generate_timestamp(base: datetime, offset_minutes: int = 0) -> str:
    ts = base + timedelta(minutes=offset_minutes)
    ms = _rng.randint(0, 999)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"


def create_user_message(session_id, parent_uuid, slug, cwd, timestamp, content):
    return {
        "type": "user",
        "uuid": _uuid(),
        "parentUuid": parent_uuid,
        "timestamp": timestamp,
        "sessionId": session_id,
        "cwd": cwd,
        "version": "2.0.76",
        "slug": slug,
        "gitBranch": "main",
        "userType": "external",
        "isSidechain": False,
        "message": {"role": "user", "content": content},
        "thinkingMetadata": {"level": "high", "disabled": False, "triggers": []},
        "todos": [],
    }


def create_assistant_message(session_id, parent_uuid, slug, cwd, timestamp, content, tool_use=False):
    msg_uuid = _uuid()
    content_blocks = [
        {
            "type": "thinking",
            "thinking": f"Analyzing the request: {content[:50]}...",
            "signature": "sig_" + uuid.UUID(int=random.Random(SEED + hash(msg_uuid)).getrandbits(128), version=4).hex[:20],
        }
    ]
    if tool_use:
        tool_name, tool_input = _rng.choice(TOOLS)
        content_blocks.append({
            "type": "tool_use",
            "id": "toolu_" + uuid.UUID(int=random.Random(SEED + hash(msg_uuid) + 1).getrandbits(128), version=4).hex[:20],
            "name": tool_name,
            "input": tool_input,
        })
    content_blocks.append({"type": "text", "text": f"Response to: {content}"})

    return {
        "type": "assistant",
        "uuid": msg_uuid,
        "parentUuid": parent_uuid,
        "timestamp": timestamp,
        "sessionId": session_id,
        "cwd": cwd,
        "version": "2.0.76",
        "slug": slug,
        "gitBranch": "main",
        "userType": "external",
        "isSidechain": False,
        "message": {
            "model": "claude-sonnet-4-20250514",
            "id": "msg_" + uuid.UUID(int=random.Random(SEED + hash(msg_uuid) + 2).getrandbits(128), version=4).hex[:20],
            "type": "message",
            "role": "assistant",
            "content": content_blocks,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": _rng.randint(100, 5000),
                "output_tokens": _rng.randint(50, 2000),
                "cache_creation_input_tokens": _rng.randint(0, 1000),
                "cache_read_input_tokens": _rng.randint(0, 500),
            },
        },
    }


def create_file_history_snapshot(message_id: str, files: List[str]):
    backups = {}
    for f in files:
        r = random.Random(SEED + hash(message_id + f))
        backups[f] = {
            "backupFileName": uuid.UUID(int=r.getrandbits(128), version=4).hex[:16] + "@v" + str(_rng.randint(1, 5)),
            "version": _rng.randint(1, 5),
            "backupTime": generate_timestamp(BASE_TIME),
        }
    return {
        "type": "file-history-snapshot",
        "messageId": message_id,
        "isSnapshotUpdate": False,
        "snapshot": {
            "messageId": message_id,
            "timestamp": generate_timestamp(BASE_TIME),
            "trackedFileBackups": backups,
        },
    }


def create_summary_message(leaf_uuid: str, summary: str):
    return {"type": "summary", "summary": summary, "leafUuid": leaf_uuid}


def generate_conversation(session_id, project_path, slug, base_time):
    messages = []
    parent_uuid = None
    for i in range(MESSAGES_PER_SESSION):
        ts = generate_timestamp(base_time, i * 5)
        user_msg = create_user_message(session_id, parent_uuid, slug, project_path, ts, _rng.choice(SAMPLE_PROMPTS))
        messages.append(user_msg)
        parent_uuid = user_msg["uuid"]

        assistant_msg = create_assistant_message(session_id, parent_uuid, slug, project_path,
                                                  generate_timestamp(base_time, i * 5 + 1),
                                                  user_msg["message"]["content"],
                                                  tool_use=(i % 3 == 0))
        messages.append(assistant_msg)
        parent_uuid = assistant_msg["uuid"]

        if i % 4 == 0:
            messages.append(create_file_history_snapshot(assistant_msg["uuid"], ["src/main.py", "tests/test_main.py"]))

    if messages:
        messages.append(create_summary_message(messages[-1].get("uuid", _uuid()),
                                                f"Conversation about {project_path.split('/')[-1]}"))
    return messages


def generate_agent_conversation(session_id, agent_id, project_path, slug, base_time):
    messages = []
    parent_uuid = None
    for i in range(3):
        ts = generate_timestamp(base_time, i * 2)
        user_msg = create_user_message(session_id, parent_uuid, slug, project_path, ts, "Explore the codebase structure")
        user_msg["agentId"] = agent_id
        messages.append(user_msg)
        parent_uuid = user_msg["uuid"]

        assistant_msg = create_assistant_message(session_id, parent_uuid, slug, project_path,
                                                  generate_timestamp(base_time, i * 2 + 1),
                                                  "Exploring codebase...", tool_use=True)
        assistant_msg["agentId"] = agent_id
        messages.append(assistant_msg)
        parent_uuid = assistant_msg["uuid"]
    return messages


def generate_plan_content(slug: str) -> str:
    return f"""# Implementation Plan: {slug}

## Problem Statement

This plan addresses the implementation of a new feature for the project.

## Current State Analysis

- Existing codebase needs refactoring
- Test coverage is at 60%
- Documentation needs updates

## Implementation Plan

### Phase 1: Setup
- [x] Initialize project structure
- [x] Set up dependencies
- [ ] Configure build system

### Phase 2: Core Implementation
- [ ] Implement main logic
- [ ] Add error handling
- [ ] Write unit tests

### Phase 3: Polish
- [ ] Add documentation
- [ ] Performance optimization
- [ ] Code review

## Notes

- Consider edge cases for empty inputs
- Ensure backward compatibility
"""


def generate_todo(session_id: str, agent_id: str) -> List[Dict[str, Any]]:
    statuses = ["pending", "in_progress", "completed"]
    count = _rng.randint(3, 6)
    return [
        {
            "content": f"Task {i + 1}: Implement feature {chr(65 + i)}",
            "status": _rng.choice(statuses),
            "activeForm": f"Working on task {i + 1}",
        }
        for i in range(count)
    ]


def generate_history_entry(project, session_id, base_time, offset_hours):
    prompts = [
        "Create a new component",
        "/init",
        "Fix the failing tests",
        "Add logging to the service",
        "/security-review",
    ]
    ts = base_time + timedelta(hours=offset_hours)
    return {
        "display": _rng.choice(prompts),
        "pastedContents": {},
        "timestamp": int(ts.timestamp() * 1000),
        "project": project,
        "sessionId": session_id,
    }


def generate_stats(num_days: int) -> Dict[str, Any]:
    base_date = BASE_TIME - timedelta(days=num_days)
    daily_activity = []
    for i in range(num_days):
        date = base_date + timedelta(days=i)
        daily_activity.append({
            "date": date.strftime("%Y-%m-%d"),
            "messageCount": _rng.randint(50, 500),
            "sessionCount": _rng.randint(1, 5),
            "toolCallCount": _rng.randint(20, 200),
        })
    return {
        "version": 1,
        "lastComputedDate": BASE_TIME.strftime("%Y-%m-%d"),
        "dailyActivity": daily_activity,
    }


def generate_claude_data():
    """Generate complete Claude Code test data."""
    print(f"Generating Claude test data in {CLAUDE_DIR}")

    if CLAUDE_DIR.exists():
        shutil.rmtree(CLAUDE_DIR)

    for d in [CLAUDE_DIR, CLAUDE_DIR / "projects", CLAUDE_DIR / "plans",
              CLAUDE_DIR / "todos", CLAUDE_DIR / "file-history"]:
        d.mkdir(parents=True, exist_ok=True)

    all_sessions = []
    for i, project_path in enumerate(PROJECT_PATHS[:NUM_PROJECTS]):
        project_dir = CLAUDE_DIR / "projects" / encode_project_path(project_path)
        project_dir.mkdir(parents=True, exist_ok=True)

        for j in range(SESSIONS_PER_PROJECT):
            session_id = _uuid()
            slug = generate_slug()
            session_time = BASE_TIME + timedelta(days=i, hours=j * 4)

            conversation = generate_conversation(session_id, project_path, slug, session_time)
            conv_file = project_dir / f"{session_id}.jsonl"
            with open(conv_file, "w") as f:
                for msg in conversation:
                    f.write(json.dumps(msg) + "\n")
            print(f"  {conv_file.name} ({len(conversation)} lines)")

            for k in range(AGENTS_PER_SESSION):
                agent_id = _short_id()
                agent_conv = generate_agent_conversation(session_id, agent_id, project_path, slug, session_time)
                agent_file = project_dir / f"agent-{agent_id}.jsonl"
                with open(agent_file, "w") as f:
                    for msg in agent_conv:
                        f.write(json.dumps(msg) + "\n")
                print(f"  {agent_file.name} ({len(agent_conv)} lines)")

            all_sessions.append((session_id, project_path, slug))

            fh_dir = CLAUDE_DIR / "file-history" / session_id
            fh_dir.mkdir(parents=True, exist_ok=True)
            for fi in range(2):
                r = random.Random(SEED + hash(session_id) + fi)
                fh_file = fh_dir / f"{uuid.UUID(int=r.getrandbits(128), version=4).hex[:16]}@v{fi + 1}"
                fh_file.write_text(f"# Backup content version {fi + 1}")

    # Plans
    print("  Plans:")
    for i in range(NUM_PLANS):
        slug = generate_slug()
        (CLAUDE_DIR / "plans" / f"{slug}.md").write_text(generate_plan_content(slug))
        print(f"    {slug}.md")

    # Todos
    print("  Todos:")
    for session_id, project_path, slug in all_sessions[:NUM_TODOS]:
        agent_id = _uuid()
        items = generate_todo(session_id, agent_id)
        todo_file = CLAUDE_DIR / "todos" / f"{session_id}-agent-{agent_id}.json"
        with open(todo_file, "w") as f:
            json.dump(items, f, indent=2)
        print(f"    {todo_file.name} ({len(items)} items)")

    # History
    history_file = CLAUDE_DIR / "history.jsonl"
    with open(history_file, "w") as f:
        for i in range(NUM_HISTORY_ENTRIES):
            session_id, project, slug = _rng.choice(all_sessions)
            f.write(json.dumps(generate_history_entry(project, session_id, BASE_TIME, i)) + "\n")
    print(f"  history.jsonl ({NUM_HISTORY_ENTRIES} entries)")

    # Stats
    stats = generate_stats(NUM_STATS_DAYS)
    with open(CLAUDE_DIR / "stats-cache.json", "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  stats-cache.json ({NUM_STATS_DAYS} days)")

    # CLAUDE.md
    (CLAUDE_DIR / "CLAUDE.md").write_text(
        "# Test Claude Configuration\n\n"
        "This is a test Claude Code data directory for extension development.\n\n"
        "## Project Guidelines\n\n"
        "- Follow TDD practices\n"
        "- Document all public APIs\n"
        "- Maintain 80% test coverage\n"
    )
    print("  CLAUDE.md")


# ─── Copilot generators ──────────────────────────────────────────────

COPILOT_DIR = Path("test/data_copilot")


def generate_copilot_data():
    """Generate Copilot CLI test data with hardcoded deterministic values."""
    print(f"\nGenerating Copilot test data in {COPILOT_DIR}")

    if COPILOT_DIR.exists():
        shutil.rmtree(COPILOT_DIR)

    # Session IDs (deterministic, human-readable)
    S1 = "aaaa1111-0000-0000-0000-000000000001"
    S2 = "bbbb2222-0000-0000-0000-000000000002"
    S3 = "cccc3333-0000-0000-0000-000000000003"
    S4 = "dddd4444-0000-0000-0000-000000000004"

    # ── Session 1: Full-featured session (30 events) ──
    s1_dir = COPILOT_DIR / "session-state" / S1
    s1_dir.mkdir(parents=True)
    (s1_dir / "workspace.yaml").write_text(
        f"id: {S1}\ncwd: /Users/testuser/project-alpha\nrepository: testuser/project-alpha\nbranch: main\n"
    )
    s1_events = [
        {"type": "session.start", "id": "evt-aaaa-0001", "timestamp": "2026-01-15T10:00:00.000Z", "parentId": None,
         "data": {"sessionId": S1, "copilotVersion": "0.0.400",
                  "context": {"cwd": "/Users/testuser/project-alpha", "gitRoot": "/Users/testuser/project-alpha",
                              "branch": "main", "repository": "testuser/project-alpha"}}},
        {"type": "session.info", "id": "evt-aaaa-0002", "timestamp": "2026-01-15T10:00:01.000Z", "parentId": "evt-aaaa-0001",
         "data": {"infoType": "authentication", "message": "Logged in as testuser"}},
        {"type": "user.message", "id": "evt-aaaa-0003", "timestamp": "2026-01-15T10:00:02.000Z", "parentId": "evt-aaaa-0002",
         "data": {"content": "Create a hello world function"}},
        {"type": "assistant.turn_start", "id": "evt-aaaa-0004", "timestamp": "2026-01-15T10:00:03.000Z", "parentId": "evt-aaaa-0003",
         "data": {"turnId": "turn-1"}},
        {"type": "assistant.message", "id": "evt-aaaa-0005", "timestamp": "2026-01-15T10:00:04.000Z", "parentId": "evt-aaaa-0004",
         "data": {"messageId": "msg-001", "content": "I'll create a hello world function for you.",
                  "toolRequests": [{"toolCallId": "tc-001", "name": "edit",
                                    "arguments": {"file": "hello.py", "content": "def hello():\n    return 'Hello, World!'"}}]}},
        {"type": "tool.execution_start", "id": "evt-aaaa-0006", "timestamp": "2026-01-15T10:00:05.000Z", "parentId": "evt-aaaa-0005",
         "data": {"toolCallId": "tc-001", "toolName": "edit",
                  "arguments": {"file": "hello.py", "content": "def hello():\n    return 'Hello, World!'"}}},
        {"type": "tool.execution_complete", "id": "evt-aaaa-0007", "timestamp": "2026-01-15T10:00:06.000Z", "parentId": "evt-aaaa-0006",
         "data": {"toolCallId": "tc-001", "success": True, "result": {"content": "File hello.py written successfully"}}},
        {"type": "assistant.message", "id": "evt-aaaa-0008", "timestamp": "2026-01-15T10:00:07.000Z", "parentId": "evt-aaaa-0007",
         "data": {"messageId": "msg-002", "content": "I've created the hello world function in hello.py."}},
        {"type": "assistant.turn_end", "id": "evt-aaaa-0009", "timestamp": "2026-01-15T10:00:08.000Z", "parentId": "evt-aaaa-0008",
         "data": {"turnId": "turn-1"}},
        {"type": "session.truncation", "id": "evt-aaaa-0010", "timestamp": "2026-01-15T10:00:09.000Z", "parentId": "evt-aaaa-0009",
         "data": {"tokenLimit": 128000, "preTruncationTokensInMessages": 95000, "postTruncationTokensInMessages": 80000}},
        # Turn 2
        {"type": "user.message", "id": "evt-aaaa-0011", "timestamp": "2026-01-15T10:01:00.000Z", "parentId": "evt-aaaa-0010",
         "data": {"content": "Now add unit tests for that function"}},
        {"type": "assistant.turn_start", "id": "evt-aaaa-0012", "timestamp": "2026-01-15T10:01:01.000Z", "parentId": "evt-aaaa-0011",
         "data": {"turnId": "turn-2"}},
        {"type": "assistant.reasoning", "id": "evt-aaaa-0013", "timestamp": "2026-01-15T10:01:02.000Z", "parentId": "evt-aaaa-0012",
         "data": {"reasoningId": "r-001", "content": "I need to write pytest tests for the hello function."}},
        {"type": "assistant.message", "id": "evt-aaaa-0014", "timestamp": "2026-01-15T10:01:03.000Z", "parentId": "evt-aaaa-0013",
         "data": {"messageId": "msg-003", "content": "I'll write unit tests using pytest.",
                  "toolRequests": [{"toolCallId": "tc-002", "name": "edit",
                                    "arguments": {"file": "test_hello.py",
                                                  "content": "from hello import hello\n\ndef test_hello():\n    assert hello() == 'Hello, World!'"}}]}},
        {"type": "tool.execution_start", "id": "evt-aaaa-0015", "timestamp": "2026-01-15T10:01:04.000Z", "parentId": "evt-aaaa-0014",
         "data": {"toolCallId": "tc-002", "toolName": "edit", "arguments": {"file": "test_hello.py"}}},
        {"type": "tool.execution_complete", "id": "evt-aaaa-0016", "timestamp": "2026-01-15T10:01:05.000Z", "parentId": "evt-aaaa-0015",
         "data": {"toolCallId": "tc-002", "success": True, "result": {"content": "File test_hello.py written successfully"}}},
        {"type": "assistant.message", "id": "evt-aaaa-0017", "timestamp": "2026-01-15T10:01:06.000Z", "parentId": "evt-aaaa-0016",
         "data": {"messageId": "msg-004", "content": "Tests created. Let me run them.",
                  "toolRequests": [{"toolCallId": "tc-003", "name": "bash", "arguments": {"command": "pytest test_hello.py"}}]}},
        {"type": "assistant.turn_end", "id": "evt-aaaa-0018", "timestamp": "2026-01-15T10:01:07.000Z", "parentId": "evt-aaaa-0017",
         "data": {"turnId": "turn-2"}},
        {"type": "session.model_change", "id": "evt-aaaa-0019", "timestamp": "2026-01-15T10:02:00.000Z", "parentId": "evt-aaaa-0018",
         "data": {"newModel": "claude-sonnet-4"}},
        # Turn 3
        {"type": "user.message", "id": "evt-aaaa-0020", "timestamp": "2026-01-15T10:02:01.000Z", "parentId": "evt-aaaa-0019",
         "data": {"content": "Add error handling to the function"}},
        {"type": "assistant.turn_start", "id": "evt-aaaa-0021", "timestamp": "2026-01-15T10:02:02.000Z", "parentId": "evt-aaaa-0020",
         "data": {"turnId": "turn-3"}},
        {"type": "assistant.message", "id": "evt-aaaa-0022", "timestamp": "2026-01-15T10:02:03.000Z", "parentId": "evt-aaaa-0021",
         "data": {"messageId": "msg-005", "content": "I'll add error handling to the hello function.",
                  "toolRequests": [{"toolCallId": "tc-004", "name": "edit", "arguments": {"file": "hello.py"}}]}},
        {"type": "tool.execution_start", "id": "evt-aaaa-0023", "timestamp": "2026-01-15T10:02:04.000Z", "parentId": "evt-aaaa-0022",
         "data": {"toolCallId": "tc-004", "toolName": "edit", "arguments": {"file": "hello.py"}}},
        {"type": "tool.execution_complete", "id": "evt-aaaa-0024", "timestamp": "2026-01-15T10:02:05.000Z", "parentId": "evt-aaaa-0023",
         "data": {"toolCallId": "tc-004", "success": True, "result": {"content": "File hello.py updated"}}},
        {"type": "session.error", "id": "evt-aaaa-0025", "timestamp": "2026-01-15T10:02:06.000Z", "parentId": "evt-aaaa-0024",
         "data": {"errorType": "tool_error", "message": "Syntax error in generated code"}},
        {"type": "assistant.message", "id": "evt-aaaa-0026", "timestamp": "2026-01-15T10:02:07.000Z", "parentId": "evt-aaaa-0025",
         "data": {"messageId": "msg-006", "content": "I notice there was a syntax error. Let me fix it."}},
        {"type": "assistant.turn_end", "id": "evt-aaaa-0027", "timestamp": "2026-01-15T10:02:08.000Z", "parentId": "evt-aaaa-0026",
         "data": {"turnId": "turn-3"}},
        {"type": "session.compaction_start", "id": "evt-aaaa-0028", "timestamp": "2026-01-15T10:03:00.000Z", "parentId": "evt-aaaa-0027",
         "data": {}},
        {"type": "session.compaction_complete", "id": "evt-aaaa-0029", "timestamp": "2026-01-15T10:03:01.000Z", "parentId": "evt-aaaa-0028",
         "data": {}},
        {"type": "abort", "id": "evt-aaaa-0030", "timestamp": "2026-01-15T10:03:02.000Z", "parentId": "evt-aaaa-0029",
         "data": {"reason": "user_cancelled"}},
    ]
    with open(s1_dir / "events.jsonl", "w") as f:
        for evt in s1_events:
            f.write(json.dumps(evt) + "\n")
    print(f"  session {S1[:8]}... ({len(s1_events)} events)")

    # Checkpoints for session 1
    cp_dir = s1_dir / "checkpoints"
    cp_dir.mkdir()
    (cp_dir / "index.md").write_text("# Checkpoints Index\n\n- [001-initial-setup](001-initial-setup.md) - Initial project setup checkpoint\n")
    (cp_dir / "001-initial-setup.md").write_text(
        "# Initial Setup Checkpoint\n"
        "- [x] Create project structure\n"
        "- [x] Add hello world function\n"
        "- [ ] Write unit tests\n"
        "- [ ] Configure CI pipeline\n"
    )
    print("  checkpoints (1 checkpoint, 4 items)")

    # ── Session 2: API refactoring (10 events) ──
    s2_dir = COPILOT_DIR / "session-state" / S2
    s2_dir.mkdir(parents=True)
    (s2_dir / "workspace.yaml").write_text(
        f"id: {S2}\ncwd: /Users/testuser/project-beta\nrepository: testuser/project-beta\nbranch: feature/api\n"
    )
    s2_events = [
        {"type": "session.start", "id": "evt-bbbb-0001", "timestamp": "2026-01-16T14:00:00.000Z", "parentId": None,
         "data": {"sessionId": S2, "copilotVersion": "0.0.401",
                  "context": {"cwd": "/Users/testuser/project-beta", "gitRoot": "/Users/testuser/project-beta",
                              "branch": "feature/api", "repository": "testuser/project-beta"}}},
        {"type": "session.info", "id": "evt-bbbb-0002", "timestamp": "2026-01-16T14:00:01.000Z", "parentId": "evt-bbbb-0001",
         "data": {"infoType": "context", "message": "Working on API refactoring"}},
        {"type": "user.message", "id": "evt-bbbb-0003", "timestamp": "2026-01-16T14:00:02.000Z", "parentId": "evt-bbbb-0002",
         "data": {"content": "Refactor the REST endpoints for v2"}},
        {"type": "assistant.message", "id": "evt-bbbb-0004", "timestamp": "2026-01-16T14:00:03.000Z", "parentId": "evt-bbbb-0003",
         "data": {"messageId": "msg-101", "content": "I'll refactor the REST endpoints.",
                  "toolRequests": [{"toolCallId": "tc-101", "name": "grep", "arguments": {"pattern": "@app.route"}}]}},
        {"type": "tool.execution_start", "id": "evt-bbbb-0005", "timestamp": "2026-01-16T14:00:04.000Z", "parentId": "evt-bbbb-0004",
         "data": {"toolCallId": "tc-101", "toolName": "grep", "arguments": {"pattern": "@app.route"}}},
        {"type": "tool.execution_complete", "id": "evt-bbbb-0006", "timestamp": "2026-01-16T14:00:05.000Z", "parentId": "evt-bbbb-0005",
         "data": {"toolCallId": "tc-101", "success": True, "result": {"content": "Found 5 route definitions"}}},
        {"type": "assistant.message", "id": "evt-bbbb-0007", "timestamp": "2026-01-16T14:00:06.000Z", "parentId": "evt-bbbb-0006",
         "data": {"messageId": "msg-102", "content": "Found 5 routes. I'll update them to v2 format."}},
        {"type": "user.message", "id": "evt-bbbb-0008", "timestamp": "2026-01-16T14:01:00.000Z", "parentId": "evt-bbbb-0007",
         "data": {"content": "Also add authentication middleware"}},
        {"type": "assistant.message", "id": "evt-bbbb-0009", "timestamp": "2026-01-16T14:01:01.000Z", "parentId": "evt-bbbb-0008",
         "data": {"messageId": "msg-103", "content": "I'll add JWT authentication middleware to all v2 endpoints."}},
        {"type": "session.resume", "id": "evt-bbbb-0010", "timestamp": "2026-01-16T15:00:00.000Z", "parentId": "evt-bbbb-0009",
         "data": {"resumeTime": "2026-01-16T15:00:00.000Z", "eventCount": 9}},
    ]
    with open(s2_dir / "events.jsonl", "w") as f:
        for evt in s2_events:
            f.write(json.dumps(evt) + "\n")
    (s2_dir / "plan.md").write_text(
        "# API Refactoring Plan\n\n"
        "## Problem\n"
        "Refactor REST endpoints for v2 API.\n\n"
        "## Tasks\n"
        "- [x] Design new endpoint structure\n"
        "- [ ] Implement authentication middleware\n"
        "- [ ] Add rate limiting\n"
    )
    print(f"  session {S2[:8]}... ({len(s2_events)} events + plan)")

    # ── Session 3: Code search (8 events) ──
    s3_dir = COPILOT_DIR / "session-state" / S3
    s3_dir.mkdir(parents=True)
    (s3_dir / "workspace.yaml").write_text(
        f"id: {S3}\ncwd: /Users/testuser/project-alpha\nrepository: testuser/project-alpha\nbranch: feature/tests\n"
    )
    s3_events = [
        {"type": "session.start", "id": "evt-cccc-0001", "timestamp": "2026-01-17T09:00:00.000Z", "parentId": None,
         "data": {"sessionId": S3, "copilotVersion": "0.0.400",
                  "context": {"cwd": "/Users/testuser/project-alpha", "gitRoot": "/Users/testuser/project-alpha",
                              "branch": "develop", "repository": "testuser/project-alpha"}}},
        {"type": "user.message", "id": "evt-cccc-0002", "timestamp": "2026-01-17T09:00:01.000Z", "parentId": "evt-cccc-0001",
         "data": {"content": "List all TODO comments in the codebase"}},
        {"type": "assistant.turn_start", "id": "evt-cccc-0003", "timestamp": "2026-01-17T09:00:02.000Z", "parentId": "evt-cccc-0002",
         "data": {"turnId": "turn-1"}},
        {"type": "assistant.message", "id": "evt-cccc-0004", "timestamp": "2026-01-17T09:00:03.000Z", "parentId": "evt-cccc-0003",
         "data": {"messageId": "msg-201", "content": "I'll search for TODO comments.",
                  "toolRequests": [{"toolCallId": "tc-201", "name": "grep", "arguments": {"pattern": "TODO", "path": "."}}]}},
        {"type": "tool.execution_start", "id": "evt-cccc-0005", "timestamp": "2026-01-17T09:00:04.000Z", "parentId": "evt-cccc-0004",
         "data": {"toolCallId": "tc-201", "toolName": "grep", "arguments": {"pattern": "TODO", "path": "."}}},
        {"type": "tool.execution_complete", "id": "evt-cccc-0006", "timestamp": "2026-01-17T09:00:05.000Z", "parentId": "evt-cccc-0005",
         "data": {"toolCallId": "tc-201", "success": True, "result": {"content": "hello.py:3: # TODO: add parameter support"}}},
        {"type": "assistant.turn_end", "id": "evt-cccc-0007", "timestamp": "2026-01-17T09:00:06.000Z", "parentId": "evt-cccc-0006",
         "data": {"turnId": "turn-1"}},
        {"type": "abort", "id": "evt-cccc-0008", "timestamp": "2026-01-17T09:00:07.000Z", "parentId": "evt-cccc-0007",
         "data": {"reason": "user_cancelled"}},
    ]
    with open(s3_dir / "events.jsonl", "w") as f:
        for evt in s3_events:
            f.write(json.dumps(evt) + "\n")
    print(f"  session {S3[:8]}... ({len(s3_events)} events)")

    # ── Session 4: Flat JSONL (no directory, 5 events) ──
    s4_events = [
        {"type": "session.start", "id": "evt-dddd-0001", "timestamp": "2026-01-18T08:00:00.000Z", "parentId": None,
         "data": {"sessionId": S4, "copilotVersion": "0.0.402",
                  "context": {"cwd": "/Users/testuser/quick-fix"}}},
        {"type": "user.message", "id": "evt-dddd-0002", "timestamp": "2026-01-18T08:00:01.000Z", "parentId": "evt-dddd-0001",
         "data": {"content": "Fix the typo in README"}},
        {"type": "assistant.turn_start", "id": "evt-dddd-0003", "timestamp": "2026-01-18T08:00:02.000Z", "parentId": "evt-dddd-0002",
         "data": {"turnId": "turn-1"}},
        {"type": "assistant.message", "id": "evt-dddd-0004", "timestamp": "2026-01-18T08:00:03.000Z", "parentId": "evt-dddd-0003",
         "data": {"messageId": "msg-301", "content": "I'll fix the typo in the README file."}},
        {"type": "assistant.turn_end", "id": "evt-dddd-0005", "timestamp": "2026-01-18T08:00:04.000Z", "parentId": "evt-dddd-0004",
         "data": {"turnId": "turn-1"}},
    ]
    s4_file = COPILOT_DIR / "session-state" / f"{S4}.jsonl"
    s4_file.parent.mkdir(parents=True, exist_ok=True)
    with open(s4_file, "w") as f:
        for evt in s4_events:
            f.write(json.dumps(evt) + "\n")
    print(f"  session {S4[:8]}... ({len(s4_events)} events, flat file)")

    # ── Command history ──
    history = {
        "commandHistory": [
            "Create a hello world function",
            "Now add tests",
            "Run the tests",
            "Refactor REST endpoints for v2 API",
            "Fix the failing test",
        ]
    }
    with open(COPILOT_DIR / "command-history-state.json", "w") as f:
        json.dump(history, f, indent=2)
    print(f"  command-history-state.json ({len(history['commandHistory'])} entries)")

    # ── Config ──
    config = {
        "model": "claude-sonnet-4",
        "theme": "auto",
        "last_logged_in_user": {"host": "https://github.com", "login": "testuser"},
    }
    with open(COPILOT_DIR / "config.json", "w") as f:
        json.dump(config, f, indent=2)
    print("  config.json")


# ─── main ─────────────────────────────────────────────────────────────

def main():
    # Reset global RNG state
    global _uuid_counter
    _uuid_counter = 0
    _rng.seed(SEED)

    generate_claude_data()
    generate_copilot_data()

    print("\n✓ All test data generated successfully.")
    print(f"  Claude: {CLAUDE_DIR}")
    print(f"  Copilot: {COPILOT_DIR}")


if __name__ == "__main__":
    main()
