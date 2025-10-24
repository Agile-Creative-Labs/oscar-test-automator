"""
Unit Tests for OSCAR Test Automator

Tests all core functionality including:
- ConfigLoader integration
- BrowserController API compatibility
- Command-line argument parsing
- Duration parsing
- Site selection and filtering
- Random sampling
- Result tracking

Run with: pytest test_oscar_automator.py -v
Or: python -m pytest test_oscar_automator.py -v
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

# Import the modules we're testing
from config_loader import ConfigLoader
from browser_controller import BrowserController
from test_automator import OSCARTestAutomator, parse_arguments


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_config():
    """Sample configuration matching default_config.json structure"""
    return {
        "browser_categories": {
            "Social Media": ["twitter.com", "facebook.com", "instagram.com"],
            "Development": ["github.com", "stackoverflow.com"],
            "News/Information": ["bbc.com", "cnn.com"],
            "Browser Internal": ["browser_internal", "chrome_internal"],
            "System/Security": ["loginwindow", "screensaver"]
        }
    }


@pytest.fixture
def temp_config_file(sample_config):
    """Create a temporary config file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_driver():
    """Mock Selenium WebDriver"""
    driver = MagicMock()
    driver.title = "Test Page Title"
    driver.execute_script.return_value = 1000  # Mock page height
    return driver


# ============================================================================
# CONFIG LOADER TESTS
# ============================================================================

class TestConfigLoader:
    """Test ConfigLoader functionality"""
    
    def test_config_loader_initialization(self, temp_config_file):
        """Test that ConfigLoader loads config correctly"""
        loader = ConfigLoader(temp_config_file)
        
        assert loader.config is not None
        assert 'browser_categories' in loader.config
        assert len(loader.browser_categories) > 0
    
    def test_get_all_sites(self, temp_config_file):
        """Test getting all sites excludes system categories"""
        loader = ConfigLoader(temp_config_file)
        sites = loader.get_all_sites()
        
        # Should have sites from Social Media, Development, and News
        assert len(sites) == 7  # 3 + 2 + 2
        
        # Check format: list of (url, category) tuples
        assert all(isinstance(site, tuple) and len(site) == 2 for site in sites)
        
        # Verify no internal/system sites
        urls = [url for url, _ in sites]
        assert 'browser_internal' not in urls
        assert 'loginwindow' not in urls
    
    def test_get_sites_by_category(self, temp_config_file):
        """Test getting sites from specific category"""
        loader = ConfigLoader(temp_config_file)
        
        dev_sites = loader.get_sites_by_category('Development')
        assert len(dev_sites) == 2
        assert 'github.com' in dev_sites
        assert 'stackoverflow.com' in dev_sites
        
        social_sites = loader.get_sites_by_category('Social Media')
        assert len(social_sites) == 3
    
    def test_get_categories(self, temp_config_file):
        """Test getting list of categories (excluding system)"""
        loader = ConfigLoader(temp_config_file)
        categories = loader.get_categories()
        
        assert 'Social Media' in categories
        assert 'Development' in categories
        assert 'Browser Internal' not in categories
        assert 'System/Security' not in categories
    
    def test_get_category_count(self, temp_config_file):
        """Test getting site counts per category"""
        loader = ConfigLoader(temp_config_file)
        counts = loader.get_category_count()
        
        assert counts['Social Media'] == 3
        assert counts['Development'] == 2
        assert 'Browser Internal' not in counts
    
    def test_config_file_not_found(self):
        """Test handling of missing config file"""
        with pytest.raises(FileNotFoundError):
            ConfigLoader('nonexistent_config.json')


# ============================================================================
# BROWSER CONTROLLER TESTS
# ============================================================================

class TestBrowserController:
    """Test BrowserController functionality"""
    
    def test_initialization_with_browser_name(self):
        """Test initialization with browser_name parameter"""
        browser = BrowserController(browser_name='chrome')
        assert browser.browser_name == 'chrome'
        assert browser.headless is False
        assert browser.simulate_behavior is False
    
    def test_initialization_with_browser_type(self):
        """Test backward compatibility with browser_type parameter"""
        browser = BrowserController(browser_type='firefox')
        assert browser.browser_name == 'firefox'
    
    def test_invalid_browser(self):
        """Test that invalid browser raises ValueError"""
        with pytest.raises(ValueError, match="Unsupported browser"):
            BrowserController(browser_name='invalid_browser')
    
    def test_safari_headless_warning(self):
        """Test that Safari headless mode is disabled with warning"""
        browser = BrowserController(browser_name='safari', headless=True)
        assert browser.headless is False  # Should be forced to False
    
    @patch('browser_controller.webdriver.Chrome')
    @patch('browser_controller.ChromeDriverManager')
    def test_start_chrome(self, mock_driver_manager, mock_chrome):
        """Test starting Chrome browser"""
        mock_driver_manager.return_value.install.return_value = '/path/to/chromedriver'
        mock_chrome.return_value = MagicMock()
        
        browser = BrowserController(browser_name='chrome')
        result = browser.start()
        
        assert result is True
        assert browser.driver is not None
        mock_chrome.assert_called_once()
    
    def test_navigate_to_adds_https(self, mock_driver):
        """Test that navigate_to adds https:// if missing"""
        browser = BrowserController(browser_name='chrome')
        browser.driver = mock_driver
        
        browser.navigate_to('example.com')
        
        # Check that driver.get was called with https://
        args = mock_driver.get.call_args[0]
        assert args[0].startswith('https://')
    
    def test_navigate_to_without_driver(self):
        """Test navigate_to fails gracefully without driver"""
        browser = BrowserController(browser_name='chrome')
        result = browser.navigate_to('example.com')
        
        assert result is False
    
    def test_get_page_title(self, mock_driver):
        """Test getting page title"""
        browser = BrowserController(browser_name='chrome')
        browser.driver = mock_driver
        
        title = browser.get_page_title()
        assert title == "Test Page Title"
    
    def test_get_page_title_without_driver(self):
        """Test get_page_title returns empty string without driver"""
        browser = BrowserController(browser_name='chrome')
        title = browser.get_page_title()
        
        assert title == ""
    
    def test_simulate_user_activity_passive(self, mock_driver):
        """Test passive activity simulation (no behavior simulation)"""
        browser = BrowserController(browser_name='chrome', simulate_behavior=False)
        browser.driver = mock_driver
        
        start = time.time()
        browser.simulate_user_activity(1)  # 1 second
        duration = time.time() - start
        
        # Should just sleep for ~1 second
        assert 0.9 < duration < 1.2
        
        # Should not call scrolling
        assert mock_driver.execute_script.call_count == 0
    
    def test_simulate_user_activity_active(self, mock_driver):
        """Test active behavior simulation (with scrolling)"""
        browser = BrowserController(browser_name='chrome', simulate_behavior=True)
        browser.driver = mock_driver
        
        browser.simulate_user_activity(0.5)  # Very short duration for testing
        
        # Should call execute_script for scrolling
        assert mock_driver.execute_script.call_count > 0
    
    def test_visit_site_method_exists(self):
        """Test that visit_site method exists and has correct signature"""
        browser = BrowserController(browser_name='chrome')
        
        assert hasattr(browser, 'visit_site')
        assert callable(browser.visit_site)
    
    @patch('browser_controller.BrowserController.navigate_to')
    @patch('browser_controller.BrowserController.get_page_title')
    @patch('browser_controller.BrowserController.simulate_user_activity')
    def test_visit_site_success(self, mock_activity, mock_title, mock_navigate, mock_driver):
        """Test successful visit_site call"""
        mock_navigate.return_value = True
        mock_title.return_value = "Example Page"
        
        browser = BrowserController(browser_name='chrome')
        browser.driver = mock_driver
        
        result = browser.visit_site('example.com', duration_seconds=2)
        
        assert result['status'] == 'success'
        assert result['url'] == 'example.com'
        assert result['page_title'] == "Example Page"
        assert result['duration'] > 0
        assert result['attempts'] == 1
        
        mock_navigate.assert_called_once_with('example.com')
        mock_activity.assert_called_once()
    
    @patch('browser_controller.BrowserController.navigate_to')
    def test_visit_site_failure(self, mock_navigate, mock_driver):
        """Test failed visit_site call"""
        mock_navigate.return_value = False
        
        browser = BrowserController(browser_name='chrome')
        browser.driver = mock_driver
        
        result = browser.visit_site('example.com', duration_seconds=2)
        
        assert result['status'] == 'failed'
        assert result['error'] == 'Navigation failed'
        assert result['attempts'] == 1
    
    def test_context_manager(self):
        """Test context manager support"""
        with patch.object(BrowserController, 'start', return_value=True):
            with patch.object(BrowserController, 'stop'):
                with BrowserController(browser_name='chrome') as browser:
                    assert browser is not None


# ============================================================================
# TEST AUTOMATOR TESTS
# ============================================================================

class TestOSCARTestAutomator:
    """Test OSCARTestAutomator functionality"""
    
    def test_initialization(self, temp_config_file):
        """Test automator initialization"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        
        assert automator.config_loader is not None
        assert isinstance(automator.visit_results, list)
        assert len(automator.visit_results) == 0
    
    def test_parse_duration_minutes(self, temp_config_file):
        """Test parsing duration in minutes"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        
        assert automator._parse_duration('30') == 1800  # 30 minutes
        assert automator._parse_duration('30m') == 1800
        assert automator._parse_duration('1') == 60
    
    def test_parse_duration_hours(self, temp_config_file):
        """Test parsing duration in hours"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        
        assert automator._parse_duration('1h') == 3600
        assert automator._parse_duration('2h') == 7200
    
    def test_parse_duration_seconds(self, temp_config_file):
        """Test parsing duration in seconds"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        
        assert automator._parse_duration('90s') == 90
        assert automator._parse_duration('3600s') == 3600
    
    def test_get_sites_to_test_all(self, temp_config_file):
        """Test getting all sites"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        sites = automator._get_sites_to_test()
        
        assert len(sites) == 7  # All non-system sites
        assert all(isinstance(site, tuple) for site in sites)
    
    def test_get_sites_to_test_specific_category(self, temp_config_file):
        """Test getting sites from specific category"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        sites = automator._get_sites_to_test(categories=['Development'])
        
        assert len(sites) == 2
        urls = [url for url, _ in sites]
        assert 'github.com' in urls
        assert 'stackoverflow.com' in urls
    
    def test_get_sites_to_test_multiple_categories(self, temp_config_file):
        """Test getting sites from multiple categories"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        sites = automator._get_sites_to_test(categories=['Development', 'Social Media'])
        
        assert len(sites) == 5  # 2 + 3
    
    def test_get_sites_to_test_with_sampling(self, temp_config_file):
        """Test random sampling of sites"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        sites = automator._get_sites_to_test(sample_size=3)
        
        assert len(sites) == 3
    
    def test_get_sites_to_test_sampling_larger_than_available(self, temp_config_file):
        """Test that sampling doesn't fail when sample > available sites"""
        automator = OSCARTestAutomator(config_path=temp_config_file)
        sites = automator._get_sites_to_test(sample_size=100)
        
        assert len(sites) == 7  # Should return all available sites


# ============================================================================
# COMMAND LINE ARGUMENT TESTS
# ============================================================================

class TestCommandLineArguments:
    """Test command-line argument parsing"""
    
    def test_default_arguments(self):
        """Test default argument values"""
        with patch('sys.argv', ['test_automator.py']):
            args = parse_arguments()
            
            assert args.browser == 'chrome'
            assert args.duration == '30'
            assert args.headless is False
            assert args.simulate_behavior is False
            assert args.categories is None
            assert args.sample is None
    
    def test_custom_browser(self):
        """Test setting custom browser"""
        with patch('sys.argv', ['test_automator.py', '--browser', 'firefox']):
            args = parse_arguments()
            assert args.browser == 'firefox'
    
    def test_headless_flag(self):
        """Test headless flag"""
        with patch('sys.argv', ['test_automator.py', '--headless']):
            args = parse_arguments()
            assert args.headless is True
    
    def test_simulate_behavior_flag(self):
        """Test simulate-behavior flag"""
        with patch('sys.argv', ['test_automator.py', '--simulate-behavior']):
            args = parse_arguments()
            assert args.simulate_behavior is True
    
    def test_categories_argument(self):
        """Test categories argument"""
        with patch('sys.argv', ['test_automator.py', '--categories', 'Development,Social Media']):
            args = parse_arguments()
            assert args.categories == 'Development,Social Media'
    
    def test_sample_argument(self):
        """Test sample argument"""
        with patch('sys.argv', ['test_automator.py', '--sample', '50']):
            args = parse_arguments()
            assert args.sample == 50
    
    def test_duration_argument(self):
        """Test duration argument"""
        with patch('sys.argv', ['test_automator.py', '--duration', '60']):
            args = parse_arguments()
            assert args.duration == '60'
    
    def test_min_max_time_arguments(self):
        """Test min-time and max-time arguments"""
        with patch('sys.argv', ['test_automator.py', '--min-time', '30', '--max-time', '120']):
            args = parse_arguments()
            assert args.min_time == '30'
            assert args.max_time == '120'
    
    def test_config_argument(self):
        """Test custom config path"""
        with patch('sys.argv', ['test_automator.py', '--config', 'custom.json']):
            args = parse_arguments()
            assert args.config == 'custom.json'


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @patch('browser_controller.BrowserController.start')
    @patch('browser_controller.BrowserController.stop')
    @patch('browser_controller.BrowserController.visit_site')
    def test_full_run_short_duration(self, mock_visit, mock_stop, mock_start, temp_config_file):
        """Test a complete run with very short duration"""
        mock_start.return_value = True
        mock_visit.return_value = {
            'status': 'success',
            'url': 'example.com',
            'duration': 2.0,
            'attempts': 1,
            'page_title': 'Example'
        }
        
        automator = OSCARTestAutomator(config_path=temp_config_file)
        
        # Create mock args
        args = Mock()
        args.browser = 'chrome'
        args.headless = False
        args.simulate_behavior = False
        args.duration = '0.05'  # 3 seconds
        args.min_time = '1'
        args.max_time = '2'
        args.categories = None
        args.sample = 2
        
        automator.run(args)
        
        # Should have visited at least 1 site
        assert len(automator.visit_results) >= 1
        assert mock_start.called
        assert mock_stop.called
    
    def test_readme_examples_parse_correctly(self):
        """Test that all README examples parse without errors"""
        examples = [
            ['--duration', '30'],
            ['--categories', 'Development', '--duration', '15'],
            ['--categories', 'Development,Social Media', '--duration', '20'],
            ['--sample', '50', '--duration', '30'],
            ['--min-time', '60', '--max-time', '180', '--duration', '30'],
            ['--headless', '--duration', '60'],
            ['--browser', 'firefox', '--duration', '30'],
        ]
        
        for example in examples:
            with patch('sys.argv', ['test_automator.py'] + example):
                args = parse_arguments()
                assert args is not None


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Basic performance sanity checks"""
    
    def test_config_loading_speed(self, temp_config_file):
        """Test that config loading is reasonably fast"""
        start = time.time()
        loader = ConfigLoader(temp_config_file)
        duration = time.time() - start
        
        assert duration < 1.0  # Should load in under 1 second
    
    def test_get_all_sites_speed(self, temp_config_file):
        """Test that getting all sites is fast"""
        loader = ConfigLoader(temp_config_file)
        
        start = time.time()
        sites = loader.get_all_sites()
        duration = time.time() - start
        
        assert duration < 0.1  # Should be near-instant


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
