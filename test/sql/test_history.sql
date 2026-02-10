-- Test: read_history correctness and invariants

-- Test 1: Expected row count
SELECT CASE WHEN cnt = 20 THEN 'PASS' ELSE 'FAIL: expected 20 history entries got ' || cnt END AS test_history_count
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data'));

-- Test 2: line_number starts at 1
SELECT CASE WHEN min_ln = 1 THEN 'PASS' ELSE 'FAIL: min line is ' || min_ln END AS test_line_starts_at_1
FROM (SELECT MIN(line_number) AS min_ln FROM read_history(path='test/data'));

-- Test 3: All entries have timestamps
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' NULL timestamps' END AS test_timestamps_present
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data') WHERE timestamp_ms IS NULL);

-- Test 4: All entries have project
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' NULL projects' END AS test_projects_present
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data') WHERE project IS NULL);

-- Test 5: session_id present for all entries
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' NULL session_ids' END AS test_session_ids_present
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data') WHERE session_id IS NULL);

-- Test 6: display text present
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' NULL display values' END AS test_display_present
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data') WHERE display IS NULL);

-- Test 7: Project paths are real paths (not encoded)
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: encoded paths in history' END AS test_real_paths
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data') WHERE project LIKE '-%');

-- Test 8: No parse errors
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' parse errors' END AS test_no_parse_errors
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data') WHERE display LIKE 'Parse error:%');
