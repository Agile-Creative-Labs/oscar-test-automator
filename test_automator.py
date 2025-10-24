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
import csv
import json
import logging
import random
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Third-party imports
try:
    from colorama import Fore, Style, init as colorama_init
    from tqdm import tqdm
    COLORAMA_AVAILABLE = True
    colorama_init(autoreset=True)
except ImportError:
    COLORAMA_AVAILABLE = False
    print("Warning: colorama not installed. Install with: pip install colorama")

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Warning: tqdm not installed. Install with: pip install tqdm")

# Import our modules
from config_loader import ConfigLoader
from browser_controller import BrowserController


class TestAutomator:
    """Main orchestrator for automated browser testing"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.config_loader = ConfigLoader(args.config)
        self.browser_controller = None
        self.start_time = None
        self.end_time = None
        self.sites_visited = 0
        self.sites_failed = 0
        self.total_sites = 0
        self.activities_logged = []
        self.failed_sites = []
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Configure logging with file and console output"""
        log_dir = Path("data/test_automator_logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"test_run_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO if not self.args.verbose else logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Test Automator initialized. Log file: {log_file}")
        
    def _print_colored(self, message: str, color: str = "white"):
        """Print colored output if colorama is available"""
        if COLORAMA_AVAILABLE:
            color_map = {
                "green": Fore.GREEN,
                "yellow": Fore.YELLOW,
                "red": Fore.RED,
                "blue": Fore.CYAN,
                "white": Fore.WHITE,
                "magenta": Fore.MAGENTA
            }
            print(f"{color_map.get(color, Fore.WHITE)}{message}{Style.RESET_ALL}")
        else:
            print(message)
    
    def _parse_time_format(self, time_str: str) -> int:
        """
        Parse flexible time format to minutes
        
        Args:
            time_str: Time string (e.g., "30", "30m", "1h", "90s")
        
        Returns:
            Time in minutes
        """
        time_str = str(time_str).strip().lower()
        
        # If just a number, assume minutes
        if time_str.isdigit():
            return int(time_str)
        
        # Parse with units
        match = re.match(r'^(\d+)\s*([smh]?)$', time_str)
        if not match:
            raise ValueError(f"Invalid time format: {time_str}")
        
        value, unit = match.groups()
        value = int(value)
        
        if unit == 's':
            return max(1, value // 60)  # Convert seconds to minutes
        elif unit == 'h':
            return value * 60  # Convert hours to minutes
        else:  # 'm' or no unit
            return value
    
    def _load_test_sites(self) -> List[Tuple[str, str]]:
        """
        Load and filter websites based on command-line arguments
        
        Returns:
            List of (url, category) tuples
        """
        all_sites = self.config_loader.get_all_sites()
        
        # Filter by categories if specified
        if self.args.categories:
            requested_categories = [c.strip() for c in self.args.categories.split(',')]
            filtered_sites = [
                (url, cat) for url, cat in all_sites 
                if cat in requested_categories
            ]
            self.logger.info(f"Filtered to categories: {requested_categories}")
        else:
            filtered_sites = all_sites
        
        if not filtered_sites:
            self.logger.error("No sites to visit after filtering")
            sys.exit(1)
        
        # Random sampling if specified
        if self.args.sample and self.args.sample < len(filtered_sites):
            filtered_sites = random.sample(filtered_sites, self.args.sample)
            self.logger.info(f"Randomly sampled {self.args.sample} sites")
        
        # Randomize order if requested
        if self.args.randomize:
            random.shuffle(filtered_sites)
            self.logger.info("Site order randomized")
        
        self.total_sites = len(filtered_sites)
        self.logger.info(f"Loaded {self.total_sites} sites for testing")
        
        return filtered_sites
    
    def _calculate_visit_duration(self) -> int:
        """Calculate random visit duration within min/max bounds"""
        return random.randint(self.args.min_time, self.args.max_time)
    
    def _should_continue(self) -> bool:
        """Check if we should continue based on total duration"""
        if not self.start_time:
            return True
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        total_duration_seconds = self.args.duration * 60
        
        return elapsed < total_duration_seconds
    
    def _visit_site(self, url: str, category: str, duration: int) -> bool:
        """
        Visit a single website for the specified duration
        
        Args:
            url: Website URL to visit
            category: Expected category for the site
            duration: How long to stay on the site (seconds)
        
        Returns:
            True if visit successful, False otherwise
        """
        try:
            # Navigate to site
            success = self.browser_controller.navigate_to(url)
            
            if not success:
                self.logger.warning(f"Failed to navigate to {url}")
                self.sites_failed += 1
                self.failed_sites.append({
                    'url': url,
                    'category': category,
                    'timestamp': datetime.now().isoformat(),
                    'reason': 'Navigation failed'
                })
                return False
            
            # Get page title
            title = self.browser_controller.get_page_title()
            
            # Log activity
            activity = {
                'timestamp': datetime.now().isoformat(),
                'app': self.browser_controller.browser_name,
                'title': title,
                'url': url,
                'idle': False,
                'confidence': 1.0,
                'tracking_method': 'automated_test',
                'platform': sys.platform,
                'component': 'test_automator',
                'expected_category': category,
                'visit_duration_seconds': duration
            }
            
            self.activities_logged.append(activity)
            
            # Wait for the specified duration
            if self.args.verbose:
                self.logger.debug(f"Staying on {url} for {duration} seconds")
            
            time.sleep(duration)
            
            self.sites_visited += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Error visiting {url}: {e}", exc_info=True)
            self.sites_failed += 1
            self.failed_sites.append({
                'url': url,
                'category': category,
                'timestamp': datetime.now().isoformat(),
                'reason': str(e)
            })
            return False
    
    def _print_progress(self, current_site: str, elapsed_time: float, 
                       remaining_time: float, current_duration: int):
        """Print progress information"""
        elapsed_str = str(timedelta(seconds=int(elapsed_time)))
        remaining_str = str(timedelta(seconds=int(remaining_time)))
        
        self._print_colored("\n" + "="*70, "blue")
        self._print_colored(f"Progress: {self.sites_visited}/{self.total_sites} sites visited | {self.sites_failed} failed", "green")
        self._print_colored(f"Current: {current_site[:60]}...", "white")
        self._print_colored(f"Duration: {current_duration} seconds", "white")
        self._print_colored(f"Elapsed: {elapsed_str} | Remaining: ~{remaining_str}", "yellow")
        self._print_colored("="*70, "blue")
    
    def _save_activities_csv(self):
        """Save logged activities to CSV file"""
        if not self.activities_logged:
            self.logger.warning("No activities to save")
            return
        
        output_dir = Path(self.args.output).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp if default
        if self.args.output == "data/logs/test_activity_{date}.csv":
            date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            output_file = output_dir / f"test_activity_{date_str}.csv"
        else:
            output_file = Path(self.args.output)
        
        # Write CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'timestamp', 'app', 'title', 'url', 'idle', 'confidence',
                'tracking_method', 'platform', 'component', 'expected_category',
                'visit_duration_seconds'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.activities_logged)
        
        self.logger.info(f"Saved {len(self.activities_logged)} activities to {output_file}")
        self._print_colored(f"✓ Activities saved to: {output_file}", "green")
    
    def _save_summary_report(self):
        """Save test run summary to text file"""
        if not self.start_time or not self.end_time:
            return
        
        output_dir = Path("data/test_automator_logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = output_dir / f"summary_{timestamp}.txt"
        
        duration = (self.end_time - self.start_time).total_seconds()
        duration_str = str(timedelta(seconds=int(duration)))
        
        # Calculate statistics
        category_counts = Counter(
            activity.get('expected_category', 'Unknown')
            for activity in self.activities_logged
        )
        
        success_rate = (self.sites_visited / (self.sites_visited + self.sites_failed) * 100) if (self.sites_visited + self.sites_failed) > 0 else 0
        
        # Write summary
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("OSCAR TEST AUTOMATOR - SUMMARY REPORT\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Test Run Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Duration: {duration_str}\n")
            f.write(f"Browser: {self.args.browser.title()}\n")
            f.write(f"Headless Mode: {self.args.headless}\n\n")
            
            f.write("RESULTS\n")
            f.write("-"*70 + "\n")
            f.write(f"Sites Visited Successfully: {self.sites_visited}\n")
            f.write(f"Sites Failed: {self.sites_failed}\n")
            f.write(f"Success Rate: {success_rate:.1f}%\n")
            f.write(f"Total Activities Logged: {len(self.activities_logged)}\n\n")
            
            if category_counts:
                f.write("CATEGORY DISTRIBUTION\n")
                f.write("-"*70 + "\n")
                for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(self.activities_logged) * 100) if self.activities_logged else 0
                    f.write(f"  {category:30s}: {count:4d} ({percentage:5.1f}%)\n")
                f.write("\n")
            
            if self.failed_sites:
                f.write("FAILED SITES\n")
                f.write("-"*70 + "\n")
                for failure in self.failed_sites:
                    f.write(f"  URL: {failure['url']}\n")
                    f.write(f"  Category: {failure['category']}\n")
                    f.write(f"  Reason: {failure['reason']}\n")
                    f.write(f"  Time: {failure['timestamp']}\n\n")
            
            f.write("="*70 + "\n")
            f.write(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.logger.info(f"Summary report saved to {summary_file}")
        self._print_colored(f"✓ Summary report saved to: {summary_file}", "green")
    
    def _print_summary(self):
        """Print test run summary to console"""
        duration = (self.end_time - self.start_time).total_seconds()
        duration_str = str(timedelta(seconds=int(duration)))
        
        # Calculate category distribution
        category_counts = Counter(
            activity.get('expected_category', 'Unknown')
            for activity in self.activities_logged
        )
        
        success_rate = (self.sites_visited / (self.sites_visited + self.sites_failed) * 100) if (self.sites_visited + self.sites_failed) > 0 else 0
        
        self._print_colored("\n" + "="*70, "blue")
        self._print_colored("TEST RUN SUMMARY", "green")
        self._print_colored("="*70, "blue")
        self._print_colored(f"Total Duration: {duration_str}", "white")
        self._print_colored(f"Sites Visited: {self.sites_visited}", "white")
        self._print_colored(f"Sites Failed: {self.sites_failed}", "red" if self.sites_failed > 0 else "white")
        self._print_colored(f"Success Rate: {success_rate:.1f}%", "green" if success_rate > 90 else "yellow")
        self._print_colored(f"Activities Logged: {len(self.activities_logged)}", "white")
        
        if category_counts:
            self._print_colored("\nCategory Distribution:", "yellow")
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(self.activities_logged) * 100) if self.activities_logged else 0
                self._print_colored(f"  {category}: {count} ({percentage:.1f}%)", "white")
        
        if self.sites_failed > 0:
            self._print_colored(f"\n⚠ {self.sites_failed} site(s) failed to load. Check logs for details.", "yellow")
        
        self._print_colored("="*70, "blue")
    
    def run(self):
        """Main execution loop"""
        try:
            self._print_colored("\n🚀 OSCAR Test Automator Starting...", "green")
            
            # Load sites
            sites = self._load_test_sites()
            
            # Initialize browser
            self._print_colored(f"\n🌐 Launching {self.args.browser.title()} browser...", "blue")
            self.browser_controller = BrowserController(
                browser_name=self.args.browser,
                headless=self.args.headless
            )
            
            if not self.browser_controller.start():
                self._print_colored("❌ Failed to start browser", "red")
                return 1
            
            self._print_colored("✓ Browser launched successfully", "green")
            
            # Start test run
            self.start_time = datetime.now()
            total_duration_seconds = self.args.duration * 60
            
            self._print_colored(f"\n📊 Test Configuration:", "yellow")
            self._print_colored(f"  Duration: {self.args.duration} minutes", "white")
            self._print_colored(f"  Sites to test: {self.total_sites}", "white")
            self._print_colored(f"  Time per site: {self.args.min_time}-{self.args.max_time} seconds", "white")
            self._print_colored(f"  Browser: {self.args.browser}", "white")
            self._print_colored(f"  Headless: {self.args.headless}", "white")
            if self.args.sample:
                self._print_colored(f"  Sampling: {self.args.sample} sites", "magenta")
            
            # Create progress bar if tqdm available
            if TQDM_AVAILABLE:
                pbar = tqdm(total=total_duration_seconds, desc="Test Progress", 
                           unit="s", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]')
            
            # Visit sites in a loop
            site_index = 0
            last_update = time.time()
            
            while self._should_continue():
                # Get next site (cycle through list)
                url, category = sites[site_index % len(sites)]
                site_index += 1
                
                # Calculate visit duration
                visit_duration = self._calculate_visit_duration()
                
                # Show progress (only if no tqdm or verbose)
                elapsed = (datetime.now() - self.start_time).total_seconds()
                remaining = max(0, total_duration_seconds - elapsed)
                
                if not TQDM_AVAILABLE or self.args.verbose:
                    self._print_progress(url, elapsed, remaining, visit_duration)
                
                # Visit site
                self._visit_site(url, category, visit_duration)
                
                # Update progress bar
                if TQDM_AVAILABLE:
                    current_time = time.time()
                    delta = int(current_time - last_update)
                    pbar.update(delta)
                    last_update = current_time
                    
                    # Update description with current site
                    pbar.set_description(f"Visited: {self.sites_visited} | Failed: {self.sites_failed}")
                
                # Check if we should continue
                if not self._should_continue():
                    break
            
            if TQDM_AVAILABLE:
                pbar.close()
            
            self.end_time = datetime.now()
            
            # Save results
            self._print_colored("\n💾 Saving results...", "blue")
            self._save_activities_csv()
            self._save_summary_report()
            
            # Print summary
            self._print_summary()
            
            self._print_colored("\n✅ Test run completed successfully!", "green")
            
            return 0
            
        except KeyboardInterrupt:
            self._print_colored("\n\n⚠️  Test interrupted by user", "yellow")
            self.end_time = datetime.now()
            
            # Save partial results
            if self.activities_logged:
                self._print_colored("\n💾 Saving partial results...", "blue")
                self._save_activities_csv()
                self._save_summary_report()
                self._print_summary()
            
            return 130  # Standard exit code for SIGINT
            
        except Exception as e:
            self._print_colored(f"\n❌ Error during test run: {e}", "red")
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            return 1
            
        finally:
            # Cleanup
            if self.browser_controller:
                self._print_colored("\n🧹 Cleaning up...", "blue")
                self.browser_controller.stop()
                self._print_colored("✓ Browser closed", "green")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="OSCAR Test Automator - Automated browser testing for activity monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic 30-minute test
  python test_automator.py --duration 30
  
  # Test specific categories
  python test_automator.py --categories "Development,Social Media" --duration 15
  
  # Random sampling (50 sites)
  python test_automator.py --sample 50 --duration 30
  
  # Headless mode for CI/CD
  python test_automator.py --headless --duration 60 --output results.csv
  
  # Custom time per site
  python test_automator.py --min-time 30 --max-time 120 --duration 20
  
  # Flexible time format
  python test_automator.py --duration 1h --min-time 45s --max-time 2m
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--duration',
        type=str,
        default='30',
        help='Total test duration (e.g., 30, 30m, 1h, 90s). Default: 30 minutes'
    )
    
    # Optional arguments
    parser.add_argument(
        '--config',
        type=str,
        default='config/default_config.json',
        help='Path to OSCAR config file (default: config/default_config.json)'
    )
    
    parser.add_argument(
        '--browser',
        type=str,
        choices=['chrome', 'firefox', 'edge', 'safari'],
        default='chrome',
        help='Browser to use (default: chrome)'
    )
    
    parser.add_argument(
        '--categories',
        type=str,
        help='Comma-separated list of categories to test (e.g., "Development,Social Media")'
    )
    
    parser.add_argument(
        '--sample',
        type=int,
        help='Randomly sample N sites instead of testing all'
    )
    
    parser.add_argument(
        '--min-time',
        type=int,
        default=60,
        help='Minimum time to spend on each site in seconds (default: 60)'
    )
    
    parser.add_argument(
        '--max-time',
        type=int,
        default=120,
        help='Maximum time to spend on each site in seconds (default: 120)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no visible window)'
    )
    
    parser.add_argument(
        '--randomize',
        action='store_true',
        help='Randomize the order of site visits'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='data/logs/test_activity_{date}.csv',
        help='Output CSV file path (default: data/logs/test_activity_{date}.csv)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Parse duration with flexible format
    try:
        automator_temp = TestAutomator(args)
        args.duration = automator_temp._parse_time_format(args.duration)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    # Validate arguments
    if args.min_time > args.max_time:
        print("Error: --min-time cannot be greater than --max-time")
        return 1
    
    if args.duration <= 0:
        print("Error: --duration must be positive")
        return 1
    
    if args.sample is not None and args.sample <= 0:
        print("Error: --sample must be positive")
        return 1
    
    # Create and run automator
    automator = TestAutomator(args)
    return automator.run()


if __name__ == '__main__':
    sys.exit(main())test
