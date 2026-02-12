-- Test: Copilot read_conversations correctness and invariants

-- Test 1: Expected row count (53 events across 4 sessions)
SELECT CASE WHEN cnt = 53 THEN 'PASS' ELSE 'FAIL: expected 53 got ' || cnt END AS test_copilot_conversations_count
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot'));

-- Test 2: All rows have source='copilot'
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' non-copilot rows' END AS test_copilot_source
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot') WHERE source != 'copilot');

-- Test 3: session_id populated for all rows
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' empty session_ids' END AS test_copilot_session_id
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot') WHERE session_id = '' OR session_id IS NULL);

-- Test 4: All 16 event types mapped to message_type
SELECT CASE WHEN cnt >= 16 THEN 'PASS' ELSE 'FAIL: expected >=16 message_types got ' || cnt END AS test_copilot_message_types
FROM (SELECT COUNT(DISTINCT message_type) AS cnt FROM read_conversations(path='test/data_copilot'));

-- Test 5: User messages have content
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' user msgs without content' END AS test_copilot_user_content
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE message_type = 'user' AND message_content IS NULL);

-- Test 6: Assistant messages have content
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' assistant msgs without content' END AS test_copilot_assistant_content
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE message_type = 'assistant' AND message_content IS NULL);

-- Test 7: Tool start events have tool_name
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' tool_start without tool_name' END AS test_copilot_tool_name
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE message_type = 'tool_start' AND tool_name IS NULL);

-- Test 8: Timestamps present on all events
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' missing timestamps' END AS test_copilot_timestamps
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE timestamp IS NULL);

-- Test 9: UUID present on all events
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' missing UUIDs' END AS test_copilot_uuids
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE uuid IS NULL);

-- Test 10: Repository populated from workspace.yaml
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL: no repository values' END AS test_copilot_repository
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE repository IS NOT NULL);

-- Test 11: Git branch populated from workspace.yaml
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL: no git_branch values' END AS test_copilot_git_branch
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE git_branch IS NOT NULL);

-- Test 12: Version populated from session.start
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL: no version values' END AS test_copilot_version
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE version IS NOT NULL);

-- Test 13: No parse errors in test data
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' parse errors' END AS test_copilot_no_parse_errors
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE message_type = '_parse_error');

-- Test 14: Role mapping correct — user messages have role=user
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' user msgs with wrong role' END AS test_copilot_user_role
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE message_type = 'user' AND message_role != 'user');

-- Test 15: Role mapping correct — assistant messages have role=assistant
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' assistant msgs with wrong role' END AS test_copilot_assistant_role
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE message_type = 'assistant' AND message_role != 'assistant');

-- Test 16: Session events have NULL role
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' session events with non-null role' END AS test_copilot_session_role
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot')
      WHERE message_type IN ('session_start', 'session_resume', 'session_info', 'session_error',
                             'truncation', 'model_change', 'compaction_start', 'compaction_complete', 'abort')
      AND message_role IS NOT NULL);

-- Test 17: Explicit source parameter works
SELECT CASE WHEN cnt = 53 THEN 'PASS' ELSE 'FAIL: expected 53 got ' || cnt END AS test_copilot_explicit_source
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data_copilot', source='copilot'));

-- Test 18: Claude source='claude' verified on existing data
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' non-claude rows' END AS test_claude_source_column
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data') WHERE source != 'claude');
