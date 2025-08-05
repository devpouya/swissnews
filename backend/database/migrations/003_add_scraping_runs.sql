-- Migration: 003_add_scraping_runs.sql
-- Add scraping runs tracking table for cron scheduler
-- Issue: https://github.com/devpouya/swissnews/issues/6

-- Create scraping_runs table for tracking scheduled runs
CREATE TABLE scraping_runs (
    id SERIAL PRIMARY KEY,
    run_id UUID UNIQUE DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'aborted')),
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    articles_scraped INTEGER DEFAULT 0,
    articles_updated INTEGER DEFAULT 0,
    articles_skipped INTEGER DEFAULT 0,
    outlets_processed INTEGER DEFAULT 0,
    outlets_failed INTEGER DEFAULT 0,
    total_duration_seconds INTEGER,
    error_message TEXT,
    error_traceback TEXT,
    lock_file_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_scraping_runs_status ON scraping_runs(status);
CREATE INDEX idx_scraping_runs_started_at ON scraping_runs(started_at DESC);
CREATE INDEX idx_scraping_runs_run_id ON scraping_runs(run_id);

-- Create table for detailed run logs per outlet
CREATE TABLE scraping_run_outlets (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES scraping_runs(run_id) ON DELETE CASCADE,
    outlet_name VARCHAR(100) NOT NULL,
    outlet_url VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failed', 'skipped')),
    articles_found INTEGER DEFAULT 0,
    articles_scraped INTEGER DEFAULT 0,
    duration_seconds INTEGER,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_scraping_run_outlets_run_id ON scraping_run_outlets(run_id);
CREATE INDEX idx_scraping_run_outlets_status ON scraping_run_outlets(status);