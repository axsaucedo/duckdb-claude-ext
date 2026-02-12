use crate::types::HistoryEntry;
use crate::utils;
use crate::vtab::{self, ColDef, TableFunc};
use duckdb::core::DataChunkHandle;
use std::io::{BufRead, BufReader};

pub struct HistoryRow {
    line_number: i64,
    timestamp_ms: Option<i64>,
    project: Option<String>,
    session_id: Option<String>,
    display: Option<String>,
    pasted_contents: Option<String>,
}

pub struct History;

impl TableFunc for History {
    type Row = HistoryRow;

    fn columns() -> Vec<ColDef> {
        vec![
            vtab::bigint("line_number"),
            vtab::bigint("timestamp_ms"),
            vtab::varchar("project"),
            vtab::varchar("session_id"),
            vtab::varchar("display"),
            vtab::varchar("pasted_contents"),
        ]
    }

    fn load_rows(path: Option<&str>, _source: Option<&str>) -> Vec<HistoryRow> {
        let base_path = utils::resolve_claude_path(path);
        let history_path = utils::history_file_path(&base_path);

        let file = match std::fs::File::open(&history_path) {
            Ok(f) => f,
            Err(_) => return Vec::new(),
        };

        BufReader::new(file).lines().enumerate().filter_map(|(line_idx, line_result)| {
            let line = line_result.ok()?;
            if line.trim().is_empty() { return None; }

            let line_number = (line_idx + 1) as i64;
            Some(match serde_json::from_str::<HistoryEntry>(&line) {
                Ok(entry) => HistoryRow {
                    line_number,
                    timestamp_ms: entry.timestamp.map(|t| t as i64),
                    project: entry.project,
                    session_id: entry.session_id,
                    display: entry.display,
                    pasted_contents: entry.pasted_contents.map(|v| v.to_string()),
                },
                Err(e) => HistoryRow {
                    line_number,
                    timestamp_ms: None,
                    project: None,
                    session_id: None,
                    display: Some(format!("Parse error: {}", e)),
                    pasted_contents: None,
                },
            })
        }).collect()
    }

    fn write_row(output: &mut DataChunkHandle, idx: usize, row: &HistoryRow) {
        vtab::set_i64(output, 0, idx, row.line_number);
        vtab::set_i64_opt(output, 1, idx, row.timestamp_ms);
        vtab::set_varchar_opt(output, 2, idx, row.project.as_deref());
        vtab::set_varchar_opt(output, 3, idx, row.session_id.as_deref());
        vtab::set_varchar_opt(output, 4, idx, row.display.as_deref());
        vtab::set_varchar_opt(output, 5, idx, row.pasted_contents.as_deref());
    }
}
