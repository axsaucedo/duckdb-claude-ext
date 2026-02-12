-- Test: Copilot read_history correctness

-- Test 1: Expected row count (5 command history entries)
SELECT CASE WHEN cnt = 5 THEN 'PASS' ELSE 'FAIL: expected 5 got ' || cnt END AS test_copilot_history_count
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data_copilot'));

-- Test 2: All rows have source='copilot'
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' non-copilot rows' END AS test_copilot_history_source
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data_copilot') WHERE source != 'copilot');

-- Test 3: Display column populated for all entries
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' entries without display' END AS test_copilot_history_display
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data_copilot') WHERE display IS NULL);

-- Test 4: Line numbers are sequential starting from 1
SELECT CASE WHEN min_ln = 1 AND max_ln = 5 THEN 'PASS' ELSE 'FAIL: line_number range ' || min_ln || '-' || max_ln END AS test_copilot_history_line_numbers
FROM (SELECT MIN(line_number) AS min_ln, MAX(line_number) AS max_ln FROM read_history(path='test/data_copilot'));

-- Test 5: Copilot history has NULL timestamps (no timestamp in command-history-state.json)
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' entries with timestamp' END AS test_copilot_history_no_timestamps
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data_copilot') WHERE timestamp_ms IS NOT NULL);

-- Test 6: Claude history still has source='claude'
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' claude history without source' END AS test_claude_history_source
FROM (SELECT COUNT(*) AS cnt FROM read_history(path='test/data') WHERE source != 'claude');
