"""
Unit tests for OSCAR Test Automator
Tests for test_automator.py, config_loader.py, and browser_controller.py

# Install pytest (recommended)
pip install pytest pytest-cov

# Run all tests with verbose output
python -m pytest test_automator_unittest.py -v

# Run with coverage report
python -m pytest test_automator_unittest.py --cov=. --cov-report=html

# Or use unittest
python -m unittest test_automator_unittest.py -v

# Run specific test class
python -m pytest test_automator_unittest.py::TestConfigLoader -v

# Run specific test
python -m pytest test_automator_unittest.py::TestBrowserController::test_navigate_retry_logic -v

Run with: 
    python -m pytest test_automator_unittest.py -v
    or
    python -m unittest test_automator_unittest.py -v
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import json
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import time


class TestConfigLoader(unittest.TestCase):
    """Test cases for config_loader.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            "browser_categories": {
                "Social Media": [
                    "twitter.com",
                    "facebook.com",
                    "linkedin.com"
                ],
                "Development": [
                    "github.com",
                    "stackoverflow.com",
                    "python.org"
                ],
                "News/Information": [
                    "bbc.com",
                    "cnn.com"
                ],
                "Browser Internal": [
                    "chrome_internal",
                    "browser_new_tab"
                ],
                "System/Security": [
                    "loginwindow",
                    "screensaver"
                ]
            }
        }
        
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.json')
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_init_loads_config(self):
        """Test that initialization loads the config file"""
        from config_loader import ConfigLoader
        
        loader = ConfigLoader(self.config_path)
        self.assertIsNotNone(loader.config)
        self.assertIsNotNone(loader.browser_categories)
    
    def test_load_valid_config(self):
        """Test loading a valid configuration file"""
        from config_loader import ConfigLoader
        
        loader = ConfigLoader(self.config_path)
        self.assertEqual(len(loader.browser_categories), 5)
        self.assertIn('Social Media', loader.browser_categories)
        self.assertIn('Development', loader.browser_categories)
    
    def test_load_nonexistent_config(self):
        """Test loading a non-existent config file"""
        from config_loader import ConfigLoader
        
        fake_path = os.path.join(self.test_dir, 'nonexistent.json')
        
        with self.assertRaises(FileNotFoundError):
            ConfigLoader(fake_path)
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON"""
        from config_loader import ConfigLoader
        
        bad_json_path = os.path.join(self.test_dir, 'bad.json')
        with open(bad_json_path, 'w') as f:
            f.write("{invalid json content")
        
        with self.assertRaises(json.JSONDecodeError):
            ConfigLoader(bad_json_path)
    
    def test_get_all_sites(self):
        """Test getting all sites from all categories"""
        from config_loader import ConfigLoader
        
        loader = ConfigLoader(self.config_path)
        all_sites = loader.get_all_sites()
        
        # Should return list of tuples (url, category)
        self.assertIsInstance(all_sites, list)
        self.assertTrue(all(isinstance(site, tuple) for site in all_sites))
        self.assertTrue(all(len(site) == 2 for site in all_sites))
        
        # Should have 8 sites (excludes Browser Internal and System/Security)
        self.assertEqual(len(all_sites), 8)
        
        # Verify some expected sites
        urls = [site[0] for site in all_sites]
        self.assertIn('twitter.com', urls)
        self.assertIn('github.com', urls)
        self.assertNotIn('chrome_internal', urls)
        self.assertNotIn('loginwindow', urls)
    
    def test_get_sites_by_category(self):
        """Test getting sites for a specific category"""
        from config_loader import ConfigLoader
        
        loader = ConfigLoader(self.config_path)
        
        # Test valid category
        dev_sites = loader.get_sites_by_category('Development')
        self.assertEqual(len(dev_sites), 3)
        self.assertIn('github.com', dev_sites)
        self.assertIn('stackoverflow.com', dev_sites)
        
        # Test non-existent category
        empty_sites = loader.get_sites_by_category('NonExistent')
        self.assertEqual(len(empty_sites), 0)
    
    def test_get_categories(self):
        """Test getting list of all category names"""
        from config_loader import ConfigLoader
        
        loader = ConfigLoader(self.config_path)
        categories = loader.get_categories()
        
        self.assertIsInstance(categories, list)
        self.assertIn('Social Media', categories)
        self.assertIn('Development', categories)
        
        # Should not include system categories
        self.assertNotIn('Browser Internal', categories)
        self.assertNotIn('System/Security', categories)
    
    def test_get_category_count(self):
        """Test getting count of sites per category"""
        from config_loader import ConfigLoader
        
        loader = ConfigLoader(self.config_path)
        counts = loader.get_category_count()
        
        self.assertIsInstance(counts, dict)
        self.assertEqual(counts['Social Media'], 3)
        self.assertEqual(counts['Development'], 3)
        self.assertEqual(counts['News/Information'], 2)
        
        # Should not include system categories
        self.assertNotIn('Browser Internal', counts)
        self.assertNotIn('System/Security', counts)
    
    def test_filters_internal_urls(self):
        """Test that internal browser URLs are filtered out"""
        from config_loader import ConfigLoader
        
        loader = ConfigLoader(self.config_path)
        all_sites = loader.get_all_sites()
        
        urls = [site[0] for site in all_sites]
        
        # None of these should be in the results
        internal_keywords = [
            'browser_internal', 'browser_new_tab', 'chrome_internal',
            'edge_internal', 'firefox_internal', 'chrome_extension',
            'firefox_extension', 'loginwindow', 'screensaver'
        ]
        
        for url in urls:
            for keyword in internal_keywords:
                self.assertNotIn(keyword, url.lower())


class TestBrowserController(unittest.TestCase):
    """Test cases for browser_controller.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        pass
    
    def test_init_valid_browser(self):
        """Test initialization with valid browser"""
        from browser_controller import BrowserController
        
        browser = BrowserController(browser_name='chrome')
        self.assertEqual(browser.browser_name, 'chrome')
        self.assertFalse(browser.headless)
        self.assertFalse(browser.simulate_behavior)
        self.assertIsNone(browser.driver)
    
    def test_init_invalid_browser(self):
        """Test initialization with invalid browser"""
        from browser_controller import BrowserController
        
        with self.assertRaises(ValueError):
            BrowserController(browser_name='invalid_browser')
    
    def test_init_headless_mode(self):
        """Test initialization with headless mode"""
        from browser_controller import BrowserController
        
        browser = BrowserController(browser_name='chrome', headless=True)
        self.assertTrue(browser.headless)
    
    def test_init_safari_headless_warning(self):
        """Test that Safari headless mode is disabled with warning"""
        from browser_controller import BrowserController
        
        browser = BrowserController(browser_name='safari', headless=True)
        self.assertFalse(browser.headless)  # Should be forced to False
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    def test_start_chrome(self, mock_driver_manager, mock_chrome):
        """Test starting Chrome browser"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        browser = BrowserController(browser_name='chrome')
        result = browser.start()
        
        self.assertTrue(result)
        self.assertIsNotNone(browser.driver)
        mock_chrome.assert_called_once()
    
    @patch('browser_controller.webdriver.Firefox')
    @patch('browser_controller.GeckoDriverManager')
    def test_start_firefox(self, mock_driver_manager, mock_firefox):
        """Test starting Firefox browser"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/geckodriver'
        mock_driver = MagicMock()
        mock_firefox.return_value = mock_driver
        
        browser = BrowserController(browser_name='firefox')
        result = browser.start()
        
        self.assertTrue(result)
        self.assertIsNotNone(browser.driver)
        mock_firefox.assert_called_once()
    
    def test_start_failure(self):
        """Test browser start failure handling"""
        from browser_controller import BrowserController
        
        with patch('browser_controller.webdriver.Chrome', side_effect=Exception("Driver error")):
            browser = BrowserController(browser_name='chrome')
            result = browser.start()
            
            self.assertFalse(result)
            self.assertIsNone(browser.driver)
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    def test_navigate_to_with_https(self, mock_driver_manager, mock_chrome):
        """Test navigation with HTTPS URL"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = 'complete'
        mock_chrome.return_value = mock_driver
        
        browser = BrowserController(browser_name='chrome')
        browser.start()
        result = browser.navigate_to('https://example.com')
        
        self.assertTrue(result)
        mock_driver.get.assert_called_with('https://example.com')
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    def test_navigate_to_adds_https(self, mock_driver_manager, mock_chrome):
        """Test that HTTPS is added if missing"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = 'complete'
        mock_chrome.return_value = mock_driver
        
        browser = BrowserController(browser_name='chrome')
        browser.start()
        result = browser.navigate_to('example.com')
        
        self.assertTrue(result)
        mock_driver.get.assert_called_with('https://example.com')
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    def test_navigate_without_driver(self, mock_driver_manager, mock_chrome):
        """Test navigation without starting browser"""
        from browser_controller import BrowserController
        
        browser = BrowserController(browser_name='chrome')
        result = browser.navigate_to('example.com')
        
        self.assertFalse(result)
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    @patch('browser_controller.time.sleep')
    def test_navigate_retry_logic(self, mock_sleep, mock_driver_manager, mock_chrome):
        """Test navigation retry logic on timeout"""
        from browser_controller import BrowserController
        from selenium.common.exceptions import TimeoutException
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        
        # First two attempts timeout, third succeeds
        mock_driver.get.side_effect = [
            TimeoutException("Timeout 1"),
            TimeoutException("Timeout 2"),
            None
        ]
        mock_driver.execute_script.return_value = 'complete'
        mock_chrome.return_value = mock_driver
        
        browser = BrowserController(browser_name='chrome')
        browser.start()
        result = browser.navigate_to('example.com')
        
        self.assertTrue(result)
        self.assertEqual(mock_driver.get.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Retry delays
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    def test_get_page_title(self, mock_driver_manager, mock_chrome):
        """Test getting page title"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        mock_driver.title = "Test Page Title"
        mock_chrome.return_value = mock_driver
        
        browser = BrowserController(browser_name='chrome')
        browser.start()
        title = browser.get_page_title()
        
        self.assertEqual(title, "Test Page Title")
    
    def test_get_page_title_no_driver(self):
        """Test getting page title without driver"""
        from browser_controller import BrowserController
        
        browser = BrowserController(browser_name='chrome')
        title = browser.get_page_title()
        
        self.assertEqual(title, "")
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    @patch('browser_controller.time.sleep')
    def test_simulate_user_activity_passive(self, mock_sleep, mock_driver_manager, mock_chrome):
        """Test passive user activity (no simulation)"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        browser = BrowserController(browser_name='chrome', simulate_behavior=False)
        browser.start()
        
        browser.simulate_user_activity(5)
        
        # Should just sleep for the duration
        mock_sleep.assert_called()
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    @patch('browser_controller.time.sleep')
    @patch('browser_controller.time.time')
    def test_simulate_user_activity_active(self, mock_time, mock_sleep, mock_driver_manager, mock_chrome):
        """Test active user activity simulation"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = 1000
        mock_chrome.return_value = mock_driver
        
        # Mock time progression
        start_time = 100.0
        mock_time.side_effect = [start_time, start_time, start_time + 10]
        
        browser = BrowserController(browser_name='chrome', simulate_behavior=True)
        browser.start()
        
        browser.simulate_user_activity(5)
        
        # Should execute scrolling scripts
        self.assertTrue(mock_driver.execute_script.called)
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    def test_stop_browser(self, mock_driver_manager, mock_chrome):
        """Test stopping the browser"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        browser = BrowserController(browser_name='chrome')
        browser.start()
        browser.stop()
        
        mock_driver.quit.assert_called_once()
        self.assertIsNone(browser.driver)
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    def test_context_manager(self, mock_driver_manager, mock_chrome):
        """Test using browser as context manager"""
        from browser_controller import BrowserController
        
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        with BrowserController(browser_name='chrome') as browser:
            self.assertIsNotNone(browser.driver)
        
        # Browser should be stopped after exiting context
        mock_driver.quit.assert_called_once()


class TestOSCARTestAutomator(unittest.TestCase):
    """Test cases for test_automator.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            "browser_categories": {
                "Social Media": ["twitter.com", "facebook.com"],
                "Development": ["github.com", "stackoverflow.com"]
            }
        }
        
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.json')
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_init_loads_config(self):
        """Test that initialization loads config"""
        from test_automator import OSCARTestAutomator
        
        automator = OSCARTestAutomator(config_path=self.config_path)
        self.assertIsNotNone(automator.config)
        self.assertEqual(automator.config, self.test_config)
    
    def test_init_missing_config(self):
        """Test initialization with missing config file"""
        from test_automator import OSCARTestAutomator
        
        fake_path = os.path.join(self.test_dir, 'nonexistent.json')
        
        with self.assertRaises(SystemExit):
            OSCARTestAutomator(config_path=fake_path)
    
    def test_parse_duration_minutes(self):
        """Test parsing duration in minutes"""
        from test_automator import OSCARTestAutomator
        
        automator = OSCARTestAutomator(config_path=self.config_path)
        
        self.assertEqual(automator._parse_duration('30m'), 1800)
        self.assertEqual(automator._parse_duration('1m'), 60)
        self.assertEqual(automator._parse_duration('120m'), 7200)
    
    def test_parse_duration_hours(self):
        """Test parsing duration in hours"""
        from test_automator import OSCARTestAutomator
        
        automator = OSCARTestAutomator(config_path=self.config_path)
        
        self.assertEqual(automator._parse_duration('1h'), 3600)
        self.assertEqual(automator._parse_duration('2h'), 7200)
    
    def test_parse_duration_seconds(self):
        """Test parsing duration in seconds"""
        from test_automator import OSCARTestAutomator
        
        automator = OSCARTestAutomator(config_path=self.config_path)
        
        self.assertEqual(automator._parse_duration('90s'), 90)
        self.assertEqual(automator._parse_duration('3600s'), 3600)
    
    def test_parse_duration_no_unit(self):
        """Test parsing duration without unit (assumes minutes)"""
        from test_automator import OSCARTestAutomator
        
        automator = OSCARTestAutomator(config_path=self.config_path)
        
        self.assertEqual(automator._parse_duration('30'), 1800)
        self.assertEqual(automator._parse_duration('5'), 300)
    
    def test_parse_duration_invalid(self):
        """Test parsing invalid duration"""
        from test_automator import OSCARTestAutomator
        
        automator = OSCARTestAutomator(config_path=self.config_path)
        
        with self.assertRaises(SystemExit):
            automator._parse_duration('invalid')


class TestArgumentParsing(unittest.TestCase):
    """Test cases for argument parsing"""
    
    def test_parse_arguments_defaults(self):
        """Test default argument values"""
        from test_automator import parse_arguments
        
        with patch('sys.argv', ['test_automator.py']):
            args = parse_arguments()
            
            self.assertEqual(args.config, 'default_config.json')
            self.assertEqual(args.duration, '30m')
            self.assertEqual(args.visits_per_site, '2m')
            self.assertEqual(args.browser, 'chrome')
            self.assertFalse(args.headless)
            self.assertFalse(args.simulate_behavior)
            self.assertIsNone(args.category)
    
    def test_parse_arguments_custom(self):
        """Test custom argument values"""
        from test_automator import parse_arguments
        
        test_args = [
            'test_automator.py',
            '--config', 'custom.json',
            '--duration', '1h',
            '--visits-per-site', '5m',
            '--browser', 'firefox',
            '--headless',
            '--simulate-behavior',
            '--category', 'Development'
        ]
        
        with patch('sys.argv', test_args):
            args = parse_arguments()
            
            self.assertEqual(args.config, 'custom.json')
            self.assertEqual(args.duration, '1h')
            self.assertEqual(args.visits_per_site, '5m')
            self.assertEqual(args.browser, 'firefox')
            self.assertTrue(args.headless)
            self.assertTrue(args.simulate_behavior)
            self.assertEqual(args.category, 'Development')


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            "browser_categories": {
                "Test": ["example.com"]
            }
        }
        
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, 'test_config.json')
        
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_config_loader_integration(self):
        """Test ConfigLoader with real file"""
        from config_loader import ConfigLoader
        
        loader = ConfigLoader(self.config_path)
        sites = loader.get_all_sites()
        
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0][0], 'example.com')
        self.assertEqual(sites[0][1], 'Test')


if __name__ == '__main__':
    unittest.main()
