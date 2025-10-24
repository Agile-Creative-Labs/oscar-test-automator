"""
Configuration Loader for OSCAR Test Automator

Reads OSCAR's default_config.json and extracts browser categories
and website lists for automated testing.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and parses OSCAR configuration files"""
    
    def __init__(self, config_path: str = 'config/default_config.json'):
        """
        Initialize config loader
        
        Args:
            config_path: Path to OSCAR config JSON file
        """
        self.config_path = Path(config_path)
        self.config = None
        self.browser_categories = {}
        
        self._load_config()
    
    def _load_config(self):
        """Load and parse the configuration file"""
        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            # Extract browser categories
            self.browser_categories = self.config.get('browser_categories', {})
            
            if not self.browser_categories:
                logger.warning("No browser_categories found in config")
            else:
                logger.info(f"Loaded {len(self.browser_categories)} browser categories")
                for category, sites in self.browser_categories.items():
                    logger.debug(f"  {category}: {len(sites)} sites")
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    def get_all_sites(self) -> List[Tuple[str, str]]:
        """
        Get all sites from all browser categories
        
        Returns:
            List of (url, category) tuples
        """
        all_sites = []
        
        for category, urls in self.browser_categories.items():
            # Skip internal/system categories
            if category in ['Browser Internal', 'System/Security']:
                logger.debug(f"Skipping system category: {category}")
                continue
            
            for url in urls:
                # Skip internal browser pages
                if any(internal in url.lower() for internal in [
                    'browser_internal', 'browser_new_tab', 'chrome_internal',
                    'edge_internal', 'firefox_internal', 'chrome_extension',
                    'firefox_extension', 'loginwindow', 'screensaver',
                    'lock_screen', 'system_security'
                ]):
                    continue
                
                all_sites.append((url, category))
        
        logger.info(f"Total testable sites: {len(all_sites)}")
        return all_sites
    
    def get_sites_by_category(self, category_name: str) -> List[str]:
        """
        Get all sites for a specific category
        
        Args:
            category_name: Name of the category
            
        Returns:
            List of URLs in that category
        """
        if category_name not in self.browser_categories:
            logger.warning(f"Category '{category_name}' not found in config")
            return []
        
        urls = self.browser_categories[category_name]
        
        # Filter out internal/system pages
        filtered_urls = [
            url for url in urls
            if not any(internal in url.lower() for internal in [
                'browser_internal', 'browser_new_tab', 'chrome_internal',
                'edge_internal', 'firefox_internal', 'chrome_extension',
                'firefox_extension'
            ])
        ]
        
        logger.info(f"Category '{category_name}': {len(filtered_urls)} testable sites")
        return filtered_urls
    
    def get_categories(self) -> List[str]:
        """
        Get list of all category names
        
        Returns:
            List of category names
        """
        # Filter out system categories
        categories = [
            cat for cat in self.browser_categories.keys()
            if cat not in ['Browser Internal', 'System/Security']
        ]
        return categories
    
    def get_category_count(self) -> Dict[str, int]:
        """
        Get count of sites per category
        
        Returns:
            Dictionary mapping category names to site counts
        """
        counts = {}
        for category, urls in self.browser_categories.items():
            if category in ['Browser Internal', 'System/Security']:
                continue
            
            # Count only real URLs
            real_urls = [
                url for url in urls
                if not any(internal in url.lower() for internal in [
                    'browser_internal', 'browser_new_tab', 'chrome_internal',
                    'edge_internal', 'firefox_internal', 'chrome_extension',
                    'firefox_extension'
                ])
            ]
            counts[category] = len(real_urls)
        
        return counts
