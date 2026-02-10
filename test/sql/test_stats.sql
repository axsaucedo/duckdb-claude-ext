-- Test: read_stats correctness and invariants

-- Test 1: Expected row count
SELECT CASE WHEN cnt = 7 THEN 'PASS' ELSE 'FAIL: expected 7 stats rows got ' || cnt END AS test_stats_count
FROM (SELECT COUNT(*) AS cnt FROM read_stats(path='test/data'));

-- Test 2: Date is never empty
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' empty dates' END AS test_dates_not_empty
FROM (SELECT COUNT(*) AS cnt FROM read_stats(path='test/data') WHERE date = '' OR date IS NULL);

-- Test 3: Counts are non-negative
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: negative counts found' END AS test_non_negative_counts
FROM (SELECT COUNT(*) AS cnt FROM read_stats(path='test/data')
      WHERE message_count < 0 OR session_count < 0 OR tool_call_count < 0);

-- Test 4: Dates are unique
SELECT CASE WHEN cnt = total THEN 'PASS' ELSE 'FAIL: duplicate dates' END AS test_unique_dates
FROM (SELECT COUNT(DISTINCT date) AS cnt, COUNT(*) AS total FROM read_stats(path='test/data'));

-- Test 5: Total activity is positive
SELECT CASE WHEN total > 0 THEN 'PASS' ELSE 'FAIL: no activity' END AS test_positive_activity
FROM (SELECT SUM(message_count) + SUM(session_count) + SUM(tool_call_count) AS total
      FROM read_stats(path='test/data'));
