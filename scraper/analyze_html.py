"""
Analyze HTML structure to find pagination controls
"""

import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from pathlib import Path
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://esankhyiki.mospi.gov.in/macroindicators?product=cpi"

def initialize_driver():
    """Initialize headless Chrome WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("start-maximized")
    
    chromedriver_path = ChromeDriverManager().install()
    chromedriver_parent = Path(chromedriver_path).parent
    actual_executable = chromedriver_parent / "chromedriver"
    if actual_executable.exists():
        chromedriver_path = str(actual_executable)
    
    os.chmod(chromedriver_path, 0o755)
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    
    return driver

def main():
    logger.info("Starting HTML analysis...")
    driver = None
    
    try:
        driver = initialize_driver()
        logger.info(f"Navigating to: {BASE_URL}")
        driver.get(BASE_URL)
        
        # Wait for page to load
        time.sleep(3)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "MuiTableRow-root")))
        logger.info("✓ Table loaded")
        
        # Extract and save full HTML
        html = driver.page_source
        
        html_file = "page_structure.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"✓ Full HTML saved to: {html_file}")
        
        # Analyze pagination elements
        logger.info("\n" + "=" * 60)
        logger.info("ANALYZING PAGINATION STRUCTURE")
        logger.info("=" * 60)
        
        # Look for common pagination patterns
        pagination_patterns = [
            ("//nav", "nav elements"),
            ("//ul[@class='MuiPaginationItem-root']", "MuiPaginationItem"),
            ("//button[contains(@aria-label, 'Next')]", "Next button (aria-label)"),
            ("//button[contains(@aria-label, 'page')]", "Page buttons"),
            ("//div[@class='MuiTablePagination-root']", "MuiTablePagination"),
            ("//div[@class='MuiPagination-root']", "MuiPagination"),
            ("//*[contains(text(), 'Next')]", "Next text"),
            ("//button[@aria-label='Go to next page']", "Go to next page"),
            ("//li[@aria-label='Go to next page']", "li next page"),
            ("//div[@role='navigation']", "navigation role"),
        ]
        
        for xpath, description in pagination_patterns:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    logger.info(f"\n✓ Found {len(elements)} element(s): {description}")
                    logger.info(f"  XPath: {xpath}")
                    for i, elem in enumerate(elements[:3]):  # Show first 3
                        try:
                            outer_html = elem.get_attribute("outerHTML")[:200]
                            logger.info(f"    [{i}] {outer_html}...")
                        except:
                            logger.info(f"    [{i}] Element found but couldn't extract HTML")
            except Exception as e:
                logger.debug(f"  No match for {description}")
        
        # Extract footer/pagination area
        logger.info("\n" + "=" * 60)
        logger.info("ANALYZING FULL PAGE STRUCTURE")
        logger.info("=" * 60)
        
        # Get all buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        logger.info(f"\nFound {len(buttons)} buttons on page:")
        for i, btn in enumerate(buttons[:15]):
            text = btn.text.strip()
            aria_label = btn.get_attribute("aria-label") or ""
            if text or aria_label:
                logger.info(f"  [{i}] text='{text}' aria-label='{aria_label}'")
        
        # Get all divs with pagination-like classes
        logger.info("\nLooking for pagination-related divs:")
        divs = driver.find_elements(By.XPATH, "//div[contains(@class, 'Pagination') or contains(@class, 'pagination') or contains(@class, 'paging')]")
        logger.info(f"Found {len(divs)} pagination-related divs")
        for i, div in enumerate(divs[:5]):
            classes = div.get_attribute("class")
            logger.info(f"  [{i}] {classes}")
        
        # Get table footer/pagination area
        logger.info("\nSearching for table pagination footer:")
        table = driver.find_element(By.TAG_NAME, "table")
        parent = table.find_element(By.XPATH, "./ancestor::div[@class='MuiTableContainer-root']")
        
        # Look for pagination in parent
        pagination = parent.find_elements(By.XPATH, ".//nav | .//div[@role='navigation']")
        logger.info(f"Found {len(pagination)} pagination containers")
        
        # Try to find the specific next button
        logger.info("\nSearching for 'Next' page button:")
        try:
            # Try different patterns
            patterns = [
                "//button[@aria-label='Go to next page']",
                "//li[@aria-label='Go to next page']/button",
                "//li[contains(., 'next')]/button",
                "//button[contains(@class, 'MuiPaginationItem-page')]",
                "//button[contains(@class, 'MuiIconButton-root')]//following::button",
            ]
            
            for pattern in patterns:
                try:
                    btn = driver.find_element(By.XPATH, pattern)
                    logger.info(f"✓ Found with pattern: {pattern}")
                    logger.info(f"  Text: {btn.text}")
                    logger.info(f"  Class: {btn.get_attribute('class')}")
                    logger.info(f"  Aria-label: {btn.get_attribute('aria-label')}")
                except:
                    pass
        except Exception as e:
            logger.warning(f"Could not find next button: {e}")
        
        # Save important HTML sections
        logger.info("\n" + "=" * 60)
        logger.info("SAVING HTML SECTIONS")
        logger.info("=" * 60)
        
        # Save footer section
        try:
            footer = driver.find_element(By.TAG_NAME, "footer")
            footer_html = footer.get_attribute("outerHTML")
            with open("footer_section.html", 'w', encoding='utf-8') as f:
                f.write(footer_html)
            logger.info("✓ Footer section saved")
        except:
            logger.debug("No footer found")
        
        # Save table container with pagination
        try:
            table_container = driver.find_element(By.XPATH, "//div[@class='MuiTableContainer-root']")
            container_parent = table_container.find_element(By.XPATH, "./parent::div")
            container_html = container_parent.get_attribute("outerHTML")
            with open("table_and_pagination.html", 'w', encoding='utf-8') as f:
                f.write(container_html)
            logger.info("✓ Table and pagination section saved")
        except Exception as e:
            logger.debug(f"Could not save table container: {e}")
        
        logger.info("\n✓ Analysis complete!")
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
