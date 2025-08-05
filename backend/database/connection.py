"""
Database connection utilities for Swiss News Aggregator

This module provides database connection management, session handling,
and common database operations for the Swiss News Aggregator project.

Author: Claude (GitHub Issue #2)
Created: 2025-08-04
"""

import logging
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Tuple, Type

if TYPE_CHECKING:
    from backend.scraper.duplicates import DuplicateDetector
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# Set up logging
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration management"""

    def __init__(self) -> None:
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "swissnews")
        self.username = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "")
        self.ssl_mode = os.getenv("DB_SSL_MODE", "prefer")

        # Connection pool settings
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))

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
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.username,
            "password": self.password,
            "sslmode": self.ssl_mode,
            "connect_timeout": 10,
            "application_name": "swissnews-aggregator",
        }


class DatabaseManager:
    """Main database manager class"""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._engine = None
        self._session_factory = None
        self.metadata = MetaData()

    @property
    def engine(self) -> Engine:
        """Lazy-loaded SQLAlchemy engine"""
        if self._engine is None:
            self._engine = create_engine(
                self.config.connection_string,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
                future=True,
            )
            logger.info(
                f"Created database engine for {self.config.host}:{self.config.port}"
            )
        return self._engine

    @property
    def session_factory(self) -> Type[Session]:
        """Lazy-loaded session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine, expire_on_commit=False
            )
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
    def get_raw_connection(
        self,
    ) -> Generator[psycopg2.extensions.connection, None, None]:
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
                    text(
                        "SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1"
                    )
                )
                row = result.fetchone()
                return str(row[0]) if row else None
        except Exception as e:
            logger.error(f"Failed to get schema version: {e}")
            return None

    def execute_sql_file(self, file_path: str) -> bool:
        """Execute SQL commands from a file"""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
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
                text("SELECT * FROM outlets WHERE id = :id"), {"id": outlet_id}
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    def get_outlets_by_language(self, language: str) -> List[Dict[str, Any]]:
        """Get outlets by language"""
        with self.db.get_session() as session:
            result = session.execute(
                text(
                    "SELECT * FROM outlets WHERE language = :lang AND is_active = true ORDER BY name"
                ),
                {"lang": language},
            )
            return [dict(row._mapping) for row in result]

    def create_outlet(self, outlet_data: Dict[str, Any]) -> int:
        """Create a new outlet"""
        with self.db.get_session() as session:
            result = session.execute(
                text(
                    """
                INSERT INTO outlets (name, url, language, owner, city, canton, occurrence, status)
                VALUES (:name, :url, :language, :owner, :city, :canton, :occurrence, :status)
                RETURNING id
                """
                ),
                outlet_data,
            )
            return int(result.fetchone()[0])

    def update_outlet(self, outlet_id: int, outlet_data: Dict[str, Any]) -> bool:
        """Update an existing outlet"""
        with self.db.get_session() as session:
            result = session.execute(
                text(
                    """
                UPDATE outlets
                SET name = :name, url = :url, language = :language, owner = :owner,
                    city = :city, canton = :canton, occurrence = :occurrence, status = :status
                WHERE id = :id
                """
                ),
                {**outlet_data, "id": outlet_id},
            )
            return bool(result.rowcount > 0)


class ArticleRepository:
    """Repository for article-related database operations"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._duplicate_detector: Optional["DuplicateDetector"] = None

    def get_recent_articles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent articles with outlet information"""
        with self.db.get_session() as session:
            result = session.execute(
                text(
                    """
                SELECT * FROM articles_with_outlets
                ORDER BY publish_date DESC NULLS LAST, scraped_at DESC
                LIMIT :limit
                """
                ),
                {"limit": limit},
            )
            return [dict(row._mapping) for row in result]

    def get_articles_by_outlet(
        self, outlet_id: int, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get articles by outlet"""
        with self.db.get_session() as session:
            result = session.execute(
                text(
                    """
                SELECT * FROM articles
                WHERE outlet_id = :outlet_id
                ORDER BY publish_date DESC NULLS LAST, scraped_at DESC
                LIMIT :limit
                """
                ),
                {"outlet_id": outlet_id, "limit": limit},
            )
            return [dict(row._mapping) for row in result]

    def create_article(self, article_data: Dict[str, Any]) -> int:
        """Create a new article"""
        with self.db.get_session() as session:
            result = session.execute(
                text(
                    """
                INSERT INTO articles (url, title, content, summary, author, publish_date,
                                    language, outlet_id, is_paywalled, word_count, tags, content_hash)
                VALUES (:url, :title, :content, :summary, :author, :publish_date,
                        :language, :outlet_id, :is_paywalled, :word_count, :tags, :content_hash)
                RETURNING id
                """
                ),
                article_data,
            )
            return int(result.fetchone()[0])

    def article_exists(self, url: str) -> bool:
        """Check if article with given URL already exists"""
        with self.db.get_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM articles WHERE url = :url"), {"url": url}
            )
            return bool(result.fetchone()[0] > 0)

    def get_outlet_stats(self) -> List[Dict[str, Any]]:
        """Get outlet statistics"""
        with self.db.get_session() as session:
            result = session.execute(text("SELECT * FROM outlet_stats"))
            return [dict(row._mapping) for row in result]

    @property
    def duplicate_detector(self) -> "DuplicateDetector":
        """Lazy-loaded duplicate detector instance"""
        if self._duplicate_detector is None:
            from backend.scraper.duplicates import DuplicateDetector

            self._duplicate_detector = DuplicateDetector(self.db)
        return self._duplicate_detector

    def create_article_with_duplicate_check(self, article_data: Any) -> Tuple[int, str]:
        """
        Create article with comprehensive duplicate detection.

        Args:
            article_data: ArticleContent object or dict with article data

        Returns:
            Tuple[article_id, action] where action is:
            - 'created': New article created
            - 'updated': Existing article updated
            - 'skipped': Duplicate found, no action taken
        """
        import time

        from backend.scraper.extractors import ArticleContent

        start_time = time.time()

        try:
            # Convert ArticleContent to dict if needed
            if isinstance(article_data, ArticleContent):
                article_dict = self._article_content_to_dict(article_data)
                article_obj = article_data
            else:
                article_dict = article_data
                # Create basic ArticleContent for duplicate detection
                article_obj = ArticleContent(
                    url=article_dict.get("url", ""),
                    title=article_dict.get("title", ""),
                    body_paragraphs=(
                        article_dict.get("content", "").split("\n\n")
                        if article_dict.get("content")
                        else []
                    ),
                    author=article_dict.get("author"),
                    publication_date=article_dict.get("publish_date"),
                )

            # 1. Check for URL duplicates first (fastest)
            if self.duplicate_detector.is_duplicate_url(article_obj.url):
                existing_article = self._get_article_by_url(article_obj.url)
                if existing_article and self.duplicate_detector.should_update_article(
                    existing_article, article_obj
                ):
                    # Update existing article
                    article_id = self._update_article(
                        existing_article["id"], article_dict
                    )
                    self._update_stats(
                        detection_time_ms=int((time.time() - start_time) * 1000),
                        articles_updated=1,
                    )
                    return article_id, "updated"
                else:
                    # Skip duplicate
                    self._update_stats(
                        detection_time_ms=int((time.time() - start_time) * 1000),
                        articles_skipped=1,
                        duplicates_url=1,
                    )
                    return existing_article["id"] if existing_article else 0, "skipped"

            # 2. Check for content duplicates
            content_text = " ".join(article_obj.body_paragraphs)
            is_duplicate, match_info = self.duplicate_detector.is_duplicate_content(
                article_obj.title, content_text
            )

            if is_duplicate and match_info:
                best_match = (
                    match_info["matched_articles"][0]
                    if match_info["matched_articles"]
                    else None
                )
                if best_match and self.duplicate_detector.should_update_article(
                    best_match, article_obj
                ):
                    # Update existing article
                    article_id = self._update_article(best_match["id"], article_dict)
                    self._update_stats(
                        detection_time_ms=match_info["detection_time_ms"],
                        articles_updated=1,
                    )
                    return article_id, "updated"
                else:
                    # Skip duplicate
                    self._update_stats(
                        detection_time_ms=match_info["detection_time_ms"],
                        articles_skipped=1,
                        duplicates_content=1,
                    )
                    return best_match["id"] if best_match else 0, "skipped"

            # 3. No duplicates found, create new article
            # Calculate and add content hash
            article_dict["content_hash"] = (
                self.duplicate_detector.calculate_content_hash(content_text)
            )

            article_id = self.create_article(article_dict)
            self._update_stats(
                detection_time_ms=int((time.time() - start_time) * 1000),
                articles_processed=1,
            )

            return article_id, "created"

        except Exception as e:
            logger.error(f"Error in create_article_with_duplicate_check: {e}")
            # Fallback to basic creation without duplicate detection
            try:
                article_id = self.create_article(
                    article_dict if "article_dict" in locals() else article_data
                )
                return article_id, "created"
            except Exception as fallback_error:
                logger.error(f"Fallback article creation failed: {fallback_error}")
                raise

    def find_duplicates_for_article(self, article_data: Any) -> List[Dict[str, Any]]:
        """
        Find all potential duplicates for an article using multiple strategies.

        Args:
            article_data: ArticleContent object or dict with article data

        Returns:
            List of potential duplicate articles with similarity information
        """
        try:
            from backend.scraper.extractors import ArticleContent

            # Convert to ArticleContent if needed
            if isinstance(article_data, ArticleContent):
                article_obj = article_data
            else:
                article_obj = ArticleContent(
                    url=article_data.get("url", ""),
                    title=article_data.get("title", ""),
                    body_paragraphs=(
                        article_data.get("content", "").split("\n\n")
                        if article_data.get("content")
                        else []
                    ),
                    author=article_data.get("author"),
                    publication_date=article_data.get("publish_date"),
                )

            return self.duplicate_detector.find_similar_articles(article_obj)

        except Exception as e:
            logger.error(f"Error finding duplicates for article: {e}")
            return []

    def get_articles_by_content_hash(self, content_hash: str) -> List[Dict[str, Any]]:
        """
        Fast lookup of articles by content hash.

        Args:
            content_hash: SHA-256 hash of article content

        Returns:
            List of articles with matching content hash
        """
        try:
            with self.db.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT id, url, title, content, author, publish_date, content_hash,
                               word_count, scraped_at, updated_at
                        FROM articles
                        WHERE content_hash = :hash
                        ORDER BY scraped_at DESC
                    """
                    ),
                    {"hash": content_hash},
                )
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error getting articles by content hash: {e}")
            return []

    def _article_content_to_dict(self, article: Any) -> Dict[str, Any]:
        """Convert ArticleContent object to dictionary for database insertion."""
        return {
            "url": article.url,
            "title": article.title or "",
            "content": (
                "\n\n".join(article.body_paragraphs) if article.body_paragraphs else ""
            ),
            "summary": getattr(article, "summary", None),
            "author": article.author,
            "publish_date": article.publication_date,
            "language": article.language,
            "outlet_id": getattr(article, "outlet_id", None),
            "is_paywalled": getattr(article, "is_paywalled", False),
            "word_count": article.word_count or 0,
            "tags": article.tags or [],
        }

    def _get_article_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get article by URL with all details."""
        try:
            with self.db.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT id, url, title, content, author, publish_date, content_hash,
                               word_count, scraped_at, updated_at, language, outlet_id,
                               is_paywalled, tags
                        FROM articles
                        WHERE url = :url
                    """
                    ),
                    {"url": url},
                )
                row = result.fetchone()
                return dict(row._mapping) if row else None
        except Exception as e:
            logger.error(f"Error getting article by URL: {e}")
            return None

    def _update_article(self, article_id: int, article_data: Dict[str, Any]) -> int:
        """Update existing article with new data."""
        try:
            with self.db.get_session() as session:
                session.execute(
                    text(
                        """
                        UPDATE articles
                        SET title = :title, content = :content, summary = :summary,
                            author = :author, publish_date = :publish_date,
                            word_count = :word_count, tags = :tags, content_hash = :content_hash,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """
                    ),
                    {**article_data, "id": article_id},
                )
                return article_id
        except Exception as e:
            logger.error(f"Error updating article {article_id}: {e}")
            raise

    def _update_stats(self, **kwargs: Any) -> None:
        """Update duplicate detection statistics."""
        try:
            self.duplicate_detector.update_detection_stats(**kwargs)
        except Exception as e:
            logger.warning(f"Failed to update detection stats: {e}")


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
                os.path.dirname(__file__), "migrations", "001_initial_schema.sql"
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
