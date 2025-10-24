"""
Configuration Loader for OSCAR Test Automator

Handles loading and parsing of configuration files containing website
categories and application settings.

Author: Agile Creative Labs Inc (c) 2025
Part of OSCAR v1.0
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class ConfigLoader:
    """Loads and manages configuration from JSON files"""
    
    def __init__(self, config_path: str = "config/default_config.json"):
        """
        Initialize the config loader
        
        Args:
            config_path: Path to the configuration JSON file
        """
        self.config_path = Path(config_path)
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            self.logger.error(f"Config file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            self.logger.info(f"Loaded configuration from {self.config_path}")
            
            # Validate required sections
            if 'browser_categories' not in self.config:
                self.logger.warning("No 'browser_categories' found in config")
                self.config['browser_categories'] = {}
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            raise
    
    def get_all_sites(self) -> List[Tuple[str, str]]:
        """
        Get all websites from all categories
        
        Returns:
            List of (url, category) tuples
        """
        sites = []
        browser_categories = self.config.get('browser_categories', {})
        
        for category, domains in browser_categories.items():
            # Skip system/internal categories
            if category in ['Browser Internal', 'System/Security']:
                continue
            
            for domain in domains:
                # Ensure proper URL format
                if not domain.startswith(('http://', 'https://')):
                    url = f"https://{domain}"
                else:
                    url = domain
                
                sites.append((url, category))
        
        self.logger.info(f"Extracted {len(sites)} sites from configuration")
        return sites
    
    def get_sites_by_category(self, category: str) -> List[Tuple[str, str]]:
        """
        Get websites from a specific category
        
        Args:
            category: Category name (e.g., "Development", "Social Media")
        
        Returns:
            List of (url, category) tuples
        """
        sites = []
        browser_categories = self.config.get('browser_categories', {})
        
        if category not in browser_categories:
            self.logger.warning(f"Category '{category}' not found in config")
            return sites
        
        domains = browser_categories[category]
        for domain in domains:
            if not domain.startswith(('http://', 'https://')):
                url = f"https://{domain}"
            else:
                url = domain
            
            sites.append((url, category))
        
        self.logger.info(f"Extracted {len(sites)} sites from category '{category}'")
        return sites
    
    def get_categories(self) -> List[str]:
        """
        Get list of all available categories
        
        Returns:
            List of category names
        """
        browser_categories = self.config.get('browser_categories', {})
        categories = [
            cat for cat in browser_categories.keys()
            if cat not in ['Browser Internal', 'System/Security']
        ]
        return categories
    
    def get_category_count(self, category: str) -> int:
        """
        Get number of sites in a category
        
        Args:
            category: Category name
        
        Returns:
            Number of sites in the category
        """
        browser_categories = self.config.get('browser_categories', {})
        return len(browser_categories.get(category, []))
    
    def get_config_value(self, key: str, default=None):
        """
        Get a configuration value by key
        
        Args:
            key: Configuration key
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)c
