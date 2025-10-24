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
        #self.config = self._load_config(config_path)
        self.config_loader = ConfigLoader(config_path)  # ← Use ConfigLoader
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
            logger.error(f"Invalid duration: {duration_str}")
            sys.exit(1)

    def _get_sites(self, categories=None, sample=None):
        """Get sites, optionally filtered and sampled"""
        if categories:
            cats = [c.strip() for c in categories.split(',')]
            sites = []
            for cat in cats:
                sites.extend([(url, cat) for url in self.config_loader.get_sites_by_category(cat)])
        else:
            sites = self.config_loader.get_all_sites()

        if sample and sample > 0:
            import random
            sites = random.sample(sites, min(sample, len(sites)))

        logger.info(f"Selected {len(sites)} sites for testing")
        return sites
    
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
        logger.info("=" * 60)
        logger.info("OSCAR Test Automator Starting")
        logger.info("=" * 60)

        total_duration = self._parse_duration(args.duration)
        min_time = self._parse_duration(args.min_time)
        max_time = self._parse_duration(args.max_time)
        sites = self._get_sites(args.categories, args.sample)

        if not sites:
            logger.error("No sites to test!")
            sys.exit(1)

        logger.info(f"Browser: {args.browser}")
        logger.info(f"Headless: {args.headless}")
        logger.info(f"Total Duration: {total_duration}s (~{total_duration//60}m)")
        logger.info(f"Per-site time: {min_time}s – {max_time}s")
        logger.info(f"Sites: {len(sites)}")
        logger.info("=" * 60)

        with BrowserController(
            browser_name=args.browser,
            headless=args.headless,
            simulate_behavior=args.simulate_behavior
        ) as browser:

            if not browser.start():
                logger.error("Failed to start browser")
                sys.exit(1)

            self.start_time = time.time()
            end_time = self.start_time + total_duration
            cycle = 1

            try:
                while time.time() < end_time:
                    logger.info(f"\n--- Cycle {cycle} ---")
                    for url, category in sites:
                        if time.time() >= end_time:
                            break
                        visit_time = random.randint(min_time, max_time)
                        remaining = end_time - time.time()
                        visit_time = min(visit_time, remaining)
                        if visit_time <= 0:
                            break

                        result = browser.visit_site(url, visit_time)
                        result.update({
                            'category': category,
                            'cycle': cycle,
                            'timestamp': datetime.now().isoformat()
                        })
                        self.visit_results.append(result)

                        if result['status'] == 'success':
                            logger.info(f"Success: {url} [{category}] {result['duration']:.1f}s")
                        else:
                            logger.warning(f"Failed: {url} {result.get('error')}")

                    cycle += 1

            except KeyboardInterrupt:
                logger.info("Interrupted by user")

            finally:
                self.end_time = time.time()
                self._generate_csv()
                self._generate_summary()

    def _generate_csv(self):
        if not self.visit_results:
            return
        filename = f"data/logs/test_activity_{datetime.now():%Y%m%d_%H%M%S}.csv"
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'url', 'category', 'title', 'duration', 'status'])
            for r in self.visit_results:
                writer.writerow([r['timestamp'], r['url'], r['category'], r['title'], r['duration'], r['status']])
        logger.info(f"CSV saved: {filename}")

    def _generate_summary(self):
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        total_time = self.end_time - self.start_time
        total_visits = len(self.visit_results)
        successful = sum(1 for r in self.visit_results if r['status'] == 'success')
        failed = total_visits - successful

        logger.info(f"Runtime: {total_time:.1f}s ({total_time/60:.1f}m)")
        logger.info(f"Visits: {total_visits} (Success: {successful}, Failed: {failed})")

        if failed:
            logger.info("\nFailed URLs:")
            for r in self.visit_results:
                if r['status'] != 'success':
                    logger.info(f"  - {r['url']}: {r.get('error')}")

        # Save JSON
        json_file = f"oscar_results_{datetime.now():%Y%m%d_%H%M%S}.json"
        try:
            with open(json_file, 'w') as f:
                json.dump({
                    'summary': {
                        'total_runtime': total_time,
                        'total_visits': total_visits,
                        'successful_visits': successful,
                        'failed_visits': failed
                    },
                    'visits': self.visit_results
                }, f, indent=2)
            logger.info(f"JSON results: {json_file}")
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")

        logger.info("="*60)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='OSCAR Test Automator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_automator.py --duration 10m --headless --sample 5
  python test_automator.py --categories "Social Media,Development" --min-time 30 --max-time 90
        """
    )
    parser.add_argument('--config', default='config/default_config.json', help='Config path')
    parser.add_argument('--duration', default='30m', help='Total duration (e.g. 30m, 1h)')
    parser.add_argument('--min-time', default='60', help='Min seconds per site')
    parser.add_argument('--max-time', default='180', help='Max seconds per site')
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'edge', 'safari'], default='chrome')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--simulate-behavior', action='store_true')
    parser.add_argument('--categories', help='Comma-separated categories')
    parser.add_argument('--sample', type=int, help='Randomly sample N sites')
    return parser.parse_args()


def main():
    args = parse_arguments()
    automator = OSCARTestAutomator(config_path=args.config)
    automator.run(args)


if __name__ == '__main__':
    main()
