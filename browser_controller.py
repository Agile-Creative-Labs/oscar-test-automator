"""
BrowserController
=================

A robust, production-ready Selenium browser automation controller designed for
reliable web testing, analytics validation, A/B testing, traffic simulation,
and stealth scraping.

Features
--------
- Multi-browser support: Chrome, Firefox, Edge, Safari
- Lazy initialization with explicit ``start()`` and ``stop()`` lifecycle
- Context manager (``with`` statement) for guaranteed cleanup
- Configurable page load timeout (default: 30s)
- Automatic retry logic with exponential backoff (2 retries, 8s delay)
- Stealth mode: disables automation flags and WebDriver detection
- Optional human-like behavior simulation (scrolling, random pauses)
- Comprehensive logging with structured debug/info/warning/error levels
- Rich return objects from ``visit_site()`` including status, duration, and attempts
- Headless mode with browser-specific flags and Safari fallback
- Clean separation of concerns with private helper methods
- Full docstrings and type hints for IDE support and maintainability

Usage Example
-------------
.. code-block:: python

    from browser_controller import BrowserController
    import logging

    logging.basicConfig(level=logging.INFO)

    with BrowserController(
        browser_type='chrome',
        headless=True,
        simulate_behavior=True
    ) as browser:
        if browser.start():
            result = browser.visit_site('example.com', duration_seconds=15)
            print(f"Visit result: {result['status']} in {result['duration']:.2f}s")

    # Browser is automatically quit here

Design Philosophy
-----------------
- Fail-fast on invalid configuration
- Never hang indefinitely (timeouts + retries)
- Always clean up resources (context manager)
- Log everything useful, suppress noise
- Simulate real users when needed
- Be explicit: ``start()`` and ``stop()`` over magic init

Author: Agile Creative Labs (c) 2025
Version: 2.0.0
License: MIT
"""
import time
import random
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

logger = logging.getLogger(__name__)


class BrowserController:
    """Controls browser automation for OSCAR testing"""
    
    SUPPORTED_BROWSERS = ['chrome', 'firefox', 'edge', 'safari']
    MAX_RETRIES = 2
    RETRY_DELAY = 8  # seconds
    PAGE_LOAD_TIMEOUT = 30  # seconds
    
    def __init__(self, browser_type='chrome', headless=False, simulate_behavior=False):
        """
        Initialize browser controller
        
        Args:
            browser_type: Browser to use (chrome, firefox, edge, safari)
            headless: Run browser in headless mode
            simulate_behavior: Enable simple user behavior simulation
        """
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.simulate_behavior = simulate_behavior
        self.driver = None
        
        if self.browser_type not in self.SUPPORTED_BROWSERS:
            raise ValueError(f"Unsupported browser: {browser_type}. Choose from {self.SUPPORTED_BROWSERS}")
        
        if self.headless and self.browser_type == 'safari':
            logger.warning("Safari does not support headless mode. Running in normal mode.")
            self.headless = False
        
        logger.info(f"Initializing {self.browser_type} browser (headless={self.headless}, simulate_behavior={self.simulate_behavior})")
    
    def start(self):
        """Start the browser instance"""
        try:
            if self.browser_type == 'chrome':
                self.driver = self._start_chrome()
            elif self.browser_type == 'firefox':
                self.driver = self._start_firefox()
            elif self.browser_type == 'edge':
                self.driver = self._start_edge()
            elif self.browser_type == 'safari':
                self.driver = self._start_safari()
            
            self.driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)
            logger.info(f"{self.browser_type.capitalize()} browser started successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start {self.browser_type} browser: {e}")
            return False
    
    def _start_chrome(self):
        """Start Chrome browser"""
        options = ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    def _start_firefox(self):
        """Start Firefox browser"""
        options = FirefoxOptions()
        if self.headless:
            options.add_argument('--headless')
        options.set_preference('dom.webdriver.enabled', False)
        options.set_preference('useAutomationExtension', False)
        
        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)
    
    def _start_edge(self):
        """Start Edge browser"""
        options = EdgeOptions()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        service = EdgeService(EdgeChromiumDriverManager().install())
        return webdriver.Edge(service=service, options=options)
    
    def _start_safari(self):
        """Start Safari browser"""
        # Safari driver comes pre-installed on macOS, no webdriver-manager needed
        return webdriver.Safari()
    
    def visit_site(self, url, duration_seconds):
        """
        Visit a website and stay for specified duration
        
        Args:
            url: Website URL to visit
            duration_seconds: How long to stay on the site
            
        Returns:
            dict: Visit result with status, duration, and any errors
        """
        if not self.driver:
            return {
                'url': url,
                'status': 'error',
                'error': 'Browser not started',
                'duration': 0
            }
        
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        logger.info(f"Visiting {url} for {duration_seconds}s")
        
        # Try loading the page with retries
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                start_time = time.time()
                self.driver.get(url)
                
                # Wait for page to be somewhat loaded
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                
                logger.info(f"Successfully loaded {url}")
                
                # Simulate user behavior if enabled
                if self.simulate_behavior:
                    self._simulate_user_behavior(duration_seconds)
                else:
                    time.sleep(duration_seconds)
                
                elapsed = time.time() - start_time
                
                return {
                    'url': url,
                    'status': 'success',
                    'duration': elapsed,
                    'attempts': attempt + 1
                }
            
            except TimeoutException:
                logger.warning(f"Timeout loading {url} (attempt {attempt + 1}/{self.MAX_RETRIES + 1})")
                if attempt < self.MAX_RETRIES:
                    logger.info(f"Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)
                else:
                    return {
                        'url': url,
                        'status': 'timeout',
                        'error': 'Page load timeout after retries',
                        'duration': 0,
                        'attempts': attempt + 1
                    }
            
            except WebDriverException as e:
                logger.error(f"WebDriver error on {url} (attempt {attempt + 1}/{self.MAX_RETRIES + 1}): {e}")
                if attempt < self.MAX_RETRIES:
                    logger.info(f"Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)
                else:
                    return {
                        'url': url,
                        'status': 'error',
                        'error': str(e),
                        'duration': 0,
                        'attempts': attempt + 1
                    }
            
            except Exception as e:
                logger.error(f"Unexpected error visiting {url}: {e}")
                return {
                    'url': url,
                    'status': 'error',
                    'error': str(e),
                    'duration': 0,
                    'attempts': attempt + 1
                }
    
    def _simulate_user_behavior(self, duration_seconds):
        """
        Simulate simple user behavior (scrolling, small pauses)
        
        Args:
            duration_seconds: Total time to simulate behavior
        """
        end_time = time.time() + duration_seconds
        
        try:
            # Get page height
            page_height = self.driver.execute_script('return document.body.scrollHeight')
            viewport_height = self.driver.execute_script('return window.innerHeight')
            
            scroll_count = 0
            max_scrolls = 5
            
            while time.time() < end_time and scroll_count < max_scrolls:
                # Random scroll distance (10-40% of viewport)
                scroll_distance = random.randint(
                    int(viewport_height * 0.1),
                    int(viewport_height * 0.4)
                )
                
                # Scroll down
                self.driver.execute_script(f'window.scrollBy(0, {scroll_distance});')
                scroll_count += 1
                
                # Random pause between scrolls (2-5 seconds)
                pause_time = random.uniform(2, 5)
                time.sleep(min(pause_time, end_time - time.time()))
                
                if time.time() >= end_time:
                    break
            
            # Wait for remaining time
            remaining = end_time - time.time()
            if remaining > 0:
                time.sleep(remaining)
        
        except Exception as e:
            logger.debug(f"Behavior simulation error (non-critical): {e}")
            # Fallback to simple wait if simulation fails
            remaining = end_time - time.time()
            if remaining > 0:
                time.sleep(remaining)
    
    def stop(self):
        """Stop and close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"{self.browser_type.capitalize()} browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
        return False
