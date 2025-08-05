#!/usr/bin/env python3
"""
Configuration Loader for Selenium Scraper Framework

Handles loading, validation, and management of outlet configurations from YAML files.
Provides configuration validation and merging with defaults.

Issue: https://github.com/devpouya/swissnews/issues/3
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml  # type: ignore
from loguru import logger


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""

    pass


class ConfigLoader:
    """
    Loads and manages outlet configurations for the scraper framework.

    Handles YAML configuration files, validation, and default value merging.
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to the configuration file. If None, uses default path.
        """
        if config_path is None:
            # Default to config/outlets.yaml in the scraper directory
            current_dir = Path(__file__).parent
            self.config_path = current_dir / "config" / "outlets.yaml"
        else:
            self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        self.outlets: Dict[str, Dict[str, Any]] = {}
        self.defaults: Dict[str, Any] = {}
        self.validation_rules: Dict[str, Any] = {}

        logger.info(f"ConfigLoader initialized with path: {self.config_path}")

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Complete configuration dictionary

        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        try:
            if not self.config_path.exists():
                raise ConfigurationError(
                    f"Configuration file not found: {self.config_path}"
                )

            with open(self.config_path, "r", encoding="utf-8") as file:
                self.config_data = yaml.safe_load(file)

            if not self.config_data:
                raise ConfigurationError("Configuration file is empty or invalid")

            # Extract sections
            self.outlets = self.config_data.get("outlets", {})
            self.defaults = self.config_data.get("defaults", {})
            self.validation_rules = self.config_data.get("validation", {})

            logger.info(f"Loaded configuration for {len(self.outlets)} outlets")
            return self.config_data

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def get_outlet_config(self, outlet_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific outlet with defaults merged.

        Args:
            outlet_name: Name of the outlet

        Returns:
            Complete outlet configuration with defaults applied

        Raises:
            ConfigurationError: If outlet not found or configuration invalid
        """
        if not self.config_data:
            self.load_config()

        if outlet_name not in self.outlets:
            available_outlets = list(self.outlets.keys())
            raise ConfigurationError(
                f"Outlet '{outlet_name}' not found. Available outlets: {available_outlets}"
            )

        outlet_config = self.outlets[outlet_name].copy()

        # Merge with defaults
        merged_config = self._merge_with_defaults(outlet_config)

        # Validate configuration
        self._validate_outlet_config(outlet_name, merged_config)

        logger.debug(f"Retrieved configuration for outlet: {outlet_name}")
        return merged_config

    def get_all_outlets(self) -> List[str]:
        """
        Get list of all configured outlet names.

        Returns:
            List of outlet names
        """
        if not self.config_data:
            self.load_config()

        return list(self.outlets.keys())

    def get_outlets_by_language(self, language: str) -> List[str]:
        """
        Get list of outlets filtered by language.

        Args:
            language: Language code (de, fr, it, rm)

        Returns:
            List of outlet names for the specified language
        """
        if not self.config_data:
            self.load_config()

        matching_outlets = []
        for outlet_name, config in self.outlets.items():
            if config.get("language") == language:
                matching_outlets.append(outlet_name)

        return matching_outlets

    def _merge_with_defaults(self, outlet_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge outlet configuration with default values.

        Args:
            outlet_config: Outlet-specific configuration

        Returns:
            Configuration with defaults applied
        """
        merged = outlet_config.copy()

        # Merge timeouts
        if "timeouts" not in merged:
            merged["timeouts"] = {}
        if "timeouts" in self.defaults:
            for key, value in self.defaults["timeouts"].items():
                if key not in merged["timeouts"]:
                    merged["timeouts"][key] = value

        # Merge retry settings
        if "retry" not in merged:
            merged["retry"] = {}
        if "retry" in self.defaults:
            for key, value in self.defaults["retry"].items():
                if key not in merged["retry"]:
                    merged["retry"][key] = value

        # Merge user agent
        if "user_agent" not in merged and "user_agent" in self.defaults:
            merged["user_agent"] = self.defaults["user_agent"]

        return merged

    def _validate_outlet_config(self, outlet_name: str, config: Dict[str, Any]) -> None:
        """
        Validate outlet configuration against defined rules.

        Args:
            outlet_name: Name of the outlet being validated
            config: Configuration to validate

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Check required fields
        required_fields = self.validation_rules.get("required_fields", [])
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(
                    f"Outlet '{outlet_name}' missing required field: {field}"
                )

        # Check required selectors
        if "selectors" in config:
            required_selectors = self.validation_rules.get("required_selectors", [])
            for selector in required_selectors:
                if selector not in config["selectors"]:
                    raise ConfigurationError(
                        f"Outlet '{outlet_name}' missing required selector: {selector}"
                    )

        # Validate language
        supported_languages = self.validation_rules.get("supported_languages", [])
        if supported_languages and config.get("language") not in supported_languages:
            raise ConfigurationError(
                f"Outlet '{outlet_name}' has unsupported language: {config.get('language')}. "
                f"Supported: {supported_languages}"
            )

        # Validate timeout limits
        if "timeouts" in config:
            self._validate_timeout_limits(outlet_name, config["timeouts"])

        # Validate retry limits
        if "retry" in config:
            self._validate_retry_limits(outlet_name, config["retry"])

    def _validate_timeout_limits(
        self, outlet_name: str, timeouts: Dict[str, Any]
    ) -> None:
        """
        Validate timeout configuration against limits.

        Args:
            outlet_name: Name of the outlet
            timeouts: Timeout configuration

        Raises:
            ConfigurationError: If timeouts are outside valid ranges
        """
        timeout_limits = self.validation_rules.get("timeout_limits", {})

        for timeout_type, value in timeouts.items():
            if timeout_type in timeout_limits:
                limits = timeout_limits[timeout_type]
                min_val = limits.get("min", 0)
                max_val = limits.get("max", float("inf"))

                if not (min_val <= value <= max_val):
                    raise ConfigurationError(
                        f"Outlet '{outlet_name}' {timeout_type} timeout ({value}) "
                        f"outside valid range: {min_val}-{max_val}"
                    )

    def _validate_retry_limits(self, outlet_name: str, retry: Dict[str, Any]) -> None:
        """
        Validate retry configuration against limits.

        Args:
            outlet_name: Name of the outlet
            retry: Retry configuration

        Raises:
            ConfigurationError: If retry settings are outside valid ranges
        """
        retry_limits = self.validation_rules.get("retry_limits", {})

        for retry_type, value in retry.items():
            if retry_type in retry_limits:
                limits = retry_limits[retry_type]
                min_val = limits.get("min", 0)
                max_val = limits.get("max", float("inf"))

                if not (min_val <= value <= max_val):
                    raise ConfigurationError(
                        f"Outlet '{outlet_name}' {retry_type} ({value}) "
                        f"outside valid range: {min_val}-{max_val}"
                    )

    def reload_config(self) -> Dict[str, Any]:
        """
        Reload configuration from file.

        Returns:
            Reloaded configuration data
        """
        logger.info("Reloading configuration from file")
        return self.load_config()

    def validate_all_outlets(self) -> Dict[str, bool]:
        """
        Validate all outlet configurations.

        Returns:
            Dictionary mapping outlet names to validation results (True/False)
        """
        if not self.config_data:
            self.load_config()

        results = {}
        for outlet_name in self.outlets:
            try:
                self.get_outlet_config(outlet_name)
                results[outlet_name] = True
                logger.debug(f"Outlet '{outlet_name}' configuration is valid")
            except ConfigurationError as e:
                results[outlet_name] = False
                logger.error(f"Outlet '{outlet_name}' configuration is invalid: {e}")

        valid_count = sum(results.values())
        total_count = len(results)
        logger.info(
            f"Configuration validation: {valid_count}/{total_count} outlets valid"
        )

        return results


# Global configuration loader instance
config_loader = ConfigLoader()


def get_outlet_config(outlet_name: str) -> Dict[str, Any]:
    """
    Convenience function to get outlet configuration.

    Args:
        outlet_name: Name of the outlet

    Returns:
        Outlet configuration dictionary
    """
    return config_loader.get_outlet_config(outlet_name)


def get_all_outlets() -> List[str]:
    """
    Convenience function to get all outlet names.

    Returns:
        List of outlet names
    """
    return config_loader.get_all_outlets()


def get_outlets_by_language(language: str) -> List[str]:
    """
    Convenience function to get outlets by language.

    Args:
        language: Language code

    Returns:
        List of outlet names for the language
    """
    return config_loader.get_outlets_by_language(language)
