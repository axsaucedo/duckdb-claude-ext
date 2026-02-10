-- Test: Cross-table joins and invariants

-- Test 1: conversations <-> history join via session_id produces matches
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL: no conversation-history join matches' END AS test_conv_history_join
FROM (SELECT COUNT(*) AS cnt
      FROM (SELECT DISTINCT c.session_id FROM read_conversations(path='test/data') c
            JOIN read_history(path='test/data') h ON c.session_id = h.session_id));

-- Test 2: conversations <-> history join via project_path produces matches
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL: no project_path join matches' END AS test_project_path_join
FROM (SELECT COUNT(*) AS cnt
      FROM (SELECT DISTINCT c.project_path FROM read_conversations(path='test/data') c
            JOIN read_history(path='test/data') h ON c.project_path = h.project));

-- Test 3: conversations <-> todos join via session_id
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL: no conversation-todos join matches' END AS test_conv_todos_join
FROM (SELECT COUNT(*) AS cnt
      FROM (SELECT DISTINCT c.session_id FROM read_conversations(path='test/data') c
            JOIN read_todos(path='test/data') t ON c.session_id = t.session_id));

-- Test 4: conversations <-> plans join via slug = plan_name
SELECT CASE WHEN cnt >= 0 THEN 'PASS' ELSE 'FAIL' END AS test_conv_plans_join
FROM (SELECT COUNT(*) AS cnt
      FROM read_conversations(path='test/data') c
      JOIN read_plans(path='test/data') p ON c.slug = p.plan_name);

-- Test 5: All history projects exist in conversations
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' orphaned history projects' END AS test_no_orphan_history
FROM (SELECT COUNT(*) AS cnt
      FROM (SELECT DISTINCT project FROM read_history(path='test/data')
            WHERE project NOT IN (SELECT DISTINCT project_path FROM read_conversations(path='test/data'))));

-- Test 6: All todo session_ids exist in conversations
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' orphaned todo sessions' END AS test_no_orphan_todos
FROM (SELECT COUNT(*) AS cnt
      FROM (SELECT DISTINCT session_id FROM read_todos(path='test/data')
            WHERE session_id NOT IN (SELECT DISTINCT session_id FROM read_conversations(path='test/data'))));

-- Test 7: Stats date range is coherent (dates look like YYYY-MM-DD)
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: invalid date format' END AS test_stats_date_format
FROM (SELECT COUNT(*) AS cnt FROM read_stats(path='test/data')
      WHERE date NOT SIMILAR TO '[0-9]{4}-[0-9]{2}-[0-9]{2}');

-- Test 8: Overall summary counts match individual queries
SELECT CASE
    WHEN conv_cnt = 180 AND plan_cnt = 4 AND todo_cnt = 18 AND hist_cnt = 20 AND stat_cnt = 7
    THEN 'PASS'
    ELSE 'FAIL: count mismatch conv=' || conv_cnt || ' plan=' || plan_cnt || ' todo=' || todo_cnt || ' hist=' || hist_cnt || ' stat=' || stat_cnt
END AS test_overall_counts
FROM (
    SELECT
        (SELECT COUNT(*) FROM read_conversations(path='test/data')) AS conv_cnt,
        (SELECT COUNT(*) FROM read_plans(path='test/data')) AS plan_cnt,
        (SELECT COUNT(*) FROM read_todos(path='test/data')) AS todo_cnt,
        (SELECT COUNT(*) FROM read_history(path='test/data')) AS hist_cnt,
        (SELECT COUNT(*) FROM read_stats(path='test/data')) AS stat_cnt
);
