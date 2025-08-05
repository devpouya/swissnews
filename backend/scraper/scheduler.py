#!/usr/bin/env python3
"""
Cron-based Periodic Scraping Scheduler

Implements a robust scheduling system for Swiss news scraping with file-based locking,
database tracking, performance monitoring, and graceful shutdown handling.

Issue: https://github.com/devpouya/swissnews/issues/6
"""

import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil
from loguru import logger

from backend.database.connection import DatabaseManager
from backend.scraper.config_loader import ConfigLoader


class ScrapingScheduler:
    """
    Cron-based scraping scheduler with comprehensive monitoring and locking.
    
    Features:
    - File-based locking to prevent overlapping executions
    - Database tracking of run status and metrics
    - Performance monitoring and error handling
    - Graceful shutdown with cleanup
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the scraping scheduler."""
        self.db_manager = db_manager or DatabaseManager()
        self.config_loader = ConfigLoader()
        self.run_id = str(uuid.uuid4())
        self.current_run_data = {}
        self.lock_file_path = Path("/tmp/swissnews/scraper.lock")
        self.lock_dir = self.lock_file_path.parent
        self.shutdown_requested = False
        
        # Ensure lock directory exists
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.handle_graceful_shutdown)
        signal.signal(signal.SIGINT, self.handle_graceful_shutdown)
        
        logger.info(f"ScrapingScheduler initialized with run_id: {self.run_id}")

    def run_scraping_cycle(self) -> Dict[str, Any]:
        """
        Execute a complete scraping cycle.
        
        Returns:
            Dict containing run results and metrics
        """
        start_time = time.time()
        
        try:
            # Check for existing lock
            if self.check_lock_file():
                logger.warning("Another scraping process is already running")
                return {
                    "status": "skipped",
                    "reason": "Another process already running",
                    "run_id": self.run_id
                }
            
            # Create lock file
            self.create_lock_file()
            
            # Initialize run in database
            self._initialize_run()
            
            # Load outlet configurations
            outlets_config = self.config_loader.load_config()
            
            # Run scraping for each outlet
            results = self._scrape_all_outlets(outlets_config)
            
            # Calculate final metrics
            total_duration = int(time.time() - start_time)
            
            # Update run status in database
            self._finalize_run(results, total_duration)
            
            return {
                "status": "completed",
                "run_id": self.run_id,
                "duration_seconds": total_duration,
                **results
            }
            
        except Exception as e:
            logger.error(f"Scraping cycle failed: {e}")
            duration = int(time.time() - start_time)
            self._mark_run_failed(str(e), duration)
            
            return {
                "status": "failed",
                "run_id": self.run_id,
                "error": str(e),
                "duration_seconds": duration
            }
            
        finally:
            # Always cleanup lock file
            self.cleanup_lock_file()

    def check_lock_file(self) -> bool:
        """
        Check if a lock file exists and if the associated process is still running.
        
        Returns:
            True if another process is running, False otherwise
        """
        if not self.lock_file_path.exists():
            return False
        
        try:
            lock_content = self.lock_file_path.read_text().strip()
            lock_data = {}
            
            for line in lock_content.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    lock_data[key] = value
            
            pid = int(lock_data.get('PID', 0))
            
            # Check if process is still running
            if pid and psutil.pid_exists(pid):
                try:
                    process = psutil.Process(pid)
                    # Check if it's actually a scraper process
                    if 'python' in process.name().lower():
                        logger.info(f"Found running scraper process with PID {pid}")
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Stale lock file - remove it
            logger.warning(f"Removing stale lock file (PID {pid} not found)")
            self.lock_file_path.unlink()
            return False
            
        except (ValueError, FileNotFoundError, PermissionError) as e:
            logger.warning(f"Error reading lock file: {e}")
            # If we can't read the lock file, assume it's stale
            try:
                self.lock_file_path.unlink()
            except:
                pass
            return False

    def create_lock_file(self) -> None:
        """Create a lock file with current process information."""
        lock_content = f"""PID={os.getpid()}
STARTED={datetime.now(timezone.utc).isoformat()}
RUN_ID={self.run_id}
HOST={os.uname().nodename}
"""
        
        try:
            self.lock_file_path.write_text(lock_content)
            logger.info(f"Created lock file: {self.lock_file_path}")
        except PermissionError as e:
            logger.error(f"Failed to create lock file: {e}")
            raise

    def cleanup_lock_file(self) -> None:
        """Remove the lock file if it exists and belongs to this process."""
        try:
            if self.lock_file_path.exists():
                # Verify it's our lock file
                lock_content = self.lock_file_path.read_text()
                if f"PID={os.getpid()}" in lock_content and f"RUN_ID={self.run_id}" in lock_content:
                    self.lock_file_path.unlink()
                    logger.info("Cleaned up lock file")
                else:
                    logger.warning("Lock file doesn't belong to this process")
        except Exception as e:
            logger.error(f"Error cleaning up lock file: {e}")

    def log_run_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log run metrics to database."""
        try:
            with self.db_manager.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE scraping_runs 
                        SET articles_scraped = %s,
                            articles_updated = %s,
                            articles_skipped = %s,
                            outlets_processed = %s,
                            outlets_failed = %s
                        WHERE run_id = %s
                    """, (
                        metrics.get('articles_scraped', 0),
                        metrics.get('articles_updated', 0),
                        metrics.get('articles_skipped', 0),
                        metrics.get('outlets_processed', 0),
                        metrics.get('outlets_failed', 0),
                        self.run_id
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to log run metrics: {e}")

    def handle_graceful_shutdown(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
        
        # Mark run as aborted in database
        try:
            with self.db_manager.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE scraping_runs 
                        SET status = 'aborted',
                            completed_at = CURRENT_TIMESTAMP,
                            error_message = 'Graceful shutdown requested'
                        WHERE run_id = %s AND status = 'running'
                    """, (self.run_id,))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to mark run as aborted: {e}")
        
        # Cleanup lock file
        self.cleanup_lock_file()
        
        logger.info("Graceful shutdown completed")
        sys.exit(0)

    def _initialize_run(self) -> None:
        """Initialize a new scraping run in the database."""
        try:
            with self.db_manager.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO scraping_runs (run_id, status, lock_file_path)
                        VALUES (%s, 'running', %s)
                    """, (self.run_id, str(self.lock_file_path)))
                    conn.commit()
                    
            logger.info(f"Initialized scraping run {self.run_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize run: {e}")
            raise

    def _scrape_all_outlets(self, outlets_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape all configured outlets.
        
        Args:
            outlets_config: Configuration for all outlets
            
        Returns:
            Dict containing aggregated results
        """
        results = {
            "articles_scraped": 0,
            "articles_updated": 0, 
            "articles_skipped": 0,
            "outlets_processed": 0,
            "outlets_failed": 0
        }
        
        outlets = outlets_config.get('outlets', {})
        
        for outlet_name, outlet_config in outlets.items():
            if self.shutdown_requested:
                logger.info("Shutdown requested, stopping outlet processing")
                break
                
            logger.info(f"Processing outlet: {outlet_name}")
            
            try:
                # TODO: Integrate with existing scraper infrastructure
                # This is a placeholder for the actual scraping logic
                outlet_result = self._scrape_single_outlet(outlet_name, outlet_config)
                
                # Update aggregated results
                results["articles_scraped"] += outlet_result.get("articles_scraped", 0)
                results["articles_updated"] += outlet_result.get("articles_updated", 0)
                results["articles_skipped"] += outlet_result.get("articles_skipped", 0)
                results["outlets_processed"] += 1
                
                logger.info(f"Completed outlet {outlet_name}: {outlet_result}")
                
            except Exception as e:
                logger.error(f"Failed to scrape outlet {outlet_name}: {e}")
                results["outlets_failed"] += 1
                self._log_outlet_error(outlet_name, outlet_config.get('url', ''), str(e))
        
        return results

    def _scrape_single_outlet(self, outlet_name: str, outlet_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape a single outlet (placeholder implementation).
        
        Args:
            outlet_name: Name of the outlet
            outlet_config: Configuration for the outlet
            
        Returns:
            Dict containing scraping results
        """
        start_time = time.time()
        outlet_url = outlet_config.get('url', '')
        
        try:
            # Log outlet start
            self._log_outlet_start(outlet_name, outlet_url)
            
            # TODO: Implement actual scraping using existing infrastructure
            # For now, simulate scraping with a small delay
            time.sleep(1)
            
            # Mock results
            result = {
                "articles_scraped": 5,
                "articles_updated": 2,
                "articles_skipped": 1,
                "status": "success"
            }
            
            duration = int(time.time() - start_time)
            self._log_outlet_completion(outlet_name, outlet_url, result, duration)
            
            return result
            
        except Exception as e:
            duration = int(time.time() - start_time)
            self._log_outlet_error(outlet_name, outlet_url, str(e), duration)
            raise

    def _finalize_run(self, results: Dict[str, Any], total_duration: int) -> None:
        """Finalize the scraping run in the database."""
        try:
            with self.db_manager.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE scraping_runs 
                        SET status = 'completed',
                            completed_at = CURRENT_TIMESTAMP,
                            articles_scraped = %s,
                            articles_updated = %s,
                            articles_skipped = %s,
                            outlets_processed = %s,
                            outlets_failed = %s,
                            total_duration_seconds = %s
                        WHERE run_id = %s
                    """, (
                        results['articles_scraped'],
                        results['articles_updated'],
                        results['articles_skipped'],
                        results['outlets_processed'],
                        results['outlets_failed'],
                        total_duration,
                        self.run_id
                    ))
                    conn.commit()
                    
            logger.info(f"Finalized scraping run {self.run_id}")
            
        except Exception as e:
            logger.error(f"Failed to finalize run: {e}")

    def _mark_run_failed(self, error_message: str, duration: int) -> None:
        """Mark the current run as failed in the database."""
        try:
            with self.db_manager.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE scraping_runs 
                        SET status = 'failed',
                            completed_at = CURRENT_TIMESTAMP,
                            error_message = %s,
                            total_duration_seconds = %s
                        WHERE run_id = %s
                    """, (error_message, duration, self.run_id))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to mark run as failed: {e}")

    def _log_outlet_start(self, outlet_name: str, outlet_url: str) -> None:
        """Log the start of outlet processing."""
        try:
            with self.db_manager.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO scraping_run_outlets 
                        (run_id, outlet_name, outlet_url, status)
                        VALUES (%s, %s, %s, 'processing')
                    """, (self.run_id, outlet_name, outlet_url))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to log outlet start: {e}")

    def _log_outlet_completion(self, outlet_name: str, outlet_url: str, 
                             result: Dict[str, Any], duration: int) -> None:
        """Log the completion of outlet processing."""
        try:
            with self.db_manager.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE scraping_run_outlets 
                        SET status = 'success',
                            articles_found = %s,
                            articles_scraped = %s,
                            duration_seconds = %s,
                            completed_at = CURRENT_TIMESTAMP
                        WHERE run_id = %s AND outlet_name = %s
                    """, (
                        result.get('articles_found', result.get('articles_scraped', 0)),
                        result.get('articles_scraped', 0),
                        duration,
                        self.run_id,
                        outlet_name
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to log outlet completion: {e}")

    def _log_outlet_error(self, outlet_name: str, outlet_url: str, 
                         error_message: str, duration: int = 0) -> None:
        """Log an error for outlet processing."""
        try:
            with self.db_manager.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE scraping_run_outlets 
                        SET status = 'failed',
                            error_message = %s,
                            duration_seconds = %s,
                            completed_at = CURRENT_TIMESTAMP
                        WHERE run_id = %s AND outlet_name = %s
                    """, (error_message, duration, self.run_id, outlet_name))
                    
                    # If no existing record, insert one
                    if cursor.rowcount == 0:
                        cursor.execute("""
                            INSERT INTO scraping_run_outlets 
                            (run_id, outlet_name, outlet_url, status, error_message, duration_seconds)
                            VALUES (%s, %s, %s, 'failed', %s, %s)
                        """, (self.run_id, outlet_name, outlet_url, error_message, duration))
                    
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to log outlet error: {e}")