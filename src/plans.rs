use crate::utils;
use crate::vtab::{self, ColDef, TableFunc};
use duckdb::core::DataChunkHandle;

pub struct PlanRow {
    plan_name: String,
    file_name: String,
    file_path: String,
    content: String,
    file_size: i64,
}

pub struct Plans;

impl TableFunc for Plans {
    type Row = PlanRow;

    fn columns() -> Vec<ColDef> {
        vec![
            vtab::varchar("plan_name"),
            vtab::varchar("file_name"),
            vtab::varchar("file_path"),
            vtab::varchar("content"),
            vtab::bigint("file_size"),
        ]
    }

    fn load_rows(path: Option<&str>) -> Vec<PlanRow> {
        let base_path = utils::resolve_claude_path(path);
        let files = utils::discover_plan_files(&base_path);

        files.into_iter().filter_map(|file_path| {
            let content = std::fs::read_to_string(&file_path).ok()?;
            let file_size = std::fs::metadata(&file_path).map(|m| m.len() as i64).unwrap_or(0);
            Some(PlanRow {
                plan_name: file_path.file_stem()?.to_string_lossy().to_string(),
                file_name: file_path.file_name()?.to_string_lossy().to_string(),
                file_path: file_path.to_string_lossy().to_string(),
                content,
                file_size,
            })
        }).collect()
    }

    fn write_row(output: &mut DataChunkHandle, idx: usize, row: &PlanRow) {
        vtab::set_varchar(output, 0, idx, &row.plan_name);
        vtab::set_varchar(output, 1, idx, &row.file_name);
        vtab::set_varchar(output, 2, idx, &row.file_path);
        vtab::set_varchar(output, 3, idx, &row.content);
        vtab::set_i64(output, 4, idx, row.file_size);
    }
}
