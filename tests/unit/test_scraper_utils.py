#!/usr/bin/env python3
"""
Unit tests for scraper utility functions.

Tests text processing, URL validation, retry decorators, and other utility functions.

Issue: https://github.com/devpouya/swissnews/issues/3
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timezone
import time

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from scraper.utils import (
    retry, clean_text, normalize_url, is_valid_url, extract_domain,
    is_article_url, parse_date_string, sanitize_filename, get_language_from_url,
    calculate_text_similarity, get_text_summary, format_filesize, log_scraping_stats
)


class TestRetryDecorator:
    """Test cases for the retry decorator."""

    def test_retry_success_first_attempt(self):
        """Test retry decorator with success on first attempt."""
        @retry(max_attempts=3, delay=0.1)
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_retry_success_after_failures(self):
        """Test retry decorator with success after some failures."""
        call_count = 0

        @retry(max_attempts=3, delay=0.1, backoff_factor=1.0)
        def function_with_retries():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        with patch('time.sleep'):  # Mock sleep to speed up test
            result = function_with_retries()

        assert result == "success"
        assert call_count == 3

    def test_retry_all_attempts_fail(self):
        """Test retry decorator when all attempts fail."""
        @retry(max_attempts=3, delay=0.1)
        def always_failing_function():
            raise Exception("Always fails")

        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(Exception, match="Always fails"):
                always_failing_function()


class TestTextProcessing:
    """Test cases for text processing functions."""

    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        dirty_text = "  This  is   a\t\ntest  with   extra   spaces  "
        clean = clean_text(dirty_text)
        assert clean == "This is a test with extra spaces"

    def test_clean_text_html_entities(self):
        """Test cleaning HTML entities."""
        text_with_entities = "Test &amp; more &lt;text&gt; &quot;quoted&quot; &nbsp;spaced"
        clean = clean_text(text_with_entities)
        assert clean == 'Test & more <text> "quoted" spaced'

    def test_clean_text_remove_brackets(self):
        """Test removal of bracketed content."""
        text_with_brackets = "This is text [Advertisement] with more content [Sponsored]"
        clean = clean_text(text_with_brackets)
        assert clean == "This is text with more content"

    def test_clean_text_remove_ads(self):
        """Test removal of advertisement text in multiple languages."""
        german_ad = "Content here (Werbung) and more"
        french_ad = "Content here (Publicité) and more"
        italian_ad = "Content here (Pubblicità) and more"

        assert clean_text(german_ad) == "Content here and more"
        assert clean_text(french_ad) == "Content here and more"
        assert clean_text(italian_ad) == "Content here and more"

    def test_clean_text_remove_personal_info(self):
        """Test removal of email addresses and phone numbers."""
        text_with_info = "Contact us at test@example.com or call +41 44 123 4567"
        clean = clean_text(text_with_info)
        assert clean == "Contact us at [email] or call [phone]"

    def test_clean_text_empty_input(self):
        """Test cleaning empty or None input."""
        assert clean_text("") == ""
        assert clean_text(None) == ""
        assert clean_text("   ") == ""


class TestURLProcessing:
    """Test cases for URL processing functions."""

    def test_normalize_url_basic(self):
        """Test basic URL normalization."""
        url = "http://example.com/path"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/path"

    def test_normalize_url_relative_to_absolute(self):
        """Test conversion of relative URL to absolute."""
        relative_url = "/article/test"
        base_url = "https://example.com"
        normalized = normalize_url(relative_url, base_url)
        assert normalized == "https://example.com/article/test"

    def test_normalize_url_remove_fragment(self):
        """Test removal of URL fragment."""
        url_with_fragment = "https://example.com/article#section1"
        normalized = normalize_url(url_with_fragment)
        assert normalized == "https://example.com/article"

    def test_normalize_url_remove_tracking_params(self):
        """Test removal of tracking parameters."""
        url_with_tracking = "https://example.com/article?utm_source=test&content=real&fbclid=123"
        normalized = normalize_url(url_with_tracking)
        assert normalized == "https://example.com/article?content=real"

    def test_is_valid_url_valid_urls(self):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "https://sub.domain.com/path/to/resource?param=value"
        ]

        for url in valid_urls:
            assert is_valid_url(url) is True

    def test_is_valid_url_invalid_urls(self):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://example.com",  # Missing netloc in parsed result
            "://missing-scheme.com",
            None
        ]

        for url in invalid_urls:
            assert is_valid_url(url) is False

    def test_extract_domain(self):
        """Test domain extraction from URLs."""
        test_cases = [
            ("https://www.example.com/path", "www.example.com"),
            ("http://subdomain.test.org", "subdomain.test.org"),
            ("https://EXAMPLE.COM", "example.com"),  # Should be lowercase
            ("invalid-url", ""),
            ("", "")
        ]

        for url, expected_domain in test_cases:
            assert extract_domain(url) == expected_domain

    def test_is_article_url_default_patterns(self):
        """Test article URL detection with default patterns."""
        article_urls = [
            "https://example.com/article/test-story",
            "https://news.com/story/breaking-news",
            "https://site.ch/news/latest-update",
            "https://outlet.com/2024/01/15/daily-report",
            "https://media.ch/long-article-title-with-hyphens",
            "https://news.org/12345/"
        ]

        for url in article_urls:
            assert is_article_url(url) is True

    def test_is_article_url_exclusions(self):
        """Test article URL detection excludes non-article URLs."""
        non_article_urls = [
            "https://example.com/category/politics",
            "https://news.com/tag/breaking",
            "https://site.ch/author/reporter",
            "https://outlet.com/search?q=test",
            "https://media.ch/about",
            "https://news.org/contact"
        ]

        for url in non_article_urls:
            assert is_article_url(url) is False

    def test_is_article_url_custom_patterns(self):
        """Test article URL detection with custom patterns."""
        custom_patterns = [r'/custom-article/', r'/special/\d+/']

        url = "https://example.com/custom-article/test"
        assert is_article_url(url, custom_patterns) is True

        url = "https://example.com/special/123/"
        assert is_article_url(url, custom_patterns) is True

        url = "https://example.com/other/path"
        assert is_article_url(url, custom_patterns) is False


class TestDateParsing:
    """Test cases for date parsing functions."""

    def test_parse_date_string_common_formats(self):
        """Test parsing common date formats."""
        test_cases = [
            ("01.01.2024 14:30", datetime(2024, 1, 1, 14, 30)),
            ("15.12.2023", datetime(2023, 12, 15)),
            ("2024-01-01 14:30:00", datetime(2024, 1, 1, 14, 30)),
            ("2024-01-01", datetime(2024, 1, 1)),
            ("01/01/2024", datetime(2024, 1, 1)),
        ]

        for date_str, expected in test_cases:
            result = parse_date_string(date_str)
            assert result == expected

    def test_parse_date_string_relative_dates(self):
        """Test parsing relative date strings."""
        relative_dates = ["vor 2 Stunden", "5 minutes ago", "heute"]

        for date_str in relative_dates:
            result = parse_date_string(date_str)
            assert result is not None
            # Should be close to current time (within 24 hours)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            time_diff = abs((result - now).total_seconds())
            assert time_diff < 86400  # Less than 24 hours

    def test_parse_date_string_invalid(self):
        """Test parsing invalid date strings."""
        invalid_dates = ["", "invalid date", "32.01.2024", None]

        for date_str in invalid_dates:
            result = parse_date_string(date_str)
            assert result is None


class TestUtilityFunctions:
    """Test cases for various utility functions."""

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            ("normal_filename.txt", "normal_filename.txt"),
            ("file with spaces.txt", "file with spaces.txt"),
            ("file<>:\"/\\|?*.txt", "file_________.txt"),  # Invalid chars replaced
            ("", "untitled"),
            ("   ", "untitled"),
            ("." * 250, "." * 200),  # Length limited
            ("...file...", "file"),  # Stripped dots
        ]

        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected

    def test_get_language_from_url(self):
        """Test language detection from URLs."""
        test_cases = [
            ("https://www.nzz.ch/article", "de"),
            ("https://www.20min.ch/story", "de"),
            ("https://www.letemps.ch/article", "fr"),
            ("https://www.rts.ch/news", "fr"),
            ("https://www.cdt.ch/articolo", "it"),
            ("https://www.rsi.ch/news", "it"),
            ("https://example.com/de/article", "de"),
            ("https://example.com/fr/nouvelles", "fr"),
            ("https://example.com/it/notizie", "it"),
            ("https://unknown.com/article", None),
        ]

        for url, expected_lang in test_cases:
            result = get_language_from_url(url)
            assert result == expected_lang

    def test_calculate_text_similarity(self):
        """Test text similarity calculation."""
        # Identical texts
        text1 = "This is a test text"
        text2 = "This is a test text"
        assert calculate_text_similarity(text1, text2) == 1.0

        # Completely different texts
        text1 = "This is text one"
        text2 = "That was content two"
        similarity = calculate_text_similarity(text1, text2)
        assert 0.0 <= similarity <= 1.0

        # Partial overlap
        text1 = "This is a test"
        text2 = "This is different"
        similarity = calculate_text_similarity(text1, text2)
        assert 0.0 < similarity < 1.0

        # Empty texts
        assert calculate_text_similarity("", "") == 1.0
        assert calculate_text_similarity("text", "") == 0.0
        assert calculate_text_similarity("", "text") == 0.0

    def test_get_text_summary(self):
        """Test text summarization."""
        # Short text (no truncation needed)
        short_text = "This is a short text."
        summary = get_text_summary(short_text, 100)
        assert summary == short_text

        # Long text (truncation needed)
        long_text = "This is the first sentence. This is the second sentence. This is the third sentence."
        summary = get_text_summary(long_text, 50)
        assert len(summary) <= 53  # 50 + "..."
        assert summary.endswith("...")
        assert "This is the first sentence." in summary

        # Empty text
        assert get_text_summary("", 100) == ""

    def test_format_filesize(self):
        """Test file size formatting."""
        test_cases = [
            (0, "0 B"),
            (512, "512.0 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
        ]

        for size_bytes, expected in test_cases:
            result = format_filesize(size_bytes)
            assert result == expected

    @patch('scraper.utils.logger')
    def test_log_scraping_stats(self, mock_logger):
        """Test scraping statistics logging."""
        stats = {
            "outlet": "Test Outlet",
            "articles_found": 10,
            "articles_scraped": 8,
            "errors": 2,
            "duration": 45.67
        }

        log_scraping_stats(stats)

        mock_logger.info.assert_called_once()
        logged_message = mock_logger.info.call_args[0][0]

        assert "Test Outlet" in logged_message
        assert "8/10" in logged_message
        assert "80.0%" in logged_message  # Success rate
        assert "2 errors" in logged_message
        assert "45.67s" in logged_message


if __name__ == "__main__":
    pytest.main([__file__])
