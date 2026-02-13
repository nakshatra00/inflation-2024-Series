"""
CPI Data Scraper from esankhyiki portal
Scrapes Consumer Price Index data using Selenium headless browser
"""

import logging
import time
import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
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
            logging.FileHandler('scraper.log'),
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

# ==================== DRIVER INITIALIZATION ====================
def initialize_driver():
    """Initialize headless Chrome WebDriver"""
    logger.info("=" * 60)
    logger.info("INITIALIZING SELENIUM DRIVER")
    logger.info("=" * 60)
    
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
        logger.debug("Running in HEADLESS mode")
    else:
        logger.debug("Running in GUI mode (for debugging)")
    
    # Additional Chrome options for stability
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("disable-infobars")
    
    logger.debug(f"Chrome options configured: {chrome_options.arguments}")
    
    try:
        # Get chromedriver path and find the actual executable
        chromedriver_path = ChromeDriverManager().install()
        logger.debug(f"ChromeDriver path from manager: {chromedriver_path}")
        
        # The path returned might be a symlink to wrong file, so find the actual executable
        chromedriver_parent = Path(chromedriver_path).parent
        logger.debug(f"Looking for chromedriver in: {chromedriver_parent}")
        
        # Find the actual chromedriver executable (not THIRD_PARTY_NOTICES)
        actual_executable = chromedriver_parent / "chromedriver"
        if actual_executable.exists() and actual_executable.is_file():
            chromedriver_path = str(actual_executable)
            logger.debug(f"✓ Found correct executable: {chromedriver_path}")
        else:
            logger.warning(f"Expected executable not found at {actual_executable}")
            logger.debug(f"Files in directory: {list(chromedriver_parent.iterdir())}")
        
        # Make executable on macOS/Linux
        try:
            os.chmod(chromedriver_path, 0o755)
            logger.debug(f"✓ Set execute permissions on {chromedriver_path}")
        except Exception as e:
            logger.warning(f"Could not set execute permissions: {e}")
        
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("✓ WebDriver initialized successfully")
        
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(IMPLICIT_WAIT)
        logger.debug(f"Page load timeout: {PAGE_LOAD_TIMEOUT}s")
        logger.debug(f"Implicit wait: {IMPLICIT_WAIT}s")
        
        return driver
    except Exception as e:
        logger.error(f"✗ Failed to initialize WebDriver: {e}")
        raise

# ==================== NAVIGATION ====================
def navigate_to_portal(driver):
    """Navigate to CPI portal and wait for page load"""
    logger.info("=" * 60)
    logger.info("NAVIGATING TO CPI PORTAL")
    logger.info("=" * 60)
    
    try:
        logger.info(f"Navigating to: {BASE_URL}")
        driver.get(BASE_URL)
        logger.info("✓ Page loaded")
        
        # Extra wait for React to render
        time.sleep(5)
        
        # DEBUG: Get comprehensive page structure
        logger.info("\n" + "=" * 60)
        logger.info("PAGE STRUCTURE ANALYSIS")
        logger.info("=" * 60)
        
        try:
            # Get all buttons
            buttons = driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"Found {len(buttons)} button elements:")
            for i, btn in enumerate(buttons[:15]):
                text = btn.text.strip() or btn.get_attribute("aria-label") or "No text"
                logger.info(f"  [{i}] Button: {text[:50]}")
            
            # Get all text inputs/dropdowns
            inputs = driver.find_elements(By.TAG_NAME, "input")
            logger.info(f"Found {len(inputs)} input elements:")
            for i, inp in enumerate(inputs[:10]):
                placeholder = inp.get_attribute("placeholder") or inp.get_attribute("aria-label") or "No placeholder"
                value = inp.get_attribute("value") or ""
                logger.info(f"  [{i}] Input: {placeholder[:40]} | value: {value[:30]}")
            
            # Get all labels
            labels = driver.find_elements(By.TAG_NAME, "label")
            logger.info(f"Found {len(labels)} label elements:")
            for i, label in enumerate(labels[:15]):
                text = label.text.strip()
                if text:
                    logger.info(f"  [{i}] Label: {text[:50]}")
            
            # Check for any form controls
            form_controls = driver.find_elements(By.XPATH, "//div[contains(@class, 'MuiFormControl')]")
            logger.info(f"Found {len(form_controls)} MuiFormControl elements")
            
            # Look for any divs with role=combobox
            comboboxes = driver.find_elements(By.XPATH, "//div[@role='combobox']")
            logger.info(f"Found {len(comboboxes)} combobox elements:")
            for i, cb in enumerate(comboboxes[:10]):
                text = cb.text or cb.get_attribute("aria-label") or "No text"
                logger.info(f"  [{i}] Combobox: {text[:50]}")
            
        except Exception as debug_e:
            logger.debug(f"Debug analysis error: {debug_e}")
        
        logger.info("=" * 60 + "\n")
        
        # Wait for main table container to be present
        wait = WebDriverWait(driver, EXPLICIT_WAIT)
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "datatable-wrapper")))
            logger.info("✓ Data table wrapper found")
        except:
            logger.debug("No datatable-wrapper found, trying alternative selectors...")
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//table")))
                logger.info("✓ Table element found")
            except:
                logger.warning("Could not find table, continuing anyway...")
        
        # Wait for first table row to be visible
        try:
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "MuiTableRow-root")))
            logger.info("✓ Table rows detected")
        except:
            logger.debug("Could not find table rows by MuiTableRow-root")
        
        time.sleep(2)  # Extra wait for any animations
        logger.debug("Page fully loaded and stabilized")
        
    except Exception as e:
        logger.error(f"✗ Failed to navigate to portal: {e}")
        raise

# ==================== ELEMENT LOCATORS ====================
def find_element_with_debug(driver, by, value, description=""):
    """Find element with debug logging"""
    try:
        wait = WebDriverWait(driver, EXPLICIT_WAIT)
        element = wait.until(EC.presence_of_element_located((by, value)))
        logger.debug(f"✓ Element found: {description} [{by}={value}]")
        return element
    except Exception as e:
        logger.error(f"✗ Could not find element: {description} [{by}={value}]")
        logger.error(f"  Error: {e}")
        raise

def find_clickable_element_with_debug(driver, by, value, description=""):
    """Find clickable element with debug logging"""
    try:
        wait = WebDriverWait(driver, EXPLICIT_WAIT)
        element = wait.until(EC.element_to_be_clickable((by, value)))
        logger.debug(f"✓ Clickable element found: {description} [{by}={value}]")
        return element
    except Exception as e:
        logger.error(f"✗ Could not find clickable element: {description} [{by}={value}]")
        logger.error(f"  Error: {e}")
        raise

# ==================== FILTER INTERACTION ====================
def try_apply_filters(driver):
    """Attempt to apply filters, but don't fail if UI not found"""
    logger.info("-" * 60)
    logger.info("ATTEMPTING TO APPLY FILTERS (optional)")
    logger.info("-" * 60)
    
    try:
        # Try to find and click Apply button (may not exist if filters are auto-applied)
        apply_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply')]")
        if apply_buttons:
            logger.info(f"Found {len(apply_buttons)} Apply button(s), clicking first...")
            apply_buttons[0].click()
            time.sleep(3)
            logger.info("✓ Apply button clicked")
        else:
            logger.info("ℹ No Apply button found - data may already be filtered")
            
    except Exception as e:
        logger.warning(f"Could not apply filters: {e}")
        logger.info("ℹ Proceeding with current table state")

# ==================== PAGINATION ====================
def get_current_page_info(driver):
    """Get current page information from the pagination control"""
    try:
        # Try to find pagination info (e.g., "1–20 of 4654")
        pagination_info = driver.find_elements(By.XPATH, "//div[contains(@class, 'MuiTablePagination')] | //*[contains(text(), 'of')]")
        
        for elem in pagination_info:
            text = elem.text.strip()
            if 'of' in text:
                logger.debug(f"Pagination info: {text}")
                return text
        
        return "Unknown"
    except:
        return "Unknown"

def has_next_page(driver):
    """Check if there's a next page button available"""
    try:
        # Look for next page button (usually in pagination controls)
        next_buttons = driver.find_elements(By.XPATH, 
            "//button[@aria-label='Next page' or contains(@class, 'MuiIconButton-colorInherit') and ancestor::*[contains(@class, 'MuiTablePagination')]]"
        )
        
        for btn in next_buttons:
            # Check if button is enabled (not disabled)
            if btn.get_attribute("disabled") is None:
                logger.debug("✓ Next page button found and enabled")
                return True
        
        logger.debug("ℹ Next page button not found or disabled")
        return False
    except Exception as e:
        logger.debug(f"Could not determine if next page available: {e}")
        return False

def click_next_page(driver):
    """Click the next page button"""
    try:
        next_buttons = driver.find_elements(By.XPATH, 
            "//button[@aria-label='Next page' or contains(@class, 'MuiIconButton-colorInherit') and ancestor::*[contains(@class, 'MuiTablePagination')]]"
        )
        
        for btn in next_buttons:
            if btn.get_attribute("disabled") is None:
                logger.debug("Clicking next page button...")
                btn.click()
                time.sleep(2)  # Wait for table to load
                logger.info("✓ Moved to next page")
                return True
        
        return False
    except Exception as e:
        logger.warning(f"Could not click next page: {e}")
        return False

# ==================== DATA EXTRACTION ====================
def extract_table_data(driver):
    """Extract all visible table rows into structured format"""
    logger.debug("-" * 60)
    logger.debug("EXTRACTING TABLE DATA")
    logger.debug("-" * 60)
    
    try:
        rows = driver.find_elements(By.CLASS_NAME, "MuiTableRow-root")
        logger.debug(f"Found {len(rows)} rows (including header)")
        
        data = []
        
        # Skip header row (first row)
        for idx, row in enumerate(rows[1:], 1):
            try:
                cells = row.find_elements(By.CLASS_NAME, "MuiTableCell-root")
                logger.debug(f"Row {idx}: Found {len(cells)} cells")
                
                if len(cells) > 0:
                    # Extract cell text
                    row_data = {
                        'base_year': cells[0].text if len(cells) > 0 else '',
                        'series': cells[1].text if len(cells) > 1 else '',
                        'year': cells[2].text if len(cells) > 2 else '',
                        'month': cells[3].text if len(cells) > 3 else '',
                        'state': cells[4].text if len(cells) > 4 else '',
                        'sector': cells[5].text if len(cells) > 5 else '',
                        'division': cells[6].text if len(cells) > 6 else '',
                        'group': cells[7].text if len(cells) > 7 else '',
                        'class': cells[8].text if len(cells) > 8 else '',
                        'sub_class': cells[9].text if len(cells) > 9 else '',
                        'item': cells[10].text if len(cells) > 10 else '',
                        'code': cells[11].text if len(cells) > 11 else '',
                        'index': cells[12].text if len(cells) > 12 else '',
                        'inflation': cells[13].text if len(cells) > 13 else '',
                        'imputation': cells[14].text if len(cells) > 14 else '',
                    }
                    data.append(row_data)
                    logger.debug(f"  Row {idx}: {row_data['item'][:30]}... | Index: {row_data['index']}")
                    
            except Exception as e:
                logger.warning(f"  Failed to extract row {idx}: {e}")
                continue
        
        logger.info(f"✓ Extracted {len(data)} data rows")
        return data
        
    except Exception as e:
        logger.error(f"✗ Failed to extract table data: {e}")
        raise

# ==================== MAIN EXECUTION ====================
def main():
    """Main scraper execution - scrape all pages without filters"""
    logger.info("\n" + "=" * 60)
    logger.info("CPI DATA SCRAPER - MAIN EXECUTION START")
    logger.info("=" * 60 + "\n")
    
    driver = None
    all_data = []
    page_count = 0
    
    try:
        # Step 1: Initialize driver
        driver = initialize_driver()
        
        # Step 2: Navigate to portal
        navigate_to_portal(driver)
        
        # Step 3: Try to apply filters (optional - if they fail, we proceed anyway)
        try:
            try_apply_filters(driver)
        except Exception as e:
            logger.warning(f"Could not apply filters: {e}")
            logger.info("ℹ Proceeding with current table state (may have default filters)")
        
        # Step 4: Extract data from all pages with pagination
        logger.info("\n" + "=" * 60)
        logger.info("DATA EXTRACTION PHASE - PAGINATING THROUGH ALL PAGES")
        logger.info("=" * 60 + "\n")
        
        max_pages = 250  # Safety limit to prevent infinite loops
        
        while page_count < max_pages:
            page_count += 1
            
            logger.info(f"\n{'─' * 60}")
            logger.info(f"PAGE {page_count}")
            logger.info(f"Pagination info: {get_current_page_info(driver)}")
            logger.info(f"{'─' * 60}")
            
            # Extract data from current page
            try:
                page_data = extract_table_data(driver)
                all_data.extend(page_data)
                logger.info(f"✓ Extracted {len(page_data)} records from page {page_count}")
                logger.info(f"  Total so far: {len(all_data)} records")
            except Exception as e:
                logger.warning(f"Failed to extract data from page {page_count}: {e}")
                break
            
            # Check if there's a next page
            if has_next_page(driver):
                if click_next_page(driver):
                    logger.info(f"✓ Moving to page {page_count + 1}")
                    time.sleep(1)  # Extra wait before next extraction
                else:
                    logger.info("Could not click next page, stopping pagination")
                    break
            else:
                logger.info("✓ Reached last page (no next page button)")
                break
        
        logger.info(f"\n✓ Total records scraped: {len(all_data)} across {page_count} pages")
        
        # Step 5: Save data
        logger.info("\n" + "=" * 60)
        logger.info("SAVING DATA")
        logger.info("=" * 60 + "\n")
        
        if all_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"cpi_data_{timestamp}.csv"
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys() if all_data else [])
                writer.writeheader()
                writer.writerows(all_data)
            
            logger.info(f"✓ Data saved to: {output_file}")
            logger.info(f"  Total records: {len(all_data)}")
            logger.info(f"  Pages scraped: {page_count}")
        else:
            logger.warning("No data was scraped - check for errors above")
        
    except Exception as e:
        logger.error(f"\n✗ FATAL ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if driver:
            try:
                screenshot_file = f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_file)
                logger.error(f"✓ Screenshot saved: {screenshot_file}")
            except:
                pass
        raise
        
    finally:
        if driver:
            logger.info("\nClosing WebDriver...")
            try:
                driver.quit()
                logger.info("✓ WebDriver closed")
            except:
                pass
        
        logger.info("\n" + "=" * 60)
        logger.info("CPI DATA SCRAPER - EXECUTION COMPLETE")
        logger.info("=" * 60 + "\n")

if __name__ == "__main__":
    main()
