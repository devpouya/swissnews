#!/usr/bin/env python3
"""
Test database schema functionality

This script performs basic validation and testing of the PostgreSQL schema
without requiring a live database connection.

Author: Claude (GitHub Issue #2)
Created: 2025-08-04
"""

import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validate_sql_syntax(sql_file_path: str) -> bool:
    """Basic SQL syntax validation"""

    if not os.path.exists(sql_file_path):
        logger.error(f"SQL file not found: {sql_file_path}")
        return False

    try:
        with open(sql_file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Basic syntax checks
        errors = []

        # Check for balanced parentheses
        paren_count = content.count("(") - content.count(")")
        if paren_count != 0:
            errors.append(f"Unbalanced parentheses: {paren_count}")

        # Check for unterminated strings
        single_quotes = content.count("'") - content.count("''") * 2
        if single_quotes % 2 != 0:
            errors.append("Unterminated string literal (odd number of single quotes)")

        # Check for required statements
        required_statements = [
            "CREATE TABLE outlets",
            "CREATE TABLE articles",
            "CREATE INDEX",
            "CREATE TRIGGER",
            "CREATE OR REPLACE FUNCTION",
        ]

        for statement in required_statements:
            if statement not in content:
                errors.append(f"Missing required statement: {statement}")

        # Check for proper constraint naming
        if "REFERENCES outlets(id)" not in content:
            errors.append("Missing foreign key reference to outlets table")

        if errors:
            logger.error(f"SQL syntax validation failed for {sql_file_path}:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info(f"SQL syntax validation passed for {sql_file_path}")
        return True

    except Exception as e:
        logger.error(f"Error validating SQL file {sql_file_path}: {e}")
        return False


def analyze_schema_structure(sql_file_path: str) -> Dict[str, Any]:
    """Analyze the database schema structure"""

    with open(sql_file_path, "r", encoding="utf-8") as file:
        content = file.read()

    analysis = {
        "tables": [],
        "indexes": [],
        "views": [],
        "triggers": [],
        "functions": [],
        "constraints": [],
    }

    # Find tables
    table_pattern = r"CREATE TABLE (\w+)"
    analysis["tables"] = re.findall(table_pattern, content, re.IGNORECASE)

    # Find indexes
    index_pattern = r"CREATE.*INDEX (\w+)"
    analysis["indexes"] = re.findall(index_pattern, content, re.IGNORECASE)

    # Find views
    view_pattern = r"CREATE VIEW (\w+)"
    analysis["views"] = re.findall(view_pattern, content, re.IGNORECASE)

    # Find triggers
    trigger_pattern = r"CREATE TRIGGER (\w+)"
    analysis["triggers"] = re.findall(trigger_pattern, content, re.IGNORECASE)

    # Find functions
    function_pattern = r"CREATE.*FUNCTION (\w+)"
    analysis["functions"] = re.findall(function_pattern, content, re.IGNORECASE)

    # Find constraints
    constraint_patterns = [
        r"(\w+) REFERENCES (\w+)",
        r"CHECK \([^)]+\)",
        r"UNIQUE\s*\([^)]+\)",
    ]

    for pattern in constraint_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        analysis["constraints"].extend(matches)

    return analysis


def validate_schema_requirements(analysis: Dict[str, Any]) -> bool:
    """Validate that schema meets the requirements from Issue #2"""

    errors = []

    # Check required tables
    required_tables = ["outlets", "articles"]
    for table in required_tables:
        if table not in analysis["tables"]:
            errors.append(f"Missing required table: {table}")

    # Check for performance indexes
    expected_indexes = ["outlets", "articles", "language", "date", "outlet"]
    found_index_keywords = " ".join(analysis["indexes"]).lower()

    for keyword in expected_indexes:
        if keyword not in found_index_keywords:
            logger.warning(
                f"Expected index keyword '{keyword}' not found in index names"
            )

    # Check for views
    expected_views = ["articles_with_outlets"]
    for view in expected_views:
        if view not in analysis["views"]:
            errors.append(f"Missing expected view: {view}")

    # Check for triggers (for timestamp updates)
    if not analysis["triggers"]:
        errors.append("No triggers found - expected timestamp update triggers")

    # Check functions
    if not analysis["functions"]:
        errors.append("No functions found - expected timestamp update function")

    if errors:
        logger.error("Schema requirements validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    logger.info("Schema requirements validation passed")
    return True


def test_python_imports() -> bool:
    """Test that all required Python packages can be imported"""

    required_packages = ["psycopg2", "sqlalchemy", "sqlalchemy.orm", "sqlalchemy.pool"]

    errors = []

    for package in required_packages:
        try:
            __import__(package)
            logger.debug(f"Successfully imported {package}")
        except ImportError as e:
            errors.append(f"Failed to import {package}: {e}")

    if errors:
        logger.error("Python package import test failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    logger.info("Python package import test passed")
    return True


def test_database_utilities() -> bool:
    """Test database utility classes without actual database connection"""

    try:
        # Import utilities
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from database.connection import DatabaseConfig, DatabaseManager

        # Test configuration
        config = DatabaseConfig()
        logger.debug(f"Database config: {config.host}:{config.port}/{config.database}")

        # Test connection string generation
        conn_str = config.connection_string
        assert "postgresql://" in conn_str, "Invalid connection string format"

        # Test database manager initialization
        db_manager = DatabaseManager(config)
        assert db_manager.config == config, "Config not properly set"

        logger.info("Database utilities test passed")
        return True

    except Exception as e:
        logger.error(f"Database utilities test failed: {e}")
        return False


def test_csv_population_script() -> bool:
    """Test CSV population script syntax"""

    try:
        populate_script = os.path.join(os.path.dirname(__file__), "populate_outlets.py")

        if not os.path.exists(populate_script):
            logger.error("CSV population script not found")
            return False

        # Basic syntax check by attempting to compile
        with open(populate_script, "r", encoding="utf-8") as file:
            script_content = file.read()

        compile(script_content, populate_script, "exec")

        logger.info("CSV population script syntax test passed")
        return True

    except SyntaxError as e:
        logger.error(f"CSV population script syntax error: {e}")
        return False
    except Exception as e:
        logger.error(f"CSV population script test failed: {e}")
        return False


def run_all_tests() -> bool:
    """Run all schema tests"""

    logger.info("Starting database schema tests...")

    # Get paths
    schema_dir = os.path.dirname(os.path.abspath(__file__))
    migration_file = os.path.join(schema_dir, "migrations", "001_initial_schema.sql")

    tests = [
        ("SQL Syntax Validation", lambda: validate_sql_syntax(migration_file)),
        ("Python Imports", test_python_imports),
        ("Database Utilities", test_database_utilities),
        ("CSV Population Script", test_csv_population_script),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        logger.info(f"Running test: {test_name}")
        try:
            if test_func():
                logger.info(f"✓ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"✗ {test_name} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} ERROR: {e}")
            failed += 1

    # Schema analysis (informational)
    logger.info("Analyzing schema structure...")
    try:
        analysis = analyze_schema_structure(migration_file)
        logger.info(f"Schema Analysis:")
        logger.info(f"  Tables: {analysis['tables']}")
        logger.info(f"  Indexes: {len(analysis['indexes'])} total")
        logger.info(f"  Views: {analysis['views']}")
        logger.info(f"  Triggers: {analysis['triggers']}")
        logger.info(f"  Functions: {analysis['functions']}")

        if validate_schema_requirements(analysis):
            logger.info("✓ Schema Requirements PASSED")
            passed += 1
        else:
            logger.error("✗ Schema Requirements FAILED")
            failed += 1

    except Exception as e:
        logger.error(f"Schema analysis failed: {e}")
        failed += 1

    # Summary
    total = passed + failed
    logger.info(f"Test Results: {passed}/{total} passed, {failed}/{total} failed")

    if failed == 0:
        logger.info("🎉 All schema tests passed successfully!")
        return True
    else:
        logger.error(f"❌ {failed} test(s) failed")
        return False


def main():
    """Main function"""

    if len(sys.argv) > 1 and sys.argv[1] == "--verbose":
        logging.getLogger().setLevel(logging.DEBUG)

    success = run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
