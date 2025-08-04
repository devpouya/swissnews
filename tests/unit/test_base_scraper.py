#!/usr/bin/env python3
"""
Unit tests for the base Selenium scraper framework.

Tests the BaseScraper and OutletScraper classes including WebDriver setup,
configuration handling, error handling, and retry logic.

Issue: https://github.com/devpouya/swissnews/issues/3
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import TimeoutException, WebDriverException

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from scraper.base import BaseScraper, OutletScraper, ScrapingError


class _TestableBaseScraper(BaseScraper):
    """Concrete implementation of BaseScraper for testing."""

    def scrape_article_list(self):
        return []

    def scrape_article_content(self, url):
        return {}


class TestBaseScraper:
    """Test cases for the BaseScraper class."""

    @pytest.fixture
    def sample_config(self):
        """Sample outlet configuration for testing."""
        return {
            "name": "test_outlet",
            "url": "https://test-outlet.ch",
            "selectors": {
                "article_links": ".article-link",
                "title": "h1.title",
                "content": ".content p",
                "author": ".author",
                "date": ".date"
            },
            "timeouts": {
                "page_load": 30,
                "element_wait": 10
            },
            "retry": {
                "max_attempts": 3,
                "delay": 1
            },
            "user_agent": "Test User Agent"
        }

    def test_initialization(self, sample_config):
        """Test BaseScraper initialization with configuration."""
        scraper = _TestableBaseScraper(sample_config)

        assert scraper.outlet_name == "test_outlet"
        assert scraper.base_url == "https://test-outlet.ch"
        assert scraper.page_load_timeout == 30
        assert scraper.element_wait_timeout == 10
        assert scraper.max_retry_attempts == 3
        assert scraper.retry_delay == 1
        assert scraper.driver is None
        assert scraper.wait is None

    def test_initialization_with_defaults(self):
        """Test initialization with minimal configuration using defaults."""
        minimal_config = {
            "name": "minimal",
            "url": "https://minimal.ch"
        }

        scraper = _TestableBaseScraper(minimal_config)

        assert scraper.outlet_name == "minimal"
        assert scraper.base_url == "https://minimal.ch"
        assert scraper.page_load_timeout == 30  # Default
        assert scraper.element_wait_timeout == 10  # Default
        assert scraper.max_retry_attempts == 3  # Default
        assert scraper.retry_delay == 2  # Default

    @patch('scraper.base.webdriver.Chrome')
    def test_setup_driver_success(self, mock_chrome, sample_config):
        """Test successful WebDriver setup."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        scraper = _TestableBaseScraper(sample_config)
        driver = scraper.setup_driver()

        assert driver == mock_driver
        assert scraper.driver == mock_driver
        mock_driver.set_page_load_timeout.assert_called_once_with(30)
        mock_chrome.assert_called_once()

    @patch('scraper.base.webdriver.Chrome')
    def test_setup_driver_failure(self, mock_chrome, sample_config):
        """Test WebDriver setup failure."""
        mock_chrome.side_effect = Exception("WebDriver setup failed")

        scraper = _TestableBaseScraper(sample_config)

        with pytest.raises(ScrapingError, match="WebDriver setup failed"):
            scraper.setup_driver()

    def test_retry_on_failure_success_on_first_attempt(self, sample_config):
        """Test retry decorator with successful first attempt."""
        scraper = _TestableBaseScraper(sample_config)

        mock_func = Mock(return_value="success")
        result = scraper.retry_on_failure(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    def test_retry_on_failure_success_after_retries(self, sample_config):
        """Test retry decorator with success after retries."""
        scraper = _TestableBaseScraper(sample_config)

        mock_func = Mock(side_effect=[TimeoutException(), TimeoutException(), "success"])

        with patch('time.sleep'):  # Mock sleep to speed up test
            result = scraper.retry_on_failure(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_on_failure_all_attempts_fail(self, sample_config):
        """Test retry decorator when all attempts fail."""
        scraper = _TestableBaseScraper(sample_config)

        mock_func = Mock(side_effect=TimeoutException("Timeout"))

        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(ScrapingError, match="Operation failed after 3 attempts"):
                scraper.retry_on_failure(mock_func)

        assert mock_func.call_count == 3

    @patch('scraper.base.WebDriverWait')
    def test_safe_find_element_success(self, mock_wait, sample_config):
        """Test successful element finding."""
        mock_driver = Mock()
        mock_element = Mock()
        mock_wait_instance = Mock()
        mock_wait_instance.until.return_value = mock_element
        mock_wait.return_value = mock_wait_instance

        scraper = _TestableBaseScraper(sample_config)
        scraper.driver = mock_driver
        scraper.wait = mock_wait_instance

        from selenium.webdriver.common.by import By
        result = scraper.safe_find_element(By.CSS_SELECTOR, ".test-selector")

        assert result == mock_element

    @patch('scraper.base.WebDriverWait')
    def test_safe_find_element_timeout(self, mock_wait, sample_config):
        """Test element finding with timeout."""
        mock_driver = Mock()
        mock_wait_instance = Mock()
        mock_wait_instance.until.side_effect = TimeoutException()
        mock_wait.return_value = mock_wait_instance

        scraper = _TestableBaseScraper(sample_config)
        scraper.driver = mock_driver
        scraper.wait = mock_wait_instance

        from selenium.webdriver.common.by import By
        result = scraper.safe_find_element(By.CSS_SELECTOR, ".missing-selector")

        assert result is None

    def test_safe_find_elements_success(self, sample_config):
        """Test successful multiple elements finding."""
        mock_driver = Mock()
        mock_elements = [Mock(), Mock()]
        mock_driver.find_elements.return_value = mock_elements

        scraper = _TestableBaseScraper(sample_config)
        scraper.driver = mock_driver

        from selenium.webdriver.common.by import By
        result = scraper.safe_find_elements(By.CSS_SELECTOR, ".test-selector")

        assert result == mock_elements

    def test_safe_find_elements_exception(self, sample_config):
        """Test multiple elements finding with exception."""
        mock_driver = Mock()
        mock_driver.find_elements.side_effect = Exception("Find error")

        scraper = _TestableBaseScraper(sample_config)
        scraper.driver = mock_driver

        from selenium.webdriver.common.by import By
        result = scraper.safe_find_elements(By.CSS_SELECTOR, ".error-selector")

        assert result == []

    @patch('scraper.base.webdriver.Chrome')
    def test_get_page_success(self, mock_chrome, sample_config):
        """Test successful page navigation."""
        mock_driver = Mock()
        mock_driver.execute_script.return_value = "complete"
        mock_chrome.return_value = mock_driver

        scraper = _TestableBaseScraper(sample_config)
        scraper.setup_driver()

        with patch('scraper.base.WebDriverWait') as mock_wait:
            mock_wait_instance = Mock()
            mock_wait.return_value = mock_wait_instance

            result = scraper.get_page("https://test.com")

        assert result is True
        mock_driver.get.assert_called_once_with("https://test.com")

    def test_get_page_failure(self, sample_config):
        """Test page navigation failure."""
        mock_driver = Mock()
        mock_driver.get.side_effect = Exception("Navigation failed")

        scraper = _TestableBaseScraper(sample_config)
        scraper.driver = mock_driver

        result = scraper.get_page("https://test.com")

        assert result is False

    def test_cleanup(self, sample_config):
        """Test WebDriver cleanup."""
        mock_driver = Mock()

        scraper = _TestableBaseScraper(sample_config)
        scraper.driver = mock_driver

        scraper.cleanup()

        mock_driver.quit.assert_called_once()
        assert scraper.driver is None
        assert scraper.wait is None

    def test_cleanup_with_exception(self, sample_config):
        """Test WebDriver cleanup with exception."""
        mock_driver = Mock()
        mock_driver.quit.side_effect = Exception("Cleanup failed")

        scraper = _TestableBaseScraper(sample_config)
        scraper.driver = mock_driver

        # Should not raise exception
        scraper.cleanup()

        assert scraper.driver is None
        assert scraper.wait is None

    def test_context_manager(self, sample_config):
        """Test BaseScraper as context manager."""
        with patch.object(_TestableBaseScraper, 'setup_driver') as mock_setup:
            with patch.object(_TestableBaseScraper, 'cleanup') as mock_cleanup:

                with _TestableBaseScraper(sample_config) as scraper:
                    assert scraper is not None

                mock_setup.assert_called_once()
                mock_cleanup.assert_called_once()


class TestOutletScraper:
    """Test cases for the OutletScraper class."""

    @pytest.fixture
    def sample_config(self):
        """Sample outlet configuration for testing."""
        return {
            "name": "test_outlet",
            "url": "https://test-outlet.ch",
            "selectors": {
                "article_links": "a.article-link",
                "title": "h1.title",
                "content": ".content p",
                "author": ".author",
                "date": ".date"
            },
            "timeouts": {
                "page_load": 30,
                "element_wait": 10
            },
            "retry": {
                "max_attempts": 3,
                "delay": 1
            }
        }

    @patch('scraper.base.OutletScraper.get_page')
    @patch('scraper.base.OutletScraper.safe_find_elements')
    def test_scrape_article_list_success(self, mock_find_elements, mock_get_page, sample_config):
        """Test successful article list scraping."""
        # Mock successful page load
        mock_get_page.return_value = True

        # Mock article link elements
        mock_element1 = Mock()
        mock_element1.get_attribute.return_value = "/article/test-1"
        mock_element2 = Mock()
        mock_element2.get_attribute.return_value = "https://test-outlet.ch/article/test-2"

        mock_find_elements.return_value = [mock_element1, mock_element2]

        scraper = OutletScraper(sample_config)
        urls = scraper.scrape_article_list()

        expected_urls = [
            "https://test-outlet.ch/article/test-1",
            "https://test-outlet.ch/article/test-2"
        ]

        assert urls == expected_urls
        mock_get_page.assert_called_once_with("https://test-outlet.ch")

    @patch('scraper.base.OutletScraper.get_page')
    def test_scrape_article_list_page_load_failure(self, mock_get_page, sample_config):
        """Test article list scraping with page load failure."""
        mock_get_page.return_value = False

        scraper = OutletScraper(sample_config)
        urls = scraper.scrape_article_list()

        assert urls == []

    def test_scrape_article_list_missing_selector(self, sample_config):
        """Test article list scraping with missing selector configuration."""
        config_without_selector = sample_config.copy()
        del config_without_selector["selectors"]["article_links"]

        scraper = OutletScraper(config_without_selector)
        urls = scraper.scrape_article_list()

        assert urls == []

    @patch('scraper.base.OutletScraper.get_page')
    @patch('scraper.base.OutletScraper.safe_find_element')
    @patch('scraper.base.OutletScraper.safe_find_elements')
    def test_scrape_article_content_success(self, mock_find_elements, mock_find_element,
                                          mock_get_page, sample_config):
        """Test successful article content scraping."""
        # Mock successful page load
        mock_get_page.return_value = True

        # Mock title element
        mock_title = Mock()
        mock_title.text = "Test Article Title"

        # Mock content elements
        mock_content1 = Mock()
        mock_content1.text = "First paragraph"
        mock_content2 = Mock()
        mock_content2.text = "Second paragraph"

        # Mock author element
        mock_author = Mock()
        mock_author.text = "Test Author"

        # Mock date element
        mock_date = Mock()
        mock_date.text = "2024-01-01"

        # Configure mock returns based on selector
        def mock_find_element_side_effect(by, selector):
            if "title" in selector:
                return mock_title
            elif "author" in selector:
                return mock_author
            elif "date" in selector:
                return mock_date
            return None

        def mock_find_elements_side_effect(by, selector):
            if "content" in selector:
                return [mock_content1, mock_content2]
            return []

        mock_find_element.side_effect = mock_find_element_side_effect
        mock_find_elements.side_effect = mock_find_elements_side_effect

        scraper = OutletScraper(sample_config)
        article_data = scraper.scrape_article_content("https://test-outlet.ch/article/test")

        assert article_data["url"] == "https://test-outlet.ch/article/test"
        assert article_data["title"] == "Test Article Title"
        assert article_data["content"] == "First paragraph\n\nSecond paragraph"
        assert article_data["author"] == "Test Author"
        assert article_data["date"] == "2024-01-01"
        assert article_data["outlet"] == "test_outlet"
        assert "scraped_at" in article_data

    @patch('scraper.base.OutletScraper.get_page')
    def test_scrape_article_content_page_load_failure(self, mock_get_page, sample_config):
        """Test article content scraping with page load failure."""
        mock_get_page.return_value = False

        scraper = OutletScraper(sample_config)
        article_data = scraper.scrape_article_content("https://test-outlet.ch/article/test")

        assert article_data["url"] == "https://test-outlet.ch/article/test"
        assert article_data["title"] == ""
        assert article_data["content"] == ""
        assert article_data["outlet"] == "test_outlet"

    @patch('scraper.base.OutletScraper.get_page')
    def test_scrape_article_content_exception(self, mock_get_page, sample_config):
        """Test article content scraping with exception."""
        mock_get_page.side_effect = Exception("Scraping error")

        scraper = OutletScraper(sample_config)
        article_data = scraper.scrape_article_content("https://test-outlet.ch/article/test")

        assert article_data["url"] == "https://test-outlet.ch/article/test"
        assert article_data["title"] == ""
        assert article_data["content"] == ""
        assert article_data["outlet"] == "test_outlet"


if __name__ == "__main__":
    pytest.main([__file__])
