#!/usr/bin/env python3
"""
Unit tests for the configuration loader.

Tests configuration loading, validation, and management for the scraper framework.

Issue: https://github.com/devpouya/swissnews/issues/3
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../backend'))

from scraper.config_loader import ConfigLoader, ConfigurationError


class TestConfigLoader:
    """Test cases for the ConfigLoader class."""

    @pytest.fixture
    def sample_yaml_config(self):
        """Sample YAML configuration for testing."""
        return """
outlets:
  test_outlet:
    name: "Test Outlet"
    url: "https://test.ch"
    language: "de"
    selectors:
      article_links: ".article-link"
      title: "h1.title"
      content: ".content p"
    timeouts:
      page_load: 25
      element_wait: 8
    retry:
      max_attempts: 2
      delay: 1.5

  minimal_outlet:
    name: "Minimal Outlet"
    url: "https://minimal.ch"
    language: "fr"
    selectors:
      article_links: ".link"
      title: "h1"
      content: "p"

defaults:
  timeouts:
    page_load: 30
    element_wait: 10
  retry:
    max_attempts: 3
    delay: 2
  user_agent: "Test Agent"

validation:
  required_fields:
    - name
    - url
    - language
    - selectors
  required_selectors:
    - article_links
    - title
    - content
  supported_languages:
    - de
    - fr
    - it
  timeout_limits:
    page_load:
      min: 10
      max: 60
    element_wait:
      min: 5
      max: 30
  retry_limits:
    max_attempts:
      min: 1
      max: 10
    delay:
      min: 0.5
      max: 10
"""

    @pytest.fixture
    def invalid_yaml_config(self):
        """Invalid YAML configuration for testing error handling."""
        return """
outlets:
  invalid_outlet:
    name: "Invalid Outlet"
    # Missing required fields: url, language, selectors

validation:
  required_fields:
    - name
    - url
    - language
    - selectors
"""

    def test_initialization_with_custom_path(self):
        """Test ConfigLoader initialization with custom path."""
        custom_path = "/custom/path/config.yaml"
        loader = ConfigLoader(custom_path)

        assert str(loader.config_path) == custom_path

    def test_initialization_with_default_path(self):
        """Test ConfigLoader initialization with default path."""
        loader = ConfigLoader()

        expected_path = Path(__file__).parent.parent.parent / "backend" / "scraper" / "config" / "outlets.yaml"
        # Just check the filename since absolute paths may vary
        assert loader.config_path.name == "outlets.yaml"

    def test_load_config_success(self, sample_yaml_config):
        """Test successful configuration loading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            config_data = loader.load_config()

            assert "outlets" in config_data
            assert "defaults" in config_data
            assert "validation" in config_data
            assert len(loader.outlets) == 2
            assert "test_outlet" in loader.outlets
            assert "minimal_outlet" in loader.outlets
        finally:
            os.unlink(temp_path)

    def test_load_config_file_not_found(self):
        """Test configuration loading with non-existent file."""
        loader = ConfigLoader("/non/existent/path.yaml")

        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            loader.load_config()

    def test_load_config_invalid_yaml(self):
        """Test configuration loading with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            with pytest.raises(ConfigurationError, match="Failed to parse YAML"):
                loader.load_config()
        finally:
            os.unlink(temp_path)

    def test_load_config_empty_file(self):
        """Test configuration loading with empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            with pytest.raises(ConfigurationError, match="Configuration file is empty"):
                loader.load_config()
        finally:
            os.unlink(temp_path)

    def test_get_outlet_config_success(self, sample_yaml_config):
        """Test successful outlet configuration retrieval."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            config = loader.get_outlet_config("test_outlet")

            assert config["name"] == "Test Outlet"
            assert config["url"] == "https://test.ch"
            assert config["language"] == "de"
            assert config["timeouts"]["page_load"] == 25
            assert config["timeouts"]["element_wait"] == 8
            assert config["retry"]["max_attempts"] == 2
            assert config["retry"]["delay"] == 1.5
        finally:
            os.unlink(temp_path)

    def test_get_outlet_config_with_defaults_merged(self, sample_yaml_config):
        """Test outlet configuration retrieval with defaults merged."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            config = loader.get_outlet_config("minimal_outlet")

            # Should have outlet-specific values
            assert config["name"] == "Minimal Outlet"
            assert config["url"] == "https://minimal.ch"
            assert config["language"] == "fr"

            # Should have defaults merged
            assert config["timeouts"]["page_load"] == 30  # From defaults
            assert config["timeouts"]["element_wait"] == 10  # From defaults
            assert config["retry"]["max_attempts"] == 3  # From defaults
            assert config["retry"]["delay"] == 2  # From defaults
            assert config["user_agent"] == "Test Agent"  # From defaults
        finally:
            os.unlink(temp_path)

    def test_get_outlet_config_not_found(self, sample_yaml_config):
        """Test outlet configuration retrieval for non-existent outlet."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)

            with pytest.raises(ConfigurationError, match="Outlet 'non_existent' not found"):
                loader.get_outlet_config("non_existent")
        finally:
            os.unlink(temp_path)

    def test_get_all_outlets(self, sample_yaml_config):
        """Test getting all outlet names."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            outlets = loader.get_all_outlets()

            assert len(outlets) == 2
            assert "test_outlet" in outlets
            assert "minimal_outlet" in outlets
        finally:
            os.unlink(temp_path)

    def test_get_outlets_by_language(self, sample_yaml_config):
        """Test getting outlets filtered by language."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)

            german_outlets = loader.get_outlets_by_language("de")
            assert german_outlets == ["test_outlet"]

            french_outlets = loader.get_outlets_by_language("fr")
            assert french_outlets == ["minimal_outlet"]

            italian_outlets = loader.get_outlets_by_language("it")
            assert italian_outlets == []
        finally:
            os.unlink(temp_path)

    def test_validate_outlet_config_missing_required_field(self, invalid_yaml_config):
        """Test configuration validation with missing required fields."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)

            with pytest.raises(ConfigurationError, match="missing required field"):
                loader.get_outlet_config("invalid_outlet")
        finally:
            os.unlink(temp_path)

    def test_validate_outlet_config_unsupported_language(self):
        """Test configuration validation with unsupported language."""
        config_with_invalid_language = """
outlets:
  invalid_lang_outlet:
    name: "Invalid Language Outlet"
    url: "https://test.ch"
    language: "xx"  # Unsupported language
    selectors:
      article_links: ".link"
      title: "h1"
      content: "p"

validation:
  required_fields:
    - name
    - url
    - language
    - selectors
  supported_languages:
    - de
    - fr
    - it
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_with_invalid_language)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)

            with pytest.raises(ConfigurationError, match="unsupported language"):
                loader.get_outlet_config("invalid_lang_outlet")
        finally:
            os.unlink(temp_path)

    def test_validate_timeout_limits(self):
        """Test timeout validation against limits."""
        config_with_invalid_timeout = """
outlets:
  invalid_timeout_outlet:
    name: "Invalid Timeout Outlet"
    url: "https://test.ch"
    language: "de"
    selectors:
      article_links: ".link"
      title: "h1"
      content: "p"
    timeouts:
      page_load: 100  # Exceeds max limit of 60

validation:
  required_fields:
    - name
    - url
    - language
    - selectors
  timeout_limits:
    page_load:
      min: 10
      max: 60
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_with_invalid_timeout)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)

            with pytest.raises(ConfigurationError, match="outside valid range"):
                loader.get_outlet_config("invalid_timeout_outlet")
        finally:
            os.unlink(temp_path)

    def test_validate_retry_limits(self):
        """Test retry validation against limits."""
        config_with_invalid_retry = """
outlets:
  invalid_retry_outlet:
    name: "Invalid Retry Outlet"
    url: "https://test.ch"
    language: "de"
    selectors:
      article_links: ".link"
      title: "h1"
      content: "p"
    retry:
      max_attempts: 20  # Exceeds max limit of 10

validation:
  required_fields:
    - name
    - url
    - language
    - selectors
  retry_limits:
    max_attempts:
      min: 1
      max: 10
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_with_invalid_retry)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)

            with pytest.raises(ConfigurationError, match="outside valid range"):
                loader.get_outlet_config("invalid_retry_outlet")
        finally:
            os.unlink(temp_path)

    def test_validate_all_outlets_success(self, sample_yaml_config):
        """Test validation of all outlets with success."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            results = loader.validate_all_outlets()

            assert len(results) == 2
            assert results["test_outlet"] is True
            assert results["minimal_outlet"] is True
        finally:
            os.unlink(temp_path)

    def test_validate_all_outlets_with_failures(self, invalid_yaml_config):
        """Test validation of all outlets with some failures."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            results = loader.validate_all_outlets()

            assert len(results) == 1
            assert results["invalid_outlet"] is False
        finally:
            os.unlink(temp_path)

    def test_reload_config(self, sample_yaml_config):
        """Test configuration reloading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)

            # Load initial config
            initial_config = loader.load_config()
            assert len(loader.outlets) == 2

            # Reload config
            reloaded_config = loader.reload_config()
            assert reloaded_config == initial_config
        finally:
            os.unlink(temp_path)


class TestConfigLoaderConvenienceFunctions:
    """Test cases for convenience functions."""

    @patch('scraper.config_loader.config_loader.get_outlet_config')
    def test_get_outlet_config_convenience(self, mock_get_outlet_config):
        """Test get_outlet_config convenience function."""
        from scraper.config_loader import get_outlet_config

        mock_config = {"name": "Test", "url": "https://test.ch"}
        mock_get_outlet_config.return_value = mock_config

        result = get_outlet_config("test_outlet")

        assert result == mock_config
        mock_get_outlet_config.assert_called_once_with("test_outlet")

    @patch('scraper.config_loader.config_loader.get_all_outlets')
    def test_get_all_outlets_convenience(self, mock_get_all_outlets):
        """Test get_all_outlets convenience function."""
        from scraper.config_loader import get_all_outlets

        mock_outlets = ["outlet1", "outlet2"]
        mock_get_all_outlets.return_value = mock_outlets

        result = get_all_outlets()

        assert result == mock_outlets
        mock_get_all_outlets.assert_called_once()

    @patch('scraper.config_loader.config_loader.get_outlets_by_language')
    def test_get_outlets_by_language_convenience(self, mock_get_outlets_by_language):
        """Test get_outlets_by_language convenience function."""
        from scraper.config_loader import get_outlets_by_language

        mock_outlets = ["german_outlet"]
        mock_get_outlets_by_language.return_value = mock_outlets

        result = get_outlets_by_language("de")

        assert result == mock_outlets
        mock_get_outlets_by_language.assert_called_once_with("de")


if __name__ == "__main__":
    pytest.main([__file__])
