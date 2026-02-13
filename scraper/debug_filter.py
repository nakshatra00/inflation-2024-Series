"""
Debug script: Diagnose why State filter doesn't work.
Opens page, clicks desktop sidebar State dropdown, captures popup HTML.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from pathlib import Path

BASE_URL = "https://esankhyiki.mospi.gov.in/macroindicators?product=cpi"

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    chromedriver_path = ChromeDriverManager().install()
    actual_path = Path(chromedriver_path).parent / "chromedriver"
    if actual_path.exists():
        chromedriver_path = str(actual_path)
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)
    return driver

def main():
    driver = init_driver()
    
    print(f"Navigating to {BASE_URL}...")
    driver.get(BASE_URL)
    
    # Wait for table to actually load (not just page load)
    print("Waiting for table to load...")
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "MuiTableRow-root"))
        )
        print("Table loaded!")
    except:
        print("Table did not load in 30s, continuing anyway...")
    time.sleep(3)
    
    # Step 1: Find ALL State labels on the page
    state_labels = driver.find_elements(By.XPATH, "//label[contains(text(), 'State')]")
    print(f"\n=== Found {len(state_labels)} 'State' labels ===")
    for i, lbl in enumerate(state_labels):
        print(f"  [{i}] text='{lbl.text}', displayed={lbl.is_displayed()}, "
              f"location={lbl.location}, size={lbl.size}")
    
    # Step 2: Find ALL comboboxes in DESKTOP sidebar
    desktop_combos = driver.find_elements(
        By.CSS_SELECTOR, "div.filter-sidebar div[role='combobox']"
    )
    print(f"\n=== Desktop sidebar comboboxes: {len(desktop_combos)} ===")
    for i, cb in enumerate(desktop_combos):
        aria = cb.get_attribute('aria-controls')
        text = cb.text.strip() or "(empty)"
        classes = cb.get_attribute('class')
        is_multi = 'MuiSelect-multiple' in classes
        print(f"  [{i}] aria-controls={aria}, text='{text}', multi={is_multi}, displayed={cb.is_displayed()}")
    
    # Step 3: The State dropdown in the desktop sidebar
    # From the HTML: the desktop sidebar State combobox has aria-controls=":r11:"
    # Let's find it by position - it's the 4th dropdown (Base Year, Series, Year, State)
    print(f"\n=== Clicking desktop State dropdown (index 3) ===")
    if len(desktop_combos) > 3:
        state_cb = desktop_combos[3]  # 0=Base Year, 1=Series, 2=Year, 3=State
        print(f"  Target: aria-controls={state_cb.get_attribute('aria-controls')}, displayed={state_cb.is_displayed()}")
        
        driver.execute_script("arguments[0].scrollIntoView(true);", state_cb)
        time.sleep(0.5)
        
        # MUI Select opens on mousedown, NOT click!
        print("  Dispatching mousedown event...")
        driver.execute_script("""
            var evt = new MouseEvent('mousedown', {
                bubbles: true, cancelable: true, view: window
            });
            arguments[0].dispatchEvent(evt);
        """, state_cb)
        time.sleep(2)
        
        # Check if dropdown popup appeared
        listboxes = driver.find_elements(By.CSS_SELECTOR, "ul[role='listbox']")
        print(f"\n=== Listboxes found after click: {len(listboxes)} ===")
        for i, lb in enumerate(listboxes):
            items = lb.find_elements(By.TAG_NAME, "li")
            item_texts = [it.text.strip() for it in items[:10]]
            print(f"  [{i}] {len(items)} items, first 10: {item_texts}")
            
            # Find "All India"
            for it in items:
                if "All India" in it.text:
                    print(f"\n  >> Found 'All India': displayed={it.is_displayed()}")
                    print(f"     Clicking 'All India'...")
                    driver.execute_script("arguments[0].click();", it)
                    time.sleep(1)
                    
                    # Check if it got selected - look at the combobox text
                    new_text = state_cb.text.strip()
                    print(f"     Combobox text after click: '{new_text}'")
                    break
        
        # Close dropdown with Escape
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(1)
        
        # Step 4: Click Apply in desktop sidebar
        print(f"\n=== Clicking Apply in desktop sidebar ===")
        apply_btns = driver.find_elements(
            By.CSS_SELECTOR, "div.filter-sidebar div.filter-buttons button"
        )
        print(f"  Found {len(apply_btns)} buttons in desktop filter-buttons")
        for i, btn in enumerate(apply_btns):
            print(f"  [{i}] text='{btn.text}', displayed={btn.is_displayed()}")
        
        if apply_btns:
            print(f"  Clicking first button (Apply)...")
            driver.execute_script("arguments[0].click();", apply_btns[0])
            
            # Wait for reload
            print("  Waiting for page to reload...")
            time.sleep(5)
            
            # Check page count
            page_inputs = driver.find_elements(By.XPATH, "//input[@type='text' and @min='1']")
            if page_inputs:
                max_val = page_inputs[0].get_attribute('max')
                cur_val = page_inputs[0].get_attribute('value')
                print(f"\n=== RESULT: Page {cur_val} of {max_val} ===")
            
            # Also check the records text
            try:
                info = driver.find_element(By.XPATH, "//p[contains(text(), 'of') and contains(text(), 'records')]")
                print(f"  Records info: {info.text}")
            except:
                pass
    
    # Also check: does the State combobox text change?
    print(f"\n=== Final state of desktop comboboxes ===")
    desktop_combos2 = driver.find_elements(
        By.CSS_SELECTOR, "div.filter-sidebar div[role='combobox']"
    )
    for i, cb in enumerate(desktop_combos2):
        text = cb.text.strip() or "(empty)"
        print(f"  [{i}] text='{text}'")
    
    driver.quit()
    print("\nDone!")

if __name__ == "__main__":
    main()
