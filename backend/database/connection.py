"""
Database connection utilities for Swiss News Aggregator

This module provides database connection management, session handling,
and common database operations for the Swiss News Aggregator project.

Author: Claude (GitHub Issue #2)
Created: 2025-08-04
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional, Generator, Dict, Any, List
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '5432'))
        self.database = os.getenv('DB_NAME', 'swissnews')
        self.username = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', '')
        self.ssl_mode = os.getenv('DB_SSL_MODE', 'prefer')
        
        # Connection pool settings
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '5'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
    
    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.ssl_mode}"
        )
    
    @property
    def psycopg2_connection_params(self) -> Dict[str, Any]:
        """Generate psycopg2 connection parameters"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.username,
            'password': self.password,
            'sslmode': self.ssl_mode,
            'connect_timeout': 10,
            'application_name': 'swissnews-aggregator'
        }


class DatabaseManager:
    """Main database manager class"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._engine = None
        self._session_factory = None
        self.metadata = MetaData()
        
    @property
    def engine(self):
        """Lazy-loaded SQLAlchemy engine"""
        if self._engine is None:
            self._engine = create_engine(
                self.config.connection_string,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
                future=True
            )
            logger.info(f"Created database engine for {self.config.host}:{self.config.port}")
        return self._engine
    
    @property
    def session_factory(self):
        """Lazy-loaded session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        return self._session_factory
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_raw_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        """Context manager for raw psycopg2 connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.config.psycopg2_connection_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Raw database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_schema_version(self) -> Optional[str]:
        """Get current schema migration version"""
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1")
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get schema version: {e}")
            return None
    
    def execute_sql_file(self, file_path: str) -> bool:
        """Execute SQL commands from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            with self.get_raw_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql_content)
            
            logger.info(f"Successfully executed SQL file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to execute SQL file {file_path}: {e}")
            return False


class OutletRepository:
    """Repository for outlet-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_all_outlets(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all outlets"""
        with self.db.get_session() as session:
            query = "SELECT * FROM outlets"
            if active_only:
                query += " WHERE is_active = true"
            query += " ORDER BY name"
            
            result = session.execute(text(query))
            return [dict(row._mapping) for row in result]
    
    def get_outlet_by_id(self, outlet_id: int) -> Optional[Dict[str, Any]]:
        """Get outlet by ID"""
        with self.db.get_session() as session:
            result = session.execute(
                text("SELECT * FROM outlets WHERE id = :id"),
                {"id": outlet_id}
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None
    
    def get_outlets_by_language(self, language: str) -> List[Dict[str, Any]]:
        """Get outlets by language"""
        with self.db.get_session() as session:
            result = session.execute(
                text("SELECT * FROM outlets WHERE language = :lang AND is_active = true ORDER BY name"),
                {"lang": language}
            )
            return [dict(row._mapping) for row in result]
    
    def create_outlet(self, outlet_data: Dict[str, Any]) -> int:
        """Create a new outlet"""
        with self.db.get_session() as session:
            result = session.execute(
                text("""
                INSERT INTO outlets (name, url, language, owner, city, canton, occurrence, status)
                VALUES (:name, :url, :language, :owner, :city, :canton, :occurrence, :status)
                RETURNING id
                """),
                outlet_data
            )
            return result.fetchone()[0]
    
    def update_outlet(self, outlet_id: int, outlet_data: Dict[str, Any]) -> bool:
        """Update an existing outlet"""
        with self.db.get_session() as session:
            result = session.execute(
                text("""
                UPDATE outlets 
                SET name = :name, url = :url, language = :language, owner = :owner,
                    city = :city, canton = :canton, occurrence = :occurrence, status = :status
                WHERE id = :id
                """),
                {**outlet_data, "id": outlet_id}
            )
            return result.rowcount > 0


class ArticleRepository:
    """Repository for article-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_recent_articles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent articles with outlet information"""
        with self.db.get_session() as session:
            result = session.execute(
                text("""
                SELECT * FROM articles_with_outlets 
                ORDER BY publish_date DESC NULLS LAST, scraped_at DESC 
                LIMIT :limit
                """),
                {"limit": limit}
            )
            return [dict(row._mapping) for row in result]
    
    def get_articles_by_outlet(self, outlet_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get articles by outlet"""
        with self.db.get_session() as session:
            result = session.execute(
                text("""
                SELECT * FROM articles 
                WHERE outlet_id = :outlet_id 
                ORDER BY publish_date DESC NULLS LAST, scraped_at DESC 
                LIMIT :limit
                """),
                {"outlet_id": outlet_id, "limit": limit}
            )
            return [dict(row._mapping) for row in result]
    
    def create_article(self, article_data: Dict[str, Any]) -> int:
        """Create a new article"""
        with self.db.get_session() as session:
            result = session.execute(
                text("""
                INSERT INTO articles (url, title, content, summary, author, publish_date, 
                                    language, outlet_id, is_paywalled, word_count, tags)
                VALUES (:url, :title, :content, :summary, :author, :publish_date,
                        :language, :outlet_id, :is_paywalled, :word_count, :tags)
                RETURNING id
                """),
                article_data
            )
            return result.fetchone()[0]
    
    def article_exists(self, url: str) -> bool:
        """Check if article with given URL already exists"""
        with self.db.get_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM articles WHERE url = :url"),
                {"url": url}
            )
            return result.fetchone()[0] > 0
    
    def get_outlet_stats(self) -> List[Dict[str, Any]]:
        """Get outlet statistics"""
        with self.db.get_session() as session:
            result = session.execute(text("SELECT * FROM outlet_stats"))
            return [dict(row._mapping) for row in result]


# Global database manager instance
db_manager = DatabaseManager()

# Repository instances
outlet_repo = OutletRepository(db_manager)
article_repo = ArticleRepository(db_manager)


def init_database(run_migrations: bool = True) -> bool:
    """Initialize the database with schema and data"""
    try:
        if not db_manager.test_connection():
            logger.error("Cannot connect to database")
            return False
        
        if run_migrations:
            # Run initial schema migration
            migration_file = os.path.join(
                os.path.dirname(__file__), 
                'migrations', 
                '001_initial_schema.sql'
            )
            
            if os.path.exists(migration_file):
                if not db_manager.execute_sql_file(migration_file):
                    logger.error("Failed to run database migrations")
                    return False
            else:
                logger.warning(f"Migration file not found: {migration_file}")
        
        logger.info("Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    # Test database connection and functionality
    import sys
    
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Test connection
    if not db_manager.test_connection():
        print("Database connection failed!")
        sys.exit(1)
    
    print("Database connection successful!")
    
    # Display schema version
    version = db_manager.get_schema_version()
    print(f"Schema version: {version}")
    
    # Test repositories
    outlets = outlet_repo.get_all_outlets()
    print(f"Found {len(outlets)} outlets")
    
    articles = article_repo.get_recent_articles(5)
    print(f"Found {len(articles)} recent articles")
    
    stats = article_repo.get_outlet_stats()
    print(f"Outlet statistics: {len(stats)} outlets with stats")
    
    print("Database utilities test completed successfully!")