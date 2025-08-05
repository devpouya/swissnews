# Scratchpad: Issue #6 - Add cron-based periodic scraping scheduler (4-hour intervals)

**Summary**: Implement a robust cron-based scheduling system to run Swiss news scraping every 4 hours with proper locking, monitoring, and database tracking.
**Outcome**: Build production-ready scheduler with file-based locking, run status tracking, performance metrics, and graceful shutdown handling.

## Issue Reference
- **GitHub Issue**: [#6 Add cron-based periodic scraping scheduler](https://github.com/devpouya/swissnews/issues/6)
- **Issue State**: OPEN
- **Priority**: High - Core automation requirement from spec.md

## Problem Analysis

### Current State
- Existing scraper infrastructure: `BaseScraper`, `ArticleExtractor`, `DuplicateDetector`
- Database connection utilities in `backend/database/connection.py` 
- No automated scheduling system implemented
- Manual scraping process only

### Requirements from Issue
1. **Scheduling**: Run scraper every 4 hours automatically using cron
2. **Lock Management**: File-based locking to prevent overlapping executions  
3. **Database Tracking**: Store run status, metrics, and performance data
4. **Monitoring**: Track scraping duration, article counts, success/failure rates
5. **Graceful Shutdown**: Handle system restarts and interruptions properly
6. **Error Handling**: Comprehensive logging and alerting on failures

## Implementation Plan

### Phase 1: Database Schema for Run Tracking
**Task**: Create migration `003_add_scraping_runs.sql`
- Add `scraping_runs` table to track each execution
- Store run status, start/end times, article counts, errors
- Add indexes for performance monitoring queries

### Phase 2: ScrapingScheduler Core Class  
**Task**: Implement `backend/scraper/scheduler.py`
```python
class ScrapingScheduler:
    def run_scraping_cycle(self) -> Dict[str, Any]
    def check_lock_file(self) -> bool
    def create_lock_file(self) -> None  
    def cleanup_lock_file(self) -> None
    def log_run_metrics(self, metrics: Dict) -> None
    def handle_graceful_shutdown(self, signal, frame) -> None
```

### Phase 3: Scraper Runner Script
**Task**: Create `backend/scraper/runner.py`
- Entry point for cron execution 
- Initialize scheduler and handle command-line arguments
- Set up signal handlers for graceful shutdown
- Comprehensive error handling and logging

### Phase 4: File-based Locking Mechanism
**Task**: Implement robust locking system
- Use PID-based lock files in `/tmp/swissnews/`
- Check for stale locks (process no longer running)
- Automatic cleanup on normal exit
- Handle edge cases (system restart, process kill)

### Phase 5: Performance Monitoring
**Task**: Add comprehensive metrics tracking
- Scraping duration per outlet and total
- Article counts (new, updated, skipped)
- Success/failure rates and error categorization
- Database performance metrics

### Phase 6: Cron Configuration
**Task**: Create `scripts/setup_cron.sh`
- Automated cron job installation script
- Template for different environments (dev, staging, prod)
- Proper path and environment variable handling
- Logging configuration

## Technical Specifications

### Database Schema - Scraping Runs Table
```sql
CREATE TABLE scraping_runs (
    id SERIAL PRIMARY KEY,
    run_id UUID UNIQUE DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL, -- 'running', 'completed', 'failed', 'aborted'
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

CREATE INDEX idx_scraping_runs_status ON scraping_runs(status);
CREATE INDEX idx_scraping_runs_started_at ON scraping_runs(started_at DESC);
```

### Lock File Format
```text
# /tmp/swissnews/scraper.lock
PID=12345
STARTED=2025-08-05T10:00:00Z
RUN_ID=550e8400-e29b-41d4-a716-446655440000
HOST=production-server
```

### Cron Configuration  
```bash
# Run every 4 hours at minute 0
0 */4 * * * /path/to/venv/bin/python /path/to/swissnews/backend/scraper/runner.py --mode=cron >> /var/log/swissnews/cron.log 2>&1
```

### Performance Targets
- **Startup Time**: < 30 seconds to initialize and start scraping
- **Lock Check**: < 1 second to verify no existing run
- **Database Logging**: < 100ms per metric insert
- **Graceful Shutdown**: < 10 seconds to cleanup and exit

## Implementation Steps

### Step 1: Database Migration (1 hour)
1. Create `003_add_scraping_runs.sql` with run tracking table  
2. Add necessary indexes for performance
3. Test migration with existing database

### Step 2: ScrapingScheduler Class (2 hours)
4. Implement core scheduler logic in `backend/scraper/scheduler.py`
5. Add file-based locking mechanism  
6. Integrate with existing database connection utilities
7. Add comprehensive error handling and logging

### Step 3: Runner Script (1 hour)  
8. Create `backend/scraper/runner.py` as cron entry point
9. Add command-line argument parsing
10. Set up signal handlers for graceful shutdown
11. Configure logging for cron environment

### Step 4: Integration with Existing Scrapers (2 hours)
12. Integrate scheduler with `BaseScraper` and `ArticleExtractor`
13. Add outlet configuration loading from `config/outlets.yaml`
14. Implement duplicate detection integration
15. Add comprehensive metrics collection

### Step 5: Cron Setup Script (30 minutes)
16. Create `scripts/setup_cron.sh` for automated installation
17. Add environment-specific templates
18. Document deployment and configuration process

## Testing Strategy (Maximum 5 Tests)

### Test Coverage Plan
1. **`test_lock_file_management()`**: File locking, stale lock detection, cleanup
2. **`test_scraping_run_tracking()`**: Database run status logging and metrics  
3. **`test_graceful_shutdown()`**: Signal handling and proper cleanup
4. **`test_scheduler_integration()`**: End-to-end scheduling with existing scrapers
5. **`test_cron_runner_script()`**: Command-line interface and error handling

### Test Environment Setup
- Use in-memory SQLite for fast database tests
- Mock file system operations for lock file tests  
- Test signal handling with controlled processes
- Use pytest fixtures for scraper mocks

## Deliverables
- [ ] `backend/database/migrations/003_add_scraping_runs.sql`
- [ ] `backend/scraper/scheduler.py` - Core scheduling logic
- [ ] `backend/scraper/runner.py` - Cron entry point script
- [ ] `scripts/setup_cron.sh` - Automated cron installation
- [ ] Comprehensive test suite (5 tests maximum)
- [ ] Documentation for deployment and monitoring

## Acceptance Criteria  
- [ ] **Runs automatically every 4 hours**: Cron job correctly configured
- [ ] **Prevents overlapping executions**: File-based locking working
- [ ] **Comprehensive logging**: All run metrics stored in database
- [ ] **Handles system restarts gracefully**: Stale lock detection and cleanup
- [ ] **Performance metrics collected**: Duration, counts, success rates tracked
- [ ] **All tests passing**: Unit tests + integration tests pass
- [ ] **CI pipeline passes**: No regressions introduced

## Risk Mitigation
- **Lock File Corruption**: Use atomic file operations and PID validation
- **Database Connection Issues**: Implement connection retry logic with exponential backoff
- **Long-running Scrapes**: Add timeout monitoring and forced termination
- **Disk Space**: Implement log rotation and cleanup of old run data
- **System Resources**: Monitor memory usage and implement resource limits

## Timeline Estimate
- **Database Migration**: 1 hour
- **ScrapingScheduler Class**: 2 hours  
- **Runner Script**: 1 hour
- **Integration**: 2 hours
- **Cron Setup**: 30 minutes
- **Testing**: 2-3 hours
- **Documentation**: 1 hour
- **Total**: ~8-10 hours

## References  
- Issue #6: https://github.com/devpouya/swissnews/issues/6
- Spec requirement: "scraper has to run periodically, every 4 hours"
- Existing infrastructure: `backend/scraper/base.py`, `backend/database/connection.py`
- Duplicate detection: `backend/scraper/duplicates.py`

---

**Status**: 🔄 Planning Complete - Ready for Implementation  
**Branch**: feature/issue-6-cron-scheduler
**Next Steps**: Create database migration and begin ScrapingScheduler implementation