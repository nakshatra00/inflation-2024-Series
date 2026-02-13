"""
CPI Data Scraper - Pagination Version
Scrapes ALL CPI data using Selenium by paginating through all pages
Skips filter selection and focuses on data extraction + pagination
"""

import logging
import time
import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# ==================== LOGGING SETUP ====================
def setup_logging():
    """Configure logging with debug statements"""
    log_format = '%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s'
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler('scraper_pagination.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ==================== CONSTANTS ====================
BASE_URL = "https://esankhyiki.mospi.gov.in/macroindicators?product=cpi"
HEADLESS = True
IMPLICIT_WAIT = 10
EXPLICIT_WAIT = 20
PAGE_LOAD_TIMEOUT = 30
MAX_PAGES = 5000  # Safety limit to avoid infinite loops
SCRIPT_TIMEOUT_SECONDS = 3600  # 1 hour timeout for entire script
PAGE_TIMEOUT_SECONDS = 60  # 60 seconds per page before timeout

# Progress tracking
pages_scraped = 0
records_scraped = 0
start_time = None

# ==================== PROGRESS TRACKING ====================
def print_progress(page_num, records, elapsed_sec):
    """Print formatted progress information"""
    avg_per_page = records / max(page_num, 1)
    rate = page_num / max(elapsed_sec, 1)
    
    progress_bar = f"""
{'='*80}
📊 SCRAPING PROGRESS
{'='*80}
📄 Pages scraped:     {page_num:,}
📋 Total records:     {records:,}
⏱️  Elapsed time:      {int(elapsed_sec // 60)}m {int(elapsed_sec % 60)}s
📈 Avg records/page:  {avg_per_page:.1f}
⚡ Pages/min:         {rate * 60:.2f}
⏳ Est. time remain:   {int((233 - page_num) / max(rate * 60, 0.1))}m (for 233 pages)
{'='*80}
"""
    print(progress_bar)
    logger.info(progress_bar)

# ==================== DRIVER INITIALIZATION ====================
def initialize_driver():
    """Initialize headless Chrome WebDriver"""
    logger.info("=" * 80)
    logger.info("INITIALIZING SELENIUM DRIVER FOR PAGINATION SCRAPER")
    logger.info("=" * 80)
    
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
        logger.debug("Running in HEADLESS mode")
    
    # Additional Chrome options
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("disable-infobars")
    
    logger.debug(f"Chrome options: {chrome_options.arguments}")
    
    try:
        chromedriver_path = ChromeDriverManager().install()
        logger.debug(f"ChromeDriver path: {chromedriver_path}")
        
        # Handle symlink issue
        chromedriver_parent = Path(chromedriver_path).parent
        actual_executable = chromedriver_parent / "chromedriver"
        if actual_executable.exists():
            chromedriver_path = str(actual_executable)
            logger.debug(f"Using actual executable: {chromedriver_path}")
        
        # Set permissions
        try:
            os.chmod(chromedriver_path, 0o755)
            logger.debug("✓ Execute permissions set")
        except:
            pass
        
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("✓ WebDriver initialized successfully")
        
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(IMPLICIT_WAIT)
        
        return driver
    except Exception as e:
        logger.error(f"✗ Failed to initialize WebDriver: {e}")
        raise

# ==================== NAVIGATION ====================
def navigate_to_portal(driver):
    """Navigate to CPI portal"""
    logger.info("=" * 80)
    logger.info("NAVIGATING TO CPI PORTAL")
    logger.info("=" * 80)
    
    try:
        logger.info(f"URL: {BASE_URL}")
        driver.get(BASE_URL)
        logger.info("✓ Page loaded")
        
        # Wait for table to load
        time.sleep(5)
        
        wait = WebDriverWait(driver, EXPLICIT_WAIT)
        try:
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "MuiTableRow-root")))
            rows_count = len(driver.find_elements(By.CLASS_NAME, "MuiTableRow-root"))
            logger.info(f"✓ Table rows detected: {rows_count} rows on first page")
        except Exception as e:
            logger.warning(f"Could not find table rows: {e}")
        
        time.sleep(2)
        logger.debug("Page fully loaded")
        
    except Exception as e:
        logger.error(f"✗ Failed to navigate: {e}")
        raise

# ==================== TABLE DATA EXTRACTION ====================
def extract_table_data(driver, page_num=1):
    """Extract all visible table rows into structured format"""
    logger.debug("-" * 80)
    logger.debug(f"EXTRACTING TABLE DATA FROM PAGE {page_num}")
    logger.debug("-" * 80)
    
    try:
        rows = driver.find_elements(By.CLASS_NAME, "MuiTableRow-root")
        logger.debug(f"Found {len(rows)} total rows (including header)")
        
        data = []
        
        # Skip header row (first row)
        for idx, row in enumerate(rows[1:], 1):
            try:
                cells = row.find_elements(By.CLASS_NAME, "MuiTableCell-root")
                
                if len(cells) >= 15:  # We expect 15 columns
                    row_data = {
                        'base_year': cells[0].text.strip() if len(cells) > 0 else '',
                        'series': cells[1].text.strip() if len(cells) > 1 else '',
                        'year': cells[2].text.strip() if len(cells) > 2 else '',
                        'month': cells[3].text.strip() if len(cells) > 3 else '',
                        'state': cells[4].text.strip() if len(cells) > 4 else '',
                        'sector': cells[5].text.strip() if len(cells) > 5 else '',
                        'division': cells[6].text.strip() if len(cells) > 6 else '',
                        'group': cells[7].text.strip() if len(cells) > 7 else '',
                        'class': cells[8].text.strip() if len(cells) > 8 else '',
                        'sub_class': cells[9].text.strip() if len(cells) > 9 else '',
                        'item': cells[10].text.strip() if len(cells) > 10 else '',
                        'code': cells[11].text.strip() if len(cells) > 11 else '',
                        'index': cells[12].text.strip() if len(cells) > 12 else '',
                        'inflation': cells[13].text.strip() if len(cells) > 13 else '',
                        'imputation': cells[14].text.strip() if len(cells) > 14 else '',
                    }
                    data.append(row_data)
                    
                    if idx <= 3 or idx % 20 == 0:  # Log first 3 and every 20th
                        logger.debug(f"  Row {idx}: {row_data['item'][:40]}")
                    
            except Exception as e:
                logger.warning(f"  Row {idx}: Failed to extract - {e}")
                continue
        
        logger.info(f"✓ Extracted {len(data)} data rows from page {page_num}")
        return data
        
    except Exception as e:
        logger.error(f"✗ Failed to extract table data: {e}")
        raise

# ==================== PAGINATION ====================
def find_page_input_field(driver):
    """Find the page number input field in pagination"""
    try:
        # The pagination structure has an input field for entering page numbers
        # Look for input with type="text" inside pagination-box
        selectors = [
            "//input[@type='text'][contains(@min, '1') and contains(@max, '44')]",  # Page input
            "//div[@class='pagination-box']//input[@type='text']",
            "//div[@class='table-pagination']//input[@type='text']",
            "//input[@type='text']",
        ]
        
        for selector in selectors:
            try:
                input_field = driver.find_element(By.XPATH, selector)
                if input_field.is_displayed():
                    logger.debug(f"✓ Found page input field via: {selector}")
                    return input_field
            except:
                continue
        
        logger.error("Could not find page input field")
        return None
        
    except Exception as e:
        logger.error(f"Error finding page input: {e}")
        return None

def find_next_button(driver):
    """Find the next page button in pagination"""
    try:
        # Look for the right arrow button (→) in pagination
        selectors = [
            "//div[@class='pagination-box']//button[contains(text(), '→')]",
            "//button[contains(text(), '→')]",
            "//div[@class='table-pagination']//button[string-length(normalize-space())=1][last()-1]",  # Second to last button
        ]
        
        for selector in selectors:
            try:
                button = driver.find_element(By.XPATH, selector)
                if button.is_displayed() and button.is_enabled():
                    logger.debug(f"✓ Found next button via: {selector}")
                    return button
            except:
                continue
        
        logger.debug("Could not find next button")
        return None
        
    except Exception as e:
        logger.error(f"Error finding next button: {e}")
        return None

def navigate_to_next_page(driver, current_page):
    """Navigate to next page using pagination controls with timeout"""
    page_start_time = time.time()
    
    logger.info("-" * 80)
    logger.info(f"NAVIGATING FROM PAGE {current_page} TO PAGE {current_page + 1}")
    logger.info("-" * 80)
    
    try:
        # Method 1: Try clicking next button (→)
        logger.debug("Method 1: Attempting to click next button (→)...")
        next_button = find_next_button(driver)
        
        if next_button:
            # Check if button is disabled (end of pagination)
            if next_button.get_attribute("disabled") is not None:
                logger.info("✗ Next button is disabled - reached end of pagination")
                return False
            
            # Check timeout
            elapsed = time.time() - page_start_time
            if elapsed > PAGE_TIMEOUT_SECONDS:
                logger.warning(f"⏱️  PAGE TIMEOUT: {elapsed:.1f}s exceeded {PAGE_TIMEOUT_SECONDS}s limit")
                return False
            
            # Click next button
            logger.debug("Clicking next button...")
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            time.sleep(0.5)
            next_button.click()
            
            # Wait for page to load
            time.sleep(2)
            
            # Wait for new table rows to appear
            wait = WebDriverWait(driver, EXPLICIT_WAIT)
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "MuiTableRow-root")))
            
            elapsed = time.time() - page_start_time
            logger.info(f"✓ Successfully navigated to page {current_page + 1} via next button ({elapsed:.1f}s)")
            return True
        
        # Check timeout
        elapsed = time.time() - page_start_time
        if elapsed > PAGE_TIMEOUT_SECONDS:
            logger.warning(f"⏱️  PAGE TIMEOUT: {elapsed:.1f}s exceeded {PAGE_TIMEOUT_SECONDS}s limit")
            return False
        
        # Method 2: Try using page input field
        logger.debug("Method 2: Next button not found, trying page input field...")
        page_input = find_page_input_field(driver)
        
        if page_input:
            logger.debug(f"Found page input field. Entering page number {current_page + 1}...")
            page_input.clear()
            time.sleep(0.3)
            page_input.send_keys(str(current_page + 1))
            time.sleep(0.3)
            page_input.send_keys(Keys.RETURN)
            
            # Wait for page to load
            time.sleep(3)
            
            # Wait for new table rows to appear
            wait = WebDriverWait(driver, EXPLICIT_WAIT)
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "MuiTableRow-root")))
            
            logger.info(f"✓ Successfully navigated to page {current_page + 1} via page input")
            return True
        
        logger.warning("✗ Neither next button nor page input field found")
        return False
        
    except Exception as e:
        logger.error(f"✗ Failed to navigate to next page: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

# ==================== MAIN EXECUTION ====================
def main():
    """Main scraper execution with pagination"""
    global start_time
    start_time = time.time()
    
    logger.info("\n" + "=" * 80)
    logger.info("CPI DATA SCRAPER - PAGINATION VERSION")
    logger.info(f"Script start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Script timeout: {SCRIPT_TIMEOUT_SECONDS}s ({SCRIPT_TIMEOUT_SECONDS/60:.1f} min)")
    logger.info(f"Page timeout: {PAGE_TIMEOUT_SECONDS}s")
    logger.info("=" * 80 + "\n")
    
    driver = None
    all_data = []
    current_page = 1
    total_pages_scraped = 0
    
    try:
        # Initialize driver
        driver = initialize_driver()
        
        # Navigate to portal
        navigate_to_portal(driver)
        
        # ========== PAGINATION LOOP ==========
        logger.info("=" * 80)
        logger.info("STARTING PAGINATION LOOP")
        logger.info("=" * 80)
        
        with tqdm(total=233, desc="Scraping pages", unit="page") as pbar:
            while current_page <= MAX_PAGES:
                # Check overall script timeout
                elapsed_total = time.time() - start_time
                if elapsed_total > SCRIPT_TIMEOUT_SECONDS:
                    logger.error(f"\n⏱️  SCRIPT TIMEOUT: {int(elapsed_total)}s exceeded {SCRIPT_TIMEOUT_SECONDS}s limit")
                    logger.error("Saving checkpoint and exiting...")
                    break
                
                logger.info(f"\n>>> PROCESSING PAGE {current_page}")
                
                try:
                    # Extract data from current page
                    page_start = time.time()
                    page_data = extract_table_data(driver, current_page)
                    page_time = time.time() - page_start
                    
                    all_data.extend(page_data)
                    total_pages_scraped += 1
                    
                    # Update progress bar
                    pbar.update(1)
                    pbar.set_description(f"Scraping pages | {len(all_data)} records")
                    
                    # Print progress every 10 pages
                    if total_pages_scraped % 10 == 0:
                        elapsed_total = time.time() - start_time
                        print_progress(total_pages_scraped, len(all_data), elapsed_total)
                    
                    logger.info(f"  ✓ Page {current_page}: {len(page_data)} records ({page_time:.1f}s)")
                    logger.info(f"  📊 Total records: {len(all_data):,}")
                    
                    # Try to go to next page
                    if not navigate_to_next_page(driver, current_page):
                        logger.info("\n" + "=" * 80)
                        logger.info("PAGINATION COMPLETE - Reached end of data")
                        logger.info("=" * 80)
                        break
                    
                    current_page += 1
                    
                    # Save checkpoint every 50 pages
                    if total_pages_scraped % 50 == 0:
                        logger.info(f"\n>>> CHECKPOINT: Saving backup after {total_pages_scraped} pages...")
                        checkpoint_file = f"checkpoint_page_{total_pages_scraped}.csv"
                        with open(checkpoint_file, 'w', newline='', encoding='utf-8') as f:
                            if all_data:
                                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                                writer.writeheader()
                                writer.writerows(all_data)
                        logger.info(f"  ✓ Checkpoint saved: {checkpoint_file}")
                    
                except Exception as e:
                    logger.error(f"Error processing page {current_page}: {e}")
                    logger.info("Continuing to next page...")
                    current_page += 1
                    continue
        
        # ========== SAVE FINAL DATA ==========
        logger.info("\n" + "=" * 80)
        logger.info("SAVING FINAL DATA")
        logger.info("=" * 80 + "\n")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"cpi_data_full_{timestamp}.csv"
        
        elapsed_total = time.time() - start_time
        logger.info(f"\n✓ Output file: {output_file}")
        logger.info(f"✓ Total records: {len(all_data):,}")
        logger.info(f"✓ Total pages scraped: {total_pages_scraped}")
        logger.info(f"✓ Total time: {int(elapsed_total // 60)}m {int(elapsed_total % 60)}s")
        logger.info(f"✓ Avg records/page: {len(all_data) / max(total_pages_scraped, 1):.1f}")
        
        if all_data:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)
            
            file_size_mb = os.path.getsize(output_file) / 1024 / 1024
            logger.info(f"✓ Data saved to: {output_file}")
            logger.info(f"✓ File size: {file_size_mb:.2f} MB")
            
            # Print final progress
            print_progress(total_pages_scraped, len(all_data), elapsed_total)
        else:
            logger.error("✗ No data collected!")
        
    except Exception as e:
        logger.error(f"\n✗ FATAL ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        if driver:
            try:
                screenshot_file = f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_file)
                logger.error(f"Screenshot saved: {screenshot_file}")
            except:
                pass
        raise
        
    finally:
        if driver:
            logger.info("\nClosing WebDriver...")
            driver.quit()
            logger.info("✓ WebDriver closed")
        
        elapsed_total = time.time() - start_time
        logger.info("\n" + "=" * 80)
        logger.info("CPI DATA SCRAPER - EXECUTION COMPLETE")
        logger.info(f"📊 Final Results:")
        logger.info(f"   Records scraped: {len(all_data):,}")
        logger.info(f"   Pages processed: {total_pages_scraped}")
        logger.info(f"   Total time: {int(elapsed_total // 60)}m {int(elapsed_total % 60)}s")
        logger.info("=" * 80 + "\n")

if __name__ == "__main__":
    main()
