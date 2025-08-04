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
    text = re.sub(
        r"\+[\d\s\-\(\)]{8,}", "[phone]", text
    )  # Only match + prefixed numbers

    # Remove extra whitespace and normalize (after all replacements)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

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
        if not url:
            return False
        parsed = urlparse(url)
        return all([parsed.scheme in ("http", "https"), parsed.netloc])
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

        # Exclude common non-article URLs (only for default patterns)
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
    else:
        # Custom patterns provided - only check these
        url_lower = url.lower()
        for pattern in article_patterns:
            if re.search(pattern, url_lower):
                return True
        return False


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
        return datetime.now()  # Approximate for relative dates (timezone-naive)

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


# Advanced Content Extraction Utilities for Issue #4


def advanced_clean_text(
    text: str, language: str = "de", outlet_config: Optional[Dict] = None
) -> str:
    """
    Advanced text cleaning with language-specific and outlet-specific processing.

    Args:
        text: Text to clean
        language: Content language (de, fr, it, rm)
        outlet_config: Optional outlet-specific configuration

    Returns:
        Cleaned and normalized text
    """
    if not text:
        return ""

    # Start with basic cleaning
    text = clean_text(text)

    # Language-specific ad removal
    text = remove_ad_content(text, language)

    # Remove outlet-specific patterns if config provided
    if outlet_config and "text_processing" in outlet_config:
        remove_patterns = outlet_config["text_processing"].get("remove_patterns", [])
        for pattern in remove_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Advanced HTML artifact cleaning
    text = clean_html_artifacts(text)

    # Handle special characters based on language
    text = handle_special_characters(text, language)

    return text.strip()


def remove_ad_content(text: str, language: str) -> str:
    """
    Remove advertisement content based on language-specific patterns.

    Args:
        text: Text to clean
        language: Content language

    Returns:
        Text with ad content removed
    """
    if not text:
        return ""

    ad_patterns = {
        "de": [
            r"\[Werbung\]",
            r"\(Anzeige\)",
            r"\(Werbung\)",
            r"Anzeige\s*:",
            r"Sponsored\s*:",
            r"Partner-Inhalte?",
            r"Werbliche\s+Inhalte?",
        ],
        "fr": [
            r"\[Publicité\]",
            r"\(Publicité\)",
            r"Publicité\s*:",
            r"Contenu\s+sponsorisé",
            r"Partenaire\s*:",
            r"Sponsored\s*:",
        ],
        "it": [
            r"\[Pubblicità\]",
            r"\(Pubblicità\)",
            r"Pubblicità\s*:",
            r"Contenuto\s+sponsorizzato",
            r"Partner\s*:",
            r"Sponsored\s*:",
        ],
    }

    patterns = ad_patterns.get(language, ad_patterns["de"])

    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text


def clean_html_artifacts(text: str) -> str:
    """
    Remove HTML artifacts and encoding issues.

    Args:
        text: Text to clean

    Returns:
        Text with HTML artifacts removed
    """
    if not text:
        return ""

    # Extended HTML entity handling
    html_entities = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&apos;": "'",
        "&#39;": "'",
        "&hellip;": "...",
        "&mdash;": "—",
        "&ndash;": "–",
        "&laquo;": "«",
        "&raquo;": "»",
        "&ldquo;": """,
        "&rdquo;": """,
        "&lsquo;": "'",
        "&rsquo;": "'",
    }

    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)

    # Remove remaining HTML entities
    text = re.sub(r"&[a-zA-Z][a-zA-Z0-9]*;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"&#x[0-9a-fA-F]+;", " ", text)

    # Remove HTML tags if any remain
    text = re.sub(r"<[^>]+>", " ", text)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def handle_special_characters(text: str, language: str) -> str:
    """
    Handle special characters specific to Swiss languages.

    Args:
        text: Text to process
        language: Language code

    Returns:
        Text with properly handled special characters
    """
    if not text:
        return ""

    # Swiss German specific handling
    if language == "de":
        # Normalize umlauts (keep them, don't convert to ae/oe/ue)
        pass  # Keep original Swiss German characters

    # French specific handling
    elif language == "fr":
        # Ensure proper French accents are preserved
        pass  # Keep French accents

    # Italian specific handling
    elif language == "it":
        # Ensure proper Italian accents are preserved
        pass  # Keep Italian accents

    # Remove problematic characters that might cause encoding issues
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

    return text


def preserve_article_structure(elements_text: List[str]) -> str:
    """
    Preserve article structure when combining text elements.

    Args:
        elements_text: List of text elements to combine

    Returns:
        Combined text with preserved structure
    """
    if not elements_text:
        return ""

    # Clean individual elements
    cleaned_elements = []
    for element in elements_text:
        cleaned = advanced_clean_text(element)
        if cleaned and len(cleaned.strip()) > 10:  # Skip very short elements
            cleaned_elements.append(cleaned)

    # Join with double newlines to preserve paragraph structure
    return "\n\n".join(cleaned_elements)


def extract_and_clean_quotes(text: str) -> List[str]:
    """
    Extract and clean quotes from text content.

    Args:
        text: Text to extract quotes from

    Returns:
        List of cleaned quotes
    """
    if not text:
        return []

    quotes = []

    # Pattern for quoted text (various quote styles)
    quote_patterns = [
        r'"([^"]{20,})"',  # Double quotes
        r"'([^']{20,})'",  # Single quotes
        r"«([^»]{20,})»",  # French quotes
        r'"([^"]{20,})"',  # Curly double quotes
        r"'([^']{20,})'",  # Curly single quotes
    ]

    for pattern in quote_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            cleaned_quote = advanced_clean_text(match)
            if cleaned_quote and len(cleaned_quote) > 20:
                quotes.append(cleaned_quote)

    # Remove duplicates while preserving order
    seen = set()
    unique_quotes = []
    for quote in quotes:
        if quote not in seen:
            seen.add(quote)
            unique_quotes.append(quote)

    return unique_quotes


def validate_article_content(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted article content for completeness and quality.

    Args:
        content: Article content dictionary

    Returns:
        Validation result with score and issues
    """
    validation: Dict[str, Any] = {
        "is_valid": True,
        "score": 0.0,
        "issues": [],
        "completeness": 0.0,
    }

    required_fields = ["title", "body_paragraphs", "url"]
    optional_fields = ["author", "publication_date", "tags", "images"]

    # Check required fields
    missing_required = []
    for field in required_fields:
        if not content.get(field):
            missing_required.append(field)

    if missing_required:
        validation["is_valid"] = False
        issues_list = validation["issues"]
        if isinstance(issues_list, list):
            issues_list.append(
                f"Missing required fields: {', '.join(missing_required)}"
            )

    # Calculate completeness score
    total_fields = len(required_fields) + len(optional_fields)
    present_fields = 0

    for field in required_fields + optional_fields:
        field_value = content.get(field)
        if field_value:
            if isinstance(field_value, list) and len(field_value) > 0:
                present_fields += 1
            elif isinstance(field_value, str) and field_value.strip():
                present_fields += 1
            elif field_value:  # For other types like datetime
                present_fields += 1

    validation["completeness"] = present_fields / total_fields

    # Content quality checks
    if content.get("body_paragraphs"):
        paragraphs = content["body_paragraphs"]
        issues_list = validation["issues"]
        score = validation["score"]

        if isinstance(paragraphs, list) and len(paragraphs) < 2:
            if isinstance(issues_list, list):
                issues_list.append("Article has very few paragraphs")

        if isinstance(paragraphs, list):
            total_words = sum(len(str(p).split()) for p in paragraphs)
            if total_words < 50:  # Reduced threshold for "very short"
                if isinstance(issues_list, list):
                    issues_list.append("Article content is very short")
                if isinstance(score, (int, float)):
                    validation["score"] = score - 0.2
            elif total_words > 2000:
                if isinstance(score, (int, float)):
                    validation["score"] = score + 0.1  # Bonus for substantial content

    # Title quality check
    if content.get("title"):
        title = content["title"]
        issues_list = validation["issues"]
        if isinstance(title, str):
            title_length = len(title)
            if title_length < 10:
                if isinstance(issues_list, list):
                    issues_list.append("Title is very short")
            elif title_length > 200:
                if isinstance(issues_list, list):
                    issues_list.append("Title is unusually long")

    # Calculate overall score
    base_score = validation["completeness"]
    current_score = validation["score"]
    if isinstance(base_score, (int, float)) and isinstance(current_score, (int, float)):
        validation["score"] = max(0.0, min(1.0, base_score + current_score))

    # Final validation
    final_score = validation["score"]
    if isinstance(final_score, (int, float)) and final_score < 0.3:
        validation["is_valid"] = False
        issues_list = validation["issues"]
        if isinstance(issues_list, list):
            issues_list.append("Overall content quality is too low")

    return validation


def check_content_completeness(content: str) -> bool:
    """
    Check if content appears to be complete and substantial.

    Args:
        content: Content text to check

    Returns:
        True if content appears complete
    """
    if not content:
        return False

    word_count = len(content.split())

    # Basic completeness indicators
    if word_count < 50:
        return False

    # Check for truncation indicators
    truncation_indicators = [
        "...",
        "[mehr]",
        "[more]",
        "[suite]",
        "[continua]",
        "weiterlesen",
        "lire la suite",
        "leggi tutto",
    ]

    content_lower = content.lower()
    for indicator in truncation_indicators:
        if content_lower.endswith(indicator.lower()):
            return False

    # Check for proper sentence structure
    sentences = re.split(r"[.!?]+", content)
    complete_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    return len(complete_sentences) >= 3


def detect_content_quality(content: str) -> float:
    """
    Detect content quality on a scale of 0.0 to 1.0.

    Args:
        content: Content text to analyze

    Returns:
        Quality score between 0.0 and 1.0
    """
    if not content:
        return 0.0

    score = 0.0

    # Length score (up to 0.3)
    word_count = len(content.split())
    if word_count > 500:
        score += 0.3
    elif word_count > 200:
        score += 0.2
    elif word_count > 100:
        score += 0.1

    # Sentence structure score (up to 0.3)
    sentences = re.split(r"[.!?]+", content)
    complete_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    if len(complete_sentences) > 10:
        score += 0.3
    elif len(complete_sentences) > 5:
        score += 0.2
    elif len(complete_sentences) > 2:
        score += 0.1

    # Language quality indicators (up to 0.2)
    # Check for proper capitalization
    if re.search(r"^[A-ZÄÖÜÀÁÂÃÉÊÍÎÓÔÕÚÛ]", content):
        score += 0.05

    # Check for varied sentence length
    if complete_sentences:
        avg_length = sum(len(s.split()) for s in complete_sentences) / len(
            complete_sentences
        )
        if 10 <= avg_length <= 30:  # Good average sentence length
            score += 0.05

    # Content structure indicators (up to 0.2)
    # Check for paragraphs
    paragraph_breaks = content.count("\n\n")
    if paragraph_breaks > 0:
        score += 0.1

    # Check for absence of excessive repetition
    words = content.lower().split()
    if words:
        unique_words = len(set(words))
        word_diversity = unique_words / len(words)
        if word_diversity > 0.5:
            score += 0.1

    return min(1.0, score)


def validate_metadata_consistency(metadata: Dict[str, Any]) -> bool:
    """
    Validate that extracted metadata is consistent and reasonable.

    Args:
        metadata: Metadata dictionary to validate

    Returns:
        True if metadata appears consistent
    """
    if not metadata:
        return False

    # Date consistency check
    if metadata.get("publication_date"):
        pub_date = metadata["publication_date"]
        if isinstance(pub_date, datetime):
            # Check if date is reasonable (not in future, not too old)
            now = datetime.now()
            if pub_date > now:
                return False
            # Check if date is not older than 20 years (adjust as needed)
            if (now - pub_date).days > 20 * 365:
                return False

    # Author consistency check
    if metadata.get("author"):
        author = metadata["author"]
        # Basic author name validation
        if len(author) < 2 or len(author) > 100:
            return False
        # Check for reasonable author format
        if not re.match(r"^[A-Za-zÀ-ÿĀ-žА-я\s\-\.\']+$", author):
            return False

    # Tags consistency check
    if metadata.get("tags"):
        tags = metadata["tags"]
        if isinstance(tags, list):
            # Check for reasonable number of tags
            if len(tags) > 20:
                return False
            # Check individual tags
            for tag in tags:
                if len(tag) < 2 or len(tag) > 50:
                    return False

    return True
