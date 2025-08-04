#!/usr/bin/env python3
"""
Integration tests for PostgreSQL Database Schema

Tests the database schema functionality, migration scripts, and data operations
for the Swiss News Aggregator PostgreSQL database (Issue #2).

Author: Claude (GitHub Issue #2)
Created: 2025-08-04
"""

import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'backend'))

class TestDatabaseSchema(unittest.TestCase):
    """Test database schema without requiring actual database connection"""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.backend_dir = self.project_root / 'backend'
        self.database_dir = self.backend_dir / 'database'
        self.migrations_dir = self.database_dir / 'migrations'
        self.migration_file = self.migrations_dir / '001_initial_schema.sql'
        self.init_file = self.database_dir / 'init.sql'
        self.connection_file = self.database_dir / 'connection.py'
        self.populate_file = self.database_dir / 'populate_outlets.py'
    
    def test_database_directory_structure(self):
        """Test that database directory structure exists."""
        self.assertTrue(self.database_dir.exists(), 
                       "Database directory should exist")
        self.assertTrue(self.migrations_dir.exists(), 
                       "Migrations directory should exist")
    
    def test_migration_file_exists(self):
        """Test that initial migration file exists."""
        self.assertTrue(self.migration_file.exists(),
                       f"Migration file should exist at {self.migration_file}")
    
    def test_init_script_exists(self):
        """Test that database initialization script exists."""
        self.assertTrue(self.init_file.exists(),
                       f"Init script should exist at {self.init_file}")
    
    def test_connection_utilities_exist(self):
        """Test that database connection utilities exist."""
        self.assertTrue(self.connection_file.exists(),
                       f"Connection utilities should exist at {self.connection_file}")
    
    def test_populate_script_exists(self):
        """Test that CSV population script exists."""
        self.assertTrue(self.populate_file.exists(),
                       f"Populate script should exist at {self.populate_file}")
    
    def test_migration_sql_syntax(self):
        """Test basic SQL syntax validation of migration file."""
        with open(self.migration_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check for balanced parentheses
        paren_count = content.count('(') - content.count(')')
        self.assertEqual(paren_count, 0, "Unbalanced parentheses in SQL")
        
        # Check for required CREATE TABLE statements
        self.assertIn('CREATE TABLE outlets', content)
        self.assertIn('CREATE TABLE articles', content)
        
        # Check for indexes
        self.assertIn('CREATE INDEX', content)
        
        # Check for foreign key relationships
        self.assertIn('REFERENCES outlets(id)', content)
        
        # Check for constraints
        self.assertIn('CHECK', content)
        self.assertIn('UNIQUE', content)
    
    def test_migration_contains_required_elements(self):
        """Test that migration contains all required database elements."""
        with open(self.migration_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        required_elements = [
            # Tables
            'CREATE TABLE outlets',
            'CREATE TABLE articles',
            'CREATE TABLE schema_migrations',
            
            # Indexes for performance
            'CREATE INDEX idx_outlets_language',
            'CREATE INDEX idx_articles_outlet_date',
            'CREATE INDEX idx_articles_language_date',
            
            # Views
            'CREATE VIEW articles_with_outlets',
            'CREATE VIEW recent_articles',
            'CREATE VIEW outlet_stats',
            
            # Triggers and functions
            'CREATE OR REPLACE FUNCTION update_updated_at_column',
            'CREATE TRIGGER update_outlets_updated_at',
            'CREATE TRIGGER update_articles_updated_at',
            
            # Constraints
            'CHECK (language IN',
            'REFERENCES outlets(id)',
            'UNIQUE NOT NULL'
        ]
        
        for element in required_elements:
            self.assertIn(element, content, f"Missing required element: {element}")
    
    def test_schema_supports_multilingual_content(self):
        """Test that schema supports Swiss multilingual content."""
        with open(self.migration_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check language constraints
        swiss_languages = ['de', 'fr', 'it', 'rm']
        for lang in swiss_languages:
            self.assertIn(f"'{lang}'", content, f"Missing support for language: {lang}")
    
    def test_schema_has_performance_indexes(self):
        """Test that schema includes performance-oriented indexes."""
        with open(self.migration_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Count indexes
        index_count = content.count('CREATE INDEX')
        self.assertGreater(index_count, 5, "Should have multiple indexes for performance")
        
        # Check for specific performance indexes
        performance_indexes = [
            'outlet_id, publish_date',  # Articles by outlet and date
            'language',  # Language filtering
            'scraped_at',  # Recent scraping
            'GIN',  # Full-text search indexes
            'tags'  # Tag array indexes
        ]
        
        for index_type in performance_indexes:
            self.assertIn(index_type, content, f"Missing performance index: {index_type}")
    
    def test_connection_utilities_syntax(self):
        """Test that connection utilities file is syntactically valid."""
        # Test by attempting to compile the file
        with open(self.connection_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        try:
            compile(content, str(self.connection_file), 'exec')
        except SyntaxError as e:
            self.fail(f"Connection utilities file has syntax error: {e}")
    
    def test_populate_script_syntax(self):
        """Test that populate script is syntactically valid."""
        with open(self.populate_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        try:
            compile(content, str(self.populate_file), 'exec')
        except SyntaxError as e:
            self.fail(f"Populate script has syntax error: {e}")
    
    def test_init_script_references_migration(self):
        """Test that init script properly references migration file."""
        with open(self.init_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Should reference the migration file
        self.assertIn('001_initial_schema.sql', content)
        self.assertIn('\\i backend/database/migrations/', content)
    
    def test_schema_has_sample_data(self):
        """Test that schema includes sample data for testing."""
        with open(self.migration_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Should have sample outlets and articles
        self.assertIn('INSERT INTO outlets', content)
        self.assertIn('INSERT INTO articles', content)
        
        # Should have outlets in different languages
        self.assertIn("'de'", content)  # German
        self.assertIn("'fr'", content)  # French
        self.assertIn("'it'", content)  # Italian
        self.assertIn("'rm'", content)  # Romansh


class TestDatabaseConfiguration(unittest.TestCase):
    """Test database configuration and connection utilities"""
    
    def setUp(self):
        """Set up test fixtures with mocked environment."""
        # Clear any existing environment variables
        self.env_vars = [
            'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
            'DB_SSL_MODE', 'DB_POOL_SIZE', 'DB_MAX_OVERFLOW', 
            'DB_POOL_TIMEOUT', 'DB_POOL_RECYCLE'
        ]
        self.original_env = {}
        for var in self.env_vars:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Restore original environment."""
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    @patch('psycopg2.connect')
    @patch('sqlalchemy.create_engine')
    def test_database_config_defaults(self, mock_engine, mock_connect):
        """Test database configuration with default values."""
        # Import here to ensure clean environment
        from database.connection import DatabaseConfig
        
        config = DatabaseConfig()
        
        # Test default values
        self.assertEqual(config.host, 'localhost')
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.database, 'swissnews')
        self.assertEqual(config.username, 'postgres')
        self.assertEqual(config.password, '')
        self.assertEqual(config.ssl_mode, 'prefer')
        self.assertEqual(config.pool_size, 5)
    
    @patch('psycopg2.connect')
    @patch('sqlalchemy.create_engine')
    def test_database_config_environment_variables(self, mock_engine, mock_connect):
        """Test database configuration with environment variables."""
        # Set environment variables
        os.environ['DB_HOST'] = 'testhost'
        os.environ['DB_PORT'] = '5433'
        os.environ['DB_NAME'] = 'testdb'
        os.environ['DB_USER'] = 'testuser'
        os.environ['DB_PASSWORD'] = 'testpass'
        os.environ['DB_POOL_SIZE'] = '10'
        
        from database.connection import DatabaseConfig
        
        config = DatabaseConfig()
        
        # Test environment variable values
        self.assertEqual(config.host, 'testhost')
        self.assertEqual(config.port, 5433)
        self.assertEqual(config.database, 'testdb')
        self.assertEqual(config.username, 'testuser')
        self.assertEqual(config.password, 'testpass')
        self.assertEqual(config.pool_size, 10)
    
    @patch('psycopg2.connect')
    @patch('sqlalchemy.create_engine')
    def test_connection_string_format(self, mock_engine, mock_connect):
        """Test connection string generation."""
        from database.connection import DatabaseConfig
        
        config = DatabaseConfig()
        conn_str = config.connection_string
        
        # Should be valid PostgreSQL connection string
        self.assertIn('postgresql://', conn_str)
        self.assertIn('localhost:5432', conn_str)
        self.assertIn('swissnews', conn_str)
        self.assertIn('sslmode=prefer', conn_str)


class TestCSVIntegration(unittest.TestCase):
    """Test CSV to database integration"""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / 'data'
        
        # Create temporary CSV for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_csv = self.temp_dir / 'test_outlets.csv'
        
        # Create sample CSV data
        csv_data = [
            ['news_website', 'url', 'original_language', 'owner', 'city', 'canton', 'occurrence', 'status'],
            ['Test Outlet 1', 'https://test1.ch', 'German', 'Test Owner', 'Zurich', 'Zurich', 'Daily', 'current'],
            ['Test Outlet 2', 'https://test2.ch', 'French', 'Test Owner 2', 'Geneva', 'Geneva', 'Weekly', 'current']
        ]
        
        with open(self.test_csv, 'w', newline='', encoding='utf-8') as file:
            import csv
            writer = csv.writer(file)
            writer.writerows(csv_data)
    
    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir)
    
    def test_csv_data_transformation(self):
        """Test CSV data transformation logic."""
        import sys
        sys.path.append(str(self.project_root / 'backend'))
        
        # Import without actually connecting to database
        with patch('database.connection.db_manager'):
            from database.populate_outlets import clean_outlet_data, normalize_language_code
            
            # Test language normalization
            self.assertEqual(normalize_language_code('German'), 'de')
            self.assertEqual(normalize_language_code('French'), 'fr')
            self.assertEqual(normalize_language_code('Italian'), 'it')
            self.assertEqual(normalize_language_code('Romansch'), 'rm')
            
            # Test data cleaning
            test_row = {
                'news_website': 'Test Outlet',
                'url': 'https://test.ch',
                'original_language': 'German',
                'owner': 'Test Owner',
                'city': 'Zurich',
                'canton': 'Zurich',
                'occurrence': 'Daily',
                'status': 'current'
            }
            
            cleaned = clean_outlet_data(test_row)
            
            self.assertEqual(cleaned['name'], 'Test Outlet')
            self.assertEqual(cleaned['language'], 'de')
            self.assertEqual(cleaned['url'], 'https://test.ch')
            self.assertEqual(cleaned['status'], 'current')
    
    def test_csv_loading(self):
        """Test loading outlets from CSV file."""
        import sys
        sys.path.append(str(self.project_root / 'backend'))
        
        with patch('database.connection.db_manager'):
            from database.populate_outlets import load_outlets_from_csv
            
            outlets = load_outlets_from_csv(str(self.test_csv))
            
            self.assertEqual(len(outlets), 2)
            self.assertEqual(outlets[0]['name'], 'Test Outlet 1')
            self.assertEqual(outlets[0]['language'], 'de')
            self.assertEqual(outlets[1]['name'], 'Test Outlet 2')
            self.assertEqual(outlets[1]['language'], 'fr')


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation functionality"""
    
    def test_schema_validation_script_exists(self):
        """Test that schema validation script exists and works."""
        project_root = Path(__file__).parent.parent.parent
        test_script = project_root / 'backend' / 'database' / 'test_schema.py'
        
        self.assertTrue(test_script.exists(), "Schema test script should exist")
        
        # Test that script is syntactically valid
        with open(test_script, 'r', encoding='utf-8') as file:
            content = file.read()
        
        try:
            compile(content, str(test_script), 'exec')
        except SyntaxError as e:
            self.fail(f"Schema test script has syntax error: {e}")


if __name__ == '__main__':
    # Set up test discovery and run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestDatabaseSchema,
        TestDatabaseConfiguration, 
        TestCSVIntegration,
        TestSchemaValidation
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)