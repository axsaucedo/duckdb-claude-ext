-- Test: Basic benchmark checks
-- These verify that queries complete in reasonable time (not exact timing, just sanity checks)

-- Benchmark 1: Full scan of conversations is not empty
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL: no rows scanned' END AS bench_conversations_scan
FROM (SELECT COUNT(*) AS cnt FROM read_conversations(path='test/data'));

-- Benchmark 2: Aggregation across all tables
SELECT CASE WHEN total > 0 THEN 'PASS' ELSE 'FAIL: aggregation produced 0' END AS bench_full_aggregation
FROM (
    SELECT
        (SELECT COUNT(*) FROM read_conversations(path='test/data')) +
        (SELECT COUNT(*) FROM read_plans(path='test/data')) +
        (SELECT COUNT(*) FROM read_todos(path='test/data')) +
        (SELECT COUNT(*) FROM read_history(path='test/data')) +
        (SELECT COUNT(*) FROM read_stats(path='test/data')) AS total
);

-- Benchmark 3: Cross-table join completes
SELECT CASE WHEN cnt >= 0 THEN 'PASS' ELSE 'FAIL' END AS bench_cross_join
FROM (
    SELECT COUNT(*) AS cnt
    FROM read_conversations(path='test/data') c
    JOIN read_history(path='test/data') h ON c.session_id = h.session_id
    JOIN read_todos(path='test/data') t ON c.session_id = t.session_id
);

-- Benchmark 4: GROUP BY with ORDER BY
SELECT CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL' END AS bench_group_order
FROM (
    SELECT COUNT(DISTINCT session_id) AS cnt
    FROM read_conversations(path='test/data')
    GROUP BY project_path
    ORDER BY cnt DESC
    LIMIT 1
);
