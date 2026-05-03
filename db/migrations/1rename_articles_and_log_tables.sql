BEGIN;

-- ============================================================
-- TABLE RENAMES
-- (PostgreSQL auto-updates FK references on table rename)
-- ============================================================
ALTER TABLE raw_comments RENAME TO comments;
ALTER TABLE raw_articles RENAME TO articles;
ALTER TABLE log_raw_articles_imports RENAME TO log_articles_imports;
ALTER TABLE log_raw_comments_imports RENAME TO log_comments_imports;

-- ============================================================
-- SEQUENCE RENAMES
-- ============================================================
ALTER SEQUENCE raw_comments_id_seq RENAME TO comments_id_seq;
ALTER SEQUENCE raw_articles_article_id_seq RENAME TO articles_article_id_seq;
ALTER SEQUENCE log_raw_articles_imports_import_id_seq RENAME TO log_articles_imports_import_id_seq;
ALTER SEQUENCE log_raw_comments_imports_import_id_seq RENAME TO log_comments_imports_import_id_seq;

-- ============================================================
-- INDEX RENAMES (stale names from renamed tables)
-- ============================================================
ALTER INDEX ix_raw_comments_article_id RENAME TO ix_comments_article_id;
ALTER INDEX ix_raw_comments_comment_lang RENAME TO ix_comments_comment_lang;
ALTER INDEX ix_raw_comments_timestamp RENAME TO ix_comments_timestamp;
ALTER INDEX ix_raw_articles_headline_lang RENAME TO ix_articles_headline_lang;
ALTER INDEX ix_raw_articles_pub_timestamp RENAME TO ix_articles_pub_timestamp;
ALTER INDEX ix_log_raw_articles_imports_file_name RENAME TO ix_log_articles_imports_file_name;
ALTER INDEX ix_log_raw_articles_imports_status RENAME TO ix_log_articles_imports_status;
ALTER INDEX ix_log_raw_comments_imports_file_name RENAME TO ix_log_comments_imports_file_name;
ALTER INDEX ix_log_raw_comments_imports_status RENAME TO ix_log_comments_imports_status;

-- ============================================================
-- ADD website COLUMN
-- ============================================================
-- Base tables
ALTER TABLE comments ADD COLUMN website VARCHAR;
ALTER TABLE articles ADD COLUMN website VARCHAR;
ALTER TABLE log_articles_imports ADD COLUMN website VARCHAR;
ALTER TABLE log_comments_imports ADD COLUMN website VARCHAR;

-- Derived / aggregation tables
ALTER TABLE predicted_comments ADD COLUMN website VARCHAR;
ALTER TABLE aggressiveness_by_day ADD COLUMN website VARCHAR;
ALTER TABLE emotion_keywords_by_day ADD COLUMN website VARCHAR;

-- ============================================================
-- INDEXES ON website
-- ============================================================
CREATE INDEX ix_comments_website ON comments(website);
CREATE INDEX ix_articles_website ON articles(website);
CREATE INDEX ix_predicted_comments_website ON predicted_comments(website);
CREATE INDEX ix_aggressiveness_by_day_website ON aggressiveness_by_day(website);
CREATE INDEX ix_emotion_keywords_by_day_website ON emotion_keywords_by_day(website);

COMMIT;
