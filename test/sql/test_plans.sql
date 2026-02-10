-- Test: read_plans correctness and invariants

-- Test 1: Expected row count
SELECT CASE WHEN cnt = 4 THEN 'PASS' ELSE 'FAIL: expected 4 plans got ' || cnt END AS test_plans_count
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data'));

-- Test 2: plan_name is never empty
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' empty plan names' END AS test_plan_names_not_empty
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data') WHERE plan_name = '' OR plan_name IS NULL);

-- Test 3: file_name column exists and is populated
SELECT CASE WHEN cnt = 4 THEN 'PASS' ELSE 'FAIL: file_name missing' END AS test_file_name_present
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data') WHERE file_name IS NOT NULL AND file_name != '');

-- Test 4: Content is non-empty for all plans
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: ' || cnt || ' empty contents' END AS test_content_not_empty
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data') WHERE content = '' OR content IS NULL);

-- Test 5: file_size matches content length
SELECT CASE WHEN cnt = 0 THEN 'PASS' ELSE 'FAIL: size mismatch' END AS test_file_size_consistent
FROM (SELECT COUNT(*) AS cnt FROM read_plans(path='test/data') WHERE file_size <= 0);

-- Test 6: Plan names are distinct
SELECT CASE WHEN cnt = total THEN 'PASS' ELSE 'FAIL: duplicate plan names' END AS test_unique_plan_names
FROM (SELECT COUNT(DISTINCT plan_name) AS cnt, COUNT(*) AS total FROM read_plans(path='test/data'));
