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
    python test_automator.py --category Development --duration 15
    
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
import random
from pathlib import Path
from datetime import datetime
from browser_controller import BrowserController
from config_loader import ConfigLoader

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
        self.config_loader = ConfigLoader(config_path)
        self.visit_results = []
        self.start_time = None
        self.end_time = None
        
    def _parse_duration(self, duration_str):
        """
        Parse duration string to seconds
        
        Args:
            duration_str: Duration like '30m', '1h', '90s'
            
        Returns:
            int: Duration in seconds
        """
        duration_str = str(duration_str).lower().strip()
        
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
    
    def _get_sites_to_test(self, categories=None, sample_size=None):
        """
        Get list of sites to test
        
        Args:
            categories: List of category names to test (optional)
            sample_size: Random sample size (optional)
            
        Returns:
            list: List of (url, category) tuples
        """
        if categories:
            # Get sites from specific categories
            sites = []
            for category in categories:
                category_sites = self.config_loader.get_sites_by_category(category)
                sites.extend([(url, category) for url in category_sites])
            
            if not sites:
                logger.warning(f"No sites found for categories {categories}, using all sites")
                sites = self.config_loader.get_all_sites()
        else:
            # Get all sites
            sites = self.config_loader.get_all_sites()
        
        if not sites:
            logger.error("No sites to test!")
            sys.exit(1)
        
        # Apply random sampling if requested
        if sample_size and sample_size < len(sites):
            logger.info(f"Randomly sampling {sample_size} sites from {len(sites)} total")
            sites = random.sample(sites, sample_size)
        
        logger.info(f"Testing {len(sites)} sites")
        return sites
    
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
        min_visit_duration = self._parse_duration(args.min_time)
        max_visit_duration = self._parse_duration(args.max_time)
        
        # Parse categories
        categories = None
        if args.categories:
            categories = [cat.strip() for cat in args.categories.split(',')]
        
        # Get sites to test
        sites = self._get_sites_to_test(categories, args.sample)
        
        # Log test parameters
        logger.info(f"Browser: {args.browser}")
        logger.info(f"Headless: {args.headless}")
        logger.info(f"Simulate Behavior: {args.simulate_behavior}")
        logger.info(f"Total Duration: {total_duration}s ({total_duration/60:.1f}m)")
        logger.info(f"Visit Duration per Site: {min_visit_duration}-{max_visit_duration}s")
        logger.info(f"Sites to Test: {len(sites)}")
        
        # Show category breakdown
        category_counts = {}
        for url, category in sites:
            category_counts[category] = category_counts.get(category, 0) + 1
        
        logger.info("\nCategory Breakdown:")
        for category, count in sorted(category_counts.items()):
            logger.info(f"  {category}: {count} sites")
        
        logger.info("="*60)
        
        # Initialize browser
        browser = BrowserController(
            browser_name=args.browser,
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
            site_index = 0
            
            while time.time() < end_time:
                logger.info(f"\n--- Cycle {cycle} ---")
                
                # Visit sites in sequence
                while site_index < len(sites) and time.time() < end_time:
                    url, category = sites[site_index]
                    
                    # Calculate remaining time
                    remaining_time = end_time - time.time()
                    
                    # Randomize visit duration within min/max range
                    visit_duration = random.uniform(min_visit_duration, max_visit_duration)
                    actual_visit_duration = min(visit_duration, remaining_time)
                    
                    if actual_visit_duration <= 5:  # Minimum 5 seconds to make visit worthwhile
                        logger.info("Insufficient time remaining. Stopping.")
                        break
                    
                    # Record visit start
                    visit_start = time.time()
                    
                    # Navigate to the site
                    success = browser.navigate_to(url)
                    
                    if success:
                        # Get page title
                        page_title = browser.get_page_title()
                        
                        # Simulate user activity for remaining duration
                        navigation_time = time.time() - visit_start
                        remaining_activity_time = actual_visit_duration - navigation_time
                        
                        if remaining_activity_time > 0:
                            browser.simulate_user_activity(remaining_activity_time)
                        
                        # Record result
                        total_duration_actual = time.time() - visit_start
                        
                        result = {
                            'status': 'success',
                            'url': url,
                            'category': category,
                            'page_title': page_title,
                            'duration': total_duration_actual,
                            'cycle': cycle,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        logger.info(f"✓ {url} ({category}): {total_duration_actual:.1f}s")
                    else:
                        result = {
                            'status': 'failed',
                            'url': url,
                            'category': category,
                            'page_title': '',
                            'duration': time.time() - visit_start,
                            'cycle': cycle,
                            'timestamp': datetime.now().isoformat(),
                            'error': 'Navigation failed'
                        }
                        
                        logger.warning(f"✗ {url} ({category}): Navigation failed")
                    
                    self.visit_results.append(result)
                    site_index += 1
                
                # Reset for next cycle if time remains
                if time.time() < end_time and site_index >= len(sites):
                    site_index = 0
                    cycle += 1
                else:
                    break
        
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
        
        if successful_visits > 0:
            avg_duration = sum(r['duration'] for r in self.visit_results if r['status'] == 'success') / successful_visits
            logger.info(f"Average Visit Duration: {avg_duration:.1f}s")
        
        # Category breakdown
        category_stats = {}
        for result in self.visit_results:
            cat = result['category']
            if cat not in category_stats:
                category_stats[cat] = {'total': 0, 'success': 0, 'failed': 0}
            
            category_stats[cat]['total'] += 1
            if result['status'] == 'success':
                category_stats[cat]['success'] += 1
            else:
                category_stats[cat]['failed'] += 1
        
        logger.info("\nCategory Statistics:")
        for category, stats in sorted(category_stats.items()):
            logger.info(f"  {category}: {stats['success']}/{stats['total']} successful")
        
        if failed_visits > 0:
            logger.info("\nFailed Sites:")
            for result in self.visit_results:
                if result['status'] != 'success':
                    logger.info(f"  - {result['url']} ({result['category']}): {result.get('error', 'Unknown')}")
        
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
  # Basic usage (30 minutes)
  python test_automator.py --duration 30
  
  # Specific category testing
  python test_automator.py --categories Development --duration 15
  
  # Multiple categories
  python test_automator.py --categories "Development,Social Media" --duration 20
  
  # Random sampling (visit 50 sites)
  python test_automator.py --sample 50 --duration 30
  
  # Custom time per site
  python test_automator.py --min-time 60 --max-time 180 --duration 30
  
  # Headless mode with behavior simulation
  python test_automator.py --headless --simulate-behavior --duration 60
  
  # Different browser
  python test_automator.py --browser firefox --duration 30
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
        default='30',
        help='Total test duration in minutes (e.g., 30, 60) or with unit (30m, 1h, 3600s) (default: 30)'
    )
    
    parser.add_argument(
        '--min-time',
        type=str,
        default='30',
        help='Minimum seconds to spend on each site (default: 30)'
    )
    
    parser.add_argument(
        '--max-time',
        type=str,
        default='120',
        help='Maximum seconds to spend on each site (default: 120)'
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
        '--categories',
        type=str,
        default=None,
        help='Test only sites from specific categories (comma-separated, e.g., "Development,Social Media")'
    )
    
    parser.add_argument(
        '--sample',
        type=int,
        default=None,
        help='Randomly sample N sites from the selected categories'
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
