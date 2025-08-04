#!/usr/bin/env python3
"""
Utility Functions for Selenium Scraper Framework

Provides common utility functions for web scraping including text processing,
URL validation, retry decorators, and helper functions for the scraper framework.

Issue: https://github.com/devpouya/swissnews/issues/3
"""

import re
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from loguru import logger


def retry(
    max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 2.0
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by for each retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.2f} seconds..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


def clean_text(text: str) -> str:
    """
    Clean and normalize text extracted from web pages.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned and normalized text
    """
    if not text:
        return ""

    # Remove HTML entities and decode them
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    # Remove extra whitespace and normalize
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # Remove common web artifacts
    text = re.sub(r"\[.*?\]", "", text)  # Remove bracketed content like [Advertisement]
    text = re.sub(
        r"\(.*?Werbung.*?\)", "", text, flags=re.IGNORECASE
    )  # Remove German ads
    text = re.sub(
        r"\(.*?Publicité.*?\)", "", text, flags=re.IGNORECASE
    )  # Remove French ads
    text = re.sub(
        r"\(.*?Pubblicità.*?\)", "", text, flags=re.IGNORECASE
    )  # Remove Italian ads

    # Remove email addresses and phone numbers (privacy)
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[email]", text
    )
    text = re.sub(r"\b\+?[\d\s\-\(\)]{8,}\b", "[phone]", text)

    return text.strip()


def normalize_url(url: str, base_url: str = "") -> str:
    """
    Normalize and validate URLs.

    Args:
        url: URL to normalize
        base_url: Base URL for resolving relative URLs

    Returns:
        Normalized absolute URL
    """
    if not url:
        return ""

    # Handle relative URLs
    if base_url and not url.startswith(("http://", "https://")):
        url = urljoin(base_url, url)

    # Parse and reconstruct URL to normalize
    parsed = urlparse(url)

    # Ensure scheme is https for security
    if parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")

    # Remove fragment (anchor) for consistency
    parsed = parsed._replace(fragment="")

    # Remove tracking parameters
    if parsed.query:
        query_params = []
        for param in parsed.query.split("&"):
            if param and not any(
                tracking in param.lower()
                for tracking in ["utm_", "fbclid", "gclid", "_ga", "ref="]
            ):
                query_params.append(param)
        parsed = parsed._replace(query="&".join(query_params))

    return urlunparse(parsed)


def is_valid_url(url: str) -> bool:
    """
    Validate if a string is a properly formatted URL.

    Args:
        url: URL string to validate

    Returns:
        True if URL is valid, False otherwise
    """
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except Exception:
        return False


def extract_domain(url: str) -> str:
    """
    Extract domain name from URL.

    Args:
        url: URL to extract domain from

    Returns:
        Domain name or empty string if invalid
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def is_article_url(url: str, article_patterns: Optional[List[str]] = None) -> bool:
    """
    Determine if a URL likely points to an article.

    Args:
        url: URL to check
        article_patterns: Optional list of patterns that indicate article URLs

    Returns:
        True if URL appears to be an article, False otherwise
    """
    if not is_valid_url(url):
        return False

    # Default patterns for Swiss news sites
    if article_patterns is None:
        article_patterns = [
            r"/article/",
            r"/story/",
            r"/news/",
            r"/\d{4}/\d{2}/\d{2}/",  # Date patterns
            r"/[a-z]+-[a-z]+-[a-z]+",  # Hyphenated titles
            r"/\d+/",  # Article IDs
        ]

    url_lower = url.lower()

    # Check for article patterns
    for pattern in article_patterns:
        if re.search(pattern, url_lower):
            return True

    # Exclude common non-article URLs
    exclusion_patterns = [
        r"/category/",
        r"/tag/",
        r"/author/",
        r"/search",
        r"/archive",
        r"/feed",
        r"/rss",
        r"/sitemap",
        r"/contact",
        r"/about",
        r"/impressum",
        r"/datenschutz",
    ]

    for pattern in exclusion_patterns:
        if re.search(pattern, url_lower):
            return False

    return True


def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse various date string formats common in Swiss news sites.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not date_str:
        return None

    # Common date formats in Swiss news
    date_formats = [
        "%d.%m.%Y %H:%M",  # 01.01.2024 14:30
        "%d.%m.%Y",  # 01.01.2024
        "%Y-%m-%d %H:%M:%S",  # 2024-01-01 14:30:00
        "%Y-%m-%d",  # 2024-01-01
        "%d/%m/%Y",  # 01/01/2024
        "%m/%d/%Y",  # 01/01/2024 (US format)
    ]

    # Clean the date string
    date_str = clean_text(date_str)

    # Try parsing with each format
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # Try parsing relative dates (German)
    if any(word in date_str.lower() for word in ["vor", "minutes", "stunden", "heute"]):
        return datetime.now(timezone.utc)  # Approximate for relative dates

    logger.warning(f"Could not parse date string: {date_str}")
    return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be safe for use as a filename.

    Args:
        filename: String to sanitize

    Returns:
        Safe filename string
    """
    if not filename:
        return "untitled"

    # Replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove control characters
    filename = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", filename)

    # Limit length
    filename = filename[:200]

    # Ensure it doesn't start/end with dots or spaces
    filename = filename.strip(". ")

    return filename or "untitled"


def get_language_from_url(url: str) -> Optional[str]:
    """
    Attempt to detect language from URL patterns.

    Args:
        url: URL to analyze

    Returns:
        Language code (de, fr, it, rm) or None if not detected
    """
    if not url:
        return None

    url_lower = url.lower()

    # Check for language in domain
    if ".ch" in url_lower:
        if any(domain in url_lower for domain in ["nzz.ch", "20min.ch", "srf.ch"]):
            return "de"
        elif any(domain in url_lower for domain in ["letemps.ch", "rts.ch", "tdg.ch"]):
            return "fr"
        elif any(
            domain in url_lower for domain in ["cdt.ch", "rsi.ch", "laregione.ch"]
        ):
            return "it"

    # Check for language indicators in path
    if "/de/" in url_lower or "/deutsch/" in url_lower:
        return "de"
    elif "/fr/" in url_lower or "/francais/" in url_lower:
        return "fr"
    elif "/it/" in url_lower or "/italiano/" in url_lower:
        return "it"
    elif "/rm/" in url_lower or "/romansh/" in url_lower:
        return "rm"

    return None


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple text similarity between two strings.

    Args:
        text1: First text string
        text2: Second text string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not text1 or not text2:
        return 0.0

    # Simple word-based similarity
    words1 = set(clean_text(text1).lower().split())
    words2 = set(clean_text(text2).lower().split())

    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0


def get_text_summary(text: str, max_length: int = 200) -> str:
    """
    Create a summary of text by taking the first sentences up to max_length.

    Args:
        text: Text to summarize
        max_length: Maximum length of summary

    Returns:
        Text summary
    """
    if not text or len(text) <= max_length:
        return text

    # Try to break at sentence boundaries
    sentences = re.split(r"[.!?]+", text)
    summary = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(summary + sentence) <= max_length - 3:  # Leave room for "..."
            summary += sentence + ". "
        else:
            break

    if len(summary) < len(text):
        summary = summary.rstrip() + "..."

    return summary.strip()


def format_filesize(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f} {size_names[i]}"


def log_scraping_stats(stats: Dict[str, Any]) -> None:
    """
    Log scraping statistics in a consistent format.

    Args:
        stats: Dictionary containing scraping statistics
    """
    outlet = stats.get("outlet", "Unknown")
    articles_found = stats.get("articles_found", 0)
    articles_scraped = stats.get("articles_scraped", 0)
    errors = stats.get("errors", 0)
    duration = stats.get("duration", 0)

    success_rate = (
        (articles_scraped / articles_found * 100) if articles_found > 0 else 0
    )

    logger.info(
        f"Scraping completed for '{outlet}': "
        f"{articles_scraped}/{articles_found} articles scraped "
        f"({success_rate:.1f}% success rate), "
        f"{errors} errors, "
        f"duration: {duration:.2f}s"
    )
