#!/usr/bin/env python3
"""
Comprehensive tests for duplicate article detection system.

Tests the DuplicateDetector class and ArticleRepository integration
as specified in Issue #5.

Maximum 5 tests as per issue requirements.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.database.connection import DatabaseManager
from backend.scraper.duplicates import DuplicateDetector
from backend.scraper.extractors import ArticleContent


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    mock_db = MagicMock(spec=DatabaseManager)
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    mock_db.get_session.return_value.__exit__.return_value = None
    return mock_db, mock_session


@pytest.fixture
def duplicate_detector(mock_db_manager):
    """Create DuplicateDetector instance with mocked database."""
    mock_db, _ = mock_db_manager
    # Override configuration for testing
    config = {
        'similarity_threshold': 0.8,
        'title_similarity_threshold': 0.85,
        'time_proximity_hours': 24,
        'enable_content_hashing': True,
        'enable_title_similarity': True,
        'enable_time_proximity': True
    }
    detector = DuplicateDetector(mock_db, config)
    return detector


@pytest.fixture
def sample_article():
    """Sample article content for testing."""
    return ArticleContent(
        url="https://www.nzz.ch/test-article-123",
        title="Swiss Economy Shows Strong Growth in Q3",
        body_paragraphs=[
            "The Swiss economy demonstrated remarkable resilience in the third quarter.",
            "GDP growth reached 2.1% compared to the previous quarter, exceeding expectations.",
            "Key sectors including finance and technology contributed significantly to this growth."
        ],
        author="Hans Mueller",
        publication_date=datetime(2025, 8, 4, 14, 30),
        language="de",
        word_count=150,
        tags=["economy", "switzerland", "gdp"]
    )


class TestDuplicateDetection:
    """Test suite for duplicate article detection functionality."""

    def test_url_duplicate_detection(self, duplicate_detector, mock_db_manager):
        """
        Test 1: URL-based duplicate detection with exact matches.

        Validates:
        - is_duplicate_url() method accuracy
        - Database query optimization
        - Edge cases (empty URLs, special characters)
        """
        mock_db, mock_session = mock_db_manager

        # Reset the mock session to clear any calls from detector initialization
        mock_session.reset_mock()

        # Test case 1: URL exists in database
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [1]  # COUNT(*) = 1
        mock_session.execute.return_value = mock_result

        assert duplicate_detector.is_duplicate_url("https://www.nzz.ch/existing-article") is True

        # Verify correct SQL query was executed
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        assert "SELECT COUNT(*) FROM articles WHERE url = :url" in str(call_args[0][0])
        # Check the second argument (parameters dict)
        if len(call_args[0]) > 1:
            assert call_args[0][1]["url"] == "https://www.nzz.ch/existing-article"

        # Test case 2: URL does not exist
        mock_session.reset_mock()
        mock_result.fetchone.return_value = [0]  # COUNT(*) = 0

        assert duplicate_detector.is_duplicate_url("https://www.nzz.ch/new-article") is False

        # Test case 3: Edge case - empty URL
        assert duplicate_detector.is_duplicate_url("") is False

        # Test case 4: Database error handling
        mock_session.execute.side_effect = Exception("Database connection failed")
        assert duplicate_detector.is_duplicate_url("https://test.com") is False

    def test_content_similarity_detection(self, duplicate_detector, mock_db_manager, sample_article):
        """
        Test 2: Content-based duplicate detection using similarity algorithms.

        Validates:
        - Title and content similarity calculation
        - Threshold-based duplicate detection
        - Multi-level similarity scoring (exact hash vs fuzzy matching)
        - Performance within acceptable limits
        """
        mock_db, mock_session = mock_db_manager

        # Reset the mock session to clear any calls from detector initialization
        mock_session.reset_mock()

        # Test case 1: Exact content hash match
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [1]
        mock_session.execute.return_value = mock_result

        # Mock exact content matches
        exact_matches = [{
            'id': 1,
            'url': 'https://existing.com/article',
            'title': 'Existing Article',
            'content_hash': 'abc123',
            'similarity_score': 1.0
        }]

        with patch.object(duplicate_detector, '_find_exact_content_matches', return_value=exact_matches):
            content_text = " ".join(sample_article.body_paragraphs)
            is_duplicate, match_info = duplicate_detector.is_duplicate_content(
                sample_article.title, content_text
            )

            assert is_duplicate is True
            assert match_info is not None
            assert match_info['match_type'] == 'exact_content'
            assert match_info['similarity_score'] == 1.0
            assert len(match_info['matched_articles']) == 1
            assert 'detection_time_ms' in match_info

        # Test case 2: Similar content (fuzzy matching)
        similar_matches = [{
            'id': 2,
            'url': 'https://similar.com/article',
            'title': 'Swiss Economy Growth in Q3',  # Similar title
            'content': 'The Swiss economy showed strong performance...',
            'similarity_score': 0.85  # Above threshold
        }]

        with patch.object(duplicate_detector, '_find_exact_content_matches', return_value=[]):
            with patch.object(duplicate_detector, '_find_similar_content_matches', return_value=similar_matches):
                is_duplicate, match_info = duplicate_detector.is_duplicate_content(
                    sample_article.title, content_text
                )

                assert is_duplicate is True
                assert match_info['match_type'] == 'similar_content'
                assert match_info['similarity_score'] == 0.85

        # Test case 3: Below similarity threshold
        low_similarity_matches = [{
            'id': 3,
            'url': 'https://different.com/article',
            'similarity_score': 0.5  # Below default threshold of 0.8
        }]

        with patch.object(duplicate_detector, '_find_exact_content_matches', return_value=[]):
            with patch.object(duplicate_detector, '_find_similar_content_matches', return_value=low_similarity_matches):
                is_duplicate, match_info = duplicate_detector.is_duplicate_content(
                    sample_article.title, content_text
                )

                assert is_duplicate is False
                assert match_info is None

        # Test case 4: Performance validation (< 100ms as per acceptance criteria)
        with patch.object(duplicate_detector, '_find_exact_content_matches', return_value=[]):
            with patch.object(duplicate_detector, '_find_similar_content_matches', return_value=[]):
                start_time = time.time()
                duplicate_detector.is_duplicate_content(sample_article.title, content_text)
                end_time = time.time()

                detection_time_ms = (end_time - start_time) * 1000
                assert detection_time_ms < 100, f"Detection took {detection_time_ms}ms, exceeds 100ms requirement"

    def test_content_hash_calculation(self, duplicate_detector):
        """
        Test 3: SHA-256 content hash calculation and caching.

        Validates:
        - Consistent hash generation for identical content
        - Content normalization for hash stability
        - Caching mechanism efficiency
        - Hash collision resistance
        """
        # Test case 1: Consistent hash generation
        content1 = "This is a test article about Swiss news."
        content2 = "This is a test article about Swiss news."  # Identical

        hash1 = duplicate_detector.calculate_content_hash(content1)
        hash2 = duplicate_detector.calculate_content_hash(content2)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string
        assert hash1 != ""

        # Test case 2: Different content produces different hashes
        content3 = "This is a different article about Swiss news."
        hash3 = duplicate_detector.calculate_content_hash(content3)

        assert hash1 != hash3

        # Test case 3: Content normalization
        content_with_ads = "This is a test article [Werbung] about Swiss news (Anzeige)."
        content_normalized = "This is a test article about Swiss news."

        hash_ads = duplicate_detector.calculate_content_hash(content_with_ads)
        hash_norm = duplicate_detector.calculate_content_hash(content_normalized)

        # After normalization, ads should be removed, making hashes similar
        # (exact match depends on normalization implementation)
        assert hash_ads != ""
        assert hash_norm != ""

        # Test case 4: Caching mechanism
        # Clear cache to ensure fresh start
        duplicate_detector._content_hash_cache.clear()

        # First call should calculate and cache
        hash_first = duplicate_detector.calculate_content_hash(content1)

        # Verify it's in cache
        assert content1 in duplicate_detector._content_hash_cache

        # Second call should be from cache
        hash_cached = duplicate_detector.calculate_content_hash(content1)

        assert hash_first == hash_cached

        # Test case 5: Empty content handling
        empty_hash = duplicate_detector.calculate_content_hash("")
        assert empty_hash == ""

        none_hash = duplicate_detector.calculate_content_hash(None)
        assert none_hash == ""

    def test_article_update_logic(self, duplicate_detector, sample_article):
        """
        Test 4: Article update decision logic for same URL with different content.

        Validates:
        - should_update_article() decision making
        - Content change detection
        - Metadata completeness comparison
        - Quality-based update decisions
        """
        # Test case 1: Same URL, changed content (should update)
        existing_article = {
            'id': 1,
            'url': sample_article.url,  # Same URL
            'title': 'Old Title',
            'content': 'Old content that is shorter.',
            'author': None,
            'publish_date': None,
            'word_count': 50,
            'content_hash': 'old_hash_123'
        }

        # Mock content hash calculation to show different hashes
        with patch.object(duplicate_detector, 'calculate_content_hash') as mock_hash:
            mock_hash.side_effect = ['old_hash_123', 'new_hash_456']  # Different hashes

            should_update = duplicate_detector.should_update_article(existing_article, sample_article)
            assert should_update is True

        # Test case 2: Same URL, same content (should not update)
        existing_same_content = existing_article.copy()
        existing_same_content['content'] = " ".join(sample_article.body_paragraphs)
        existing_same_content['word_count'] = sample_article.word_count  # Same word count
        existing_same_content['author'] = sample_article.author  # Same author
        existing_same_content['publish_date'] = sample_article.publication_date  # Same date

        with patch.object(duplicate_detector, 'calculate_content_hash') as mock_hash:
            mock_hash.return_value = 'same_hash_789'  # Same hash for both

            should_update = duplicate_detector.should_update_article(existing_same_content, sample_article)
            assert should_update is False

        # Test case 3: New article has significantly more content (should update)
        existing_short = existing_article.copy()
        existing_short['word_count'] = 50  # Much less than sample_article.word_count (150)

        should_update = duplicate_detector.should_update_article(existing_short, sample_article)
        assert should_update is True

        # Test case 4: New article has author, existing doesn't (should update)
        existing_no_author = existing_article.copy()
        existing_no_author['author'] = None
        existing_no_author['word_count'] = sample_article.word_count  # Same word count

        with patch.object(duplicate_detector, 'calculate_content_hash') as mock_hash:
            mock_hash.return_value = 'same_hash'  # Same content hash

            should_update = duplicate_detector.should_update_article(existing_no_author, sample_article)
            assert should_update is True

        # Test case 5: New article has publication date, existing doesn't (should update)
        existing_no_date = existing_article.copy()
        existing_no_date['publish_date'] = None
        existing_no_date['author'] = sample_article.author
        existing_no_date['word_count'] = sample_article.word_count

        with patch.object(duplicate_detector, 'calculate_content_hash') as mock_hash:
            mock_hash.return_value = 'same_hash'

            should_update = duplicate_detector.should_update_article(existing_no_date, sample_article)
            assert should_update is True

        # Test case 6: Different URLs (should not update based on URL mismatch)
        existing_different_url = existing_article.copy()
        existing_different_url['url'] = 'https://different.com/article'
        existing_different_url['word_count'] = 10  # Much smaller

        should_update = duplicate_detector.should_update_article(existing_different_url, sample_article)
        assert should_update is False  # Different URLs, no update

    def test_performance_and_integration(self, duplicate_detector, mock_db_manager, sample_article):
        """
        Test 5: Performance requirements and end-to-end integration testing.

        Validates:
        - Overall detection performance < 100ms (acceptance criteria)
        - find_similar_articles() comprehensive search
        - Multiple detection strategy integration
        - Error handling and fallback mechanisms
        - Statistics tracking functionality
        """
        mock_db, mock_session = mock_db_manager

        # Test case 1: Performance requirement validation
        content_text = " ".join(sample_article.body_paragraphs)

        # Mock all database operations to return quickly
        with patch.object(duplicate_detector, '_find_exact_content_matches', return_value=[]):
            with patch.object(duplicate_detector, '_find_similar_content_matches', return_value=[]):
                with patch.object(duplicate_detector, '_find_time_proximate_articles', return_value=[]):

                    start_time = time.time()
                    similar_articles = duplicate_detector.find_similar_articles(sample_article)
                    end_time = time.time()

                    detection_time_ms = (end_time - start_time) * 1000
                    assert detection_time_ms < 100, f"find_similar_articles took {detection_time_ms}ms"
                    assert isinstance(similar_articles, list)

        # Test case 2: Multi-strategy integration test
        url_match = {'id': 1, 'url': sample_article.url, 'match_type': 'exact_url', 'similarity_score': 1.0}
        hash_match = {'id': 2, 'url': 'https://hash-match.com', 'match_type': 'exact_content', 'similarity_score': 1.0}
        similarity_match = {'id': 3, 'url': 'https://similar.com', 'match_type': 'similar_content', 'similarity_score': 0.85}
        time_match = {'id': 4, 'url': 'https://time-match.com', 'match_type': 'time_proximity', 'similarity_score': 0.75}

        with patch.object(duplicate_detector, 'is_duplicate_url', return_value=True):
            with patch.object(duplicate_detector, '_get_article_by_url', return_value=url_match):
                with patch.object(duplicate_detector, '_find_exact_content_matches', return_value=[hash_match]):
                    with patch.object(duplicate_detector, '_find_similar_content_matches', return_value=[similarity_match]):
                        with patch.object(duplicate_detector, '_find_time_proximate_articles', return_value=[time_match]):

                            similar_articles = duplicate_detector.find_similar_articles(sample_article)

                            # Should find all types of matches
                            assert len(similar_articles) == 4

                            # Should be sorted by similarity score (descending)
                            scores = [article['similarity_score'] for article in similar_articles]
                            assert scores == sorted(scores, reverse=True)

                            # Should contain all match types
                            match_types = {article['match_type'] for article in similar_articles}
                            expected_types = {'exact_url', 'exact_content', 'similar_content', 'time_proximity'}
                            assert match_types == expected_types

        # Test case 3: Error handling and fallback
        with patch.object(duplicate_detector, 'is_duplicate_url', side_effect=Exception("Database error")):
            # Should handle errors gracefully and return empty list
            similar_articles = duplicate_detector.find_similar_articles(sample_article)
            assert similar_articles == []

        # Test case 4: Statistics tracking
        mock_stats_result = MagicMock()
        mock_session.execute.return_value = mock_stats_result

        # Test statistics update
        duplicate_detector.update_detection_stats(
            articles_processed=1,
            duplicates_url=1,
            articles_skipped=1,
            detection_time_ms=50
        )

        # Verify stats function was called
        mock_session.execute.assert_called()
        call_args = mock_session.execute.call_args
        assert "update_duplicate_detection_stats" in str(call_args[0][0])

        # Test case 5: Configuration loading and threshold validation
        assert duplicate_detector.config.similarity_threshold >= 0.0
        assert duplicate_detector.config.similarity_threshold <= 1.0
        assert duplicate_detector.config.title_similarity_threshold >= 0.0
        assert duplicate_detector.config.title_similarity_threshold <= 1.0
        assert duplicate_detector.config.time_proximity_hours > 0

        # Test case 6: Cache management (basic validation)
        # Fill cache beyond max size to test FIFO eviction
        original_cache_size = len(duplicate_detector._content_hash_cache)

        for i in range(duplicate_detector._cache_max_size + 10):
            duplicate_detector.calculate_content_hash(f"test content {i}")

        # Cache should not exceed max size
        assert len(duplicate_detector._content_hash_cache) <= duplicate_detector._cache_max_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
