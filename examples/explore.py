import marimo

__generated_with = "0.19.9"
app = marimo.App(width="medium", app_title="agent_data Explorer")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
    # agent_data Explorer

    Interactive exploration of Claude Code session data using the `agent_data` DuckDB extension.

    This notebook connects to test data by default. To explore your own data,
    set `DATA_PATH` to your Claude data directory (e.g., `~/.claude`).
    """
    )
    return (mo,)


@app.cell
def _(mo):
    import os

    # Configuration: change this to explore your own data
    DATA_PATH = os.environ.get("AGENT_DATA_PATH", "test/data")
    EXTENSION_PATH = os.environ.get(
        "AGENT_DATA_EXT", "build/debug/agent_data.duckdb_extension"
    )

    mo.md(
        f"""
    **Data source:** `{DATA_PATH}`
    **Extension:** `{EXTENSION_PATH}`
    """
    )
    return DATA_PATH, EXTENSION_PATH, os


@app.cell
def _(DATA_PATH, EXTENSION_PATH):
    import duckdb

    con = duckdb.connect(config={"allow_unsigned_extensions": "true"})
    con.execute(f"LOAD '{EXTENSION_PATH}'")

    # Load all tables
    conversations = con.execute(
        f"SELECT * FROM read_conversations(path='{DATA_PATH}')"
    ).df()
    plans = con.execute(f"SELECT * FROM read_plans(path='{DATA_PATH}')").df()
    todos = con.execute(f"SELECT * FROM read_todos(path='{DATA_PATH}')").df()
    history = con.execute(f"SELECT * FROM read_history(path='{DATA_PATH}')").df()
    stats = con.execute(f"SELECT * FROM read_stats(path='{DATA_PATH}')").df()
    return con, conversations, duckdb, history, plans, stats, todos


@app.cell
def _(conversations, history, mo, plans, stats, todos):
    mo.md(
        f"""
    ## Overview

    | Table | Rows |
    |-------|------|
    | Conversations | {len(conversations)} |
    | Plans | {len(plans)} |
    | Todos | {len(todos)} |
    | History | {len(history)} |
    | Stats | {len(stats)} |
    """
    )
    return


@app.cell
def _(conversations, mo):
    mo.md("## Conversations by Project and Type")
    return


@app.cell
def _(conversations, mo):
    project_summary = (
        conversations.groupby(["project_path", "message_type"])
        .size()
        .reset_index(name="count")
        .sort_values(["project_path", "count"], ascending=[True, False])
    )
    mo.ui.table(project_summary, label="Messages by Project and Type")
    return (project_summary,)


@app.cell
def _(conversations, mo):
    mo.md("## Session Explorer")
    return


@app.cell
def _(conversations, mo):
    sessions = conversations[["session_id", "project_path", "is_agent", "file_name"]].drop_duplicates()
    session_selector = mo.ui.dropdown(
        options={s: s for s in sessions["session_id"].unique()},
        label="Select Session",
    )
    session_selector
    return session_selector, sessions


@app.cell
def _(conversations, mo, session_selector):
    if session_selector.value:
        session_msgs = conversations[
            conversations["session_id"] == session_selector.value
        ][
            [
                "line_number",
                "message_type",
                "message_role",
                "timestamp",
                "model",
                "tool_name",
                "slug",
            ]
        ].sort_values("line_number")
        mo.ui.table(session_msgs, label=f"Messages in session {session_selector.value}")
    else:
        mo.md("*Select a session above*")
    return (session_msgs,)


@app.cell
def _(mo):
    mo.md("## Todos Status")
    return


@app.cell
def _(mo, todos):
    todo_status = (
        todos.groupby("status").size().reset_index(name="count").sort_values("count", ascending=False)
    )
    mo.ui.table(todo_status, label="Todo Status Distribution")
    return (todo_status,)


@app.cell
def _(mo, todos):
    mo.ui.table(
        todos[["session_id", "agent_id", "content", "status", "active_form"]],
        label="All Todos",
    )
    return


@app.cell
def _(mo):
    mo.md("## Plans")
    return


@app.cell
def _(mo, plans):
    mo.ui.table(
        plans[["plan_name", "file_name", "file_size"]],
        label="Available Plans",
    )
    return


@app.cell
def _(mo):
    mo.md("## History")
    return


@app.cell
def _(history, mo):
    hist_display = history.copy()
    if "timestamp_ms" in hist_display.columns:
        import pandas as pd

        hist_display["timestamp"] = pd.to_datetime(
            hist_display["timestamp_ms"], unit="ms", errors="coerce"
        )
    mo.ui.table(
        hist_display[["timestamp", "project", "session_id", "display"]].sort_values(
            "timestamp", ascending=False
        ),
        label="Command History",
    )
    return hist_display, pd


@app.cell
def _(mo):
    mo.md("## Daily Activity Stats")
    return


@app.cell
def _(mo, stats):
    mo.ui.table(stats, label="Daily Activity")
    return


@app.cell
def _(mo):
    mo.md(
        """
    ## Cross-Table Analysis

    Join conversations with todos and history to see the full picture.
    """
    )
    return


@app.cell
def _(con, DATA_PATH, mo):
    cross_query = f"""
    SELECT
        c.session_id,
        c.project_path,
        COUNT(DISTINCT c.uuid) as message_count,
        COUNT(DISTINCT t.content) as todo_count,
        COUNT(DISTINCT h.display) as history_entries
    FROM read_conversations(path='{DATA_PATH}') c
    LEFT JOIN read_todos(path='{DATA_PATH}') t ON c.session_id = t.session_id
    LEFT JOIN read_history(path='{DATA_PATH}') h ON c.session_id = h.session_id
    GROUP BY c.session_id, c.project_path
    ORDER BY message_count DESC
    """
    cross_data = con.execute(cross_query).df()
    mo.ui.table(cross_data, label="Session Activity Summary")
    return cross_data, cross_query


if __name__ == "__main__":
    app.run()
