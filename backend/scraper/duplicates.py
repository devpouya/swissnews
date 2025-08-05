#!/usr/bin/env python3
"""
Duplicate Article Detection System

Provides comprehensive duplicate detection capabilities for Swiss news articles
using multiple strategies: URL-based, content-based, hash-based, and time-based.

Issue: https://github.com/devpouya/swissnews/issues/5
"""

import hashlib
import re
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import text

from backend.database.connection import DatabaseManager
from backend.scraper.extractors import ArticleContent


class DuplicateDetectionConfig:
    """Configuration for duplicate detection thresholds and settings."""

    def __init__(
        self,
        similarity_threshold: float = 0.800,
        title_similarity_threshold: float = 0.850,
        time_proximity_hours: int = 24,
        max_similarity_search_days: int = 90,
        enable_content_hashing: bool = True,
        enable_title_similarity: bool = True,
        enable_time_proximity: bool = True,
    ):
        self.similarity_threshold = similarity_threshold
        self.title_similarity_threshold = title_similarity_threshold
        self.time_proximity_hours = time_proximity_hours
        self.max_similarity_search_days = max_similarity_search_days
        self.enable_content_hashing = enable_content_hashing
        self.enable_title_similarity = enable_title_similarity
        self.enable_time_proximity = enable_time_proximity

    @classmethod
    def from_database(cls, db_manager: DatabaseManager) -> "DuplicateDetectionConfig":
        """Load configuration from database."""
        try:
            with db_manager.get_session() as session:
                result = session.execute(
                    text("SELECT * FROM get_duplicate_detection_config()")
                )
                row = result.fetchone()
                if row:
                    return cls(
                        similarity_threshold=float(row[0]),
                        title_similarity_threshold=float(row[1]),
                        time_proximity_hours=int(row[2]),
                        max_similarity_search_days=int(row[3]),
                        enable_content_hashing=bool(row[4]),
                        enable_title_similarity=bool(row[5]),
                        enable_time_proximity=bool(row[6]),
                    )
        except Exception as e:
            logger.warning(f"Failed to load config from database, using defaults: {e}")

        return cls()


class DuplicateDetector:
    """
    Comprehensive duplicate article detection system.

    Implements multiple detection strategies as specified in Issue #5:
    - URL-based: Exact URL matches
    - Content-based: Title + content similarity
    - Hash-based: SHA-256 content fingerprinting
    - Time-based: Publication date proximity analysis
    """

    def __init__(
        self, db_manager: DatabaseManager, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize duplicate detector with database manager and configuration.

        Args:
            db_manager: DatabaseManager instance for database operations
            config: Optional configuration dictionary (overrides database config)
        """
        self.db = db_manager
        self.config = self._load_configuration(config)
        self._content_hash_cache: Dict[str, str] = {}  # Simple LRU-style cache
        self._cache_max_size = 1000

        logger.info(
            f"Initialized DuplicateDetector with thresholds: "
            f"content={self.config.similarity_threshold}, "
            f"title={self.config.title_similarity_threshold}, "
            f"time={self.config.time_proximity_hours}h"
        )

    def _load_configuration(
        self, override_config: Optional[Dict[str, Any]] = None
    ) -> DuplicateDetectionConfig:
        """Load configuration from database with optional overrides."""
        config = DuplicateDetectionConfig.from_database(self.db)

        if override_config:
            for key, value in override_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        return config

    def is_duplicate_url(self, url: str) -> bool:
        """
        Check if article with given URL already exists.

        Args:
            url: Article URL to check

        Returns:
            True if URL already exists in database
        """
        try:
            with self.db.get_session() as session:
                result = session.execute(
                    text("SELECT COUNT(*) FROM articles WHERE url = :url"), {"url": url}
                )
                count = result.fetchone()[0]
                return bool(count > 0)
        except Exception as e:
            logger.error(f"Error checking URL duplicate for {url}: {e}")
            return False

    def is_duplicate_content(
        self, title: str, content: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if article content matches existing articles using similarity.

        Args:
            title: Article title
            content: Article content

        Returns:
            Tuple of (is_duplicate, match_info_dict)
        """
        start_time = time.time()

        try:
            # Calculate content hash for fast exact matches
            content_hash = self.calculate_content_hash(content)

            # First check for exact content hash matches
            exact_matches = self._find_exact_content_matches(content_hash)
            if exact_matches:
                match_info = {
                    "match_type": "exact_content",
                    "similarity_score": 1.0,
                    "matched_articles": exact_matches,
                    "detection_time_ms": int((time.time() - start_time) * 1000),
                }
                return True, match_info

            # If no exact matches, check for similar content
            if self.config.enable_title_similarity:
                similar_matches = self._find_similar_content_matches(title, content)
                if similar_matches:
                    best_match = max(
                        similar_matches, key=lambda x: x["similarity_score"]
                    )
                    if (
                        best_match["similarity_score"]
                        >= self.config.similarity_threshold
                    ):
                        match_info = {
                            "match_type": "similar_content",
                            "similarity_score": best_match["similarity_score"],
                            "matched_articles": similar_matches,
                            "detection_time_ms": int((time.time() - start_time) * 1000),
                        }
                        return True, match_info

            detection_time = int((time.time() - start_time) * 1000)
            logger.debug(f"Content duplicate check completed in {detection_time}ms")
            return False, None

        except Exception as e:
            logger.error(f"Error in content duplicate detection: {e}")
            return False, None

    def calculate_content_hash(self, content: str) -> str:
        """
        Calculate SHA-256 hash of normalized article content.

        Args:
            content: Article content text

        Returns:
            SHA-256 hash string
        """
        if not content:
            return ""

        # Check cache first
        if content in self._content_hash_cache:
            return self._content_hash_cache[content]

        # Normalize content for consistent hashing
        normalized_content = self._normalize_content_for_hashing(content)

        # Calculate SHA-256 hash
        content_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()

        # Cache result (with simple size limit)
        if len(self._content_hash_cache) >= self._cache_max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._content_hash_cache))
            del self._content_hash_cache[oldest_key]

        self._content_hash_cache[content] = content_hash
        return content_hash

    def find_similar_articles(self, article: ArticleContent) -> List[Dict[str, Any]]:
        """
        Find all potentially similar articles using multiple detection methods.

        Args:
            article: ArticleContent object to find similarities for

        Returns:
            List of similar articles with similarity scores and match types
        """
        similar_articles = []

        try:
            # 1. URL-based check
            if self.is_duplicate_url(article.url):
                url_match = self._get_article_by_url(article.url)
                if url_match:
                    url_match["match_type"] = "exact_url"
                    url_match["similarity_score"] = 1.0
                    similar_articles.append(url_match)

            # 2. Content hash check
            if self.config.enable_content_hashing:
                content_text = " ".join(article.body_paragraphs)
                content_hash = self.calculate_content_hash(content_text)
                hash_matches = self._find_exact_content_matches(content_hash)
                for match in hash_matches:
                    match["match_type"] = "exact_content"
                    match["similarity_score"] = 1.0
                    similar_articles.append(match)

            # 3. Title and content similarity check
            if self.config.enable_title_similarity:
                content_text = " ".join(article.body_paragraphs)
                similarity_matches = self._find_similar_content_matches(
                    article.title, content_text
                )
                for match in similarity_matches:
                    match["match_type"] = "similar_content"
                    similar_articles.append(match)

            # 4. Time-based proximity check
            if self.config.enable_time_proximity and article.publication_date:
                time_matches = self._find_time_proximate_articles(
                    article.title, article.publication_date
                )
                for match in time_matches:
                    match["match_type"] = "time_proximity"
                    similar_articles.append(match)

            # Remove duplicates and sort by similarity score
            unique_articles = self._deduplicate_matches(similar_articles)
            return sorted(
                unique_articles, key=lambda x: x["similarity_score"], reverse=True
            )

        except Exception as e:
            logger.error(f"Error finding similar articles: {e}")
            return []

    def should_update_article(
        self, existing: Dict[str, Any], new: ArticleContent
    ) -> bool:
        """
        Determine if an existing article should be updated with new content.

        Args:
            existing: Existing article data from database
            new: New ArticleContent object

        Returns:
            True if article should be updated
        """
        try:
            # Check if URLs match (same article, potentially updated content)
            if existing.get("url") == new.url:
                # Check if content has actually changed
                existing_content = existing.get("content", "")
                new_content = " ".join(new.body_paragraphs)

                existing_hash = self.calculate_content_hash(existing_content)
                new_hash = self.calculate_content_hash(new_content)

                if existing_hash != new_hash:
                    logger.info(f"Content changed for URL {new.url}, should update")
                    return True

                # If content is the same, check for metadata improvements
                existing_word_count = existing.get("word_count", 0)
                new_word_count = new.word_count

                if new_word_count > existing_word_count * 1.2:  # 20% more content
                    logger.info(
                        f"New article has significantly more content "
                        f"({new_word_count} vs {existing_word_count} words)"
                    )
                    return True

                # Check if new article has more complete metadata
                existing_author = existing.get("author")
                new_author = new.author

                if not existing_author and new_author:
                    logger.info("New article has author information, should update")
                    return True

                # Check publication date - prefer earlier/more accurate dates
                existing_date = existing.get("publish_date")
                new_date = new.publication_date

                if not existing_date and new_date:
                    logger.info("New article has publication date, should update")
                    return True

                # Same URL, same content, no metadata improvements
                return False

            # Different URLs - don't update
            return False

        except Exception as e:
            logger.error(f"Error in should_update_article: {e}")
            return False

    def _normalize_content_for_hashing(self, content: str) -> str:
        """Normalize content for consistent hashing."""
        if not content:
            return ""

        # Convert to lowercase
        normalized = content.lower()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove common punctuation that might vary
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Remove common article artifacts
        normalized = re.sub(
            r"\b(werbung|anzeige|publicité|pubblicità)\b", "", normalized
        )

        return normalized.strip()

    def _find_exact_content_matches(self, content_hash: str) -> List[Dict[str, Any]]:
        """Find articles with exact content hash matches."""
        if not content_hash:
            return []

        try:
            with self.db.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT id, url, title, author, publish_date, content_hash, word_count
                        FROM articles
                        WHERE content_hash = :hash
                        ORDER BY scraped_at DESC
                    """
                    ),
                    {"hash": content_hash},
                )
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error finding exact content matches: {e}")
            return []

    def _find_similar_content_matches(
        self, title: str, content: str
    ) -> List[Dict[str, Any]]:
        """Find articles with similar titles and content."""
        try:
            with self.db.get_session() as session:
                # Use trigram similarity for title matching
                result = session.execute(
                    text(
                        """
                        SELECT id, url, title, content, author, publish_date, word_count,
                               similarity(title, :title) as title_similarity
                        FROM recent_articles_for_similarity
                        WHERE similarity(title, :title) > 0.3
                        ORDER BY title_similarity DESC
                        LIMIT 50
                    """
                    ),
                    {"title": title},
                )

                candidates = [dict(row._mapping) for row in result]
                similar_matches = []

                for candidate in candidates:
                    title_sim = self._calculate_title_similarity(
                        title, candidate["title"]
                    )
                    content_sim = self._calculate_content_similarity(
                        content, candidate.get("content", "")
                    )
                    overall_sim = (title_sim * 0.6) + (
                        content_sim * 0.4
                    )  # Weighted average

                    if overall_sim >= self.config.similarity_threshold:
                        candidate["similarity_score"] = overall_sim
                        candidate["title_similarity"] = title_sim
                        candidate["content_similarity"] = content_sim
                        similar_matches.append(candidate)

                return similar_matches

        except Exception as e:
            logger.error(f"Error finding similar content matches: {e}")
            return []

    def _find_time_proximate_articles(
        self, title: str, publish_date: datetime
    ) -> List[Dict[str, Any]]:
        """Find articles published within time proximity window."""
        if not self.config.enable_time_proximity:
            return []

        try:
            time_window = timedelta(hours=self.config.time_proximity_hours)
            start_time = publish_date - time_window
            end_time = publish_date + time_window

            with self.db.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT id, url, title, author, publish_date, word_count,
                               similarity(title, :title) as title_similarity
                        FROM articles
                        WHERE publish_date BETWEEN :start_time AND :end_time
                          AND similarity(title, :title) > :min_similarity
                        ORDER BY title_similarity DESC
                        LIMIT 20
                    """
                    ),
                    {
                        "title": title,
                        "start_time": start_time,
                        "end_time": end_time,
                        "min_similarity": 0.5,
                    },
                )

                matches = []
                for row in result:
                    article = dict(row._mapping)
                    article["similarity_score"] = article["title_similarity"]
                    matches.append(article)

                return matches

        except Exception as e:
            logger.error(f"Error finding time proximate articles: {e}")
            return []

    def _get_article_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get article details by URL."""
        try:
            with self.db.get_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT id, url, title, content, author, publish_date, word_count, content_hash
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

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using SequenceMatcher."""
        if not title1 or not title2:
            return 0.0

        # Normalize titles
        norm_title1 = re.sub(r"[^\w\s]", "", title1.lower()).strip()
        norm_title2 = re.sub(r"[^\w\s]", "", title2.lower()).strip()

        return SequenceMatcher(None, norm_title1, norm_title2).ratio()

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        if not content1 or not content2:
            return 0.0

        # For long content, use Jaccard similarity on word sets
        words1 = set(re.findall(r"\w+", content1.lower()))
        words2 = set(re.findall(r"\w+", content2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _is_within_time_proximity(self, date1: datetime, date2: datetime) -> bool:
        """Check if two dates are within configured time proximity."""
        if not date1 or not date2:
            return False

        time_diff = abs((date1 - date2).total_seconds() / 3600)  # Convert to hours
        return time_diff <= self.config.time_proximity_hours

    def _deduplicate_matches(
        self, matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate matches based on article ID."""
        seen_ids = set()
        unique_matches = []

        for match in matches:
            article_id = match.get("id")
            if article_id and article_id not in seen_ids:
                seen_ids.add(article_id)
                unique_matches.append(match)

        return unique_matches

    def update_detection_stats(
        self,
        articles_processed: int = 1,
        duplicates_url: int = 0,
        duplicates_content: int = 0,
        articles_updated: int = 0,
        articles_skipped: int = 0,
        detection_time_ms: int = 0,
    ) -> None:
        """Update daily duplicate detection statistics."""
        try:
            with self.db.get_session() as session:
                session.execute(
                    text(
                        """
                        SELECT update_duplicate_detection_stats(
                            :articles_processed,
                            :duplicates_url,
                            :duplicates_content,
                            :articles_updated,
                            :articles_skipped,
                            :detection_time_ms
                        )
                    """
                    ),
                    {
                        "articles_processed": articles_processed,
                        "duplicates_url": duplicates_url,
                        "duplicates_content": duplicates_content,
                        "articles_updated": articles_updated,
                        "articles_skipped": articles_skipped,
                        "detection_time_ms": detection_time_ms,
                    },
                )
        except Exception as e:
            logger.error(f"Error updating detection stats: {e}")
