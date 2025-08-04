-- Migration: 001_initial_schema.sql
-- Description: Create initial database schema for Swiss News Aggregator
-- Created: 2025-08-04
-- Author: Claude (GitHub Issue #2)

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- OUTLETS TABLE
-- =====================================================
-- Stores Swiss news outlet information
CREATE TABLE outlets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500),  -- Nullable for outlets without websites
    language VARCHAR(5) NOT NULL CHECK (language IN ('de', 'fr', 'it', 'rm')),
    owner VARCHAR(255),
    city VARCHAR(100),
    canton VARCHAR(50),
    occurrence VARCHAR(50),  -- Daily, Weekly, Monthly, etc.
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'current' CHECK (status IN ('current', 'discontinued', 'suspended', 'merged')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments for outlets table
COMMENT ON TABLE outlets IS 'Swiss news outlets and their metadata';
COMMENT ON COLUMN outlets.name IS 'Name of the news outlet';
COMMENT ON COLUMN outlets.url IS 'Website URL of the outlet, nullable if no website';
COMMENT ON COLUMN outlets.language IS 'Primary language: de=German, fr=French, it=Italian, rm=Romansh';
COMMENT ON COLUMN outlets.owner IS 'Owner or parent company of the outlet';
COMMENT ON COLUMN outlets.occurrence IS 'Publication frequency (Daily, Weekly, Monthly, etc.)';
COMMENT ON COLUMN outlets.status IS 'Current operational status of the outlet';

-- =====================================================
-- ARTICLES TABLE  
-- =====================================================
-- Stores scraped articles and their metadata
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    url VARCHAR(1000) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    author VARCHAR(255),
    publish_date TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    language VARCHAR(5) CHECK (language IN ('de', 'fr', 'it', 'rm')),
    outlet_id INT NOT NULL REFERENCES outlets(id) ON DELETE CASCADE,
    is_paywalled BOOLEAN DEFAULT FALSE,
    word_count INT CHECK (word_count >= 0),
    tags TEXT[]
);

-- Add comments for articles table
COMMENT ON TABLE articles IS 'Scraped news articles with full content and metadata';
COMMENT ON COLUMN articles.url IS 'Unique URL of the article';
COMMENT ON COLUMN articles.title IS 'Article headline/title';
COMMENT ON COLUMN articles.content IS 'Full article text content';
COMMENT ON COLUMN articles.summary IS 'Article summary or excerpt';
COMMENT ON COLUMN articles.publish_date IS 'Original publication date from the outlet';
COMMENT ON COLUMN articles.scraped_at IS 'When the article was scraped by our system';
COMMENT ON COLUMN articles.outlet_id IS 'Reference to the outlet that published this article';
COMMENT ON COLUMN articles.is_paywalled IS 'Whether the article is behind a paywall';
COMMENT ON COLUMN articles.word_count IS 'Number of words in the article content';
COMMENT ON COLUMN articles.tags IS 'Array of tags/categories for the article';

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Outlets indexes
CREATE INDEX idx_outlets_language ON outlets(language);
CREATE INDEX idx_outlets_active ON outlets(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_outlets_status ON outlets(status);
CREATE INDEX idx_outlets_name ON outlets(name);

-- Articles indexes for common queries
CREATE INDEX idx_articles_outlet_date ON articles(outlet_id, publish_date DESC NULLS LAST);
CREATE INDEX idx_articles_language_date ON articles(language, publish_date DESC NULLS LAST);
CREATE INDEX idx_articles_scraped_at ON articles(scraped_at DESC);
CREATE INDEX idx_articles_publish_date ON articles(publish_date DESC NULLS LAST);
CREATE INDEX idx_articles_outlet_scraped ON articles(outlet_id, scraped_at DESC);

-- Partial indexes for better performance
CREATE INDEX idx_articles_recent ON articles(publish_date DESC) 
    WHERE publish_date > CURRENT_DATE - INTERVAL '90 days';
CREATE INDEX idx_articles_paywalled ON articles(outlet_id, publish_date DESC) 
    WHERE is_paywalled = TRUE;

-- Full-text search indexes
CREATE INDEX idx_articles_title_fts ON articles USING GIN(to_tsvector('simple', title));
CREATE INDEX idx_articles_content_fts ON articles USING GIN(to_tsvector('simple', content));

-- Tags array index
CREATE INDEX idx_articles_tags ON articles USING GIN(tags);

-- =====================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for outlets table
CREATE TRIGGER update_outlets_updated_at 
    BEFORE UPDATE ON outlets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for articles table
CREATE TRIGGER update_articles_updated_at 
    BEFORE UPDATE ON articles 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ADDITIONAL CONSTRAINTS AND VALIDATIONS
-- =====================================================

-- Ensure URLs are properly formatted
ALTER TABLE outlets ADD CONSTRAINT outlets_url_format 
    CHECK (url IS NULL OR url ~ '^https?://');

ALTER TABLE articles ADD CONSTRAINT articles_url_format 
    CHECK (url ~ '^https?://');

-- Ensure reasonable date ranges
ALTER TABLE articles ADD CONSTRAINT articles_publish_date_reasonable 
    CHECK (publish_date IS NULL OR publish_date <= CURRENT_TIMESTAMP);

ALTER TABLE articles ADD CONSTRAINT articles_scraped_at_reasonable 
    CHECK (scraped_at <= CURRENT_TIMESTAMP);

-- =====================================================
-- SAMPLE DATA FOR TESTING
-- =====================================================

-- Insert a few sample outlets for testing (will be replaced with real data)
INSERT INTO outlets (name, url, language, owner, city, canton, occurrence, status) VALUES
('Neue Zürcher Zeitung', 'https://www.nzz.ch', 'de', 'NZZ-Mediengruppe', 'Zürich', 'Zürich', 'Daily', 'current'),
('Le Temps', 'https://www.letemps.ch', 'fr', 'Fondation Aventinus', 'Geneva', 'Geneva', 'Daily', 'current'),
('Corriere del Ticino', 'https://www.cdt.ch', 'it', 'Tamedia', 'Lugano', 'Ticino', 'Daily', 'current'),
('La Quotidiana', 'https://www.laquotidiana.ch', 'rm', 'Gammeter Media', 'Chur', 'Graubünden', 'Daily', 'current');

-- Insert sample articles for testing
INSERT INTO articles (url, title, content, summary, author, publish_date, language, outlet_id, is_paywalled, word_count, tags) VALUES
('https://www.nzz.ch/test-article-1', 'Test Article 1', 'This is a test article content in German.', 'Test summary', 'Test Author', '2025-08-04 10:00:00', 'de', 1, FALSE, 150, ARRAY['test', 'politics']),
('https://www.letemps.ch/test-article-2', 'Article de Test 2', 'Ceci est un contenu d''article de test en français.', 'Résumé de test', 'Auteur Test', '2025-08-04 11:00:00', 'fr', 2, TRUE, 200, ARRAY['test', 'economy']),
('https://www.cdt.ch/test-article-3', 'Articolo di Test 3', 'Questo è un contenuto di articolo di test in italiano.', 'Riassunto di test', 'Autore Test', '2025-08-04 12:00:00', 'it', 3, FALSE, 180, ARRAY['test', 'culture']);

-- =====================================================
-- USEFUL VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for articles with outlet information
CREATE VIEW articles_with_outlets AS
SELECT 
    a.id,
    a.url,
    a.title,
    a.summary,
    a.author,
    a.publish_date,
    a.scraped_at,
    a.language,
    a.is_paywalled,
    a.word_count,
    a.tags,
    o.name as outlet_name,
    o.owner as outlet_owner,
    o.city as outlet_city,
    o.canton as outlet_canton
FROM articles a
JOIN outlets o ON a.outlet_id = o.id
WHERE o.is_active = TRUE;

COMMENT ON VIEW articles_with_outlets IS 'Articles joined with their outlet information, filtered to active outlets only';

-- View for recent articles (last 30 days)
CREATE VIEW recent_articles AS
SELECT *
FROM articles_with_outlets
WHERE publish_date > CURRENT_DATE - INTERVAL '30 days'
ORDER BY publish_date DESC;

COMMENT ON VIEW recent_articles IS 'Articles published in the last 30 days with outlet information';

-- View for outlet statistics
CREATE VIEW outlet_stats AS
SELECT 
    o.id,
    o.name,
    o.language,
    o.city,
    o.canton,
    COUNT(a.id) as total_articles,
    COUNT(CASE WHEN a.publish_date > CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as articles_last_week,
    COUNT(CASE WHEN a.publish_date > CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as articles_last_month,
    MAX(a.scraped_at) as last_scraped,
    AVG(a.word_count) as avg_word_count
FROM outlets o
LEFT JOIN articles a ON o.id = a.outlet_id
WHERE o.is_active = TRUE
GROUP BY o.id, o.name, o.language, o.city, o.canton
ORDER BY total_articles DESC;

COMMENT ON VIEW outlet_stats IS 'Statistics for each outlet including article counts and scraping activity';

-- =====================================================
-- DATABASE METADATA
-- =====================================================

-- Track schema version and migration info
CREATE TABLE schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_migrations (version, description) VALUES 
('001', 'Initial schema with outlets and articles tables');

-- =====================================================
-- GRANTS AND PERMISSIONS
-- =====================================================
-- Note: Specific permissions should be configured based on application users
-- This is a placeholder for production deployment

-- Grant usage on sequences (needed for SERIAL columns)
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON outlets, articles TO app_user;
-- GRANT SELECT ON articles_with_outlets, recent_articles, outlet_stats TO app_user;

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Swiss News Aggregator database schema (v001) created successfully!';
    RAISE NOTICE 'Created tables: outlets, articles';
    RAISE NOTICE 'Created indexes: % total indexes', (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public');
    RAISE NOTICE 'Created views: articles_with_outlets, recent_articles, outlet_stats';
    RAISE NOTICE 'Sample data inserted for testing';
END $$;