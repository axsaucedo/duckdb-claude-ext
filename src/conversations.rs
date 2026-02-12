use crate::types::*;
use crate::utils;
use crate::vtab::{self, ColDef, TableFunc};
use duckdb::core::DataChunkHandle;
use std::io::{BufRead, BufReader};

/// A flattened conversation row ready for output.
#[derive(Default)]
pub struct ConversationRow {
    session_id: String,
    project_path: String,
    project_dir: String,
    file_name: String,
    is_agent: bool,
    line_number: i64,
    message_type: String,
    uuid: Option<String>,
    parent_uuid: Option<String>,
    timestamp: Option<String>,
    message_role: Option<String>,
    message_content: Option<String>,
    model: Option<String>,
    tool_name: Option<String>,
    tool_use_id: Option<String>,
    tool_input: Option<String>,
    input_tokens: Option<i64>,
    output_tokens: Option<i64>,
    cache_creation_tokens: Option<i64>,
    cache_read_tokens: Option<i64>,
    slug: Option<String>,
    git_branch: Option<String>,
    cwd: Option<String>,
    version: Option<String>,
    stop_reason: Option<String>,
}

pub struct Conversations;

impl Conversations {
    /// Build common row fields from BaseFields shared across User/Assistant/System messages.
    fn base_row(base: &BaseFields, project_dir: &str, file_name: &str, is_agent: bool,
                file_session_id: &str, line_number: i64, message_type: &str) -> ConversationRow {
        let fallback = utils::decode_project_path(project_dir);
        ConversationRow {
            session_id: base.session_id.clone().unwrap_or_else(|| file_session_id.to_string()),
            project_path: base.cwd.clone().unwrap_or(fallback),
            project_dir: project_dir.to_string(),
            file_name: file_name.to_string(),
            is_agent,
            line_number,
            message_type: message_type.to_string(),
            uuid: base.uuid.clone(),
            parent_uuid: base.parent_uuid.clone(),
            timestamp: base.timestamp.clone(),
            slug: base.slug.clone(),
            git_branch: base.git_branch.clone(),
            cwd: base.cwd.clone(),
            version: base.version.clone(),
            ..Default::default()
        }
    }

    /// Build a minimal row for message types without BaseFields.
    fn simple_row(project_dir: &str, file_name: &str, is_agent: bool,
                  file_session_id: &str, line_number: i64, message_type: &str) -> ConversationRow {
        ConversationRow {
            session_id: file_session_id.to_string(),
            project_path: utils::decode_project_path(project_dir),
            project_dir: project_dir.to_string(),
            file_name: file_name.to_string(),
            is_agent,
            line_number,
            message_type: message_type.to_string(),
            ..Default::default()
        }
    }

    fn message_to_row(msg: ConversationMessage, project_dir: &str, file_name: &str,
                      is_agent: bool, file_session_id: &str, line_number: i64) -> ConversationRow {
        match msg {
            ConversationMessage::User(u) => {
                let content = u.message.as_ref()
                    .and_then(|m| m.content.as_ref())
                    .map(utils::extract_text_content);
                let mut row = Self::base_row(&u.base, project_dir, file_name, is_agent, file_session_id, line_number, "user");
                row.message_role = Some("user".to_string());
                row.message_content = content;
                row
            }
            ConversationMessage::Assistant(a) => {
                let msg_content = a.message.as_ref();
                let mut row = Self::base_row(&a.base, project_dir, file_name, is_agent, file_session_id, line_number, "assistant");
                row.message_role = Some("assistant".to_string());

                // Extract text from content blocks
                row.message_content = msg_content
                    .and_then(|m| m.content.as_ref())
                    .map(|blocks| blocks.iter().filter_map(|b| match b {
                        ContentBlock::Text { text } => Some(text.as_str()),
                        _ => None,
                    }).collect::<Vec<_>>().join("\n"));

                // Extract first tool use
                if let Some(blocks) = msg_content.and_then(|m| m.content.as_ref()) {
                    for b in blocks {
                        if let ContentBlock::ToolUse { id, name, input } = b {
                            row.tool_name = name.clone();
                            row.tool_use_id = id.clone();
                            row.tool_input = input.as_ref().map(|i| i.to_string());
                            break;
                        }
                    }
                }

                let usage = msg_content.and_then(|m| m.usage.as_ref());
                row.model = msg_content.and_then(|m| m.model.clone());
                row.input_tokens = usage.and_then(|u| u.input_tokens);
                row.output_tokens = usage.and_then(|u| u.output_tokens);
                row.cache_creation_tokens = usage.and_then(|u| u.cache_creation_input_tokens);
                row.cache_read_tokens = usage.and_then(|u| u.cache_read_input_tokens);
                row.stop_reason = msg_content.and_then(|m| m.stop_reason.clone());
                row
            }
            ConversationMessage::System(s) => {
                let mut row = Self::base_row(&s.base, project_dir, file_name, is_agent, file_session_id, line_number, "system");
                row.message_content = s.content.as_ref().map(utils::extract_text_content);
                row
            }
            ConversationMessage::Summary(s) => {
                let mut row = Self::simple_row(project_dir, file_name, is_agent, file_session_id, line_number, "summary");
                row.message_content = s.summary;
                row
            }
            ConversationMessage::FileHistorySnapshot { .. } => {
                Self::simple_row(project_dir, file_name, is_agent, file_session_id, line_number, "file-history-snapshot")
            }
            ConversationMessage::QueueOperation(q) => {
                let mut row = Self::simple_row(project_dir, file_name, is_agent, file_session_id, line_number, "queue-operation");
                if let Some(sid) = q.session_id { row.session_id = sid; }
                row.timestamp = q.timestamp;
                row.message_content = q.content;
                row
            }
        }
    }
}

impl TableFunc for Conversations {
    type Row = ConversationRow;

    fn columns() -> Vec<ColDef> {
        vec![
            vtab::varchar("session_id"),    vtab::varchar("project_path"),
            vtab::varchar("project_dir"),   vtab::varchar("file_name"),
            vtab::boolean("is_agent"),      vtab::bigint("line_number"),
            vtab::varchar("message_type"),  vtab::varchar("uuid"),
            vtab::varchar("parent_uuid"),   vtab::varchar("timestamp"),
            vtab::varchar("message_role"),  vtab::varchar("message_content"),
            vtab::varchar("model"),         vtab::varchar("tool_name"),
            vtab::varchar("tool_use_id"),   vtab::varchar("tool_input"),
            vtab::bigint("input_tokens"),   vtab::bigint("output_tokens"),
            vtab::bigint("cache_creation_tokens"), vtab::bigint("cache_read_tokens"),
            vtab::varchar("slug"),          vtab::varchar("git_branch"),
            vtab::varchar("cwd"),           vtab::varchar("version"),
            vtab::varchar("stop_reason"),
        ]
    }

    fn load_rows(path: Option<&str>, _source: Option<&str>) -> Vec<ConversationRow> {
        let base_path = utils::resolve_claude_path(path);
        let files = utils::discover_conversation_files(&base_path);
        let mut rows = Vec::new();

        for (project_dir, is_agent, file_path) in &files {
            let file_name = file_path.file_name()
                .map(|f| f.to_string_lossy().to_string())
                .unwrap_or_default();
            let file_session_id = utils::extract_session_id_from_filename(&file_name);

            let file = match std::fs::File::open(file_path) {
                Ok(f) => f,
                Err(_) => continue,
            };

            let file_rows_start = rows.len();
            let mut file_cwd: Option<String> = None;
            let mut file_line: i64 = 0;

            for line_result in BufReader::new(file).lines() {
                file_line += 1;
                let line = match line_result {
                    Ok(l) if !l.trim().is_empty() => l,
                    _ => continue,
                };

                let row = match serde_json::from_str::<ConversationMessage>(&line) {
                    Ok(msg) => Self::message_to_row(msg, project_dir, &file_name, *is_agent, &file_session_id, file_line),
                    Err(e) => {
                        let mut row = Self::simple_row(project_dir, &file_name, *is_agent, &file_session_id, file_line, "_parse_error");
                        row.message_content = Some(format!("Parse error: {}", e));
                        row
                    }
                };

                if file_cwd.is_none() && row.cwd.is_some() {
                    file_cwd = row.cwd.clone();
                }
                rows.push(row);
            }

            // Backfill project_path for rows without cwd
            if let Some(ref cwd) = file_cwd {
                let fallback = utils::decode_project_path(project_dir);
                for row in &mut rows[file_rows_start..] {
                    if row.project_path == fallback {
                        row.project_path = cwd.clone();
                    }
                }
            }
        }
        rows
    }

    fn write_row(output: &mut DataChunkHandle, idx: usize, row: &ConversationRow) {
        vtab::set_varchar(output, 0, idx, &row.session_id);
        vtab::set_varchar(output, 1, idx, &row.project_path);
        vtab::set_varchar(output, 2, idx, &row.project_dir);
        vtab::set_varchar(output, 3, idx, &row.file_name);
        vtab::set_bool(output, 4, idx, row.is_agent);
        vtab::set_i64(output, 5, idx, row.line_number);
        vtab::set_varchar(output, 6, idx, &row.message_type);
        vtab::set_varchar_opt(output, 7, idx, row.uuid.as_deref());
        vtab::set_varchar_opt(output, 8, idx, row.parent_uuid.as_deref());
        vtab::set_varchar_opt(output, 9, idx, row.timestamp.as_deref());
        vtab::set_varchar_opt(output, 10, idx, row.message_role.as_deref());
        vtab::set_varchar_opt(output, 11, idx, row.message_content.as_deref());
        vtab::set_varchar_opt(output, 12, idx, row.model.as_deref());
        vtab::set_varchar_opt(output, 13, idx, row.tool_name.as_deref());
        vtab::set_varchar_opt(output, 14, idx, row.tool_use_id.as_deref());
        vtab::set_varchar_opt(output, 15, idx, row.tool_input.as_deref());
        vtab::set_i64_opt(output, 16, idx, row.input_tokens);
        vtab::set_i64_opt(output, 17, idx, row.output_tokens);
        vtab::set_i64_opt(output, 18, idx, row.cache_creation_tokens);
        vtab::set_i64_opt(output, 19, idx, row.cache_read_tokens);
        vtab::set_varchar_opt(output, 20, idx, row.slug.as_deref());
        vtab::set_varchar_opt(output, 21, idx, row.git_branch.as_deref());
        vtab::set_varchar_opt(output, 22, idx, row.cwd.as_deref());
        vtab::set_varchar_opt(output, 23, idx, row.version.as_deref());
        vtab::set_varchar_opt(output, 24, idx, row.stop_reason.as_deref());
    }
}
