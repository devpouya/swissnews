#!/usr/bin/env python3
"""
Populate outlets table from CSV data

This script imports Swiss news outlets from the CSV files created in Issue #1
into the PostgreSQL database schema created in Issue #2.

Usage:
    python backend/database/populate_outlets.py [--csv-file path/to/file.csv] [--dry-run]

Author: Claude (GitHub Issue #2)
Created: 2025-08-04
"""

import argparse
import csv
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path to import database utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db_manager, outlet_repo

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def normalize_language_code(language: str) -> str:
    """Convert language names to ISO codes"""
    language_mapping = {
        "German": "de",
        "French": "fr",
        "Italian": "it",
        "Romansch": "rm",
        "Romansh": "rm",  # Alternative spelling
    }
    return language_mapping.get(language, language.lower())


def clean_outlet_data(row: Dict[str, str]) -> Dict[str, Any]:
    """Clean and transform CSV row data for database insertion"""

    # Map CSV columns to database columns
    outlet_data = {
        "name": row.get("news_website", "").strip(),
        "url": row.get("url", "").strip() or None,  # Convert empty strings to None
        "language": normalize_language_code(row.get("original_language", "").strip()),
        "owner": row.get("owner", "").strip() or None,
        "city": row.get("city", "").strip() or None,
        "canton": row.get("canton", "").strip() or None,
        "occurrence": row.get("occurrence", "").strip() or None,
        "status": row.get("status", "current").strip(),
    }

    # Validate required fields
    if not outlet_data["name"]:
        raise ValueError("Outlet name is required")

    if not outlet_data["language"]:
        raise ValueError("Language is required")

    # Validate language code
    valid_languages = ["de", "fr", "it", "rm"]
    if outlet_data["language"] not in valid_languages:
        logger.warning(
            f"Unknown language code: {outlet_data['language']} for outlet {outlet_data['name']}"
        )

    # Validate URL format if provided
    if outlet_data["url"] and not outlet_data["url"].startswith(
        ("http://", "https://")
    ):
        logger.warning(
            f"Invalid URL format for {outlet_data['name']}: {outlet_data['url']}"
        )
        outlet_data["url"] = (
            f"https://{outlet_data['url']}" if "." in outlet_data["url"] else None
        )

    return outlet_data


def load_outlets_from_csv(csv_file_path: str) -> List[Dict[str, Any]]:
    """Load and clean outlet data from CSV file"""

    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    outlets = []
    errors = []

    with open(csv_file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row_num, row in enumerate(
            reader, start=2
        ):  # Start at 2 to account for header
            try:
                outlet_data = clean_outlet_data(row)
                outlets.append(outlet_data)

            except Exception as e:
                error_msg = f"Row {row_num}: {e} - Data: {row}"
                errors.append(error_msg)
                logger.error(error_msg)

    if errors:
        logger.warning(f"Found {len(errors)} errors while processing CSV")

    logger.info(f"Successfully processed {len(outlets)} outlets from CSV")
    return outlets


def populate_outlets_table(
    outlets: List[Dict[str, Any]], dry_run: bool = False
) -> bool:
    """Populate the outlets table with data"""

    if dry_run:
        logger.info(f"DRY RUN: Would insert {len(outlets)} outlets")
        for outlet in outlets[:5]:  # Show first 5 as sample
            logger.info(
                f"Would insert: {outlet['name']} ({outlet['language']}) - {outlet['url']}"
            )
        if len(outlets) > 5:
            logger.info(f"... and {len(outlets) - 5} more outlets")
        return True

    # Test database connection
    if not db_manager.test_connection():
        logger.error("Cannot connect to database")
        return False

    success_count = 0
    error_count = 0

    # Clear existing sample data first
    try:
        with db_manager.get_session() as session:
            # Delete test articles first (due to foreign key constraint)
            session.execute(
                "DELETE FROM articles WHERE outlet_id IN "
                "(SELECT id FROM outlets WHERE name LIKE '%Test%' OR url LIKE '%test%')"
            )
            # Delete test outlets
            session.execute(
                "DELETE FROM outlets WHERE name LIKE '%Test%' OR url LIKE '%test%'"
            )
            session.commit()
            logger.info("Cleared existing sample data")
    except Exception as e:
        logger.error(f"Failed to clear sample data: {e}")
        return False

    # Insert real outlets
    for outlet in outlets:
        try:
            outlet_id = outlet_repo.create_outlet(outlet)
            success_count += 1
            logger.debug(f"Inserted outlet: {outlet['name']} (ID: {outlet_id})")

        except Exception as e:
            error_count += 1
            logger.error(f"Failed to insert outlet {outlet['name']}: {e}")

    logger.info(f"Successfully inserted {success_count} outlets")
    if error_count > 0:
        logger.warning(f"Failed to insert {error_count} outlets")

    return error_count == 0


def verify_data_integrity() -> bool:
    """Verify the populated data meets expectations"""

    try:
        # Check total count
        all_outlets = outlet_repo.get_all_outlets()
        logger.info(f"Total outlets in database: {len(all_outlets)}")

        if len(all_outlets) < 10:
            logger.warning("Fewer than 10 outlets found - this seems low")

        # Check language distribution
        language_counts: Dict[str, int] = {}
        for outlet in all_outlets:
            lang = outlet["language"]
            language_counts[lang] = language_counts.get(lang, 0) + 1

        logger.info("Language distribution:")
        for lang, count in sorted(language_counts.items()):
            logger.info(f"  {lang}: {count} outlets")

        # Verify German is the largest group
        if "de" in language_counts and language_counts["de"] < len(all_outlets) * 0.4:
            logger.warning("German outlets should be the largest group")

        # Check for outlets with URLs
        outlets_with_urls = [o for o in all_outlets if o["url"]]
        logger.info(f"Outlets with URLs: {len(outlets_with_urls)}/{len(all_outlets)}")

        # Check for major outlets
        outlet_names = [o["name"].lower() for o in all_outlets]
        major_outlets = ["nzz", "blick", "tages-anzeiger", "le temps", "20 minuten"]
        found_major = [
            name
            for name in major_outlets
            if any(name in outlet_name for outlet_name in outlet_names)
        ]
        logger.info(f"Found major outlets: {found_major}")

        return True

    except Exception as e:
        logger.error(f"Data integrity verification failed: {e}")
        return False


def main() -> None:
    """Main function"""

    parser = argparse.ArgumentParser(description="Populate outlets table from CSV data")
    parser.add_argument(
        "--csv-file",
        default="data/processed/swiss_news_outlets_with_urls.csv",
        help="Path to CSV file containing outlet data",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually inserting data",
    )
    parser.add_argument(
        "--verify-only", action="store_true", help="Only verify existing data integrity"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle verify-only mode
    if args.verify_only:
        logger.info("Verifying data integrity only...")
        success = verify_data_integrity()
        sys.exit(0 if success else 1)

    # Find CSV file (try multiple locations)
    csv_paths = [
        args.csv_file,
        "data/processed/swiss_news_outlets_with_urls.csv",
        "data/swiss_news_outlets.csv",
        "../../data/processed/swiss_news_outlets_with_urls.csv",
        "../../data/swiss_news_outlets.csv",
    ]

    csv_file = None
    for path in csv_paths:
        if os.path.exists(path):
            csv_file = path
            break

    if not csv_file:
        logger.error(f"CSV file not found. Tried: {csv_paths}")
        sys.exit(1)

    logger.info(f"Using CSV file: {csv_file}")

    try:
        # Load outlets from CSV
        outlets = load_outlets_from_csv(csv_file)

        if not outlets:
            logger.error("No outlets loaded from CSV")
            sys.exit(1)

        # Populate database
        success = populate_outlets_table(outlets, dry_run=args.dry_run)

        if not success:
            logger.error("Failed to populate outlets table")
            sys.exit(1)

        # Verify data integrity (unless dry run)
        if not args.dry_run:
            verify_data_integrity()

        logger.info("Outlets population completed successfully!")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
