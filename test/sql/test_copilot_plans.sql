-- Test: Copilot read_plans correctness

-- Test 1: Expected row count (1 plan file in session bbbb)
SELECT CASE WHEN cnt = 1 THEN 'PASS' ELSE 'FAIL: expected 1 got ' || cnt END AS test_copilot_plans_count
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data_copilot'));

-- Test 2: All rows have source='copilot'
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' non-copilot rows' END AS test_copilot_plans_source
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data_copilot') WHERE source != 'copilot');

-- Test 3: Session ID populated
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' plans without session_id' END AS test_copilot_plans_session_id
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data_copilot') WHERE session_id IS NULL);

-- Test 4: Content is non-empty
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' plans with empty content' END AS test_copilot_plans_content
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data_copilot') WHERE content = '' OR content IS NULL);

-- Test 5: File size > 0
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' plans with zero size' END AS test_copilot_plans_file_size
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data_copilot') WHERE file_size <= 0);

-- Test 6: Claude plans still have source='claude'
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' claude plans without source' END AS test_claude_plans_source
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data') WHERE source != 'claude');

-- Test 7: Claude plans have NULL session_id (Claude plans are global)
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' claude plans with session_id' END AS test_claude_plans_session_id
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data') WHERE session_id IS NOT NULL);
