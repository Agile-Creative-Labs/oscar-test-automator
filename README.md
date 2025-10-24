# OSCAR Test Automator

Automated browser-based testing tool that simulates real user activity across websites defined in OSCAR's configuration. Perfect for generating realistic activity data for testing ML categorization accuracy, model training, and regression testing.

## Features

✨ **Core Features:**
- 🌐 Reads websites from `default_config.json`
- 📊 Sequential navigation with configurable durations
- 🔄 Multi-browser support (Chrome, Firefox, Edge, Safari)
- 📝 CSV output compatible with OSCAR's activity logs
- 📈 Real-time progress tracking with tqdm
- 🎨 Colored console output
- 🤖 Headless mode for CI/CD integration

✨ **Advanced Features:**
- 🎲 Random sampling of sites
- 🔀 Randomize visit order
- ⏱️ Flexible time format support (30, 30m, 1h, 90s)
- 📋 Category-specific testing
- 📄 Detailed summary reports
- 🔍 Comprehensive error logging

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Directory Structure

Ensure your project has this structure:

```
project/
├── config/
│   └── default_config.json
├── data/
│   ├── logs/                    # CSV output
│   └── test_automator_logs/     # Logs & summaries
├── test_automator.py
├── config_loader.py
├── browser_controller.py
└── requirements.txt
```

### 3. Configuration File

Your `config/default_config.json` should have this structure:

```json
{
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
        ]
    }
}
```
### Notes
Ensure that you have the correct directory structure
```
mkdir -p config data/logs
cp default_config.json config/
```

### Basic Examples

```bash
# Run for 30 minutes with Chrome (default)
python test_automator.py --duration 30

# Run for 1 hour in headless mode
python test_automator.py --duration 1h --headless

# Run for 5 minutes with 10 sample in headless mode
python test_automator.py --duration 5m --headless --sample 10

# Run for 5 minutes with 10 sample in headless mode and categories
python test_automator.py --duration 5m --headless --sample 3 --categories "Social Media"

# Test specific categories
python test_automator.py --categories "Development,Social Media" --duration 15

# Random sample of 50 sites
python test_automator.py --sample 50 --duration 30

# Custom time per site (30-120 seconds)
python test_automator.py --min-time 30 --max-time 120 --duration 20
```

### Advanced Examples

```bash
# Firefox with verbose logging
python test_automator.py --browser firefox --verbose --duration 30

# Randomized order, custom output
python test_automator.py --randomize --output custom_results.csv --duration 45

# Headless CI/CD mode
python test_automator.py --headless --duration 60 --output results.csv

# Quick test with sampling
python test_automator.py --sample 20 --min-time 10 --max-time 30 --duration 10
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--duration` | Total test duration (30, 30m, 1h, 90s) | 30 minutes |
| `--config` | Path to config JSON file | config/default_config.json |
| `--browser` | Browser choice (chrome/firefox/edge/safari) | chrome |
| `--categories` | Comma-separated categories to test | All categories |
| `--sample` | Random sample N sites | All sites |
| `--min-time` | Min seconds per site | 60 |
| `--max-time` | Max seconds per site | 120 |
| `--headless` | Run browser invisibly | False |
| `--randomize` | Randomize site visit order | False |
| `--output` | CSV output path | data/logs/test_activity_{date}.csv |
| `--verbose` | Enable verbose logging | False |

## Output Files

### 1. Activity Log (CSV)
Location: `data/logs/test_activity_YYYY-MM-DD_HHMMSS.csv`

Contains:
- Timestamp
- Browser name
- Page title
- URL
- Expected category
- Visit duration
- Platform info

### 2. Summary Report (TXT)
Location: `data/test_automator_logs/summary_YYYYMMDD_HHMMSS.txt`

Contains:
- Test configuration
- Success/failure statistics
- Category distribution
- Failed sites with reasons
- Execution timeline

### 3. Debug Log
Location: `data/test_automator_logs/test_run_YYYYMMDD_HHMMSS.log`

Contains:
- Detailed execution logs
- Error stack traces
- Debug information (with --verbose)

## Troubleshooting

### Browser Driver Issues

If you get driver errors:

```bash
# The script auto-downloads drivers, but you can also install manually:
pip install --upgrade webdriver-manager
```

### Import Errors

```bash
# Ensure all dependencies are installed:
pip install -r requirements.txt

# Or install individually:
pip install selenium webdriver-manager tqdm colorama
```

### Permission Errors

On macOS/Linux, you may need to allow the browser in Security settings:
- Go to System Preferences > Security & Privacy
- Allow the browser to run

### Safari Setup

For Safari on macOS:
1. Enable Remote Automation: Safari > Preferences > Advanced > Show Develop menu
2. Develop > Allow Remote Automation

## Examples by Use Case

### 1. Quick Smoke Test
```bash
python test_automator.py --sample 10 --duration 5 --min-time 10 --max-time 20
```

### 2. Category-Specific Training Data
```bash
python test_automator.py --categories "Development" --duration 30 --randomize
```

### 3. Overnight Comprehensive Test
```bash
python test_automator.py --duration 8h --headless --output overnight_test.csv
```

### 4. CI/CD Pipeline Integration
```bash
python test_automator.py --headless --duration 15 --sample 30 --output ci_test.csv
```

## Tips

- 🎯 Start with `--sample 10` for quick testing
- 🔍 Use `--verbose` when debugging
- ⚡ Use `--headless` for faster execution
- 📊 Check summary reports for insights
- 🔄 Use `--randomize` for varied test patterns
- ⏱️ Adjust `--min-time` and `--max-time` based on your sites

## Requirements

- Python 3.7+
- Chrome/Firefox/Edge/Safari browser installed
- Internet connection

## License

Copyright (c) 2025 Agile Creative Labs Inc
Part of OSCAR v1.0 - On-device System for Computing and Analytics Reporting
