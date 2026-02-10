use crate::types::*;
use crate::utils;
use duckdb::{
    core::{DataChunkHandle, Inserter, LogicalTypeHandle, LogicalTypeId},
    vtab::{BindInfo, InitInfo, TableFunctionInfo, VTab},
    Result,
};
use std::ffi::CString;
use std::io::{BufRead, BufReader};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Mutex;

/// A flattened conversation row ready for output.
struct ConversationRow {
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

#[repr(C)]
pub struct ConversationsBindData {
    rows: Mutex<Vec<ConversationRow>>,
}

#[repr(C)]
pub struct ConversationsInitData {
    offset: AtomicUsize,
}

pub struct ReadConversationsVTab;

impl ReadConversationsVTab {
    fn load_rows(path: Option<&str>) -> Vec<ConversationRow> {
        let base_path = utils::resolve_claude_path(path);
        let files = utils::discover_conversation_files(&base_path);
        let mut rows = Vec::new();
        for (project_dir, is_agent, file_path) in &files {
            let file_name = file_path
                .file_name()
                .map(|f| f.to_string_lossy().to_string())
                .unwrap_or_default();

            let file_session_id = utils::extract_session_id_from_filename(&file_name);

            let file = match std::fs::File::open(file_path) {
                Ok(f) => f,
                Err(_) => continue,
            };
            let reader = BufReader::new(file);
            let mut file_line: i64 = 0;
            let mut file_rows_start = rows.len();
            let mut file_cwd: Option<String> = None;

            for line_result in reader.lines() {
                file_line += 1;
                let line = match line_result {
                    Ok(l) => l,
                    Err(_) => continue,
                };
                if line.trim().is_empty() {
                    continue;
                }

                match serde_json::from_str::<ConversationMessage>(&line) {
                    Ok(msg) => {
                        let row = Self::message_to_row(
                            msg,
                            project_dir,
                            &file_name,
                            *is_agent,
                            &file_session_id,
                            file_line,
                        );
                        if file_cwd.is_none() && row.cwd.is_some() {
                            file_cwd = row.cwd.clone();
                        }
                        rows.push(row);
                    }
                    Err(e) => {
                        rows.push(ConversationRow {
                            session_id: file_session_id.clone(),
                            project_path: utils::decode_project_path(project_dir),
                            project_dir: project_dir.clone(),
                            file_name: file_name.clone(),
                            is_agent: *is_agent,
                            line_number: file_line,
                            message_type: "_parse_error".to_string(),
                            uuid: None,
                            parent_uuid: None,
                            timestamp: None,
                            message_role: None,
                            message_content: Some(format!("Parse error: {}", e)),
                            model: None,
                            tool_name: None,
                            tool_use_id: None,
                            tool_input: None,
                            input_tokens: None,
                            output_tokens: None,
                            cache_creation_tokens: None,
                            cache_read_tokens: None,
                            slug: None,
                            git_branch: None,
                            cwd: None,
                            version: None,
                            stop_reason: None,
                        });
                    }
                }
            }

            // Backfill project_path for rows without cwd (summary, file-history-snapshot, etc.)
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

    fn message_to_row(
        msg: ConversationMessage,
        project_dir: &str,
        file_name: &str,
        is_agent: bool,
        file_session_id: &str,
        line_number: i64,
    ) -> ConversationRow {
        let fallback_project_path = utils::decode_project_path(project_dir);
        match msg {
            ConversationMessage::User(u) => {
                let content = u
                    .message
                    .as_ref()
                    .and_then(|m| m.content.as_ref())
                    .map(utils::extract_text_content);
                let session_id = u
                    .base
                    .session_id
                    .clone()
                    .unwrap_or_else(|| file_session_id.to_string());
                let project_path = u.base.cwd.clone().unwrap_or_else(|| fallback_project_path.clone());
                ConversationRow {
                    session_id,
                    project_path,
                    project_dir: project_dir.to_string(),
                    file_name: file_name.to_string(),
                    is_agent,
                    line_number,
                    message_type: "user".to_string(),
                    uuid: u.base.uuid,
                    parent_uuid: u.base.parent_uuid,
                    timestamp: u.base.timestamp,
                    message_role: Some("user".to_string()),
                    message_content: content,
                    model: None,
                    tool_name: None,
                    tool_use_id: None,
                    tool_input: None,
                    input_tokens: None,
                    output_tokens: None,
                    cache_creation_tokens: None,
                    cache_read_tokens: None,
                    slug: u.base.slug,
                    git_branch: u.base.git_branch,
                    cwd: u.base.cwd,
                    version: u.base.version,
                    stop_reason: None,
                }
            }
            ConversationMessage::Assistant(a) => {
                let msg_content = a.message.as_ref();
                let session_id = a
                    .base
                    .session_id
                    .clone()
                    .unwrap_or_else(|| file_session_id.to_string());
                let project_path = a.base.cwd.clone().unwrap_or_else(|| fallback_project_path.clone());

                // Extract text content from content blocks
                let text_content = msg_content
                    .and_then(|m| m.content.as_ref())
                    .map(|blocks| {
                        blocks
                            .iter()
                            .filter_map(|b| match b {
                                ContentBlock::Text { text } => Some(text.as_str()),
                                _ => None,
                            })
                            .collect::<Vec<_>>()
                            .join("\n")
                    });

                // Extract first tool use
                let tool_info = msg_content
                    .and_then(|m| m.content.as_ref())
                    .and_then(|blocks| {
                        blocks.iter().find_map(|b| match b {
                            ContentBlock::ToolUse { id, name, input } => Some((
                                name.clone(),
                                id.clone(),
                                input.as_ref().map(|i| i.to_string()),
                            )),
                            _ => None,
                        })
                    });

                let usage = msg_content.and_then(|m| m.usage.as_ref());

                ConversationRow {
                    session_id,
                    project_path,
                    project_dir: project_dir.to_string(),
                    file_name: file_name.to_string(),
                    is_agent,
                    line_number,
                    message_type: "assistant".to_string(),
                    uuid: a.base.uuid,
                    parent_uuid: a.base.parent_uuid,
                    timestamp: a.base.timestamp,
                    message_role: Some("assistant".to_string()),
                    message_content: text_content,
                    model: msg_content.and_then(|m| m.model.clone()),
                    tool_name: tool_info.as_ref().and_then(|(n, _, _)| n.clone()),
                    tool_use_id: tool_info.as_ref().and_then(|(_, id, _)| id.clone()),
                    tool_input: tool_info.and_then(|(_, _, input)| input),
                    input_tokens: usage.and_then(|u| u.input_tokens),
                    output_tokens: usage.and_then(|u| u.output_tokens),
                    cache_creation_tokens: usage.and_then(|u| u.cache_creation_input_tokens),
                    cache_read_tokens: usage.and_then(|u| u.cache_read_input_tokens),
                    slug: a.base.slug,
                    git_branch: a.base.git_branch,
                    cwd: a.base.cwd,
                    version: a.base.version,
                    stop_reason: msg_content.and_then(|m| m.stop_reason.clone()),
                }
            }
            ConversationMessage::System(s) => {
                let session_id = s
                    .base
                    .session_id
                    .clone()
                    .unwrap_or_else(|| file_session_id.to_string());
                let content = s.content.as_ref().map(utils::extract_text_content);
                let project_path = s.base.cwd.clone().unwrap_or_else(|| fallback_project_path.clone());
                ConversationRow {
                    session_id,
                    project_path,
                    project_dir: project_dir.to_string(),
                    file_name: file_name.to_string(),
                    is_agent,
                    line_number,
                    message_type: "system".to_string(),
                    uuid: s.base.uuid,
                    parent_uuid: s.base.parent_uuid,
                    timestamp: s.base.timestamp,
                    message_role: None,
                    message_content: content,
                    model: None,
                    tool_name: None,
                    tool_use_id: None,
                    tool_input: None,
                    input_tokens: None,
                    output_tokens: None,
                    cache_creation_tokens: None,
                    cache_read_tokens: None,
                    slug: s.base.slug,
                    git_branch: s.base.git_branch,
                    cwd: s.base.cwd,
                    version: s.base.version,
                    stop_reason: None,
                }
            }
            ConversationMessage::Summary(s) => ConversationRow {
                session_id: file_session_id.to_string(),
                project_path: fallback_project_path.clone(),
                project_dir: project_dir.to_string(),
                file_name: file_name.to_string(),
                is_agent,
                line_number,
                message_type: "summary".to_string(),
                uuid: None,
                parent_uuid: None,
                timestamp: None,
                message_role: None,
                message_content: s.summary,
                model: None,
                tool_name: None,
                tool_use_id: None,
                tool_input: None,
                input_tokens: None,
                output_tokens: None,
                cache_creation_tokens: None,
                cache_read_tokens: None,
                slug: None,
                git_branch: None,
                cwd: None,
                version: None,
                stop_reason: None,
            },
            ConversationMessage::FileHistorySnapshot(_) => ConversationRow {
                session_id: file_session_id.to_string(),
                project_path: fallback_project_path.clone(),
                project_dir: project_dir.to_string(),
                file_name: file_name.to_string(),
                is_agent,
                line_number,
                message_type: "file-history-snapshot".to_string(),
                uuid: None,
                parent_uuid: None,
                timestamp: None,
                message_role: None,
                message_content: None,
                model: None,
                tool_name: None,
                tool_use_id: None,
                tool_input: None,
                input_tokens: None,
                output_tokens: None,
                cache_creation_tokens: None,
                cache_read_tokens: None,
                slug: None,
                git_branch: None,
                cwd: None,
                version: None,
                stop_reason: None,
            },
            ConversationMessage::QueueOperation(q) => ConversationRow {
                session_id: q
                    .session_id
                    .clone()
                    .unwrap_or_else(|| file_session_id.to_string()),
                project_path: fallback_project_path.clone(),
                project_dir: project_dir.to_string(),
                file_name: file_name.to_string(),
                is_agent,
                line_number,
                message_type: "queue-operation".to_string(),
                uuid: None,
                parent_uuid: None,
                timestamp: q.timestamp,
                message_role: None,
                message_content: q.content,
                model: None,
                tool_name: None,
                tool_use_id: None,
                tool_input: None,
                input_tokens: None,
                output_tokens: None,
                cache_creation_tokens: None,
                cache_read_tokens: None,
                slug: None,
                git_branch: None,
                cwd: None,
                version: None,
                stop_reason: None,
            },
        }
    }
}

impl VTab for ReadConversationsVTab {
    type InitData = ConversationsInitData;
    type BindData = ConversationsBindData;

    fn bind(bind: &BindInfo) -> Result<Self::BindData, Box<dyn std::error::Error>> {
        // Define output columns
        let cols = [
            "session_id",
            "project_path",
            "project_dir",
            "file_name",
            "is_agent",
            "line_number",
            "message_type",
            "uuid",
            "parent_uuid",
            "timestamp",
            "message_role",
            "message_content",
            "model",
            "tool_name",
            "tool_use_id",
            "tool_input",
            "input_tokens",
            "output_tokens",
            "cache_creation_tokens",
            "cache_read_tokens",
            "slug",
            "git_branch",
            "cwd",
            "version",
            "stop_reason",
        ];

        // VARCHAR columns
        for &col in &cols {
            match col {
                "is_agent" => {
                    bind.add_result_column(col, LogicalTypeHandle::from(LogicalTypeId::Boolean));
                }
                "line_number" | "input_tokens" | "output_tokens" | "cache_creation_tokens"
                | "cache_read_tokens" => {
                    bind.add_result_column(col, LogicalTypeHandle::from(LogicalTypeId::Bigint));
                }
                _ => {
                    bind.add_result_column(col, LogicalTypeHandle::from(LogicalTypeId::Varchar));
                }
            }
        }

        let path = if bind.get_parameter_count() > 0 {
            let p = bind.get_parameter(0).to_string();
            if p.is_empty() { None } else { Some(p) }
        } else {
            None
        };
        let named_path = bind.get_named_parameter("path").map(|v| v.to_string());
        let effective_path = named_path.or(path);

        let rows = Self::load_rows(effective_path.as_deref());
        Ok(ConversationsBindData {
            rows: Mutex::new(rows),
        })
    }

    fn init(_: &InitInfo) -> Result<Self::InitData, Box<dyn std::error::Error>> {
        Ok(ConversationsInitData {
            offset: AtomicUsize::new(0),
        })
    }

    fn func(
        func: &TableFunctionInfo<Self>,
        output: &mut DataChunkHandle,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let bind_data = func.get_bind_data();
        let init_data = func.get_init_data();
        let rows = bind_data.rows.lock().unwrap();

        let offset = init_data.offset.load(Ordering::Relaxed);
        if offset >= rows.len() {
            output.set_len(0);
            return Ok(());
        }

        let batch_size = std::cmp::min(2048, rows.len() - offset);

        for i in 0..batch_size {
            let row = &rows[offset + i];
            let idx = i;

            set_varchar(output, 0, idx, &row.session_id);
            set_varchar(output, 1, idx, &row.project_path);
            set_varchar(output, 2, idx, &row.project_dir);
            set_varchar(output, 3, idx, &row.file_name);
            set_bool(output, 4, idx, row.is_agent);
            set_i64(output, 5, idx, row.line_number);
            set_varchar(output, 6, idx, &row.message_type);
            set_varchar_opt(output, 7, idx, row.uuid.as_deref());
            set_varchar_opt(output, 8, idx, row.parent_uuid.as_deref());
            set_varchar_opt(output, 9, idx, row.timestamp.as_deref());
            set_varchar_opt(output, 10, idx, row.message_role.as_deref());
            set_varchar_opt(output, 11, idx, row.message_content.as_deref());
            set_varchar_opt(output, 12, idx, row.model.as_deref());
            set_varchar_opt(output, 13, idx, row.tool_name.as_deref());
            set_varchar_opt(output, 14, idx, row.tool_use_id.as_deref());
            set_varchar_opt(output, 15, idx, row.tool_input.as_deref());
            set_i64_opt(output, 16, idx, row.input_tokens);
            set_i64_opt(output, 17, idx, row.output_tokens);
            set_i64_opt(output, 18, idx, row.cache_creation_tokens);
            set_i64_opt(output, 19, idx, row.cache_read_tokens);
            set_varchar_opt(output, 20, idx, row.slug.as_deref());
            set_varchar_opt(output, 21, idx, row.git_branch.as_deref());
            set_varchar_opt(output, 22, idx, row.cwd.as_deref());
            set_varchar_opt(output, 23, idx, row.version.as_deref());
            set_varchar_opt(output, 24, idx, row.stop_reason.as_deref());
        }

        output.set_len(batch_size);
        init_data
            .offset
            .store(offset + batch_size, Ordering::Relaxed);

        Ok(())
    }

    fn named_parameters() -> Option<Vec<(String, LogicalTypeHandle)>> {
        Some(vec![(
            "path".to_string(),
            LogicalTypeHandle::from(LogicalTypeId::Varchar),
        )])
    }
}

// ─── Helper functions for vector operations ───

fn set_varchar(output: &mut DataChunkHandle, col: usize, row: usize, val: &str) {
    let mut vec = output.flat_vector(col);
    let cstr = CString::new(val).unwrap_or_else(|_| CString::new("").unwrap());
    vec.insert(row, cstr);
}

fn set_varchar_opt(output: &mut DataChunkHandle, col: usize, row: usize, val: Option<&str>) {
    let mut vec = output.flat_vector(col);
    match val {
        Some(v) => {
            let cstr = CString::new(v).unwrap_or_else(|_| CString::new("").unwrap());
            vec.insert(row, cstr);
        }
        None => {
            vec.set_null(row);
        }
    }
}

fn set_bool(output: &mut DataChunkHandle, col: usize, row: usize, val: bool) {
    let mut vec = output.flat_vector(col);
    let data = vec.as_mut_slice::<bool>();
    data[row] = val;
}

fn set_i64(output: &mut DataChunkHandle, col: usize, row: usize, val: i64) {
    let mut vec = output.flat_vector(col);
    let data = vec.as_mut_slice::<i64>();
    data[row] = val;
}

fn set_i64_opt(output: &mut DataChunkHandle, col: usize, row: usize, val: Option<i64>) {
    let mut vec = output.flat_vector(col);
    match val {
        Some(v) => {
            let data = vec.as_mut_slice::<i64>();
            data[row] = v;
        }
        None => {
            vec.set_null(row);
        }
    }
}
