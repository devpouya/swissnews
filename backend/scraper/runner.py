#!/usr/bin/env python3
"""
Scraper Runner Script for Cron Execution

Entry point script for running scheduled Swiss news scraping via cron.
Handles command-line arguments, logging configuration, and error reporting.

Usage:
    python runner.py --mode=cron
    python runner.py --mode=manual --dry-run
    python runner.py --status

Issue: https://github.com/devpouya/swissnews/issues/6
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from backend.database.connection import DatabaseManager
from backend.scraper.scheduler import ScrapingScheduler


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Configure logging for the scraper runner.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    # Remove default logger
    logger.remove()
    
    # Add console logging
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>"
    )
    
    # Add file logging if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="10 MB",
            retention="30 days",
            compression="gz"
        )


def run_scraping(dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute a scraping cycle.
    
    Args:
        dry_run: If True, simulate scraping without actual execution
        
    Returns:
        Dict containing run results
    """
    logger.info("Starting scraping cycle...")
    
    if dry_run:
        logger.info("DRY RUN MODE - No actual scraping will be performed")
        return {
            "status": "dry_run_completed",
            "message": "Dry run completed successfully",
            "duration_seconds": 0
        }
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Create and run scheduler
        scheduler = ScrapingScheduler(db_manager)
        result = scheduler.run_scraping_cycle()
        
        logger.info(f"Scraping cycle completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Scraping cycle failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "duration_seconds": 0
        }


def check_status() -> Dict[str, Any]:
    """
    Check the status of recent scraping runs.
    
    Returns:
        Dict containing status information
    """
    try:
        db_manager = DatabaseManager()
        
        with db_manager.get_raw_connection() as conn:
            with conn.cursor() as cursor:
                # Get recent runs
                cursor.execute("""
                    SELECT run_id, status, started_at, completed_at, 
                           articles_scraped, outlets_processed, outlets_failed,
                           total_duration_seconds, error_message
                    FROM scraping_runs 
                    ORDER BY started_at DESC 
                    LIMIT 10
                """)
                
                recent_runs = []
                for row in cursor.fetchall():
                    recent_runs.append({
                        "run_id": row[0],
                        "status": row[1],
                        "started_at": row[2].isoformat() if row[2] else None,
                        "completed_at": row[3].isoformat() if row[3] else None,
                        "articles_scraped": row[4],
                        "outlets_processed": row[5],
                        "outlets_failed": row[6],
                        "duration_seconds": row[7],
                        "error_message": row[8]
                    })
                
                # Check for currently running processes
                cursor.execute("""
                    SELECT COUNT(*) FROM scraping_runs 
                    WHERE status = 'running'
                """)
                running_count = cursor.fetchone()[0]
                
                return {
                    "status": "success",
                    "currently_running": running_count > 0,
                    "running_count": running_count,
                    "recent_runs": recent_runs
                }
                
    except Exception as e:
        logger.error(f"Failed to check status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def main() -> int:
    """
    Main entry point for the scraper runner.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Swiss News Scraper Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode=cron                 # Run scraping (for cron)
  %(prog)s --mode=manual --dry-run     # Manual dry run
  %(prog)s --status                    # Check scraping status
  %(prog)s --mode=cron --log-file=/var/log/scraper.log
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["cron", "manual"],
        default="manual",
        help="Execution mode (default: manual)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate scraping without actual execution"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check status of recent scraping runs"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Log file path (optional)"
    )
    
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results in JSON format"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    try:
        if args.status:
            # Check status
            result = check_status()
            
        else:
            # Run scraping
            result = run_scraping(dry_run=args.dry_run)
        
        # Output results
        if args.json_output:
            print(json.dumps(result, indent=2))
        else:
            if result.get("status") in ["completed", "success", "dry_run_completed"]:
                logger.success(f"Operation successful: {result}")
            else:
                logger.error(f"Operation failed: {result}")
        
        # Return appropriate exit code
        if result.get("status") in ["completed", "success", "dry_run_completed"]:
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        logger.warning("Operation interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)