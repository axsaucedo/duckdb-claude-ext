#!/usr/bin/env python3
"""
Generate synthetic Claude Code test data for DuckDB extension testing.
Creates a mock ~/.claude directory structure with realistic data.
"""

import os
import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Configuration
OUTPUT_DIR = Path("test/data")
NUM_PROJECTS = 3
SESSIONS_PER_PROJECT = 2
MESSAGES_PER_SESSION = 10
AGENTS_PER_SESSION = 1
NUM_PLANS = 4
NUM_TODOS = 5
NUM_HISTORY_ENTRIES = 20
NUM_STATS_DAYS = 7

# Slugs for plans
ADJECTIVES = ["keen", "binary", "bright", "cozy", "swift", "quiet"]
VERBS = ["juggling", "prancing", "exploring", "napping", "coding", "testing"]
NOUNS = ["origami", "shore", "wolf", "hippo", "stream", "dolphin"]

# Sample project paths
PROJECT_PATHS = [
    "/Users/testuser/project-alpha",
    "/Users/testuser/project-beta",
    "/Users/testuser/project-gamma",
]

# Sample tool names and their usage
TOOLS = [
    ("Bash", {"command": "ls -la"}),
    ("Read", {"file_path": "src/main.py"}),
    ("Write", {"file_path": "output.txt", "content": "test content"}),
    ("Edit", {"file_path": "config.json", "old_string": "old", "new_string": "new"}),
    ("Glob", {"pattern": "**/*.py"}),
    ("TodoWrite", {"todos": "- [ ] Task 1\n- [x] Task 2"}),
]


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_short_id() -> str:
    return "a" + uuid.uuid4().hex[:7]


def generate_slug() -> str:
    return f"{random.choice(ADJECTIVES)}-{random.choice(VERBS)}-{random.choice(NOUNS)}"


def generate_timestamp(base: datetime = None, offset_minutes: int = 0) -> str:
    if base is None:
        base = datetime.now()
    ts = base + timedelta(minutes=offset_minutes)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{random.randint(0, 999):03d}Z"


def encode_project_path(path: str) -> str:
    """Convert project path to folder name format."""
    return path.replace("/", "-")


def create_user_message(
    session_id: str,
    parent_uuid: str,
    slug: str,
    cwd: str,
    timestamp: str,
    content: str,
) -> Dict[str, Any]:
    return {
        "type": "user",
        "uuid": generate_uuid(),
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
            "role": "user",
            "content": content,
        },
        "thinkingMetadata": {
            "level": "high",
            "disabled": False,
            "triggers": [],
        },
        "todos": [],
    }


def create_assistant_message(
    session_id: str,
    parent_uuid: str,
    slug: str,
    cwd: str,
    timestamp: str,
    content: str,
    tool_use: bool = False,
) -> Dict[str, Any]:
    msg_uuid = generate_uuid()
    content_blocks = []

    # Add thinking block
    content_blocks.append({
        "type": "thinking",
        "thinking": f"Analyzing the request: {content[:50]}...",
        "signature": "sig_" + uuid.uuid4().hex[:20],
    })

    # Add tool use if requested
    if tool_use:
        tool_name, tool_input = random.choice(TOOLS)
        content_blocks.append({
            "type": "tool_use",
            "id": "toolu_" + uuid.uuid4().hex[:20],
            "name": tool_name,
            "input": tool_input,
        })

    # Add text response
    content_blocks.append({
        "type": "text",
        "text": f"Response to: {content}",
    })

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
            "id": "msg_" + uuid.uuid4().hex[:20],
            "type": "message",
            "role": "assistant",
            "content": content_blocks,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": random.randint(100, 5000),
                "output_tokens": random.randint(50, 2000),
                "cache_creation_input_tokens": random.randint(0, 1000),
                "cache_read_input_tokens": random.randint(0, 500),
            },
        },
    }


def create_file_history_snapshot(message_id: str, files: List[str]) -> Dict[str, Any]:
    backups = {}
    for f in files:
        backups[f] = {
            "backupFileName": uuid.uuid4().hex[:16] + "@v" + str(random.randint(1, 5)),
            "version": random.randint(1, 5),
            "backupTime": generate_timestamp(),
        }

    return {
        "type": "file-history-snapshot",
        "messageId": message_id,
        "isSnapshotUpdate": False,
        "snapshot": {
            "messageId": message_id,
            "timestamp": generate_timestamp(),
            "trackedFileBackups": backups,
        },
    }


def create_summary_message(leaf_uuid: str, summary: str) -> Dict[str, Any]:
    return {
        "type": "summary",
        "summary": summary,
        "leafUuid": leaf_uuid,
    }


def generate_conversation(
    session_id: str,
    project_path: str,
    slug: str,
    base_time: datetime,
) -> List[Dict[str, Any]]:
    """Generate a full conversation with multiple message pairs."""
    messages = []
    parent_uuid = None

    sample_prompts = [
        "Create a new Python project with a basic structure",
        "Add unit tests for the main module",
        "Fix the bug in the authentication handler",
        "Refactor the database connection logic",
        "Add error handling to the API endpoints",
        "Document the public functions",
        "Optimize the search algorithm",
        "Set up CI/CD pipeline",
    ]

    for i in range(MESSAGES_PER_SESSION):
        timestamp = generate_timestamp(base_time, i * 5)

        # User message
        user_msg = create_user_message(
            session_id=session_id,
            parent_uuid=parent_uuid,
            slug=slug,
            cwd=project_path,
            timestamp=timestamp,
            content=random.choice(sample_prompts),
        )
        messages.append(user_msg)
        parent_uuid = user_msg["uuid"]

        # Assistant response
        assistant_msg = create_assistant_message(
            session_id=session_id,
            parent_uuid=parent_uuid,
            slug=slug,
            cwd=project_path,
            timestamp=generate_timestamp(base_time, i * 5 + 1),
            content=user_msg["message"]["content"],
            tool_use=(i % 3 == 0),  # Add tool use every 3rd message
        )
        messages.append(assistant_msg)
        parent_uuid = assistant_msg["uuid"]

        # Occasionally add file history snapshot
        if i % 4 == 0:
            snapshot = create_file_history_snapshot(
                assistant_msg["uuid"],
                ["src/main.py", "tests/test_main.py"],
            )
            messages.append(snapshot)

    # Add summary at end
    if messages:
        summary = create_summary_message(
            messages[-1].get("uuid", generate_uuid()),
            f"Conversation about {project_path.split('/')[-1]}",
        )
        messages.append(summary)

    return messages


def generate_agent_conversation(
    session_id: str,
    agent_id: str,
    project_path: str,
    slug: str,
    base_time: datetime,
) -> List[Dict[str, Any]]:
    """Generate a sub-agent conversation."""
    messages = []
    parent_uuid = None

    for i in range(3):  # Shorter agent conversations
        timestamp = generate_timestamp(base_time, i * 2)

        user_msg = create_user_message(
            session_id=session_id,
            parent_uuid=parent_uuid,
            slug=slug,
            cwd=project_path,
            timestamp=timestamp,
            content="Explore the codebase structure",
        )
        user_msg["agentId"] = agent_id
        messages.append(user_msg)
        parent_uuid = user_msg["uuid"]

        assistant_msg = create_assistant_message(
            session_id=session_id,
            parent_uuid=parent_uuid,
            slug=slug,
            cwd=project_path,
            timestamp=generate_timestamp(base_time, i * 2 + 1),
            content="Exploring codebase...",
            tool_use=True,
        )
        assistant_msg["agentId"] = agent_id
        messages.append(assistant_msg)
        parent_uuid = assistant_msg["uuid"]

    return messages


def generate_plan(slug: str) -> str:
    """Generate a markdown plan file."""
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
    """Generate todo items."""
    statuses = ["pending", "in_progress", "completed"]
    return [
        {
            "content": f"Task {i + 1}: Implement feature {chr(65 + i)}",
            "status": random.choice(statuses),
            "activeForm": f"Working on task {i + 1}",
        }
        for i in range(random.randint(3, 6))
    ]


def generate_history_entry(
    project: str,
    session_id: str,
    base_time: datetime,
    offset_hours: int,
) -> Dict[str, Any]:
    """Generate a history entry."""
    prompts = [
        "Create a new component",
        "/init",
        "Fix the failing tests",
        "Add logging to the service",
        "/security-review",
    ]

    ts = base_time + timedelta(hours=offset_hours)
    return {
        "display": random.choice(prompts),
        "pastedContents": {},
        "timestamp": int(ts.timestamp() * 1000),
        "project": project,
        "sessionId": session_id,
    }


def generate_stats(num_days: int) -> Dict[str, Any]:
    """Generate stats cache."""
    base_date = datetime.now() - timedelta(days=num_days)

    daily_activity = []
    for i in range(num_days):
        date = base_date + timedelta(days=i)
        daily_activity.append({
            "date": date.strftime("%Y-%m-%d"),
            "messageCount": random.randint(50, 500),
            "sessionCount": random.randint(1, 5),
            "toolCallCount": random.randint(20, 200),
        })

    return {
        "version": 1,
        "lastComputedDate": datetime.now().strftime("%Y-%m-%d"),
        "dailyActivity": daily_activity,
    }


def main():
    """Generate complete test data structure."""
    print(f"Generating test data in {OUTPUT_DIR}")

    # Create directory structure
    dirs = [
        OUTPUT_DIR,
        OUTPUT_DIR / "projects",
        OUTPUT_DIR / "plans",
        OUTPUT_DIR / "todos",
        OUTPUT_DIR / "file-history",
        OUTPUT_DIR / "debug",
        OUTPUT_DIR / "session-env",
        OUTPUT_DIR / "telemetry",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    base_time = datetime.now() - timedelta(days=7)

    # Generate projects and conversations
    all_sessions = []
    for i, project_path in enumerate(PROJECT_PATHS[:NUM_PROJECTS]):
        project_dir = OUTPUT_DIR / "projects" / encode_project_path(project_path)
        project_dir.mkdir(parents=True, exist_ok=True)

        for j in range(SESSIONS_PER_PROJECT):
            session_id = generate_uuid()
            slug = generate_slug()
            session_time = base_time + timedelta(days=i, hours=j * 4)

            # Main conversation
            conversation = generate_conversation(
                session_id, project_path, slug, session_time
            )
            conv_file = project_dir / f"{session_id}.jsonl"
            with open(conv_file, "w") as f:
                for msg in conversation:
                    f.write(json.dumps(msg) + "\n")

            print(f"  Created {conv_file.name} ({len(conversation)} messages)")

            # Sub-agent conversations
            for k in range(AGENTS_PER_SESSION):
                agent_id = generate_short_id()
                agent_conv = generate_agent_conversation(
                    session_id, agent_id, project_path, slug, session_time
                )
                agent_file = project_dir / f"agent-{agent_id}.jsonl"
                with open(agent_file, "w") as f:
                    for msg in agent_conv:
                        f.write(json.dumps(msg) + "\n")

                print(f"  Created {agent_file.name} ({len(agent_conv)} messages)")

            all_sessions.append((session_id, project_path, slug))

            # Create file-history entries
            fh_dir = OUTPUT_DIR / "file-history" / session_id
            fh_dir.mkdir(parents=True, exist_ok=True)
            for fi in range(2):
                fh_file = fh_dir / f"{uuid.uuid4().hex[:16]}@v{fi + 1}"
                fh_file.write_text(f"# Backup content version {fi + 1}")

    # Generate plans
    print("\nGenerating plans...")
    for i in range(NUM_PLANS):
        slug = generate_slug()
        plan_content = generate_plan(slug)
        plan_file = OUTPUT_DIR / "plans" / f"{slug}.md"
        plan_file.write_text(plan_content)
        print(f"  Created {plan_file.name}")

    # Generate todos
    print("\nGenerating todos...")
    for session_id, project_path, slug in all_sessions[:NUM_TODOS]:
        agent_id = generate_uuid()
        todo_items = generate_todo(session_id, agent_id)
        todo_file = OUTPUT_DIR / "todos" / f"{session_id}-agent-{agent_id}.json"
        with open(todo_file, "w") as f:
            json.dump(todo_items, f, indent=2)
        print(f"  Created {todo_file.name}")

    # Generate history
    print("\nGenerating history...")
    history_file = OUTPUT_DIR / "history.jsonl"
    with open(history_file, "w") as f:
        for i in range(NUM_HISTORY_ENTRIES):
            if all_sessions:
                session_id, project, slug = random.choice(all_sessions)
            else:
                session_id, project = generate_uuid(), PROJECT_PATHS[0]
            entry = generate_history_entry(project, session_id, base_time, i)
            f.write(json.dumps(entry) + "\n")
    print(f"  Created {history_file.name} ({NUM_HISTORY_ENTRIES} entries)")

    # Generate stats
    print("\nGenerating stats...")
    stats = generate_stats(NUM_STATS_DAYS)
    stats_file = OUTPUT_DIR / "stats-cache.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  Created {stats_file.name}")

    # Generate CLAUDE.md
    claude_md = OUTPUT_DIR / "CLAUDE.md"
    claude_md.write_text("""# Test Claude Configuration

This is a test Claude Code data directory for extension development.

## Project Guidelines

- Follow TDD practices
- Document all public APIs
- Maintain 80% test coverage
""")
    print(f"\n  Created {claude_md.name}")

    print(f"\nTest data generation complete!")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
