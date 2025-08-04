-- Swiss News Aggregator Database Initialization Script
-- This script initializes the complete database schema for the Swiss News Aggregator
-- 
-- Usage:
--   psql -d swissnews -f backend/database/init.sql
--   
-- Or with Docker:
--   docker exec -i postgres_container psql -U username -d swissnews < backend/database/init.sql
--
-- Prerequisites:
--   - PostgreSQL 12+ database created
--   - User with CREATE privileges
--
-- Author: Claude (GitHub Issue #2)
-- Created: 2025-08-04

\echo 'Starting Swiss News Aggregator database initialization...'

-- Set client encoding and timezone
SET client_encoding = 'UTF8';
SET timezone = 'UTC';

-- Create database if it doesn't exist (run as superuser)
-- CREATE DATABASE swissnews WITH ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8';

-- Connect to the target database
-- \c swissnews

\echo 'Setting up database extensions and configuration...'

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text matching

-- Set search path
SET search_path TO public;

\echo 'Running migration 001: Initial schema...'

-- Run the initial schema migration
\i backend/database/migrations/001_initial_schema.sql

\echo 'Loading Swiss outlets data from CSV...'

-- Create temporary table for CSV import
CREATE TEMP TABLE temp_outlets_import (
    news_website VARCHAR(255),
    url VARCHAR(500),
    original_language VARCHAR(50),
    owner VARCHAR(255),
    city VARCHAR(100),
    canton VARCHAR(50),
    occurrence VARCHAR(50),
    status VARCHAR(20)
);

-- Import CSV data (requires file access - adjust path as needed)
-- \copy temp_outlets_import FROM 'data/processed/swiss_news_outlets_with_urls.csv' WITH CSV HEADER;

-- Note: The above COPY command requires the CSV file to be accessible to PostgreSQL
-- If running in Docker or remote environment, you may need to:
-- 1. Mount the data directory as a volume
-- 2. Copy the CSV file to the container
-- 3. Or use an alternative import method

-- Transform and insert outlet data
\echo 'Transforming and inserting outlet data...'

-- Clear sample data first
DELETE FROM articles WHERE outlet_id IN (SELECT id FROM outlets WHERE name LIKE 'Test%' OR url LIKE '%test%');
DELETE FROM outlets WHERE name LIKE 'Test%' OR url LIKE '%test%';

-- Insert real outlets data (this would normally come from CSV import)
-- For now, we'll insert a representative sample of Swiss outlets

INSERT INTO outlets (name, url, language, owner, city, canton, occurrence, status) VALUES
-- German language outlets
('20 Minuten', 'https://www.20min.ch', 'de', 'TX Group', NULL, NULL, 'Daily', 'current'),
('Aargauer Zeitung', 'https://www.aargauerzeitung.ch', 'de', 'AZ Medien Gruppe', 'Aarau', 'Canton of Aargau', 'Daily', 'current'),
('Appenzeller Zeitung', 'https://www.appenzellerzeitung.ch', 'de', 'CH Media', NULL, 'Appenzell Ausserrhoden', 'Daily', 'current'),
('Basellandschaftliche Zeitung', 'https://www.bzbasel.ch', 'de', 'Luedin', 'Liestal', 'Basel-Landschaft', 'Daily', 'current'),
('Basler Zeitung', 'https://www.bazonline.ch', 'de', 'Basler Zeitung Medien', 'Basel', 'Basel-Stadt', 'Daily', 'current'),
('Berner Zeitung', 'https://www.bernerzeitung.ch', 'de', 'Espace Media Groupe/TX Group', 'Bern', 'Canton of Bern', 'Daily', 'current'),
('Bieler Tagblatt', 'https://www.bielertagblatt.ch', 'de', 'Gassmann AG', 'Biel/Bienne', 'Canton of Bern', 'Daily', 'current'),
('Blick', 'https://www.blick.ch', 'de', 'Ringier', 'Zurich', 'Canton of Zurich', 'Daily', 'current'),
('Neue Zürcher Zeitung', 'https://www.nzz.ch', 'de', 'NZZ-Mediengruppe', 'Zürich', 'Zürich', 'Daily', 'current'),
('Tages-Anzeiger', 'https://www.tagesanzeiger.ch', 'de', 'TX Group', 'Zurich', 'Canton of Zurich', 'Daily', 'current'),

-- French language outlets  
('24 heures', 'https://www.24heures.ch', 'fr', 'TX Group', 'Lausanne', 'Canton of Vaud', 'Daily', 'current'),
('Journal du Jura', 'https://www.journaldujura.ch', 'fr', 'Gassmann AG', 'Biel/Bienne', 'Canton of Bern', 'Daily', 'current'),
('Le Matin', 'https://www.lematin.ch', 'fr', 'Edipresse', 'Lausanne', 'Canton of Vaud', 'Daily', 'current'),
('Le Nouvelliste', 'https://www.lenouvelliste.ch', 'fr', 'Éditions Le Nouvelliste', 'Sion', 'Canton of Valais', 'Daily', 'current'),
('Le Temps', 'https://www.letemps.ch', 'fr', 'Fondation Aventinus', 'Geneva', 'Canton of Geneva', 'Daily', 'current'),
('La Tribune de Genève', 'https://www.tdg.ch', 'fr', 'TX Group', 'Geneva', 'Canton of Geneva', 'Daily', 'current'),

-- Italian language outlets
('Corriere del Ticino', 'https://www.cdt.ch', 'it', 'Tamedia', 'Lugano', 'Ticino', 'Daily', 'current'),
('La Regione Ticino', 'https://www.laregione.ch', 'it', 'Editrice La Regione SA', 'Bellinzona', 'Ticino', 'Daily', 'current'),
('Giornale del Popolo', 'https://www.gdp.ch', 'it', 'Giornale del Popolo SA', 'Lugano', 'Ticino', 'Daily', 'current'),

-- Romansh language outlets
('La Quotidiana', 'https://www.laquotidiana.ch', 'rm', 'Gammeter Media', 'Chur', 'Graubünden', 'Daily', 'current'),
('Engadiner Post', 'https://www.engadinerpost.ch', 'rm', 'Gammeter Media', 'St. Moritz', 'Graubünden', 'Weekly', 'current');

\echo 'Database initialization completed successfully!'

-- Display summary statistics
\echo 'Database Summary:'
SELECT 
    'Outlets' as table_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT language) as languages
FROM outlets
WHERE is_active = TRUE

UNION ALL

SELECT 
    'Articles' as table_name,
    COALESCE(COUNT(*), 0) as record_count,
    COUNT(DISTINCT language) as languages
FROM articles;

\echo 'Outlets by language:'
SELECT 
    language,
    COUNT(*) as outlet_count
FROM outlets 
WHERE is_active = TRUE
GROUP BY language
ORDER BY outlet_count DESC;

\echo 'Schema version:'
SELECT version, applied_at, description 
FROM schema_migrations 
ORDER BY applied_at DESC;

\echo ''
\echo '==========================================='
\echo 'Swiss News Aggregator Database Ready!'
\echo '==========================================='
\echo 'Next steps:'
\echo '1. Configure your application database connection'
\echo '2. Set up user permissions as needed'
\echo '3. Begin scraping articles from the outlets'
\echo '4. Monitor database performance and adjust indexes'
\echo ''
\echo 'Useful queries:'
\echo '- View all outlets: SELECT * FROM outlets;'
\echo '- View recent articles: SELECT * FROM recent_articles;'
\echo '- View outlet stats: SELECT * FROM outlet_stats;'
\echo '==========================================='