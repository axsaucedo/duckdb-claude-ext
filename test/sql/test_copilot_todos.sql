-- Test: Copilot read_todos correctness (extracted from checkpoint markdown checklists)

-- Test 1: Expected row count (4 checklist items in session aaaa checkpoint)
SELECT CASE WHEN cnt = 4 THEN 'PASS' ELSE 'FAIL: expected 4 got ' || cnt END AS test_copilot_todos_count
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data_copilot'));

-- Test 2: All rows have source='copilot'
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' non-copilot rows' END AS test_copilot_todos_source
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data_copilot') WHERE source != 'copilot');

-- Test 3: Session ID populated
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' todos without session_id' END AS test_copilot_todos_session_id
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data_copilot') WHERE session_id = '' OR session_id IS NULL);

-- Test 4: Status is completed or pending
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' todos with invalid status' END AS test_copilot_todos_status
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data_copilot') WHERE status NOT IN ('completed', 'pending'));

-- Test 5: Content is non-empty
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' todos with empty content' END AS test_copilot_todos_content
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data_copilot') WHERE content = '' OR content IS NULL);

-- Test 6: Completed count matches (2 checked items in checkpoint)
SELECT CASE WHEN cnt = 2 THEN 'PASS' ELSE 'FAIL: expected 2 completed got ' || cnt END AS test_copilot_todos_completed
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data_copilot') WHERE status = 'completed');

-- Test 7: Pending count matches (2 unchecked items in checkpoint)
SELECT CASE WHEN cnt = 2 THEN 'PASS' ELSE 'FAIL: expected 2 pending got ' || cnt END AS test_copilot_todos_pending
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data_copilot') WHERE status = 'pending');

-- Test 8: Claude todos still have source='claude'
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' claude todos without source' END AS test_claude_todos_source
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data') WHERE source != 'claude');

-- Test 9: Copilot agent_id is NULL (not applicable)
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' copilot todos with agent_id' END AS test_copilot_todos_no_agent_id
FROM (SELECT COUNT(*) AS cnt FROM read_todos(path='test/data_copilot') WHERE agent_id IS NOT NULL);
