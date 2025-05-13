import os
import time
import requests
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

COMPANIES = {
    "DIPD": "https://www.cse.lk/pages/company-profile/company-profile.component.html?symbol=DIPD.N0000",
    "REXP": "https://www.cse.lk/pages/company-profile/company-profile.component.html?symbol=REXP.N0000",
}
OUTPUT_DIR = "backend/data_collection/downloaded_pdfs"
HEADLESS = True
DOWNLOAD_DELAY = 2

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_pdf(url, dest_path):
    if os.path.exists(dest_path):
        print(f"Exists: {dest_path}")
        return
    resp = requests.get(url)
    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application"):
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        print("Downloaded:", dest_path)
    else:
        print("Failed to fetch PDF:", url, "(status:", resp.status_code, ")")

def init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def click_tab_by_text(driver, text, timeout=10):
    try:
        # Wait for any element with the tab text to be visible
        tab = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, f"//*[normalize-space(text())='{text}']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
        tab.click()
        time.sleep(1)
        return True
    except Exception as e:
        print(f"Could not click tab '{text}': {e}")
        return False

def click_tab_by_href(driver, href_value, timeout=10):
    try:
        tab = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'a[data-toggle=\"tab\"][href=\"{href_value}\"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
        tab.click()
        time.sleep(1)
        return True
    except Exception as e:
        print(f"Could not click tab with href '{href_value}': {e}")
        return False

def click_tab_and_wait_for_content(driver, href_value, content_selector, timeout=10):
    if not click_tab_by_href(driver, href_value, timeout):
        return False
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, content_selector))
        )
        return True
    except Exception as e:
        print(f"Could not find content for tab {href_value}: {e}")
        return False

def sanitize_filename(s):
    # Replace forbidden characters with underscore
    return re.sub(r'[\\\\/:*?"<>|]', '_', s)

def scrape_company_quarters(driver, company_code, company_url):
    driver.get(company_url)
    time.sleep(2)
    # Click Financials tab
    if not click_tab_by_href(driver, "#tab3"):
        print(f"[{company_code}] Could not click Financials tab")
        return
    time.sleep(2)
    # Click Quarterly Reports sub-tab and wait for its content
    if not click_tab_and_wait_for_content(driver, "#21b", "div#\\32 1b", timeout=10):
        print(f"[{company_code}] Could not click Quarterly Reports tab or content did not load")
        return
    time.sleep(1)
    # Parse the correct table for PDFs
    soup = BeautifulSoup(driver.page_source, "html.parser")
    quarterly_tab_div = soup.find("div", id="21b")
    if not quarterly_tab_div:
        print(f"[{company_code}] Could not find Quarterly Reports tab content")
        return
    table = quarterly_tab_div.find("table")
    if not table:
        print(f"[{company_code}] No table found in Quarterly Reports tab")
        return
    out_folder = os.path.join(OUTPUT_DIR, company_code)
    ensure_dir(out_folder)
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        uploaded_date = cols[0].get_text(strip=True)
        report_name = cols[1].get_text(strip=True)
        pdf_link = None
        for a in row.find_all("a", href=True):
            if a['href'].lower().endswith('.pdf'):
                pdf_link = a['href']
                break
        if not pdf_link:
            continue
        if not pdf_link.startswith("http"):
            pdf_link = urljoin(company_url, pdf_link)
        name = f"{sanitize_filename(uploaded_date.replace(' ', '_'))}_{sanitize_filename(report_name.replace(' ', '_'))}.pdf"
        dest = os.path.join(out_folder, name)
        save_pdf(pdf_link, dest)
        print(f"Downloaded: {dest}")
        time.sleep(DOWNLOAD_DELAY)

if __name__ == "__main__":
    driver = init_driver(HEADLESS)
    ensure_dir(OUTPUT_DIR)
    for code, url in COMPANIES.items():
        print(f"--- Scraping {code} ---")
        scrape_company_quarters(driver, code, url)
    driver.quit()