#!/usr/bin/env python3
"""
Quick inspection script to examine portal structure
"""
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from pathlib import Path
import os

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://esankhyiki.mospi.gov.in/macroindicators?product=cpi"

def init_driver():
    """Initialize Chrome driver"""
    logger.info("Initializing Chrome driver...")
    
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
    
    if not actual_executable.exists():
        logger.warning(f"Expected chromedriver at {actual_executable}, falling back to {chromedriver_path}")
        actual_executable = chromedriver_path
    
    os.chmod(str(actual_executable), 0o755)
    
    driver = webdriver.Chrome(
        service=Service(str(actual_executable)),
        options=chrome_options
    )
    return driver

def main():
    driver = None
    try:
        driver = init_driver()
        logger.info(f"Navigating to {BASE_URL}")
        driver.get(BASE_URL)
        
        # Wait for page to load
        time.sleep(3)
        
        logger.info("Taking screenshot...")
        driver.save_screenshot("portal_inspection.png")
        logger.info("✓ Screenshot saved to portal_inspection.png")
        
        # Get page HTML
        logger.info("\n" + "="*80)
        logger.info("PAGE TITLE: " + driver.title)
        logger.info("="*80 + "\n")
        
        # Look for common dropdown indicators
        logger.info("Searching for filter labels...")
        labels = driver.find_elements(By.TAG_NAME, "label")
        logger.info(f"Found {len(labels)} labels")
        for label in labels[:20]:
            text = label.text.strip()
            if text:
                logger.info(f"  - {text}")
        
        # Look for select elements
        logger.info("\nSearching for SELECT elements...")
        selects = driver.find_elements(By.TAG_NAME, "select")
        logger.info(f"Found {len(selects)} select elements")
        
        # Look for Material-UI button/menu elements
        logger.info("\nSearching for Material-UI buttons...")
        buttons = driver.find_elements(By.XPATH, "//button[@role='button']")
        logger.info(f"Found {len(buttons)} button elements")
        for btn in buttons[:15]:
            text = btn.text.strip()
            aria_label = btn.get_attribute("aria-label")
            logger.info(f"  - Button: '{text}' | aria-label: '{aria_label}'")
        
        # Look for divs with role=button (MUI buttons)
        logger.info("\nSearching for div[role=button]...")
        div_buttons = driver.find_elements(By.XPATH, "//div[@role='button']")
        logger.info(f"Found {len(div_buttons)} div buttons")
        for dbtn in div_buttons[:10]:
            text = dbtn.text.strip()
            logger.info(f"  - {text}")
        
        # Look for specific text patterns
        logger.info("\nSearching for 'Base Year' text...")
        base_year_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Base Year')]")
        logger.info(f"Found {len(base_year_elements)} elements with 'Base Year'")
        for elem in base_year_elements:
            logger.info(f"  - Tag: {elem.tag_name}, Text: '{elem.text.strip()}', Class: {elem.get_attribute('class')}")
        
        # Try to get HTML of main container
        logger.info("\nGetting HTML of potential filter area...")
        main_content = driver.find_elements(By.XPATH, "//main | //div[@class*='container'] | //div[@class*='filter']")
        if main_content:
            html_snippet = main_content[0].get_attribute("innerHTML")[:2000]
            logger.info(f"HTML snippet (first 2000 chars):\n{html_snippet}")
        
        # Save full page source
        with open("portal_source.html", "w") as f:
            f.write(driver.page_source)
        logger.info("\n✓ Full page source saved to portal_source.html")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            logger.info("Driver closed")

if __name__ == "__main__":
    main()
