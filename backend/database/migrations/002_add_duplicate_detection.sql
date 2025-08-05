-- Migration: 002_add_duplicate_detection.sql
-- Description: Add duplicate detection capabilities to articles table
-- Created: 2025-08-04
-- Author: Claude (GitHub Issue #5)
-- Dependencies: 001_initial_schema.sql

-- =====================================================
-- ADD DUPLICATE DETECTION FIELDS
-- =====================================================

-- Add content hash field for fast duplicate detection
ALTER TABLE articles ADD COLUMN content_hash VARCHAR(64);

-- Add comments for new fields
COMMENT ON COLUMN articles.content_hash IS 'SHA-256 hash of normalized article content for duplicate detection';

-- =====================================================
-- INDEXES FOR DUPLICATE DETECTION PERFORMANCE
-- =====================================================

-- Content hash index for O(1) duplicate lookups
CREATE INDEX idx_articles_content_hash ON articles(content_hash) WHERE content_hash IS NOT NULL;

-- Title and publication date composite index for similarity searches
CREATE INDEX idx_articles_title_date ON articles(title, publish_date DESC NULLS LAST);

-- Enhanced title similarity search using trigrams
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_articles_title_similarity ON articles USING GIN(title gin_trgm_ops);

-- Outlet and date index for time-based proximity searches
CREATE INDEX idx_articles_outlet_date_proximity ON articles(outlet_id, publish_date DESC NULLS LAST);

-- =====================================================
-- DUPLICATE DETECTION CONFIGURATION TABLE
-- =====================================================

-- Configuration table for duplicate detection thresholds
CREATE TABLE duplicate_detection_config (
    id SERIAL PRIMARY KEY,
    similarity_threshold DECIMAL(4,3) DEFAULT 0.800 CHECK (similarity_threshold BETWEEN 0.0 AND 1.0),
    title_similarity_threshold DECIMAL(4,3) DEFAULT 0.850 CHECK (title_similarity_threshold BETWEEN 0.0 AND 1.0),
    time_proximity_hours INT DEFAULT 24 CHECK (time_proximity_hours > 0),
    max_similarity_search_days INT DEFAULT 90 CHECK (max_similarity_search_days > 0),
    enable_content_hashing BOOLEAN DEFAULT TRUE,
    enable_title_similarity BOOLEAN DEFAULT TRUE,
    enable_time_proximity BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments for configuration table
COMMENT ON TABLE duplicate_detection_config IS 'Configuration settings for article duplicate detection';
COMMENT ON COLUMN duplicate_detection_config.similarity_threshold IS 'Minimum content similarity score (0.0-1.0) to consider articles duplicates';
COMMENT ON COLUMN duplicate_detection_config.title_similarity_threshold IS 'Minimum title similarity score (0.0-1.0) to consider articles similar';
COMMENT ON COLUMN duplicate_detection_config.time_proximity_hours IS 'Hours within which articles are considered time-proximate';
COMMENT ON COLUMN duplicate_detection_config.max_similarity_search_days IS 'Maximum days back to search for similar articles (performance optimization)';

-- Insert default configuration
INSERT INTO duplicate_detection_config (
    similarity_threshold,
    title_similarity_threshold,
    time_proximity_hours,
    max_similarity_search_days
) VALUES (0.800, 0.850, 24, 90);

-- =====================================================
-- DUPLICATE DETECTION STATISTICS TABLE
-- =====================================================

-- Table to track duplicate detection statistics
CREATE TABLE duplicate_detection_stats (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    total_articles_processed INT DEFAULT 0,
    duplicates_found_url INT DEFAULT 0,
    duplicates_found_content INT DEFAULT 0,
    articles_updated INT DEFAULT 0,
    articles_skipped INT DEFAULT 0,
    avg_detection_time_ms INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date)
);

COMMENT ON TABLE duplicate_detection_stats IS 'Daily statistics for duplicate detection performance';

-- =====================================================
-- FUNCTIONS FOR DUPLICATE DETECTION
-- =====================================================

-- Function to calculate content hash (to be called from Python)
CREATE OR REPLACE FUNCTION update_article_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    -- Content hash will be calculated in Python using SHA-256
    -- This trigger ensures updated_at is set when content_hash changes
    IF NEW.content_hash IS DISTINCT FROM OLD.content_hash THEN
        NEW.updated_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update timestamps when content_hash changes
CREATE TRIGGER update_article_content_hash_trigger
    BEFORE UPDATE ON articles
    FOR EACH ROW
    EXECUTE FUNCTION update_article_content_hash();

-- =====================================================
-- VIEWS FOR DUPLICATE DETECTION
-- =====================================================

-- View for recent articles (for similarity searches)
CREATE VIEW recent_articles_for_similarity AS
SELECT
    id,
    url,
    title,
    content,
    content_hash,
    author,
    publish_date,
    scraped_at,
    language,
    outlet_id,
    word_count,
    tags
FROM articles
WHERE publish_date > CURRENT_DATE - INTERVAL '90 days'
   OR scraped_at > CURRENT_TIMESTAMP - INTERVAL '90 days'
ORDER BY publish_date DESC NULLS LAST, scraped_at DESC;

COMMENT ON VIEW recent_articles_for_similarity IS 'Recent articles for efficient similarity search queries';

-- View for duplicate detection statistics
CREATE VIEW duplicate_detection_daily_stats AS
SELECT
    date,
    total_articles_processed,
    duplicates_found_url,
    duplicates_found_content,
    articles_updated,
    articles_skipped,
    ROUND((duplicates_found_url + duplicates_found_content)::DECIMAL / NULLIF(total_articles_processed, 0) * 100, 2) as duplicate_rate_percent,
    avg_detection_time_ms
FROM duplicate_detection_stats
ORDER BY date DESC;

COMMENT ON VIEW duplicate_detection_daily_stats IS 'Daily duplicate detection statistics with calculated rates';

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Function to get duplicate detection configuration
CREATE OR REPLACE FUNCTION get_duplicate_detection_config()
RETURNS TABLE(
    similarity_threshold DECIMAL(4,3),
    title_similarity_threshold DECIMAL(4,3),
    time_proximity_hours INT,
    max_similarity_search_days INT,
    enable_content_hashing BOOLEAN,
    enable_title_similarity BOOLEAN,
    enable_time_proximity BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ddc.similarity_threshold,
        ddc.title_similarity_threshold,
        ddc.time_proximity_hours,
        ddc.max_similarity_search_days,
        ddc.enable_content_hashing,
        ddc.enable_title_similarity,
        ddc.enable_time_proximity
    FROM duplicate_detection_config ddc
    ORDER BY ddc.id DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to update daily statistics
CREATE OR REPLACE FUNCTION update_duplicate_detection_stats(
    p_articles_processed INT DEFAULT 1,
    p_duplicates_url INT DEFAULT 0,
    p_duplicates_content INT DEFAULT 0,
    p_articles_updated INT DEFAULT 0,
    p_articles_skipped INT DEFAULT 0,
    p_detection_time_ms INT DEFAULT 0
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO duplicate_detection_stats AS dds (
        date,
        total_articles_processed,
        duplicates_found_url,
        duplicates_found_content,
        articles_updated,
        articles_skipped,
        avg_detection_time_ms
    ) VALUES (
        CURRENT_DATE,
        p_articles_processed,
        p_duplicates_url,
        p_duplicates_content,
        p_articles_updated,
        p_articles_skipped,
        p_detection_time_ms
    )
    ON CONFLICT (date) DO UPDATE SET
        total_articles_processed = dds.total_articles_processed + p_articles_processed,
        duplicates_found_url = dds.duplicates_found_url + p_duplicates_url,
        duplicates_found_content = dds.duplicates_found_content + p_duplicates_content,
        articles_updated = dds.articles_updated + p_articles_updated,
        articles_skipped = dds.articles_skipped + p_articles_skipped,
        avg_detection_time_ms = CASE
            WHEN dds.total_articles_processed + p_articles_processed > 0 THEN
                ((dds.avg_detection_time_ms * dds.total_articles_processed) + p_detection_time_ms) /
                (dds.total_articles_processed + p_articles_processed)
            ELSE 0
        END;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- POPULATE CONTENT HASHES FOR EXISTING DATA
-- =====================================================

-- Note: Content hashes for existing articles will be calculated
-- and populated by the Python duplicate detection system during first run.
-- This is more efficient than trying to do text processing in SQL.

-- =====================================================
-- UPDATE SCHEMA MIGRATIONS TABLE
-- =====================================================

INSERT INTO schema_migrations (version, description) VALUES
('002', 'Add duplicate detection capabilities with content hashing and similarity indexes');

-- =====================================================
-- PERFORMANCE ANALYSIS QUERIES
-- =====================================================

-- The following queries can be used to analyze duplicate detection performance:

-- 1. Check index usage on content_hash lookups:
-- EXPLAIN ANALYZE SELECT * FROM articles WHERE content_hash = 'sample_hash';

-- 2. Check title similarity performance:
-- EXPLAIN ANALYZE SELECT * FROM articles WHERE title % 'sample title' ORDER BY similarity(title, 'sample title') DESC LIMIT 10;

-- 3. Check recent articles view performance:
-- EXPLAIN ANALYZE SELECT * FROM recent_articles_for_similarity LIMIT 100;

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE 'Duplicate detection migration (v002) completed successfully!';
    RAISE NOTICE 'Added content_hash field and % performance indexes', (
        SELECT COUNT(*) FROM pg_indexes
        WHERE schemaname = 'public'
        AND indexname LIKE 'idx_articles_%'
    );
    RAISE NOTICE 'Created duplicate_detection_config table with default thresholds';
    RAISE NOTICE 'Created duplicate_detection_stats table for monitoring';
    RAISE NOTICE 'Added utility functions and views for duplicate detection';
    RAISE NOTICE 'Ready for DuplicateDetector class implementation';
END $$;
