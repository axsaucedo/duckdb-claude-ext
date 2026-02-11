use crate::types::TodoItem;
use crate::utils;
use crate::vtab::{self, ColDef, TableFunc};
use duckdb::core::DataChunkHandle;

pub struct TodoRow {
    session_id: String,
    agent_id: String,
    file_name: String,
    item_index: i64,
    content: String,
    status: String,
    active_form: Option<String>,
}

pub struct Todos;

impl TableFunc for Todos {
    type Row = TodoRow;

    fn columns() -> Vec<ColDef> {
        vec![
            vtab::varchar("session_id"),
            vtab::varchar("agent_id"),
            vtab::varchar("file_name"),
            vtab::bigint("item_index"),
            vtab::varchar("content"),
            vtab::varchar("status"),
            vtab::varchar("active_form"),
        ]
    }

    fn load_rows(path: Option<&str>) -> Vec<TodoRow> {
        let base_path = utils::resolve_claude_path(path);
        let files = utils::discover_todo_files(&base_path);
        let mut rows = Vec::new();

        for (session_id, agent_id, file_path) in files {
            let fname = file_path.file_name()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_default();

            let content = match std::fs::read_to_string(&file_path) {
                Ok(c) => c,
                Err(_) => continue,
            };

            match serde_json::from_str::<Vec<TodoItem>>(&content) {
                Ok(items) => {
                    for (idx, item) in items.into_iter().enumerate() {
                        rows.push(TodoRow {
                            session_id: session_id.clone(),
                            agent_id: agent_id.clone(),
                            file_name: fname.clone(),
                            item_index: idx as i64,
                            content: item.content.unwrap_or_default(),
                            status: item.status.unwrap_or_default(),
                            active_form: item.active_form,
                        });
                    }
                }
                Err(e) => {
                    rows.push(TodoRow {
                        session_id: session_id.clone(),
                        agent_id: agent_id.clone(),
                        file_name: fname,
                        item_index: -1,
                        content: format!("Parse error: {}", e),
                        status: "_parse_error".to_string(),
                        active_form: None,
                    });
                }
            }
        }
        rows
    }

    fn write_row(output: &mut DataChunkHandle, idx: usize, row: &TodoRow) {
        vtab::set_varchar(output, 0, idx, &row.session_id);
        vtab::set_varchar(output, 1, idx, &row.agent_id);
        vtab::set_varchar(output, 2, idx, &row.file_name);
        vtab::set_i64(output, 3, idx, row.item_index);
        vtab::set_varchar(output, 4, idx, &row.content);
        vtab::set_varchar(output, 5, idx, &row.status);
        vtab::set_varchar_opt(output, 6, idx, row.active_form.as_deref());
    }
}
