#!/usr/bin/env python3
"""
Advanced Article Content Extraction System

Provides comprehensive content extraction capabilities for Swiss news outlets,
including full article text, metadata, multimedia content, and validation.

Issue: https://github.com/devpouya/swissnews/issues/4
"""

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


@dataclass
class ImageContent:
    """Represents extracted image content with metadata."""

    url: str
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class ExtractionMetadata:
    """Metadata about the extraction process."""

    extraction_timestamp: datetime
    extraction_duration_ms: int
    selectors_used: Dict[str, str]
    fallback_used: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ArticleContent:
    """Complete article content with all extracted information."""

    url: str
    title: str
    subtitle: Optional[str] = None
    body_paragraphs: List[str] = field(default_factory=list)
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    images: List[ImageContent] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    language: Optional[str] = None
    word_count: int = 0
    reading_time_minutes: int = 0
    content_quality_score: float = 0.0
    extraction_metadata: Optional[ExtractionMetadata] = None


class ArticleExtractor:
    """
    Advanced article content extraction system.

    Extracts comprehensive content from news articles including text, metadata,
    and multimedia content with structure preservation and validation.
    """

    def __init__(self, outlet_config: Dict[str, Any]):
        """
        Initialize extractor with outlet-specific configuration.

        Args:
            outlet_config: Configuration dictionary containing selectors and settings
        """
        self.config = outlet_config
        self.outlet_name = outlet_config.get("name", "unknown")
        self.language = outlet_config.get("language", "de")
        self.selectors = outlet_config.get("selectors", {})
        self.content_selectors = outlet_config.get("content_selectors", {})
        self.exclusion_selectors = outlet_config.get("exclusion_selectors", {})

        # Initialize content processor
        self.processor = ContentProcessor(outlet_config)

        logger.info(f"Initialized ArticleExtractor for {self.outlet_name}")

    def extract_full_content(
        self, driver: webdriver.Chrome, url: str
    ) -> ArticleContent:
        """
        Extract complete article content with all metadata and media.

        Args:
            driver: Selenium WebDriver instance
            url: Article URL being extracted

        Returns:
            ArticleContent object with all extracted information
        """
        start_time = time.time()
        extraction_metadata = ExtractionMetadata(
            extraction_timestamp=datetime.now(),
            extraction_duration_ms=0,
            selectors_used={},
        )

        try:
            article = ArticleContent(url=url, title="")

            # Extract core content
            article.title = self._extract_title(driver, extraction_metadata)
            article.subtitle = self._extract_subtitle(driver, extraction_metadata)
            article = self._extract_body_content(driver, article, extraction_metadata)

            # Extract metadata
            article.author = self._extract_author(driver, extraction_metadata)
            article.publication_date = self._extract_date(driver, extraction_metadata)
            article.tags = self._extract_tags(driver, extraction_metadata)
            article.categories = self._extract_categories(driver, extraction_metadata)

            # Extract multimedia content
            article.images = self._extract_images(driver, url, extraction_metadata)

            # Process and enhance content
            article = self.processor.enhance_content(article)

            # Calculate content metrics
            article.word_count = self._calculate_word_count(article)
            article.reading_time_minutes = self._calculate_reading_time(
                article.word_count
            )
            article.content_quality_score = self._assess_content_quality(article)
            article.language = self.language

            # Finalize extraction metadata
            extraction_metadata.extraction_duration_ms = int(
                (time.time() - start_time) * 1000
            )
            article.extraction_metadata = extraction_metadata

            logger.info(
                f"Successfully extracted content for '{article.title[:50]}...' "
                f"({article.word_count} words, quality: {article.content_quality_score:.2f})"
            )

            return article

        except Exception as e:
            logger.error(f"Failed to extract content from {url}: {e}")
            # Return basic article structure with error info
            extraction_metadata.extraction_duration_ms = int(
                (time.time() - start_time) * 1000
            )
            extraction_metadata.warnings.append(f"Extraction failed: {str(e)}")

            return ArticleContent(
                url=url, title="", extraction_metadata=extraction_metadata
            )

    def _extract_title(
        self, driver: webdriver.Chrome, metadata: ExtractionMetadata
    ) -> str:
        """Extract article title using configured selectors."""
        selectors = [
            self.content_selectors.get("title"),
            self.selectors.get("title"),
            "h1",  # Fallback
            ".headline",
            "[data-testid*='title']",
            "[data-qa*='headline']",
        ]

        for selector in selectors:
            if not selector:
                continue

            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                title = element.text.strip()
                if title:
                    metadata.selectors_used["title"] = selector
                    return self.processor.clean_title(title)
            except NoSuchElementException:
                continue

        metadata.warnings.append("No title found")
        return ""

    def _extract_subtitle(
        self, driver: webdriver.Chrome, metadata: ExtractionMetadata
    ) -> Optional[str]:
        """Extract article subtitle if present."""
        selectors = [
            self.content_selectors.get("subtitle"),
            ".subtitle",
            ".article__subtitle",
            ".headline__subtitle",
            "h2:first-of-type",
            ".lead",
        ]

        for selector in selectors:
            if not selector:
                continue

            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                subtitle = element.text.strip()
                if subtitle and len(subtitle) > 10:  # Avoid false positives
                    metadata.selectors_used["subtitle"] = selector
                    return self.processor.clean_text(subtitle)
            except NoSuchElementException:
                continue

        return None

    def _extract_body_content(
        self,
        driver: webdriver.Chrome,
        article: ArticleContent,
        metadata: ExtractionMetadata,
    ) -> ArticleContent:
        """Extract article body content with structure preservation."""
        content_selectors = [
            self.content_selectors.get("main_text"),
            self.selectors.get("content"),
            ".article__body p",
            ".content__body p",
            ".article-content p",
            ".story-content p",
        ]

        # Extract main content paragraphs
        paragraphs = []
        for selector in content_selectors:
            if not selector:
                continue

            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    metadata.selectors_used["content"] = selector
                    paragraphs = [
                        elem.text.strip() for elem in elements if elem.text.strip()
                    ]
                    break
            except Exception as e:
                logger.warning(f"Error with content selector '{selector}': {e}")
                continue

        # Clean and process paragraphs
        article.body_paragraphs = self.processor.process_paragraphs(paragraphs)

        # Extract quotes
        article.quotes = self._extract_quotes(driver, metadata)

        # Extract highlights
        article.highlights = self._extract_highlights(driver, metadata)

        return article

    def _extract_author(
        self, driver: webdriver.Chrome, metadata: ExtractionMetadata
    ) -> Optional[str]:
        """Extract article author information."""
        selectors = [
            self.content_selectors.get("author"),
            self.selectors.get("author"),
            ".author__name",
            ".byline__author",
            ".article__author",
            "[data-testid*='author']",
        ]

        for selector in selectors:
            if not selector:
                continue

            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                author = element.text.strip()
                if author:
                    metadata.selectors_used["author"] = selector
                    return self.processor.clean_author_name(author)
            except NoSuchElementException:
                continue

        return None

    def _extract_date(
        self, driver: webdriver.Chrome, metadata: ExtractionMetadata
    ) -> Optional[datetime]:
        """Extract publication date."""
        selectors = [
            self.content_selectors.get("date"),
            self.selectors.get("date"),
            ".article__date",
            ".publish-date",
            ".publication-date",
            "time[datetime]",
            "[data-testid*='date']",
        ]

        for selector in selectors:
            if not selector:
                continue

            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)

                # Try datetime attribute first
                datetime_attr = element.get_attribute("datetime")
                if datetime_attr:
                    try:
                        parsed_date = datetime.fromisoformat(
                            datetime_attr.replace("Z", "+00:00")
                        )
                        metadata.selectors_used["date"] = selector
                        return parsed_date
                    except ValueError:
                        pass

                # Try text content
                date_text = element.text.strip()
                if date_text:
                    parsed_date = self.processor.parse_date_string(date_text)
                    if parsed_date:
                        metadata.selectors_used["date"] = selector
                        return parsed_date

            except NoSuchElementException:
                continue

        return None

    def _extract_tags(
        self, driver: webdriver.Chrome, metadata: ExtractionMetadata
    ) -> List[str]:
        """Extract article tags/topics."""
        selectors = [
            self.content_selectors.get("tags"),
            ".article__tags a",
            ".topic-tags a",
            ".tags a",
            "[data-testid*='tag'] a",
        ]

        tags = []
        for selector in selectors:
            if not selector:
                continue

            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    metadata.selectors_used["tags"] = selector
                    tags = [elem.text.strip() for elem in elements if elem.text.strip()]
                    break
            except Exception:
                continue

        return self.processor.clean_tags(tags)

    def _extract_categories(
        self, driver: webdriver.Chrome, metadata: ExtractionMetadata
    ) -> List[str]:
        """Extract article categories."""
        selectors = [
            self.content_selectors.get("categories"),
            ".breadcrumb a",
            ".category-link",
            ".section-name",
            "[data-testid*='category']",
        ]

        categories = []
        for selector in selectors:
            if not selector:
                continue

            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    metadata.selectors_used["categories"] = selector
                    categories = [
                        elem.text.strip() for elem in elements if elem.text.strip()
                    ]
                    break
            except Exception:
                continue

        return self.processor.clean_categories(categories)

    def _extract_images(
        self, driver: webdriver.Chrome, base_url: str, metadata: ExtractionMetadata
    ) -> List[ImageContent]:
        """Extract article images with captions."""
        image_selectors = [
            self.content_selectors.get("images"),
            ".article__image img",
            ".content-image img",
            ".article-content img",
            "figure img",
        ]

        caption_selectors = [
            self.content_selectors.get("image_captions"),
            ".image-caption",
            ".photo-caption",
            "figcaption",
            ".caption",
        ]

        images = []
        for selector in image_selectors:
            if not selector:
                continue

            try:
                img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if img_elements:
                    metadata.selectors_used["images"] = selector

                    for img in img_elements:
                        src = img.get_attribute("src")
                        if not src:
                            continue

                        # Convert relative URLs to absolute
                        if not src.startswith(("http://", "https://")):
                            src = urljoin(base_url, src)

                        # Extract image metadata
                        alt_text = img.get_attribute("alt")
                        width_str = img.get_attribute("width")
                        height_str = img.get_attribute("height")
                        width = self._safe_int(width_str)
                        height = self._safe_int(height_str)

                        # Try to find caption for this image
                        caption = self._find_image_caption(img, caption_selectors)

                        images.append(
                            ImageContent(
                                url=src,
                                caption=caption,
                                alt_text=alt_text,
                                width=width,
                                height=height,
                            )
                        )
                    break
            except Exception as e:
                logger.warning(
                    f"Error extracting images with selector '{selector}': {e}"
                )
                continue

        return self.processor.filter_quality_images(images)

    def _extract_quotes(
        self, driver: webdriver.Chrome, metadata: ExtractionMetadata
    ) -> List[str]:
        """Extract quotes and blockquotes from article."""
        selectors = [
            self.content_selectors.get("quotes"),
            "blockquote",
            ".quote",
            ".pullquote",
            "[data-component='Quote']",
        ]

        quotes = []
        for selector in selectors:
            if not selector:
                continue

            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    quotes = [
                        elem.text.strip() for elem in elements if elem.text.strip()
                    ]
                    if quotes:
                        metadata.selectors_used["quotes"] = selector
                        break
            except Exception:
                continue

        return self.processor.clean_quotes(quotes)

    def _extract_highlights(
        self, driver: webdriver.Chrome, metadata: ExtractionMetadata
    ) -> List[str]:
        """Extract highlighted or emphasized content."""
        selectors = [
            self.content_selectors.get("highlights"),
            ".highlight",
            ".callout",
            ".emphasis",
            "strong",
            ".important",
        ]

        highlights = []
        for selector in selectors:
            if not selector:
                continue

            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    highlights = [
                        elem.text.strip()
                        for elem in elements
                        if elem.text.strip() and len(elem.text.strip()) > 10
                    ]
                    if highlights:
                        metadata.selectors_used["highlights"] = selector
                        break
            except Exception:
                continue

        return highlights[:5]  # Limit to avoid noise

    def _find_image_caption(
        self, img_element: WebElement, caption_selectors: List[str]
    ) -> Optional[str]:
        """Find caption for a specific image element."""
        # Try to find caption in parent elements
        parent = img_element.find_element(By.XPATH, "..")

        for selector in caption_selectors:
            if not selector:
                continue

            try:
                caption_elem = parent.find_element(By.CSS_SELECTOR, selector)
                caption = caption_elem.text.strip()
                if caption:
                    return str(caption)
            except NoSuchElementException:
                continue

        return None

    def _safe_int(self, value: Optional[str]) -> Optional[int]:
        """Safely convert string to integer."""
        try:
            return int(value) if value else None
        except (ValueError, TypeError):
            return None

    def _calculate_word_count(self, article: ArticleContent) -> int:
        """Calculate total word count of article content."""
        text_parts = [article.title or ""]
        if article.subtitle:
            text_parts.append(article.subtitle)
        text_parts.extend(article.body_paragraphs)

        full_text = " ".join(text_parts)
        return len(full_text.split())

    def _calculate_reading_time(self, word_count: int) -> int:
        """Calculate estimated reading time in minutes (assuming 200 WPM)."""
        return max(1, round(word_count / 200))

    def _assess_content_quality(self, article: ArticleContent) -> float:
        """Assess content quality on a scale of 0.0 to 1.0."""
        score = 0.0

        # Title quality (20%)
        if article.title and len(article.title) > 10:
            score += 0.2

        # Content quality (40%)
        if article.body_paragraphs and len(article.body_paragraphs) >= 3:
            avg_paragraph_length = sum(
                len(p.split()) for p in article.body_paragraphs
            ) / len(article.body_paragraphs)
            if avg_paragraph_length > 15:  # Substantial paragraphs
                score += 0.4
            else:
                score += 0.2

        # Metadata quality (25%)
        metadata_score = 0.0
        if article.author:
            metadata_score += 0.1
        if article.publication_date:
            metadata_score += 0.1
        if article.tags:
            metadata_score += 0.05
        score += metadata_score

        # Content richness (15%)
        if article.images:
            score += 0.05
        if article.quotes:
            score += 0.05
        if article.word_count > 300:
            score += 0.05

        return min(1.0, score)


class ContentProcessor:
    """
    Content processing and enhancement utilities.

    Handles text cleaning, structure preservation, and content enhancement.
    """

    def __init__(self, outlet_config: Dict[str, Any]):
        """Initialize processor with outlet configuration."""
        self.config = outlet_config
        self.language = outlet_config.get("language", "de")
        self.text_processing = outlet_config.get("text_processing", {})

    def enhance_content(self, article: ArticleContent) -> ArticleContent:
        """Enhance and clean all content in the article."""
        # Clean title and subtitle
        if article.title:
            article.title = self.clean_title(article.title)
        if article.subtitle:
            article.subtitle = self.clean_text(article.subtitle)

        # Process body paragraphs
        article.body_paragraphs = self.process_paragraphs(article.body_paragraphs)

        # Clean quotes
        article.quotes = self.clean_quotes(article.quotes)

        return article

    def clean_title(self, title: str) -> str:
        """Clean and normalize article title."""
        if not title:
            return ""

        # Remove common title artifacts
        title = re.sub(r"\s*\|\s*.*$", "", title)  # Remove site name after |
        title = re.sub(r"\s*-\s*.*$", "", title)  # Remove site name after -

        return self.clean_text(title)

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Remove HTML artifacts
        text = re.sub(r"&[a-zA-Z]+;", " ", text)
        text = re.sub(r"&#\d+;", " ", text)

        # Remove ad indicators based on language
        if self.language == "de":
            text = re.sub(
                r"\[Werbung\]|\(Anzeige\)|\(Werbung\)", "", text, flags=re.IGNORECASE
            )
        elif self.language == "fr":
            text = re.sub(r"\[Publicité\]|\(Publicité\)", "", text, flags=re.IGNORECASE)
        elif self.language == "it":
            text = re.sub(
                r"\[Pubblicità\]|\(Pubblicità\)", "", text, flags=re.IGNORECASE
            )

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def process_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """Process and clean paragraph content."""
        processed = []

        for paragraph in paragraphs:
            cleaned = self.clean_text(paragraph)

            # Skip short or likely non-content paragraphs
            if len(cleaned) < 20:
                continue

            # Skip paragraphs that look like navigation or UI elements
            if self._is_navigation_text(cleaned):
                continue

            processed.append(cleaned)

        return processed

    def clean_author_name(self, author: str) -> str:
        """Clean author name and remove common prefixes."""
        if not author:
            return ""

        # Remove common prefixes
        prefixes = ["Von ", "By ", "Autor: ", "Author: "]
        for prefix in prefixes:
            if author.startswith(prefix):
                author = author[len(prefix) :]

        return self.clean_text(author)

    def parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date string in various Swiss formats."""
        if not date_str:
            return None

        # Common Swiss date formats
        formats = [
            "%d.%m.%Y %H:%M",  # 01.01.2024 14:30
            "%d.%m.%Y",  # 01.01.2024
            "%Y-%m-%d %H:%M:%S",  # 2024-01-01 14:30:00
            "%Y-%m-%d",  # 2024-01-01
            "%d/%m/%Y",  # 01/01/2024
        ]

        cleaned_date = self.clean_text(date_str)

        for fmt in formats:
            try:
                return datetime.strptime(cleaned_date, fmt)
            except ValueError:
                continue

        return None

    def clean_tags(self, tags: List[str]) -> List[str]:
        """Clean and normalize tag list."""
        cleaned = []
        for tag in tags:
            clean_tag = self.clean_text(tag)
            if clean_tag and len(clean_tag) > 2:
                cleaned.append(clean_tag)
        return list(set(cleaned))  # Remove duplicates

    def clean_categories(self, categories: List[str]) -> List[str]:
        """Clean and normalize category list."""
        cleaned = []
        for category in categories:
            clean_category = self.clean_text(category)
            if clean_category and len(clean_category) > 2:
                # Skip common non-category items
                if clean_category.lower() not in ["home", "startseite", "accueil"]:
                    cleaned.append(clean_category)
        return list(set(cleaned))

    def clean_quotes(self, quotes: List[str]) -> List[str]:
        """Clean and normalize quotes."""
        cleaned = []
        for quote in quotes:
            clean_quote = self.clean_text(quote)
            if clean_quote and len(clean_quote) > 20:  # Substantial quotes only
                # Remove quote marks if present
                clean_quote = clean_quote.strip('"\'""' "")
                cleaned.append(clean_quote)
        return cleaned

    def filter_quality_images(self, images: List[ImageContent]) -> List[ImageContent]:
        """Filter out low-quality or UI images."""
        filtered = []

        for image in images:
            # Skip small images (likely UI elements)
            if image.width and image.height:
                if image.width < 100 or image.height < 100:
                    continue

            # Skip images with UI-related names
            if any(
                ui_term in image.url.lower()
                for ui_term in ["logo", "icon", "button", "banner", "ad"]
            ):
                continue

            filtered.append(image)

        return filtered

    def _is_navigation_text(self, text: str) -> bool:
        """Check if text appears to be navigation or UI element."""
        text_lower = text.lower()

        navigation_indicators = [
            "mehr lesen",
            "weiterlesen",
            "lesen sie auch",
            "related",
            "teilen",
            "share",
            "kommentare",
            "comments",
            "newsletter",
            "abonnieren",
            "subscribe",
        ]

        return any(indicator in text_lower for indicator in navigation_indicators)
