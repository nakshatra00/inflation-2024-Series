"""
CPI Data Scraper - Smart Version with State Filter
Uses State dropdown to select "All India" FIRST, then paginates
This should reduce data load significantly
"""

import logging
import time
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# ==================== LOGGING ====================
def setup_logging():
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[logging.StreamHandler(), logging.FileHandler('scraper_state_filter.log')]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ==================== CONSTANTS ====================
BASE_URL = "https://esankhyiki.mospi.gov.in/macroindicators?product=cpi"
HEADLESS = True

def init_driver():
    """Initialize Chrome WebDriver"""
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
    
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        from pathlib import Path
        chromedriver_path = ChromeDriverManager().install()
        
        # Handle symlink issue - find the actual chromedriver executable
        chromedriver_parent = Path(chromedriver_path).parent
        actual_executable = chromedriver_parent / "chromedriver"
        if actual_executable.exists():
            chromedriver_path = str(actual_executable)
            logger.info(f"Using actual executable: {chromedriver_path}")
        
        # Set execute permissions
        os.chmod(chromedriver_path, 0o755)
        
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        logger.info("✓ WebDriver initialized")
        return driver
    except Exception as e:
        logger.error(f"✗ Failed to init driver: {e}")
        raise

def select_filter_value(driver, filter_label, value):
    """Open a dropdown in the DESKTOP sidebar by label and select a value.
    
    MUI Select components use mousedown events (not click) to open.
    We dispatch a proper mousedown event via JavaScript.
    
    Args:
        driver: Selenium WebDriver
        filter_label: Label text to find (e.g. "State", "Sector")
        value: Option text to select (e.g. "All India", "Combined")
    Returns:
        True if selection succeeded, False otherwise
    """
    try:
        logger.info(f"Finding '{filter_label}' dropdown in desktop sidebar...")
        
        # Find all comboboxes in the DESKTOP sidebar
        combos = driver.find_elements(
            By.CSS_SELECTOR, "div.filter-sidebar div[role='combobox']"
        )
        
        # Identify the target dropdown by matching its parent FormControl's label
        target_combo = None
        for i, cb in enumerate(combos):
            try:
                parent_fc = cb.find_element(By.XPATH, "./ancestor::div[contains(@class, 'MuiFormControl-root')]")
                # Try multiple ways to get the label text:
                # 1. label element's .text
                # 2. label element's textContent (JS) — works even if visually hidden
                # 3. legend > span inside fieldset
                label_text = ""
                try:
                    label_el = parent_fc.find_element(By.TAG_NAME, "label")
                    label_text = label_el.text.strip()
                    if not label_text:
                        label_text = driver.execute_script(
                            "return arguments[0].textContent;", label_el
                        ).strip()
                except:
                    pass
                if not label_text:
                    try:
                        legend_span = parent_fc.find_element(By.CSS_SELECTOR, "fieldset legend span")
                        label_text = legend_span.text.strip()
                        if not label_text:
                            label_text = driver.execute_script(
                                "return arguments[0].textContent;", legend_span
                            ).strip()
                    except:
                        pass
                
                if filter_label in label_text:
                    target_combo = cb
                    logger.info(f"Found '{filter_label}' combobox at index {i}, "
                                f"label='{label_text}', "
                                f"aria-controls={cb.get_attribute('aria-controls')}")
                    break
            except:
                continue
        
        if not target_combo:
            # Debug: log all labels we found
            logger.error(f"Could not find '{filter_label}' combobox in desktop sidebar. "
                         f"Total comboboxes found: {len(combos)}")
            for i, cb in enumerate(combos):
                try:
                    parent_fc = cb.find_element(By.XPATH, "./ancestor::div[contains(@class, 'MuiFormControl-root')]")
                    lbl = ""
                    try:
                        label_el = parent_fc.find_element(By.TAG_NAME, "label")
                        lbl = driver.execute_script("return arguments[0].textContent;", label_el).strip()
                    except:
                        pass
                    logger.error(f"  [{i}] label='{lbl}', text='{cb.text.strip()}', displayed={cb.is_displayed()}")
                except:
                    logger.error(f"  [{i}] (could not inspect)")
            return False
        
        # Scroll into view
        driver.execute_script("arguments[0].scrollIntoView(true);", target_combo)
        time.sleep(0.5)
        
        # MUI Select opens on mousedown, NOT click
        logger.info(f"Dispatching mousedown event on '{filter_label}' combobox...")
        driver.execute_script("""
            var evt = new MouseEvent('mousedown', {
                bubbles: true, cancelable: true, view: window
            });
            arguments[0].dispatchEvent(evt);
        """, target_combo)
        time.sleep(2)
        
        # Check if listbox popup appeared
        listboxes = driver.find_elements(By.CSS_SELECTOR, "ul[role='listbox']")
        logger.info(f"Listboxes found after mousedown: {len(listboxes)}")
        
        if not listboxes:
            logger.warning("No listbox appeared, trying regular click as fallback...")
            target_combo.click()
            time.sleep(2)
            listboxes = driver.find_elements(By.CSS_SELECTOR, "ul[role='listbox']")
        
        if not listboxes:
            logger.error("Dropdown popup did not appear at all!")
            return False
        
        # Find the target value in the listbox options
        target_option = None
        for lb in listboxes:
            items = lb.find_elements(By.TAG_NAME, "li")
            logger.info(f"Listbox has {len(items)} items, first few: "
                        f"{[it.text.strip()[:25] for it in items[:5]]}")
            for it in items:
                if value in it.text:
                    target_option = it
                    break
            if target_option:
                break
        
        if not target_option:
            logger.error(f"Could not find '{value}' option in '{filter_label}' dropdown")
            return False
        
        logger.info(f"Found '{value}', clicking it...")
        driver.execute_script("arguments[0].click();", target_option)
        time.sleep(1)
        
        # Verify selection — combobox text should now show the value
        new_text = target_combo.text.strip()
        logger.info(f"Combobox text after selection: '{new_text}'")
        
        # Close dropdown with Escape
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.5)
        
        logger.info(f"✓ Selected '{value}' in '{filter_label}' dropdown")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to select '{value}' in '{filter_label}': {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def click_apply_button(driver):
    """Click Apply button in the DESKTOP sidebar to apply filters"""
    try:
        logger.info("Looking for Apply button in desktop sidebar...")
        
        # Target the Apply button inside the DESKTOP .filter-sidebar only
        apply_buttons = driver.find_elements(
            By.XPATH, 
            "//div[@class='filter-sidebar']//button[contains(text(), 'Apply')]"
        )
        
        if not apply_buttons:
            # Fallback: try filter-buttons class inside filter-sidebar
            apply_buttons = driver.find_elements(
                By.XPATH,
                "//div[@class='filter-sidebar']//div[contains(@class, 'filter-buttons')]//button[1]"
            )
        
        if apply_buttons:
            logger.info(f"Found {len(apply_buttons)} Apply button(s) in desktop sidebar")
            driver.execute_script("arguments[0].scrollIntoView(true);", apply_buttons[0])
            time.sleep(0.5)
            
            logger.info("Clicking Apply button with JavaScript...")
            driver.execute_script("arguments[0].click();", apply_buttons[0])
            
            # Wait for data to reload — watch for loading indicator to appear and disappear
            logger.info("Waiting for data to reload after Apply...")
            time.sleep(2)
            
            # Check if a loading spinner appeared and wait for it to go away
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "MuiCircularProgress-root"))
                )
                logger.info("Loading spinner detected, waiting for it to disappear...")
                WebDriverWait(driver, 30).until_not(
                    EC.presence_of_element_located((By.CLASS_NAME, "MuiCircularProgress-root"))
                )
                logger.info("Loading complete!")
            except:
                pass  # No spinner, data may have loaded quickly
            
            time.sleep(2)  # Extra buffer
            logger.info("✓ Apply button clicked and data reloaded")
            return True
        
        logger.warning("Could not find Apply button in desktop sidebar")
        return False
    except Exception as e:
        logger.error(f"✗ Failed to click Apply: {e}")
        return False

def extract_page_data(driver):
    """Extract current page data"""
    try:
        # Wait for table to be present
        wait = WebDriverWait(driver, 20)
        rows = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "MuiTableRow-root")))
        
        data = []
        # Skip header row (first one)
        for row in rows[1:]:
            cells = row.find_elements(By.CLASS_NAME, "MuiTableCell-root")
            if len(cells) >= 15:
                record = {
                    'base_year': cells[0].text,
                    'series': cells[1].text,
                    'year': cells[2].text,
                    'month': cells[3].text,
                    'state': cells[4].text,
                    'sector': cells[5].text,
                    'division': cells[6].text,
                    'group': cells[7].text,
                    'class': cells[8].text,
                    'sub_class': cells[9].text,
                    'item': cells[10].text,
                    'code': cells[11].text,
                    'index': cells[12].text,
                    'inflation': cells[13].text,
                    'imputation': cells[14].text,
                }
                data.append(record)
        
        logger.info(f"Extracted {len(data)} records from current page")
        return data
        
    except Exception as e:
        logger.error(f"✗ Failed to extract data: {e}")
        return []

def get_current_page_info(driver):
    """Get current page number and total pages"""
    try:
        # Find the page input field
        page_inputs = driver.find_elements(By.XPATH, "//input[@type='text' and @min='1']")
        if page_inputs:
            current = page_inputs[0].get_attribute('value')
            max_pages = page_inputs[0].get_attribute('max')
            
            # Also try to get from the text
            info_text = driver.find_element(By.XPATH, "//p[contains(text(), 'of')]").text
            logger.info(f"Page info: {info_text}")
            return int(current), int(max_pages)
        return 1, 1
    except Exception as e:
        logger.error(f"✗ Failed to get page info: {e}")
        return 1, 1

def go_to_page(driver, page_num):
    """Navigate to specific page using page input.
    Uses JavaScript to set the value and dispatch events,
    since the MUI input may not be directly interactable via Selenium.
    """
    try:
        page_inputs = driver.find_elements(By.XPATH, "//input[@type='text' and @min='1']")
        if page_inputs:
            page_input = page_inputs[0]
            
            # Use JS to set value and trigger React's onChange
            driver.execute_script("""
                var input = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(input, arguments[1]);
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            """, page_input, str(page_num))
            time.sleep(0.3)
            
            # Simulate Enter key to trigger navigation
            driver.execute_script("""
                var input = arguments[0];
                input.dispatchEvent(new KeyboardEvent('keydown', {
                    key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
                }));
            """, page_input)
            time.sleep(2)
            
            logger.info(f"✓ Navigated to page {page_num}")
            return True
        return False
    except Exception as e:
        logger.error(f"✗ Failed to navigate to page {page_num}: {e}")
        return False

def main():
    """Main execution"""
    logger.info("\n" + "="*80)
    logger.info("CPI DATA SCRAPER - STATE FILTER VERSION (DESKTOP SIDEBAR FIX)")
    logger.info("="*80)
    
    driver = None
    all_data = []
    
    try:
        driver = init_driver()
        logger.info(f"Navigating to {BASE_URL}...")
        driver.get(BASE_URL)
        
        # Wait for table to actually load
        logger.info("Waiting for table to load...")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "MuiTableRow-root"))
            )
            logger.info("Table loaded!")
        except:
            logger.warning("Table did not load in 30s, continuing anyway...")
        time.sleep(3)
        
        # Get BEFORE page count
        _, max_pages_before = get_current_page_info(driver)
        logger.info(f"\n[BEFORE FILTER] Total pages: {max_pages_before}")
        
        # Apply filters: State="All India" + Sector="Combined"
        logger.info("\n--- Applying filters (targeting DESKTOP sidebar) ---")
        filter_success = False
        
        state_ok = select_filter_value(driver, "State", "All India")
        sector_ok = select_filter_value(driver, "Sector", "Combined")
        
        if state_ok or sector_ok:
            logger.info(f"Filters selected — State: {'✓' if state_ok else '✗'}, Sector: {'✓' if sector_ok else '✗'}")
            if click_apply_button(driver):
                filter_success = True
                logger.info("✓ Filters applied successfully!")
            else:
                logger.warning("✗ Apply button click failed")
        else:
            logger.warning("✗ Failed to select any filters")
        
        # Get AFTER page count — this is the KEY verification
        time.sleep(2)
        current_page, max_pages = get_current_page_info(driver)
        logger.info(f"\n[AFTER FILTER] Total pages: {max_pages}")
        
        if filter_success and max_pages < max_pages_before:
            logger.info(f"✓✓ FILTER WORKED! Pages reduced from {max_pages_before} to {max_pages}")
        elif filter_success:
            logger.warning(f"⚠ Filter reported success but pages unchanged: {max_pages_before} → {max_pages}")
            logger.warning("⚠ The filter may not have actually applied. Continuing anyway...")
        else:
            logger.warning("⚠ Filter failed. Will scrape unfiltered data.")
        
        # Extract first page
        logger.info(f"\nExtracting page 1/{max_pages}...")
        page_data = extract_page_data(driver)
        all_data.extend(page_data)
        
        # Scrape ALL pages (no artificial limit)
        total_pages = max_pages
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting full extraction: {total_pages} pages")
        logger.info(f"{'='*60}")
        
        checkpoint_interval = 50  # Save every 50 pages
        output_base = f"cpi_data_allIndia_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        for page in range(2, total_pages + 1):
            logger.info(f"--- Page {page}/{total_pages} --- (records so far: {len(all_data):,})")
            if go_to_page(driver, page):
                page_data = extract_page_data(driver)
                all_data.extend(page_data)
            else:
                logger.error(f"Failed to go to page {page}, retrying once...")
                time.sleep(3)
                if not go_to_page(driver, page):
                    logger.error(f"Retry failed for page {page}, stopping.")
                    break
                page_data = extract_page_data(driver)
                all_data.extend(page_data)
            
            # Checkpoint save
            if page % checkpoint_interval == 0 and all_data:
                checkpoint_file = f"{output_base}_checkpoint_p{page}.csv"
                with open(checkpoint_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                    writer.writeheader()
                    writer.writerows(all_data)
                logger.info(f"💾 Checkpoint saved: {checkpoint_file} ({len(all_data):,} records)")
        
        # Final save
        if all_data:
            output_file = f"{output_base}_FINAL.csv"
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"✓ COMPLETE! Data saved to: {output_file}")
            logger.info(f"  Total records: {len(all_data):,}")
            logger.info(f"  Total pages scraped: {total_pages}")
            logger.info(f"  File size: {os.path.getsize(output_file) / 1024:.2f} KB")
            logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"\n✗ ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Emergency save on error
        if all_data:
            emergency_file = f"cpi_data_EMERGENCY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(emergency_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)
            logger.info(f"💾 Emergency save: {emergency_file} ({len(all_data):,} records)")
    
    finally:
        if driver:
            logger.info("\nClosing driver...")
            driver.quit()
        logger.info("="*80 + "\n")

if __name__ == "__main__":
    main()
