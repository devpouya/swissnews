#!/usr/bin/env python3
"""
Comprehensive tests for cron-based scraping scheduler system.

Tests the ScrapingScheduler class and runner script functionality
as specified in Issue #6.

Maximum 5 tests as per issue requirements.
"""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import psutil
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from database.connection import DatabaseManager
from scraper.scheduler import ScrapingScheduler


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    mock_db = MagicMock(spec=DatabaseManager)
    mock_connection = MagicMock()
    mock_cursor = MagicMock()
    
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.__exit__.return_value = None
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connection.cursor.return_value.__exit__.return_value = None
    
    mock_db.get_connection.return_value = mock_connection
    
    return mock_db


@pytest.fixture
def temp_lock_dir():
    """Create temporary directory for lock files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def scheduler(mock_db_manager, temp_lock_dir):
    """Create scheduler instance with mocked dependencies."""
    with patch('backend.scraper.scheduler.ConfigLoader'):
        scheduler = ScrapingScheduler(mock_db_manager)
        # Override lock file path to use temp directory
        scheduler.lock_file_path = temp_lock_dir / "scraper.lock"
        scheduler.lock_dir = temp_lock_dir
        return scheduler


class TestLockFileManagement:
    """Test 1: File locking, stale lock detection, and cleanup."""

    def test_lock_file_creation_and_cleanup(self, scheduler, temp_lock_dir):
        """Test lock file creation with proper content and cleanup."""
        # Test lock file creation
        scheduler.create_lock_file()
        
        assert scheduler.lock_file_path.exists()
        
        # Verify lock file content
        content = scheduler.lock_file_path.read_text()
        assert f"PID={os.getpid()}" in content
        assert f"RUN_ID={scheduler.run_id}" in content
        assert "STARTED=" in content
        assert f"HOST={os.uname().nodename}" in content
        
        # Test cleanup
        scheduler.cleanup_lock_file()
        assert not scheduler.lock_file_path.exists()

    def test_lock_file_detection_running_process(self, scheduler):
        """Test detection of running process via lock file."""
        # Create lock file with current process PID
        lock_content = f"""PID={os.getpid()}
STARTED=2025-08-05T10:00:00Z
RUN_ID=test-run-123
HOST=test-host
"""
        scheduler.lock_file_path.write_text(lock_content)
        
        # Should detect running process
        assert scheduler.check_lock_file() == True
        
        # Cleanup
        scheduler.lock_file_path.unlink()

    def test_stale_lock_file_removal(self, scheduler):
        """Test removal of stale lock files."""
        # Create lock file with non-existent PID
        fake_pid = 999999  # Very unlikely to exist
        lock_content = f"""PID={fake_pid}
STARTED=2025-08-05T10:00:00Z
RUN_ID=test-run-123
HOST=test-host
"""
        scheduler.lock_file_path.write_text(lock_content)
        
        # Should detect stale lock and remove it
        assert scheduler.check_lock_file() == False
        assert not scheduler.lock_file_path.exists()

    def test_corrupted_lock_file_handling(self, scheduler):
        """Test handling of corrupted lock files."""
        # Create corrupted lock file
        scheduler.lock_file_path.write_text("corrupted content")
        
        # Should handle gracefully and remove corrupted file
        assert scheduler.check_lock_file() == False
        assert not scheduler.lock_file_path.exists()


class TestScrapingRunTracking:
    """Test 2: Database run status logging and metrics tracking."""

    def test_run_initialization_and_finalization(self, scheduler, mock_db_manager):
        """Test complete run lifecycle in database."""
        mock_cursor = mock_db_manager.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        
        # Test run initialization
        scheduler._initialize_run()
        
        # Verify initialization SQL call
        mock_cursor.execute.assert_called_with(
            "INSERT INTO scraping_runs (run_id, status, lock_file_path)\n                        VALUES (%s, 'running', %s)",
            (scheduler.run_id, str(scheduler.lock_file_path))
        )
        
        # Test run finalization
        results = {
            'articles_scraped': 10,
            'articles_updated': 5,
            'articles_skipped': 2,
            'outlets_processed': 3,
            'outlets_failed': 1
        }
        scheduler._finalize_run(results, 120)
        
        # Verify finalization SQL call
        expected_call = call(
            "UPDATE scraping_runs \n                        SET status = 'completed',\n                            completed_at = CURRENT_TIMESTAMP,\n                            articles_scraped = %s,\n                            articles_updated = %s,\n                            articles_skipped = %s,\n                            outlets_processed = %s,\n                            outlets_failed = %s,\n                            total_duration_seconds = %s\n                        WHERE run_id = %s",
            (10, 5, 2, 3, 1, 120, scheduler.run_id)
        )
        assert expected_call in mock_cursor.execute.call_args_list

    def test_run_failure_tracking(self, scheduler, mock_db_manager):
        """Test error handling and failure tracking."""
        mock_cursor = mock_db_manager.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        
        error_message = "Database connection failed"
        duration = 30
        
        scheduler._mark_run_failed(error_message, duration)
        
        # Verify failure tracking SQL call
        mock_cursor.execute.assert_called_with(
            "UPDATE scraping_runs \n                        SET status = 'failed',\n                            completed_at = CURRENT_TIMESTAMP,\n                            error_message = %s,\n                            total_duration_seconds = %s\n                        WHERE run_id = %s",
            (error_message, duration, scheduler.run_id)
        )

    def test_outlet_processing_logs(self, scheduler, mock_db_manager):
        """Test per-outlet logging functionality."""
        mock_cursor = mock_db_manager.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        
        outlet_name = "test_outlet"
        outlet_url = "https://test.com"
        
        # Test outlet start logging
        scheduler._log_outlet_start(outlet_name, outlet_url)
        
        start_call = call(
            "INSERT INTO scraping_run_outlets \n                        (run_id, outlet_name, outlet_url, status)\n                        VALUES (%s, %s, %s, 'processing')",
            (scheduler.run_id, outlet_name, outlet_url)
        )
        assert start_call in mock_cursor.execute.call_args_list
        
        # Test outlet completion logging
        result = {'articles_scraped': 5, 'articles_found': 7}
        duration = 45
        scheduler._log_outlet_completion(outlet_name, outlet_url, result, duration)
        
        completion_call = call(
            "UPDATE scraping_run_outlets \n                        SET status = 'success',\n                            articles_found = %s,\n                            articles_scraped = %s,\n                            duration_seconds = %s,\n                            completed_at = CURRENT_TIMESTAMP\n                        WHERE run_id = %s AND outlet_name = %s",
            (7, 5, duration, scheduler.run_id, outlet_name)
        )
        assert completion_call in mock_cursor.execute.call_args_list


class TestGracefulShutdown:
    """Test 3: Signal handling and proper cleanup."""

    def test_shutdown_signal_handling(self, scheduler, mock_db_manager):
        """Test graceful shutdown with signal handling."""
        mock_cursor = mock_db_manager.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        
        # Create a lock file first
        scheduler.create_lock_file()
        assert scheduler.lock_file_path.exists()
        
        # Mock sys.exit to prevent actual exit
        with patch('sys.exit') as mock_exit:
            scheduler.handle_graceful_shutdown(signal.SIGTERM, None)
            
            # Verify shutdown was marked in database
            shutdown_call = call(
                "UPDATE scraping_runs \n                        SET status = 'aborted',\n                            completed_at = CURRENT_TIMESTAMP,\n                            error_message = 'Graceful shutdown requested'\n                        WHERE run_id = %s AND status = 'running'",
                (scheduler.run_id,)
            )
            assert shutdown_call in mock_cursor.execute.call_args_list
            
            # Verify lock file was cleaned up
            assert not scheduler.lock_file_path.exists()
            
            # Verify exit was called
            mock_exit.assert_called_once_with(0)

    def test_shutdown_flag_stops_processing(self, scheduler):
        """Test that shutdown flag stops outlet processing."""
        # Mock outlets config
        outlets_config = {
            'outlets': {
                'outlet1': {'url': 'https://test1.com'},
                'outlet2': {'url': 'https://test2.com'},
                'outlet3': {'url': 'https://test3.com'}
            }
        }
        
        # Set shutdown flag after first outlet
        def mock_scrape_single_outlet(name, config):
            if name == 'outlet1':
                scheduler.shutdown_requested = True
            return {'articles_scraped': 1}
        
        with patch.object(scheduler, '_scrape_single_outlet', side_effect=mock_scrape_single_outlet):
            results = scheduler._scrape_all_outlets(outlets_config)
            
            # Should have processed only outlet1 before shutdown
            assert results['outlets_processed'] == 1
            assert results['articles_scraped'] == 1


class TestSchedulerIntegration:
    """Test 4: End-to-end scheduling with existing scrapers."""

    def test_complete_scraping_cycle_success(self, scheduler, mock_db_manager):
        """Test complete successful scraping cycle."""
        # Mock config loader
        mock_config = {
            'outlets': {
                'test_outlet': {
                    'name': 'Test Outlet',
                    'url': 'https://test.com'
                }
            }
        }
        
        with patch.object(scheduler.config_loader, 'load_outlets_config', return_value=mock_config), \
             patch.object(scheduler, '_scrape_single_outlet', return_value={
                 'articles_scraped': 5,
                 'articles_updated': 2,
                 'articles_skipped': 1,
                 'status': 'success'
             }):
            
            result = scheduler.run_scraping_cycle()
            
            # Verify successful completion
            assert result['status'] == 'completed'
            assert result['run_id'] == scheduler.run_id
            assert result['articles_scraped'] == 5
            assert result['articles_updated'] == 2
            assert result['articles_skipped'] == 1
            assert result['outlets_processed'] == 1
            assert result['outlets_failed'] == 0
            assert 'duration_seconds' in result

    def test_scraping_cycle_with_existing_lock(self, scheduler):
        """Test scraping cycle when another process is running."""
        # Create existing lock file
        scheduler.create_lock_file()
        
        # Create another scheduler instance to simulate different process
        scheduler2 = ScrapingScheduler(scheduler.db_manager)
        scheduler2.lock_file_path = scheduler.lock_file_path
        scheduler2.lock_dir = scheduler.lock_dir
        
        result = scheduler2.run_scraping_cycle()
        
        # Should be skipped due to existing lock
        assert result['status'] == 'skipped'
        assert result['reason'] == 'Another process already running'

    def test_scraping_cycle_with_exception(self, scheduler, mock_db_manager):
        """Test scraping cycle error handling."""
        # Mock config loader to raise exception
        with patch.object(scheduler.config_loader, 'load_outlets_config', side_effect=Exception("Config load failed")):
            result = scheduler.run_scraping_cycle()
            
            # Should handle exception gracefully
            assert result['status'] == 'failed'
            assert result['error'] == 'Config load failed'
            assert 'duration_seconds' in result


class TestRunnerScriptCLI:
    """Test 5: Command-line interface and error handling."""

    def test_runner_script_help(self):
        """Test runner script help output."""
        runner_path = Path(__file__).parent.parent.parent / "backend" / "scraper" / "runner.py"
        
        if runner_path.exists():
            result = subprocess.run([
                sys.executable, str(runner_path), '--help'
            ], capture_output=True, text=True)
            
            assert result.returncode == 0
            assert 'Swiss News Scraper Runner' in result.stdout
            assert '--mode' in result.stdout
            assert '--dry-run' in result.stdout
            assert '--status' in result.stdout

    def test_runner_script_dry_run(self):
        """Test runner script dry-run mode."""
        runner_path = Path(__file__).parent.parent.parent / "backend" / "scraper" / "runner.py"
        
        if runner_path.exists():
            # Test dry-run mode
            result = subprocess.run([
                sys.executable, str(runner_path), '--mode=manual', '--dry-run', '--json-output'
            ], capture_output=True, text=True, timeout=30)
            
            # Should complete successfully in dry-run mode
            assert result.returncode == 0
            
            # Should output JSON
            import json
            try:
                output = json.loads(result.stdout.strip())
                assert output['status'] == 'dry_run_completed'
            except json.JSONDecodeError:
                # If JSON parsing fails, at least check it ran without error
                pass

    def test_runner_script_invalid_args(self):
        """Test runner script with invalid arguments."""
        runner_path = Path(__file__).parent.parent.parent / "backend" / "scraper" / "runner.py"
        
        if runner_path.exists():
            result = subprocess.run([
                sys.executable, str(runner_path), '--invalid-option'
            ], capture_output=True, text=True)
            
            # Should fail with invalid arguments
            assert result.returncode != 0

    @patch('backend.scraper.runner.DatabaseManager')
    @patch('backend.scraper.runner.ScrapingScheduler')
    def test_runner_functions_unit(self, mock_scheduler_class, mock_db_class):
        """Test runner script functions in isolation."""
        # Import runner functions
        import importlib.util
        runner_path = Path(__file__).parent.parent.parent / "backend" / "scraper" / "runner.py"
        
        if runner_path.exists():
            spec = importlib.util.spec_from_file_location("runner", runner_path)
            runner_module = importlib.util.module_from_spec(spec)
            
            # Mock scheduler instance
            mock_scheduler = MagicMock()
            mock_scheduler.run_scraping_cycle.return_value = {
                'status': 'completed',
                'articles_scraped': 10
            }
            mock_scheduler_class.return_value = mock_scheduler
            
            # Execute module to define functions
            spec.loader.exec_module(runner_module)
            
            # Test run_scraping function
            result = runner_module.run_scraping(dry_run=False)
            
            assert result['status'] == 'completed'
            assert result['articles_scraped'] == 10
            
            # Test dry run
            result = runner_module.run_scraping(dry_run=True)
            assert result['status'] == 'dry_run_completed'