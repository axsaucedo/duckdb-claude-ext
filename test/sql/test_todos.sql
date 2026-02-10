-- Test: read_todos correctness and invariants

-- Test 1: Expected row count
SELECT CASE WHEN cnt = 18 THEN 'PASS' ELSE 'FAIL: expected 18 todos got ' || cnt END AS test_todos_count
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data'));

-- Test 2: session_id is never NULL
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' NULL session_ids' END AS test_session_id_not_null
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data') WHERE session_id IS NULL);

-- Test 3: agent_id is never NULL
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' NULL agent_ids' END AS test_agent_id_not_null
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data') WHERE agent_id IS NULL);

-- Test 4: file_name column exists and is populated
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL: no file_name values' END AS test_file_name_present
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data') WHERE file_name IS NOT NULL AND file_name != '');

-- Test 5: Status values are valid
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' invalid statuses' END AS test_valid_statuses
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data')
      WHERE status NOT IN ('pending', 'in_progress', 'completed', '_parse_error'));

-- Test 6: item_index starts at 0
SELECT CASE WHEN min_idx = 0 THEN 'PASS' ELSE 'FAIL: min index is ' || min_idx END AS test_index_starts_at_0
FROM (SELECT MIN(item_index) AS min_idx FROM read_todos(path='test/data'));

-- Test 7: 5 distinct todo files
SELECT CASE WHEN cnt = 5 THEN 'PASS' ELSE 'FAIL: expected 5 todo files got ' || cnt END AS test_todo_file_count
FROM (SELECT COUNT(DISTINCT file_name) AS cnt FROM read_todos(path='test/data'));

-- Test 8: No parse errors in test data
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' parse errors' END AS test_no_parse_errors
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data') WHERE status = '_parse_error');
