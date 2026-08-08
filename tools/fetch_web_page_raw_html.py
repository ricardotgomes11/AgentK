import os
import shutil
import urllib.request
from langchain_core.tools import tool

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

@tool
def fetch_web_page_raw_html(url: str) -> str:
    """Fetches the raw HTML of a web page."""
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument("--disable-gpu")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
            
        chromedriver_path = None
        if os.path.exists('/usr/bin/chromedriver'):
            chromedriver_path = '/usr/bin/chromedriver'
        elif shutil.which('chromedriver'):
            chromedriver_path = shutil.which('chromedriver')
            
        if chromedriver_path:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(options=options, service=service)
        else:
            driver = webdriver.Chrome(options=options)

        driver.get(url)
        html = driver.execute_script("return document.body.outerHTML;")
        driver.quit()
        return html
    except Exception:
        # Fallback to standard HTTP GET request if selenium/chromedriver is unavailable
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')