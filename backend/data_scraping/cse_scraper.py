"""
CSE Quarterly Financial PDF Scraper

This module provides a robust, automated scraper for downloading quarterly financial PDF reports
from the Colombo Stock Exchange (CSE) website for specified companies. It uses Selenium for dynamic
web navigation and BeautifulSoup for HTML parsing. The scraper is designed to be resilient to changes
in the CSE website structure and to log all download activity for auditability.

Key Features:
- Automatically downloads the correct ChromeDriver version for your installed Chrome.
- Navigates to each company's profile and extracts quarterly report PDFs.
- Handles dynamic tabs and content loading with Selenium.
- Logs all downloads and errors to both file and console.
- Organizes PDFs by company in a structured directory.

Usage:
    python cse_scraper.py

Requirements:
    - Google Chrome installed
    - Selenium, BeautifulSoup4, requests, etc.
"""

import os
import time
import requests
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import logging
import subprocess
import zipfile
import io

# Set up logging for both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Company codes and their CSE profile URLs
COMPANIES = {
    "DIPD": "https://www.cse.lk/pages/company-profile/company-profile.component.html?symbol=DIPD.N0000",
    "REXP": "https://www.cse.lk/pages/company-profile/company-profile.component.html?symbol=REXP.N0000",
}
OUTPUT_DIR = "backend/data_scraping/pdfs"
HEADLESS = True
DOWNLOAD_DELAY = 2  # seconds between downloads to avoid overloading the server

def get_chrome_version():
    """
    Detect the installed Google Chrome version on Windows.
    Returns:
        str or None: The version string (e.g., '123.0.6312.86') or None if not found.
    """
    try:
        # Try to get Chrome version from registry
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return version
    except Exception:
        try:
            # Try to get Chrome version from program files
            paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            for path in paths:
                if os.path.exists(path):
                    result = subprocess.run([path, '--version'], capture_output=True, text=True)
                    version = result.stdout.strip().split()[-1]
                    return version
        except:
            pass
    return None

def ensure_dir(path):
    """
    Ensure that a directory exists; create it if it does not.
    Args:
        path (str): Directory path to check/create.
    """
    if not os.path.exists(path):
        os.makedirs(path)

def save_pdf(url, dest_path):
    """
    Download a PDF from a URL and save it to the specified path.
    Args:
        url (str): The URL of the PDF to download.
        dest_path (str): The local file path to save the PDF.
    """
    if os.path.exists(dest_path):
        logging.info(f"Exists: {dest_path}")
        return
    resp = requests.get(url)
    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application"):
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        logging.info(f"Downloaded: {dest_path}")
    else:
        logging.error(f"Failed to fetch PDF: {url} (status: {resp.status_code})")

def download_chromedriver():
    """
    Download the ChromeDriver version matching the installed Chrome browser.
    Returns:
        str: Path to the downloaded chromedriver.exe
    Raises:
        Exception: If Chrome version cannot be detected or download fails.
    """
    chrome_version = get_chrome_version()
    if not chrome_version:
        raise Exception("Could not detect Chrome version")
    # Extract major version
    major_version = chrome_version.split('.')[0]
    logging.info(f"Using Chrome version: {chrome_version} (major version: {major_version})")
    # Download ChromeDriver
    url = f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}/win64/chromedriver-win64.zip"
    logging.info(f"Downloading ChromeDriver from: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download ChromeDriver: {response.status_code}")
    # Extract the zip file
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        # Find chromedriver.exe in the zip
        chromedriver_path = None
        for file in zip_file.namelist():
            if file.endswith('chromedriver.exe'):
                chromedriver_path = file
                break
        if not chromedriver_path:
            raise Exception("Could not find chromedriver.exe in the downloaded zip")
        # Extract to a temporary directory
        temp_dir = os.path.join(os.path.expanduser("~"), ".chromedriver")
        ensure_dir(temp_dir)
        # Extract the file
        zip_file.extract(chromedriver_path, temp_dir)
        # Get the full path to the extracted chromedriver
        driver_path = os.path.join(temp_dir, chromedriver_path)
        logging.info(f"ChromeDriver extracted to: {driver_path}")
        return driver_path

def init_driver(headless=True):
    """
    Initialize a Selenium Chrome WebDriver with the correct driver and options.
    Args:
        headless (bool): Whether to run Chrome in headless mode.
    Returns:
        webdriver.Chrome: The initialized Chrome WebDriver.
    Raises:
        Exception: If ChromeDriver cannot be initialized.
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    try:
        # Download and get ChromeDriver path
        driver_path = download_chromedriver()
        # Initialize Chrome with the downloaded driver
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logging.error(f"Error initializing ChromeDriver: {str(e)}")
        raise

def click_tab_by_text(driver, text, timeout=10):
    """
    Click a tab in the web page by its visible text.
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver.
        text (str): The visible text of the tab to click.
        timeout (int): How long to wait for the tab to appear.
    Returns:
        bool: True if the tab was clicked, False otherwise.
    """
    try:
        tab = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, f"//*[normalize-space(text())='{text}']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
        tab.click()
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"Could not click tab '{text}': {e}")
        return False

def click_tab_by_href(driver, href_value, timeout=10):
    """
    Click a tab in the web page by its href attribute value.
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver.
        href_value (str): The href value of the tab to click (e.g., '#tab3').
        timeout (int): How long to wait for the tab to appear.
    Returns:
        bool: True if the tab was clicked, False otherwise.
    """
    try:
        tab = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'a[data-toggle="tab"][href="{href_value}"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
        tab.click()
        time.sleep(1)
        return True
    except Exception as e:
        logging.error(f"Could not click tab with href '{href_value}': {e}")
        return False

def click_tab_and_wait_for_content(driver, href_value, content_selector, timeout=10):
    """
    Click a tab and wait for its content to become visible.
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver.
        href_value (str): The href value of the tab to click.
        content_selector (str): CSS selector for the content to wait for.
        timeout (int): How long to wait for the content to appear.
    Returns:
        bool: True if the content appeared, False otherwise.
    """
    if not click_tab_by_href(driver, href_value, timeout):
        return False
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, content_selector))
        )
        return True
    except Exception as e:
        logging.error(f"Could not find content for tab {href_value}: {e}")
        return False

def sanitize_filename(s):
    """
    Sanitize a string to be safe for use as a filename.
    Args:
        s (str): The string to sanitize.
    Returns:
        str: The sanitized string.
    """
    return re.sub(r'[\\/:*?"<>|]', '_', s)

def scrape_company_quarters(driver, company_code, company_url):
    """
    Scrape all quarterly report PDFs for a given company from its CSE profile page.
    Navigates to the correct tabs, parses the table, and downloads all found PDFs.
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver.
        company_code (str): The stock code of the company (e.g., 'DIPD').
        company_url (str): The URL of the company's CSE profile page.
    """
    driver.get(company_url)
    time.sleep(2)
    # Click Financials tab
    if not click_tab_by_href(driver, "#tab3"):
        logging.error(f"[{company_code}] Could not click Financials tab")
        return
    time.sleep(2)
    # Click Quarterly Reports sub-tab and wait for its content
    if not click_tab_and_wait_for_content(driver, "#21b", "div#\\32 1b", timeout=10):
        logging.error(f"[{company_code}] Could not click Quarterly Reports tab or content did not load")
        return
    time.sleep(1)
    # Parse the correct table for PDFs
    soup = BeautifulSoup(driver.page_source, "html.parser")
    quarterly_tab_div = soup.find("div", id="21b")
    if not quarterly_tab_div:
        logging.error(f"[{company_code}] Could not find Quarterly Reports tab content")
        return
    table = quarterly_tab_div.find("table")
    if not table:
        logging.error(f"[{company_code}] No table found in Quarterly Reports tab")
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
        time.sleep(DOWNLOAD_DELAY)

if __name__ == "__main__":
    """
    Main entry point: initializes the driver and scrapes all companies in COMPANIES.
    """
    driver = init_driver(HEADLESS)
    ensure_dir(OUTPUT_DIR)
    try:
        for code, url in COMPANIES.items():
            logging.info(f"--- Scraping {code} ---")
            scrape_company_quarters(driver, code, url)
    finally:
        driver.quit() 