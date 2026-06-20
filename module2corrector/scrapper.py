import time
import pandas as pd
import re
import hashlib

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager


class NairobiMarketDataPipeline:
    def __init__(self):
        print("🚀 Launching Jiji Property Data Pipeline (STEALTH FIXED VERSION)...")

        chrome_options = Options()

        # ❌ REMOVED HEADLESS (IMPORTANT FIX)
        # chrome_options.add_argument("--headless=new")

        # ✅ STEALTH / ANTI-BOT SETTINGS
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        self.wait = WebDriverWait(self.driver, 15)
        self.dataset = []

    # ---------------- FEATURE EXTRACTION ----------------
    def extract_property_features(self, text):
        text_lower = text.lower()

        borehole = 1 if any(w in text_lower for w in ["borehole", "water supply"]) else 0
        parking = 1 if "parking" in text_lower else 0
        security = 1 if any(w in text_lower for w in ["security", "cctv", "guard", "fenced"]) else 0

        price = 0
        price_match = re.search(r'(?:kes|ksh|sh)\.?\s?([\d,]+)', text_lower)
        if price_match:
            price = int(price_match.group(1).replace(",", ""))

        sq_ft = 0
        sqft_match = re.search(r'(\d+)\s?(?:sqft|sq ft|sq\.ft|m²)', text_lower)
        if sqft_match:
            sq_ft = int(sqft_match.group(1))

        return {
            "price": price,
            "sq_ft": sq_ft,
            "borehole": borehole,
            "parking": parking,
            "security": security
        }

    # ---------------- MAIN SCRAPER ----------------
    def process_all_listings(self):

        queries = [
            "property",
            "houses for rent",
            "apartment for rent nairobi",
            "bedsitter nairobi",
            "studio apartment nairobi",
            "house kenya rent"
        ]

        for query in queries:
            print(f"\n🔎 Searching: {query}")

            for page in range(1, 6):
                try:
                    url = f"https://jiji.co.ke/search?query={query}&page={page}"
                    self.driver.get(url)

                    # wait for page body
                    self.wait.until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    time.sleep(5)

                    # scroll to trigger lazy loading
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)

                    # ---------------- FIXED: DIRECT SELENIUM SCRAPING ----------------
                    listings = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/ad/')]")

                    print(f"📦 Page {page} -> Found {len(listings)} listings")

                    if len(listings) == 0:
                        break

                    for item in listings:
                        text = item.text.strip()

                        if len(text) < 20:
                            continue

                        features = self.extract_property_features(text)
                        content_hash = hashlib.md5(text.encode()).hexdigest()

                        self.dataset.append({
                            "query": query,
                            "page": page,
                            "text": text,
                            "price_ksh": features["price"],
                            "sq_ft": features["sq_ft"],
                            "borehole": features["borehole"],
                            "parking": features["parking"],
                            "security": features["security"],
                            "content_hash": content_hash
                        })

                except Exception as e:
                    print(f"❌ Error on page {page}: {e}")
                    continue

    # ---------------- SAVE DATA ----------------
    def save_to_csv(self, filename="nairobi_jiji_dataset.csv"):
        if not self.dataset:
            print("⚠️ No data collected.")
            return

        df = pd.DataFrame(self.dataset)

        df.drop_duplicates(subset=["content_hash"], inplace=True)
        df = df[df["price_ksh"] > 0]

        df.to_csv(filename, index=False)

        print(f"\n📁 DONE: {len(df)} records saved to {filename}")

    # ---------------- CLEAN EXIT ----------------
    def stop(self):
        try:
            self.driver.quit()
        except:
            pass


# ---------------- RUN ----------------
if __name__ == "__main__":
    pipeline = NairobiMarketDataPipeline()

    try:
        pipeline.process_all_listings()
        pipeline.save_to_csv()
    finally:
        pipeline.stop()