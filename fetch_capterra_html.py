from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep

url = "https://www.capterra.com/performance-appraisal-software/"
opts = Options()
opts.headless = True
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)
try:
    driver.get(url)
    sleep(3)
    html = driver.page_source
    with open("capterra_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved capterra_page.html")
finally:
    driver.quit()
