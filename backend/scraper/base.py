#!/usr/bin/env python3
"""
Base Selenium Scraper Framework

Provides a robust foundation for web scraping Swiss news outlets using Selenium WebDriver.
Includes configurable selectors, error handling, retry logic, and proper resource management.

Issue: https://github.com/devpouya/swissnews/issues/3
"""

import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ScrapingError(Exception):
    """Custom exception for scraping-related errors."""

    pass


class BaseScraper(ABC):
    """
    Base class for Selenium-based web scrapers.

    Provides common functionality for Swiss news outlet scraping including:
    - WebDriver setup and management
    - Configurable timeouts and retry logic
    - Error handling and logging
    - Resource cleanup
    """

    def __init__(self, outlet_config: Dict[str, Any]) -> None:
        """
        Initialize the scraper with outlet-specific configuration.

        Args:
            outlet_config: Dictionary containing outlet configuration including
                          URL, selectors, timeouts, and retry settings
        """
        self.config = outlet_config
        self.outlet_name = outlet_config.get("name", "unknown")
        self.base_url = outlet_config.get("url", "")
        self.selectors = outlet_config.get("selectors", {})
        self.timeouts = outlet_config.get("timeouts", {})
        self.retry_config = outlet_config.get("retry", {})

        # Default configuration values
        self.page_load_timeout = self.timeouts.get("page_load", 30)
        self.element_wait_timeout = self.timeouts.get("element_wait", 10)
        self.max_retry_attempts = self.retry_config.get("max_attempts", 3)
        self.retry_delay = self.retry_config.get("delay", 2)

        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

        logger.info(f"Initialized scraper for outlet: {self.outlet_name}")

    def setup_driver(self) -> webdriver.Chrome:
        """
        Set up and configure Chrome WebDriver with optimal settings.

        Returns:
            Configured Chrome WebDriver instance

        Raises:
            ScrapingError: If driver setup fails
        """
        try:
            chrome_options = Options()

            # Headless mode for production
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument(
                "--disable-javascript"
            )  # Can be overridden if JS needed

            # Window size for consistent rendering
            chrome_options.add_argument("--window-size=1920,1080")

            # User agent for realistic requests
            user_agent = self.config.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            chrome_options.add_argument(f"--user-agent={user_agent}")

            # Performance optimizations
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")

            # Security settings
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")

            # Create driver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.page_load_timeout)

            # Initialize WebDriverWait
            self.wait = WebDriverWait(self.driver, self.element_wait_timeout)

            logger.info(f"WebDriver setup completed for {self.outlet_name}")
            return self.driver

        except Exception as e:
            logger.error(f"Failed to set up WebDriver for {self.outlet_name}: {e}")
            raise ScrapingError(f"WebDriver setup failed: {e}")

    @contextmanager
    def managed_driver(self) -> Any:
        """
        Context manager for automatic driver cleanup.

        Ensures WebDriver is properly closed even if exceptions occur.
        """
        try:
            if not self.driver:
                self.setup_driver()
            yield self.driver
        finally:
            self.cleanup()

    def retry_on_failure(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function with retry logic and exponential backoff.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result if successful

        Raises:
            ScrapingError: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(self.max_retry_attempts):
            try:
                return func(*args, **kwargs)
            except (TimeoutException, WebDriverException, NoSuchElementException) as e:
                last_exception = e
                if attempt < self.max_retry_attempts - 1:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {self.outlet_name}: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retry_attempts} attempts failed for {self.outlet_name}: {e}"
                    )

        raise ScrapingError(
            f"Operation failed after {self.max_retry_attempts} attempts: {last_exception}"
        )

    def safe_find_element(
        self, by: By, selector: str, timeout: Optional[int] = None
    ) -> Optional[Any]:
        """
        Safely find an element with error handling and optional timeout.

        Args:
            by: Selenium By locator type
            selector: CSS selector or other locator string
            timeout: Custom timeout (uses default if None)

        Returns:
            WebElement if found, None otherwise
        """
        try:
            if timeout:
                wait = WebDriverWait(self.driver, timeout)
                return wait.until(EC.presence_of_element_located((by, selector)))
            else:
                return self.wait.until(EC.presence_of_element_located((by, selector)))
        except TimeoutException:
            logger.warning(f"Element not found: {selector} on {self.outlet_name}")
            return None
        except Exception as e:
            logger.error(f"Error finding element {selector} on {self.outlet_name}: {e}")
            return None

    def safe_find_elements(self, by: By, selector: str) -> List[Any]:
        """
        Safely find multiple elements with error handling.

        Args:
            by: Selenium By locator type
            selector: CSS selector or other locator string

        Returns:
            List of WebElements (empty list if none found)
        """
        try:
            return list(self.driver.find_elements(by, selector))
        except Exception as e:
            logger.error(
                f"Error finding elements {selector} on {self.outlet_name}: {e}"
            )
            return []

    def get_page(self, url: str) -> bool:
        """
        Navigate to a page with error handling and validation.

        Args:
            url: URL to navigate to

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.driver:
                self.setup_driver()

            logger.info(f"Navigating to: {url}")
            self.driver.get(url)

            # Wait for page to load
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState")
                == "complete"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to load page {url}: {e}")
            return False

    @abstractmethod
    def scrape_article_list(self) -> List[str]:
        """
        Extract article URLs from the outlet's main page or archive.

        Must be implemented by outlet-specific scrapers.

        Returns:
            List of article URLs
        """
        pass

    @abstractmethod
    def scrape_article_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a specific article URL.

        Must be implemented by outlet-specific scrapers.

        Args:
            url: Article URL to scrape

        Returns:
            Dictionary containing article data (title, content, author, date, etc.)
        """
        pass

    def cleanup(self) -> None:
        """
        Clean up WebDriver resources and close browser.

        Should be called when scraping is complete or in error scenarios.
        """
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"WebDriver cleanup completed for {self.outlet_name}")
            except Exception as e:
                logger.error(f"Error during cleanup for {self.outlet_name}: {e}")
            finally:
                self.driver = None
                self.wait = None

    def __enter__(self) -> "BaseScraper":
        """Context manager entry."""
        self.setup_driver()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with cleanup."""
        self.cleanup()


class OutletScraper(BaseScraper):
    """
    Concrete implementation of BaseScraper for Swiss news outlets.

    Uses configuration-driven selectors to handle different outlet structures.
    """

    def scrape_article_list(self) -> List[str]:
        """
        Extract article URLs using configured selectors.

        Returns:
            List of absolute article URLs
        """
        try:
            article_links_selector = self.selectors.get("article_links")
            if not article_links_selector:
                logger.error(
                    f"No article_links selector configured for {self.outlet_name}"
                )
                return []

            if not self.get_page(self.base_url):
                return []

            # Find article link elements
            link_elements = self.safe_find_elements(
                By.CSS_SELECTOR, article_links_selector
            )

            urls = []
            for element in link_elements:
                try:
                    href = element.get_attribute("href")
                    if href:
                        # Convert relative URLs to absolute
                        absolute_url = urljoin(self.base_url, href)
                        urls.append(absolute_url)
                except StaleElementReferenceException:
                    logger.warning(f"Stale element reference in {self.outlet_name}")
                    continue
                except Exception as e:
                    logger.error(
                        f"Error extracting URL from element in {self.outlet_name}: {e}"
                    )
                    continue

            logger.info(f"Found {len(urls)} article URLs for {self.outlet_name}")
            return urls

        except Exception as e:
            logger.error(f"Failed to scrape article list for {self.outlet_name}: {e}")
            return []

    def scrape_article_content(self, url: str) -> Dict[str, Any]:
        """
        Extract article content using configured selectors.

        Args:
            url: Article URL to scrape

        Returns:
            Dictionary with article data
        """
        article_data = {
            "url": url,
            "title": "",
            "content": "",
            "author": "",
            "date": "",
            "outlet": self.outlet_name,
            "scraped_at": time.time(),
        }

        try:
            if not self.get_page(url):
                return article_data

            # Extract title
            title_selector = self.selectors.get("title")
            if title_selector:
                title_element = self.safe_find_element(By.CSS_SELECTOR, title_selector)
                if title_element:
                    article_data["title"] = title_element.text.strip()

            # Extract content
            content_selector = self.selectors.get("content")
            if content_selector:
                content_elements = self.safe_find_elements(
                    By.CSS_SELECTOR, content_selector
                )
                content_parts = []
                for element in content_elements:
                    if element.text.strip():
                        content_parts.append(element.text.strip())
                article_data["content"] = "\n\n".join(content_parts)

            # Extract author
            author_selector = self.selectors.get("author")
            if author_selector:
                author_element = self.safe_find_element(
                    By.CSS_SELECTOR, author_selector
                )
                if author_element:
                    article_data["author"] = author_element.text.strip()

            # Extract date
            date_selector = self.selectors.get("date")
            if date_selector:
                date_element = self.safe_find_element(By.CSS_SELECTOR, date_selector)
                if date_element:
                    article_data["date"] = date_element.text.strip()

            logger.info(
                f"Successfully scraped article: {article_data['title'][:50]}..."
            )
            return article_data

        except Exception as e:
            logger.error(f"Failed to scrape article content from {url}: {e}")
            return article_data
