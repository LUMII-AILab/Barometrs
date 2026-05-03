BEGIN;

-- ============================================================
-- 1. articles — derive directly from url
-- ============================================================
UPDATE articles
SET website = CASE
    WHEN url ILIKE '%tvnet%'  THEN 'tvnet'
    WHEN url ILIKE '%apollo%' THEN 'apollo'
    WHEN url ILIKE '%delfi%'  THEN 'delfi'
    ELSE 'tvnet'
END;

-- ============================================================
-- 2. comments — join to articles; leave NULL for orphans
--    (comments with no matching article are excluded from the
--    prediction pipeline anyway)
-- ============================================================
UPDATE comments c
SET website = a.website
FROM articles a
WHERE c.article_id = a.article_id;

-- ============================================================
-- 3. predicted_comments — join to articles
-- ============================================================
UPDATE predicted_comments pc
SET website = a.website
FROM articles a
WHERE pc.article_id = a.article_id;

-- ============================================================
-- NOTE: aggressiveness_by_day, emotion_keywords_by_day
-- cannot be backfilled from URLs —
-- they are aggregates with no article FK. Truncate and rerun
-- the pipeline scripts after this migration.
-- ============================================================

COMMIT;

-- Sanity check — run after COMMIT to verify coverage
SELECT 'articles'          AS tbl, COUNT(*) AS total, COUNT(website) AS populated, COUNT(*) - COUNT(website) AS nulls FROM articles
UNION ALL
SELECT 'comments'          AS tbl, COUNT(*),           COUNT(website),              COUNT(*) - COUNT(website)           FROM comments
UNION ALL
SELECT 'predicted_comments' AS tbl, COUNT(*),          COUNT(website),              COUNT(*) - COUNT(website)           FROM predicted_comments
ORDER BY tbl;
