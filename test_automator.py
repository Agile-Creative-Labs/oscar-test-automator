"""
OSCAR Test Automator - Automated Browser Testing for Activity Monitoring

Overview:
    Automated browser-based testing tool that simulates real user activity across
    websites defined in OSCAR's configuration. Generates realistic activity data
    for testing ML categorization accuracy, model training, and regression testing.

Features:
    - Reads websites from default_config.json
    - Sequential navigation with configurable durations
    - Multi-browser support (Chrome, Firefox, Edge, Safari)
    - CSV output compatible with OSCAR's activity logs
    - Progress tracking and detailed logging
    - Headless mode for CI/CD integration
    - Random sampling option
    - Flexible time format support

Usage:
    # Basic usage (30 minutes, Chrome)
    python test_automator.py --duration 30
    
    # Specific category testing
    python test_automator.py --categories Development --duration 15
    
    # Multiple categories
    python test_automator.py --categories "Development,Social Media" --duration 20
    
    # Random sampling (visit 50 sites)
    python test_automator.py --sample 50 --duration 30
    
    # Custom time per site
    python test_automator.py --min-time 60 --max-time 180 --duration 30
    
    # Headless mode
    python test_automator.py --headless --duration 60
    
    # Different browser
    python test_automator.py --browser firefox --duration 30

Dependencies:
    pip install selenium webdriver-manager colorama tqdm

Author: Agile Creative Labs Inc (c) 2025
Part of OSCAR v1.0 - On-device System for Computing and Analytics Reporting
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from browser_controller import BrowserController

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'oscar_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class OSCARTestAutomator:
    """Main automator class for OSCAR testing"""
    
    def __init__(self, config_path='default_config.json'):
        """
        Initialize automator with config
        
        Args:
            config_path: Path to configuration JSON file
        """
        self.config = self._load_config(config_path)
        self.visit_results = []
        self.start_time = None
        self.end_time = None
        
    def _load_config(self, config_path):
        """Load configuration from JSON file"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.error(f"Config file not found: {config_path}")
                sys.exit(1)
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Loaded config from {config_path}")
            return config
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            sys.exit(1)
    
    def _parse_duration(self, duration_str):
        """
        Parse duration string to seconds
        
        Args:
            duration_str: Duration like '30m', '1h', '90s'
            
        Returns:
            int: Duration in seconds
        """
        duration_str = duration_str.lower().strip()
        
        try:
            if duration_str.endswith('m'):
                return int(duration_str[:-1]) * 60
            elif duration_str.endswith('h'):
                return int(duration_str[:-1]) * 3600
            elif duration_str.endswith('s'):
                return int(duration_str[:-1])
            else:
                # Assume minutes if no unit
                return int(duration_str) * 60
        except ValueError:
            logger.error(f"Invalid duration format: {duration_str}")
            sys.exit(1)
    
    def _get_sites_for_category(self, category=None):
        """
        Get list of sites, optionally filtered by category
        
        Args:
            category: Category to filter by (optional)
            
        Returns:
            list: List of site dictionaries
        """
        if category:
            # Filter sites by category
            filtered_sites = []
            for cat in self.config.get('categories', []):
                if cat['name'].lower() == category.lower():
                    filtered_sites = cat['sites']
                    logger.info(f"Testing category '{category}' with {len(filtered_sites)} sites")
                    break
            
            if not filtered_sites:
                logger.warning(f"Category '{category}' not found in config, using all sites")
                return self._flatten_all_sites()
            
            return filtered_sites
        else:
            # Use all sites from all categories
            return self._flatten_all_sites()
    
    def _flatten_all_sites(self):
        """Get all sites from all categories"""
        all_sites = []
        for category in self.config.get('categories', []):
            all_sites.extend(category['sites'])
        logger.info(f"Using all sites: {len(all_sites)} total")
        return all_sites
    
    def run(self, args):
        """
        Main execution method
        
        Args:
            args: Parsed command line arguments
        """
        logger.info("="*60)
        logger.info("OSCAR Test Automator Starting")
        logger.info("="*60)
        
        # Parse durations
        total_duration = self._parse_duration(args.duration)
        visit_duration = self._parse_duration(args.visits_per_site)
        
        # Get sites to test
        sites = self._get_sites_for_category(args.category)
        
        if not sites:
            logger.error("No sites to test!")
            sys.exit(1)
        
        # Log test parameters
        logger.info(f"Browser: {args.browser}")
        logger.info(f"Headless: {args.headless}")
        logger.info(f"Simulate Behavior: {args.simulate_behavior}")
        logger.info(f"Total Duration: {total_duration}s ({total_duration/60:.1f}m)")
        logger.info(f"Visit Duration per Site: {visit_duration}s")
        logger.info(f"Sites to Test: {len(sites)}")
        logger.info("="*60)
        
        # Initialize browser
        browser = BrowserController(
            browser_type=args.browser,
            headless=args.headless,
            simulate_behavior=args.simulate_behavior
        )
        
        if not browser.start():
            logger.error("Failed to start browser. Exiting.")
            sys.exit(1)
        
        # Track timing
        self.start_time = time.time()
        end_time = self.start_time + total_duration
        
        try:
            cycle = 1
            while time.time() < end_time:
                logger.info(f"\n--- Cycle {cycle} ---")
                
                for site in sites:
                    # Check if we've exceeded total duration
                    if time.time() >= end_time:
                        logger.info("Total duration reached. Stopping.")
                        break
                    
                    # Calculate remaining time
                    remaining_time = end_time - time.time()
                    actual_visit_duration = min(visit_duration, remaining_time)
                    
                    if actual_visit_duration <= 0:
                        break
                    
                    # Visit the site
                    result = browser.visit_site(site['url'], actual_visit_duration)
                    result['site_name'] = site.get('name', site['url'])
                    result['cycle'] = cycle
                    result['timestamp'] = datetime.now().isoformat()
                    
                    self.visit_results.append(result)
                    
                    # Log result
                    if result['status'] == 'success':
                        logger.info(f"✓ {result['site_name']}: {result['duration']:.1f}s")
                    else:
                        logger.warning(f"✗ {result['site_name']}: {result['status']} - {result.get('error', 'Unknown error')}")
                
                cycle += 1
        
        except KeyboardInterrupt:
            logger.info("\n\nTest interrupted by user (Ctrl+C)")
        
        finally:
            # Clean up
            self.end_time = time.time()
            browser.stop()
            
            # Generate summary
            self._generate_summary()
    
    def _generate_summary(self):
        """Generate and log test summary"""
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        
        total_time = self.end_time - self.start_time
        total_visits = len(self.visit_results)
        successful_visits = sum(1 for r in self.visit_results if r['status'] == 'success')
        failed_visits = total_visits - successful_visits
        
        logger.info(f"Total Runtime: {total_time:.1f}s ({total_time/60:.1f}m)")
        logger.info(f"Total Site Visits: {total_visits}")
        logger.info(f"Successful Visits: {successful_visits}")
        logger.info(f"Failed Visits: {failed_visits}")
        
        if failed_visits > 0:
            logger.info("\nFailed Sites:")
            for result in self.visit_results:
                if result['status'] != 'success':
                    logger.info(f"  - {result['site_name']}: {result.get('error', 'Unknown')}")
        
        # Save detailed results to JSON
        results_file = f"oscar_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(results_file, 'w') as f:
                json.dump({
                    'summary': {
                        'total_runtime': total_time,
                        'total_visits': total_visits,
                        'successful_visits': successful_visits,
                        'failed_visits': failed_visits,
                        'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                        'end_time': datetime.fromtimestamp(self.end_time).isoformat()
                    },
                    'visits': self.visit_results
                }, f, indent=2)
            
            logger.info(f"\nDetailed results saved to: {results_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
        
        logger.info("="*60)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='OSCAR Test Automator - Automated browser testing for OSCAR productivity tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python test_automator.py --duration 30m --browser chrome
  
  # Custom config
  python test_automator.py --config custom_sites.json --visits-per-site 2m
  
  # Specific category testing
  python test_automator.py --category Development --duration 15m
  
  # Headless mode with behavior simulation
  python test_automator.py --headless --simulate-behavior --duration 60m
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='default_config.json',
        help='Path to config JSON file (default: default_config.json)'
    )
    
    parser.add_argument(
        '--duration',
        type=str,
        default='30m',
        help='Total test duration (e.g., 30m, 1h, 3600s) (default: 30m)'
    )
    
    parser.add_argument(
        '--visits-per-site',
        type=str,
        default='2m',
        help='Duration to spend on each site (e.g., 2m, 120s) (default: 2m)'
    )
    
    parser.add_argument(
        '--browser',
        type=str,
        choices=['chrome', 'firefox', 'edge', 'safari'],
        default='chrome',
        help='Browser to use for testing (default: chrome)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no visible window)'
    )
    
    parser.add_argument(
        '--simulate-behavior',
        action='store_true',
        help='Enable simple user behavior simulation (scrolling, pauses)'
    )
    
    parser.add_argument(
        '--category',
        type=str,
        default=None,
        help='Test only sites from specific category (e.g., Development, Social)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    try:
        automator = OSCARTestAutomator(config_path=args.config)
        automator.run(args)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
