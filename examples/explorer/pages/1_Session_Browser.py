"""Session Browser — Chronicle-style session explorer.

Browse sessions with a chat-like event timeline and detail panel.
Matches the Copilot Chronicle UI pattern: timestamps, colored pill badges,
truncated content previews, and a right-side detail panel.
"""

import streamlit as st
import pandas as pd
import json
import html
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection, get_data_paths, load_session_index, load_session_events

st.set_page_config(page_title="Session Browser", page_icon="📋", layout="wide")

con = get_connection()
claude_path, copilot_path = get_data_paths()

# ── Helpers ─────────────────────────────────────────────────────────────────

BADGE_COLORS = {
    "user":      ("#e879f9", "#3b0764"),
    "assistant": ("#f97316", "#431407"),
    "system":    ("#64748b", "#1e293b"),
    "summary":   ("#64748b", "#1e293b"),
    "tool_start":  ("#22d3ee", "#083344"),
    "tool_result": ("#22d3ee", "#083344"),
    "session_start":  ("#a3e635", "#1a2e05"),
    "session_resume": ("#a3e635", "#1a2e05"),
    "session_info":   ("#38bdf8", "#0c4a6e"),
    "session_error":  ("#ef4444", "#450a0a"),
    "turn_start":  ("#94a3b8", "#1e293b"),
    "turn_end":    ("#94a3b8", "#1e293b"),
    "reasoning":   ("#a78bfa", "#2e1065"),
    "truncation":  ("#fbbf24", "#451a03"),
    "model_change": ("#fbbf24", "#451a03"),
    "compaction_start":    ("#fbbf24", "#451a03"),
    "compaction_complete": ("#fbbf24", "#451a03"),
    "abort": ("#ef4444", "#450a0a"),
}


def _is_valid(val) -> bool:
    if val is None:
        return False
    try:
        if pd.isna(val):
            return False
    except (TypeError, ValueError):
        pass
    return True


def parse_ts(ts_str) -> datetime | None:
    if not _is_valid(ts_str):
        return None
    s = str(ts_str).strip()
    if not s or s in ("nan", "None", "NaT", ""):
        return None
    try:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                     "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                     "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        result = pd.to_datetime(s)
        if pd.isna(result):
            return None
        return result.to_pydatetime()
    except Exception:
        return None


def badge_html(msg_type: str) -> str:
    fg, bg = BADGE_COLORS.get(msg_type, ("#94a3b8", "#1e293b"))
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:12px;'
        f'font-size:11px;font-family:monospace;font-weight:600;white-space:nowrap;'
        f'color:{fg};background:{bg};border:1px solid {fg}50;">'
        f'{html.escape(msg_type)}</span>'
    )


def format_delta(ms) -> str:
    if not _is_valid(ms) or ms <= 0:
        return ""
    if ms < 1000:
        return f"+{int(ms)}ms"
    if ms < 60_000:
        return f"+{ms/1000:.1f}s"
    m, s = int(ms // 60_000), int((ms % 60_000) // 1000)
    return f"+{m}m {s:02d}s"


def format_duration(ms) -> str:
    if not _is_valid(ms) or ms <= 0:
        return ""
    if ms < 60_000:
        return f"{ms/1000:.1f}s"
    if ms < 3_600_000:
        m, s = int(ms // 60_000), int((ms % 60_000) // 1000)
        return f"{m}m {s:02d}s"
    h, m = int(ms // 3_600_000), int((ms % 3_600_000) // 60_000)
    return f"{h}h {m}m"


def summarize_event(row: pd.Series, max_len: int = 150) -> str:
    msg_type = str(row.get("message_type", ""))
    content = str(row.get("message_content", "") or "").replace("\n", " ").strip()
    tool = str(row.get("tool_name", "") or "")

    if msg_type == "user":
        text = f"User: {content}" if content else "User: (empty)"
    elif msg_type == "assistant":
        if tool:
            text = f"Assistant calls: {tool}"
        else:
            text = f"Assistant: {content}" if content else "Assistant: (no content)"
    elif msg_type == "tool_start":
        args = ""
        ti = str(row.get("tool_input", "") or "")
        if ti and ti != "None":
            try:
                args = ", ".join(f"{k}=…" for k in list(json.loads(ti).keys())[:2])
            except Exception:
                args = "…"
        text = f"⚡ {tool}({args})"
    elif msg_type == "tool_result":
        text = f"✓ {tool} completed"
    elif msg_type == "session_start":
        v = row.get("version", "")
        text = f"Session started — v{v}" if _is_valid(v) else "Session started"
    elif msg_type == "session_info":
        text = content or "Session info"
    elif msg_type == "session_error":
        text = f"Error: {content}" if content else "Error"
    elif msg_type == "turn_start":
        text = "Turn started"
    elif msg_type == "turn_end":
        text = "Turn ended"
    elif msg_type == "truncation":
        tokens = row.get("input_tokens", "")
        text = f"Truncation: {tokens} tokens" if _is_valid(tokens) else "Truncation"
    elif msg_type == "reasoning":
        text = f"Reasoning: {content}" if content else "Reasoning"
    else:
        text = content or msg_type

    return text[:max_len] + "…" if len(text) > max_len else text


# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.event-card {
    padding: 10px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    cursor: pointer;
    border-radius: 6px;
    margin-bottom: 2px;
    transition: background 0.12s;
}
.event-card:hover { background: rgba(255,255,255,0.04); }
.event-card.selected {
    background: rgba(59,130,246,0.15);
    border-left: 3px solid #3b82f6;
}
.event-time {
    font-family: 'SF Mono','Fira Code',monospace;
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 4px;
}
.event-time .delta { color: #64748b; font-size: 11px; margin-left: 8px; }
.event-time .offset { color: #475569; font-size: 11px; margin-left: 8px; }
.event-summary {
    font-size: 13px;
    color: #cbd5e1;
    margin-top: 4px;
    line-height: 1.4;
    word-break: break-word;
}
.detail-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    margin-bottom: 4px;
    margin-top: 12px;
}
.detail-content {
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
}
.stats-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 8px;
}
.stats-bar strong { color: #e2e8f0; }
.day-sep {
    padding: 4px 0;
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
    margin-top: 8px;
}
.session-card {
    padding: 8px 12px;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    margin-bottom: 6px;
    cursor: pointer;
}
.session-card:hover { background: rgba(255,255,255,0.04); }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR: Source & project filter
# ═══════════════════════════════════════════════════════════════════════════

st.sidebar.header("📋 Session Browser")

source_choice = st.sidebar.radio(
    "Data source",
    ["Claude", "Copilot", "Both"],
    index=0,
    horizontal=True,
)

# Reset session selection when source changes
if st.session_state.get("_prev_source") != source_choice:
    st.session_state["_prev_source"] = source_choice
    st.session_state["selected_event_idx"] = None

paths_to_load = []
if source_choice in ("Claude", "Both"):
    paths_to_load.append(claude_path)
if source_choice in ("Copilot", "Both"):
    paths_to_load.append(copilot_path)

# Load session index
all_sessions = []
for p in paths_to_load:
    df = load_session_index(p)
    if not df.empty:
        df["_path"] = p
        all_sessions.append(df)

if not all_sessions:
    st.warning("No sessions found. Check your data paths.")
    st.info(f"Claude: `{claude_path}` | Copilot: `{copilot_path}`")
    st.stop()

sessions_df = pd.concat(all_sessions, ignore_index=True).sort_values("first_ts", ascending=False)

# ── Sidebar: project filter (trimmed names) ─────────────────────────────
st.sidebar.divider()

# Build trimmed project names
raw_projects = sorted(sessions_df["project_path"].dropna().unique())
project_short_map = {}  # short_name → full_path
for fp in raw_projects:
    short = str(fp).split("/")[-1] if "/" in str(fp) else str(fp)
    # Handle duplicates by adding parent
    if short in project_short_map and project_short_map[short] != fp:
        parts = str(fp).rsplit("/", 2)
        short = "/".join(parts[-2:]) if len(parts) >= 2 else short
    project_short_map[short] = fp

project_options = ["All projects"] + list(project_short_map.keys())
selected_project_short = st.sidebar.selectbox("Project", project_options)

if selected_project_short != "All projects":
    full_project_path = project_short_map[selected_project_short]
    sessions_df = sessions_df[sessions_df["project_path"] == full_project_path]

max_events = sessions_df["event_count"].max()
max_events = int(max_events) if _is_valid(max_events) else 1
min_events = st.sidebar.slider("Min events", 0, max(max_events, 1), 0)
if min_events > 0:
    sessions_df = sessions_df[sessions_df["event_count"] >= min_events]

# ── Sidebar: truncation controls ────────────────────────────────────────
st.sidebar.divider()
truncate_content = st.sidebar.checkbox("Truncate long strings", value=True)

if sessions_df.empty:
    st.info("No sessions match filters.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN AREA — Session selector (above timeline)
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("### Select Session")

# Search bar for sessions
session_search = st.text_input(
    "🔍 Search sessions",
    placeholder="Search by project, message, session ID…",
    label_visibility="collapsed",
)

# Filter sessions by search
if session_search:
    q = session_search.lower()
    mask = (
        sessions_df["project_path"].fillna("").str.lower().str.contains(q, na=False) |
        sessions_df["session_id"].fillna("").str.lower().str.contains(q, na=False) |
        sessions_df["first_user_message"].fillna("").str.lower().str.contains(q, na=False)
    )
    filtered_sessions = sessions_df[mask]
else:
    filtered_sessions = sessions_df

# Build session options for selectbox
session_options = []
session_id_map = {}  # label → (session_id, path, source)
for _, row in filtered_sessions.iterrows():
    proj = str(row["project_path"] or "").split("/")[-1] or "unknown"
    ts_val = row["first_ts"]
    ts_str = str(ts_val)[:16] if _is_valid(ts_val) else "?"
    events = int(row["event_count"]) if _is_valid(row["event_count"]) else 0
    src = str(row.get("source", ""))

    # First user message preview
    first_msg = str(row.get("first_user_message", "") or "").replace("\n", " ").strip()
    if not first_msg or first_msg in ("None", "nan"):
        first_msg = "(no user message)"
    first_msg = first_msg[:80] + "…" if len(first_msg) > 80 else first_msg

    label = f"[{src}] {proj} — {events} events — {ts_str} — {first_msg}"
    session_options.append(label)
    session_id_map[label] = (row["session_id"], row["_path"], row["source"])

if not session_options:
    st.info("No sessions match search.")
    st.stop()

selected_label = st.selectbox(
    "Session",
    session_options,
    key=f"session_select_{source_choice}",
    label_visibility="collapsed",
)

session_id, source_path, session_source = session_id_map[selected_label]

# Session metadata (collapsible)
sel_row = filtered_sessions[filtered_sessions["session_id"] == session_id].iloc[0]
with st.expander("Session Metadata", expanded=False):
    meta_cols = st.columns(3)
    with meta_cols[0]:
        st.markdown(f"**Source:** {sel_row.get('source', '')}")
        st.markdown(f"**Session ID:** `{session_id}`")
        proj_full = sel_row.get("project_path", "")
        st.markdown(f"**Project:** `{proj_full}`")
    with meta_cols[1]:
        st.markdown(f"**First seen:** {sel_row.get('first_ts', '')}")
        st.markdown(f"**Last seen:** {sel_row.get('last_ts', '')}")
        slug = sel_row.get("slug", "")
        if _is_valid(slug):
            st.markdown(f"**Slug:** {slug}")
    with meta_cols[2]:
        ec = sel_row.get("event_count", 0)
        tc = sel_row.get("tool_calls", 0)
        it = sel_row.get("total_input_tokens", 0)
        ot = sel_row.get("total_output_tokens", 0)
        st.markdown(f"**Events:** {ec}")
        st.markdown(f"**Tool calls:** {tc}")
        st.markdown(f"**Tokens:** {it:,} in / {ot:,} out")


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: Event timeline
# ═══════════════════════════════════════════════════════════════════════════

events_df = load_session_events(source_path, session_id)

if events_df.empty:
    st.warning("No events found for this session.")
    st.stop()

# Parse timestamps
events_df["_ts"] = events_df["timestamp"].apply(parse_ts)

# Calculate deltas
valid_ts = events_df["_ts"].apply(_is_valid)
first_ts = events_df.loc[valid_ts, "_ts"].iloc[0] if valid_ts.any() else None
deltas, offsets = [], []
prev = None
for _, row in events_df.iterrows():
    ts = row["_ts"]
    if _is_valid(ts) and _is_valid(first_ts):
        offsets.append((ts - first_ts).total_seconds() * 1000)
        if prev is not None:
            deltas.append((ts - prev).total_seconds() * 1000)
        else:
            deltas.append(0)
        prev = ts
    else:
        deltas.append(None)
        offsets.append(None)

events_df["_delta_ms"] = deltas
events_df["_offset_ms"] = offsets

# ── Filter bar ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Session Timeline")

fc = st.columns([3, 3, 2, 2])
with fc[0]:
    search_q = st.text_input("🔍 Search events", "", placeholder="message, tool name…",
                              label_visibility="collapsed")
all_types = sorted(events_df["message_type"].dropna().unique())
with fc[1]:
    type_filter = st.selectbox("Type filter", ["All"] + list(all_types), label_visibility="collapsed")
with fc[2]:
    hide_noise = st.checkbox("Hide turn/truncation", value=False)
with fc[3]:
    if st.button("✕ Clear"):
        st.rerun()

# Apply filters
filt = events_df.copy()
if type_filter != "All":
    filt = filt[filt["message_type"] == type_filter]
if hide_noise:
    filt = filt[~filt["message_type"].isin({"turn_start", "turn_end", "truncation", "compaction_start", "compaction_complete"})]
if search_q:
    q = search_q.lower()
    mask = (
        filt["message_content"].fillna("").str.lower().str.contains(q, na=False) |
        filt["tool_name"].fillna("").str.lower().str.contains(q, na=False) |
        filt["message_type"].fillna("").str.lower().str.contains(q, na=False)
    )
    filt = filt[mask]

# Stats bar
last_ts = events_df.loc[valid_ts, "_ts"].iloc[-1] if valid_ts.any() else None
try:
    dur = (last_ts - first_ts).total_seconds() * 1000 if _is_valid(first_ts) and _is_valid(last_ts) else 0
except Exception:
    dur = 0

st.markdown(
    f'<div class="stats-bar">'
    f'<span><strong>{len(filt)}</strong> showing / <strong>{len(events_df)}</strong> events</span>'
    f'<span>Duration: {format_duration(dur)}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Two-column: event list + detail ─────────────────────────────────────
col_list, col_detail = st.columns([3, 2])

if "selected_event_idx" not in st.session_state:
    st.session_state["selected_event_idx"] = None

with col_list:
    if filt.empty:
        st.info("No events match filters.")
    else:
        # Render Chronicle-style event cards using buttons for click
        current_day = None
        for idx, row in filt.iterrows():
            ts = row["_ts"]

            # Day separator
            if _is_valid(ts):
                day = ts.strftime("%Y-%m-%d")
                if day != current_day:
                    current_day = day
                    st.markdown(f'<div class="day-sep">📅 {day}</div>', unsafe_allow_html=True)

            # Time info
            ts_utc = ts.strftime("%H:%M:%S.") + ts.strftime("%f")[:3] if _is_valid(ts) else "—"
            delta_val = row.get("_delta_ms")
            delta_s = format_delta(delta_val) if _is_valid(delta_val) else ""
            offset_val = row.get("_offset_ms")
            offset_s = f"t{format_delta(offset_val)}" if _is_valid(offset_val) else ""

            msg_type = str(row.get("message_type", ""))
            badge = badge_html(msg_type)
            summary = html.escape(summarize_event(row, max_len=120))

            is_selected = st.session_state.get("selected_event_idx") == idx
            sel_class = "selected" if is_selected else ""

            # Render card as HTML + a button to select
            card_html = (
                f'<div class="event-card {sel_class}">'
                f'  <div class="event-time">'
                f'    {ts_utc}'
                f'    <span class="delta">{delta_s}</span>'
                f'    <span class="offset">{offset_s}</span>'
                f'  </div>'
                f'  <div>{badge}</div>'
                f'  <div class="event-summary">{summary}</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

            if st.button("Select", key=f"sel_{idx}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state["selected_event_idx"] = idx
                st.rerun()


# ── Detail panel ────────────────────────────────────────────────────────
with col_detail:
    sel_idx = st.session_state.get("selected_event_idx")

    if sel_idx is not None and sel_idx in filt.index:
        event = filt.loc[sel_idx]
        msg_type = str(event.get("message_type", ""))

        st.markdown(f"### {badge_html(msg_type)}", unsafe_allow_html=True)

        content = str(event.get("message_content", "") or "")
        tool = str(event.get("tool_name", "") or "")
        tool_input_str = str(event.get("tool_input", "") or "")
        max_display = 2000 if truncate_content else 50000

        # Type-specific rendering
        if msg_type == "user":
            st.markdown('<div class="detail-label">USER MESSAGE</div>', unsafe_allow_html=True)
            display = content[:max_display] + "…" if len(content) > max_display else content
            st.markdown(f'<div class="detail-content">{html.escape(display)}</div>', unsafe_allow_html=True)

        elif msg_type == "assistant":
            if tool:
                st.markdown('<div class="detail-label">TOOL CALL</div>', unsafe_allow_html=True)
                st.code(tool, language=None)
                if tool_input_str and tool_input_str not in ("None", ""):
                    try:
                        parsed = json.loads(tool_input_str)
                        disp = json.dumps(parsed, indent=2)
                        if len(disp) > max_display:
                            disp = disp[:max_display] + "\n…[truncated]"
                        st.code(disp, language="json")
                    except (json.JSONDecodeError, TypeError):
                        st.code(tool_input_str[:500], language=None)
            if content:
                st.markdown('<div class="detail-label">RESPONSE</div>', unsafe_allow_html=True)
                display = content[:max_display] + "…" if len(content) > max_display else content
                st.text(display)

        elif msg_type in ("tool_start", "tool_result"):
            label = "TOOL EXECUTION" if msg_type == "tool_start" else "TOOL RESULT"
            st.markdown(f'<div class="detail-label">{label}</div>', unsafe_allow_html=True)
            if tool:
                st.code(tool, language=None)
            if tool_input_str and tool_input_str not in ("None", ""):
                try:
                    parsed = json.loads(tool_input_str)
                    st.code(json.dumps(parsed, indent=2)[:max_display], language="json")
                except (json.JSONDecodeError, TypeError):
                    st.code(tool_input_str[:500], language=None)
            if content:
                st.text(content[:max_display])

        elif msg_type in ("session_start", "session_info", "session_error", "session_resume"):
            st.markdown('<div class="detail-label">SESSION EVENT</div>', unsafe_allow_html=True)
            if content:
                st.text(content[:1000])

        elif msg_type in ("system", "summary", "reasoning"):
            st.markdown(f'<div class="detail-label">{msg_type.upper()}</div>', unsafe_allow_html=True)
            st.text(content[:max_display] if content else "")

        else:
            if content:
                st.markdown(f'<div class="detail-label">{html.escape(msg_type).upper()}</div>', unsafe_allow_html=True)
                st.text(content[:1000])

        # Metadata
        st.divider()
        st.markdown('<div class="detail-label">METADATA</div>', unsafe_allow_html=True)
        for label, col_name in [
            ("UUID", "uuid"), ("Parent UUID", "parent_uuid"),
            ("Timestamp", "timestamp"), ("Model", "model"),
            ("Tool", "tool_name"), ("Tool Use ID", "tool_use_id"),
            ("Input Tokens", "input_tokens"), ("Output Tokens", "output_tokens"),
            ("Cache Creation", "cache_creation_tokens"), ("Cache Read", "cache_read_tokens"),
            ("Stop Reason", "stop_reason"), ("Git Branch", "git_branch"),
            ("CWD", "cwd"), ("Version", "version"),
        ]:
            val = event.get(col_name)
            if _is_valid(val) and str(val) not in ("nan", "None", "", "<NA>"):
                st.text(f"{label}: {val}")

        # Raw JSON
        with st.expander("Raw JSON"):
            raw = {}
            for col_name in event.index:
                if col_name.startswith("_"):
                    continue
                v = event[col_name]
                if _is_valid(v) and str(v) not in ("nan", "None", "<NA>"):
                    if col_name == "tool_input" and v:
                        try:
                            raw[col_name] = json.loads(str(v))
                        except (json.JSONDecodeError, TypeError):
                            raw[col_name] = str(v)
                    else:
                        raw[col_name] = str(v) if not isinstance(v, (int, float, bool)) else v
            disp_json = json.dumps(raw, indent=2, default=str)
            if truncate_content and len(disp_json) > 5000:
                disp_json = disp_json[:5000] + "\n…[truncated]"
            st.code(disp_json, language="json")
    else:
        st.info("← Click **Select** on an event to see details")
