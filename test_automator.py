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
    - Progress tracking with visual progress bars (tqdm)
    - Detailed logging with runtime statistics
    - Headless mode for CI/CD integration
    - Random sampling option
    - Flexible time format support
    - Cross-platform support (Windows, macOS, Linux)

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
    pip install selenium webdriver-manager tqdm

Author: Agile Creative Labs Inc (c) 2025
Part of OSCAR v1.0 - On-device System for Computing and Analytics Reporting
Version: 2.0.0
"""
import argparse
import csv
import json
import logging
import sys
import time
import random
import platform
from pathlib import Path
from datetime import datetime, timedelta
from browser_controller import BrowserController
from config_loader import ConfigLoader
from tqdm import tqdm

# Setup logging with UTF-8 encoding for cross-platform compatibility
log_handlers = [
    logging.FileHandler(
        f'oscar_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
        encoding='utf-8'
    )
]

# Windows console encoding fix
if platform.system() == 'Windows':
    import sys
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    log_handlers.append(logging.StreamHandler(sys.stdout))
else:
    log_handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
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
        self.platform = platform.system()
        
        # Use ASCII-safe symbols for Windows
        if self.platform == 'Windows':
            self.success_symbol = '[OK]'
            self.fail_symbol = '[FAIL]'
        else:
            self.success_symbol = '✓'
            self.fail_symbol = '✗'
        
        logger.info(f"Running on {self.platform} ({platform.platform()})")
    
    def _parse_duration(self, duration_str, default_unit='minutes'):
        """
        Parse duration string to seconds
        
        Args:
            duration_str: Duration like '30m', '1h', '90s', or plain number
            default_unit: 'minutes' or 'seconds' - unit to use if none specified
            
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
                # Plain number - use default unit
                num = int(duration_str)
                if default_unit == 'seconds':
                    return num
                else:
                    return num * 60
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
            sites = random.sample(sites, min(sample, len(sites)))

        logger.info(f"Selected {len(sites)} sites for testing")
        return sites
    
    def _format_time(self, seconds):
        """Format seconds into human-readable time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m {int(seconds%60)}s"
        else:
            hours = int(seconds/3600)
            minutes = int((seconds%3600)/60)
            return f"{hours}h {minutes}m"
    
    def run(self, args):
        logger.info("=" * 80)
        logger.info("OSCAR Test Automator Starting")
        logger.info("=" * 80)

        total_duration = self._parse_duration(args.duration, default_unit='minutes')
        min_time = self._parse_duration(args.min_time, default_unit='seconds')
        max_time = self._parse_duration(args.max_time, default_unit='seconds')
        sites = self._get_sites(args.categories, args.sample)

        if not sites:
            logger.error("No sites to test!")
            sys.exit(1)

        # Platform-specific browser warning
        if args.browser == 'safari' and self.platform != 'Darwin':
            logger.error(f"Safari is only available on macOS. Current platform: {self.platform}")
            logger.info("Available browsers: chrome, firefox, edge")
            sys.exit(1)

        # Estimate number of visits
        avg_time = (min_time + max_time) / 2
        estimated_visits = int(total_duration / avg_time) * len(sites)

        logger.info(f"Platform: {self.platform}")
        logger.info(f"Browser: {args.browser}")
        logger.info(f"Headless: {args.headless}")
        logger.info(f"Simulate Behavior: {args.simulate_behavior}")
        logger.info(f"Total Duration: {self._format_time(total_duration)} ({total_duration}s)")
        logger.info(f"Per-site time: {min_time}s – {max_time}s (avg: {avg_time:.0f}s)")
        logger.info(f"Sites in rotation: {len(sites)}")
        logger.info(f"Estimated visits: ~{estimated_visits}")
        
        # Calculate estimated completion time
        completion_time = datetime.now() + timedelta(seconds=total_duration)
        logger.info(f"Estimated completion: {completion_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        with BrowserController(
            browser_name=args.browser,
            headless=args.headless,
            simulate_behavior=args.simulate_behavior,
            show_progress=True
        ) as browser:

            if not browser.start():
                logger.error("Failed to start browser")
                sys.exit(1)

            self.start_time = time.time()
            end_time = self.start_time + total_duration
            cycle = 1

            # Overall progress bar
            overall_pbar = tqdm(
                total=total_duration,
                desc="Overall Progress",
                unit="s",
                ncols=100,
                position=0
            )

            try:
                while time.time() < end_time:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Cycle {cycle} - Sites: {len(sites)}")
                    logger.info(f"{'='*60}")
                    
                    # Cycle progress bar
                    cycle_pbar = tqdm(
                        total=len(sites),
                        desc=f"Cycle {cycle}",
                        unit="site",
                        ncols=100,
                        position=1,
                        leave=False
                    )
                    
                    for idx, (url, category) in enumerate(sites):
                        if time.time() >= end_time:
                            break
                        
                        visit_time = random.randint(min_time, max_time)
                        remaining = end_time - time.time()
                        visit_time = min(visit_time, int(remaining))
                        
                        if visit_time <= 0:
                            break

                        # Update cycle progress description
                        cycle_pbar.set_description(f"Cycle {cycle} [{idx+1}/{len(sites)}]")
                        
                        # Visit site
                        result = browser.visit_site(url, visit_time)
                        result.update({
                            'category': category,
                            'cycle': cycle,
                            'timestamp': datetime.now().isoformat()
                        })
                        self.visit_results.append(result)

                        # Update progress bars
                        overall_pbar.update(result['duration'])
                        cycle_pbar.update(1)

                        # Log result
                        if result['status'] == 'success':
                            logger.info(
                                f"{self.success_symbol} {url[:50]} [{category}] "
                                f"{result['duration']:.1f}s | "
                                f"Title: {result['title'][:40]}"
                            )
                        else:
                            logger.warning(
                                f"{self.fail_symbol} {url[:50]} [{category}] "
                                f"Failed: {result.get('error')}"
                            )

                        # Show remaining time
                        remaining = end_time - time.time()
                        overall_pbar.set_postfix({
                            'remaining': self._format_time(remaining),
                            'visits': len(self.visit_results)
                        })

                    cycle_pbar.close()
                    cycle += 1

            except KeyboardInterrupt:
                logger.info("\n\nInterrupted by user (Ctrl+C)")

            finally:
                overall_pbar.close()
                self.end_time = time.time()
                self._generate_csv()
                self._generate_summary()

    def _generate_csv(self):
        """Generate CSV report of all visits"""
        if not self.visit_results:
            logger.warning("No visit results to save")
            return
        
        filename = f"data/logs/test_activity_{datetime.now():%Y%m%d_%H%M%S}.csv"
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'url', 'category', 'title', 
                    'duration', 'status', 'cycle', 'error'
                ])
                for r in self.visit_results:
                    writer.writerow([
                        r['timestamp'], 
                        r['url'], 
                        r['category'], 
                        r['title'], 
                        r['duration'], 
                        r['status'],
                        r['cycle'],
                        r.get('error', '')
                    ])
            logger.info(f"✓ CSV saved: {filename}")
        except Exception as e:
            logger.error(f"✗ Failed to save CSV: {e}")

    def _generate_summary(self):
        """Generate and display test summary"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        if not self.visit_results:
            logger.warning("No visits completed")
            return
        
        total_time = self.end_time - self.start_time
        total_visits = len(self.visit_results)
        successful = sum(1 for r in self.visit_results if r['status'] == 'success')
        failed = total_visits - successful
        success_rate = (successful / total_visits * 100) if total_visits > 0 else 0

        # Time statistics
        logger.info(f"Platform: {self.platform}")
        logger.info(f"Runtime: {self._format_time(total_time)} ({total_time:.1f}s)")
        logger.info(f"Start: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"End: {datetime.fromtimestamp(self.end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Visit statistics
        logger.info(f"\nTotal Visits: {total_visits}")
        logger.info(f"  {self.success_symbol} Successful: {successful} ({success_rate:.1f}%)")
        logger.info(f"  {self.fail_symbol} Failed: {failed} ({100-success_rate:.1f}%)")
        
        # Category breakdown
        if successful > 0:
            categories = {}
            for r in self.visit_results:
                if r['status'] == 'success':
                    cat = r['category']
                    categories[cat] = categories.get(cat, 0) + 1
            
            logger.info("\nCategory Breakdown:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {cat}: {count} visits")
        
        # Failed URLs
        if failed > 0:
            logger.info("\nFailed URLs:")
            for r in self.visit_results:
                if r['status'] != 'success':
                    logger.info(f"  {self.fail_symbol} {r['url']}: {r.get('error', 'Unknown error')}")

        # Save JSON summary
        json_file = f"oscar_results_{datetime.now():%Y%m%d_%H%M%S}.json"
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'summary': {
                        'platform': self.platform,
                        'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                        'end_time': datetime.fromtimestamp(self.end_time).isoformat(),
                        'total_runtime_seconds': total_time,
                        'total_visits': total_visits,
                        'successful_visits': successful,
                        'failed_visits': failed,
                        'success_rate': success_rate
                    },
                    'visits': self.visit_results
                }, f, indent=2)
            logger.info(f"\n{self.success_symbol} JSON results saved: {json_file}")
        except Exception as e:
            logger.error(f"{self.fail_symbol} Failed to save JSON: {e}")

        logger.info("="*80)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='OSCAR Test Automator - Cross-platform browser testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic 30-minute test with Chrome
  python test_automator.py --duration 30m
  
  # Headless mode with random sampling
  python test_automator.py --duration 10m --headless --sample 10
  
  # Test specific categories
  python test_automator.py --categories "Social Media,Development" --duration 15m
  
  # Custom timing per site
  python test_automator.py --min-time 30 --max-time 90 --duration 1h
  
  # Firefox with behavior simulation
  python test_automator.py --browser firefox --simulate-behavior --duration 20m

Supported Platforms:
  - Windows: chrome, firefox, edge
  - macOS: chrome, firefox, edge, safari
  - Linux: chrome, firefox
        """
    )
    
    parser.add_argument(
        '--config', 
        default='config/default_config.json', 
        help='Path to OSCAR config file'
    )
    parser.add_argument(
        '--duration', 
        default='30m', 
        help='Total test duration (e.g., 30m, 1h, 90s)'
    )
    parser.add_argument(
        '--min-time', 
        default='60', 
        help='Minimum seconds per site (default: 60s). Use plain number for seconds or add suffix (60s, 2m)'
    )
    parser.add_argument(
        '--max-time', 
        default='180', 
        help='Maximum seconds per site (default: 180s). Use plain number for seconds or add suffix (180s, 3m)'
    )
    parser.add_argument(
        '--browser', 
        choices=['chrome', 'firefox', 'edge', 'safari'], 
        default='chrome',
        help='Browser to use (safari only on macOS)'
    )
    parser.add_argument(
        '--headless', 
        action='store_true',
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--simulate-behavior', 
        action='store_true',
        help='Enable human-like scrolling and pauses'
    )
    parser.add_argument(
        '--categories', 
        help='Comma-separated categories to test (e.g., "Development,Social Media")'
    )
    parser.add_argument(
        '--sample', 
        type=int, 
        help='Randomly sample N sites from selection'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    try:
        automator = OSCARTestAutomator(config_path=args.config)
        automator.run(args)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()