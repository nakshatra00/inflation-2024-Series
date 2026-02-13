# CPI Data Scraper

A Selenium-based web scraper for extracting Consumer Price Index (CPI) data from the esankhyiki portal (Ministry of Statistics & Programme Implementation, Government of India).

## Project Structure

```
scraper/
├── scraper.py           # Main scraper script with all functionality
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Features

- **Headless Browser Automation**: Uses Selenium with Chrome WebDriver in headless mode
- **Filter Support**:
  - Base Year: 2024
  - State: All India
  - Sector: Combined
  - Items: Select All
- **Data Extraction**: Parses table data into structured CSV format
- **Debug Logging**: Comprehensive logging at every step (file + console)
- **Error Handling**: Screenshot capture on errors, retry logic
- **Data Export**: Saves to CSV with timestamp

## Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- macOS (tested), Linux, or Windows

### Setup Steps

1. **Navigate to scraper directory**:
   ```bash
   cd /Users/nakshatragupta/Documents/Coding/inflation-2024-Series/scraper
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Run the Scraper

```bash
python3 scraper.py
```

### Output

- **CSV File**: `cpi_data_YYYYMMDD_HHMMSS.csv` - Contains all scraped records
- **Log File**: `scraper.log` - Detailed execution logs with debug statements
- **Console Output**: Real-time progress (mirrored to log file)
- **Error Screenshots**: `error_screenshot_YYYYMMDD_HHMMSS.png` (if errors occur)

## Debug Output Example

```
============================================================
CPI DATA SCRAPER - MAIN EXECUTION START
============================================================

============================================================
INITIALIZING SELENIUM DRIVER
============================================================
2026-02-12 10:30:45,123 - DEBUG - [initialize_driver] Running in HEADLESS mode
2026-02-12 10:30:45,234 - DEBUG - [initialize_driver] Chrome options configured: [...]
2026-02-12 10:30:47,456 - INFO - [initialize_driver] ✓ WebDriver initialized successfully
...

============================================================
DATA EXTRACTION PHASE
============================================================
2026-02-12 10:31:20,567 - DEBUG - [extract_table_data] Found 21 rows (including header)
2026-02-12 10:31:20,568 - DEBUG - [extract_table_data] Row 1: Found 15 cells
2026-02-12 10:31:20,569 - DEBUG - [extract_table_data]   Row 1: Rice... | Index: 102.22
...

✓ Total records scraped: 20
```

## Configuration

Edit the constants at the top of `scraper.py`:

```python
BASE_URL = "https://esankhyiki.mospi.gov.in/macroindicators"
HEADLESS = True              # Set to False to see browser in action
IMPLICIT_WAIT = 10           # Wait for elements (seconds)
EXPLICIT_WAIT = 20           # Wait for conditions (seconds)
PAGE_LOAD_TIMEOUT = 30       # Page load timeout (seconds)
```

## Troubleshooting

### Issue: "WebDriver initialization failed"
- **Solution**: Ensure you have Chrome browser installed. WebDriver manager will auto-download ChromeDriver.

### Issue: "Could not find element"
- **Solution**: Check `scraper.log` for XPath details. Portal DOM might have changed. Update selectors in the script.

### Issue: Timeout on filter selection
- **Solution**: Increase `EXPLICIT_WAIT` value in constants. Portal might be slow.

### Issue: Table not updating after Apply click
- **Solution**: Increase sleep time in `click_apply_button()` function. Portal JS rendering might be slow.

## Debug Logging Levels

The script includes debug statements for:
- ✓ Driver initialization and configuration
- ✓ Page navigation and wait conditions
- ✓ Element locator attempts and success
- ✓ Filter selection and verification
- ✓ Data extraction row-by-row progress
- ✓ Error details and stack traces
- ✓ File I/O operations

Check `scraper.log` for complete execution details.

## Next Steps

1. **Pagination Support**: Add logic to navigate through all 233 pages
2. **Data Validation**: Validate CPI values, dates, and hierarchies
3. **Database Integration**: Store to PostgreSQL/SQLite instead of CSV
4. **Scheduling**: Set up cron job for daily/weekly scraping
5. **Notifications**: Email alerts on successful/failed runs

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| selenium | 4.15.2 | Web automation |
| webdriver-manager | 4.0.1 | Chrome driver management |
| pandas | 2.1.4 | Data manipulation (optional for now) |
| python-dotenv | 1.0.0 | Environment variables (future use) |

## Author

Created for inflation-2024-Series project

## License

Project license applies
