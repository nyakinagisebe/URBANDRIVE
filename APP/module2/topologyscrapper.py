import time
import pandas as pd
import re
import os
import shutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from gologin import GoLogin

class NairobiMarketDataPipeline:
    def __init__(self, token, profile_id):
        # Using a very short path to prevent Windows Errno 22
        custom_temp = "C:\\gl_deep_scrape"
        if os.path.exists(custom_temp):
            # Aggressive cleanup of previous sessions
            os.system('taskkill /f /im chrome.exe /t >nul 2>&1')
            os.system('taskkill /f /im orbita.exe /t >nul 2>&1')
            time.sleep(2)
            shutil.rmtree(custom_temp, ignore_errors=True)
            
        os.makedirs(custom_temp, exist_ok=True)

        self.gl = GoLogin({
            "token": token,
            "profile_id": profile_id,
            "auto_check_proxy": False,
            "tmpdir": custom_temp,
            "extra_params": ["--headless", "--disable-gpu"]
        })
        
        print("🚀 Launching Greater Nairobi & Satellite Towns Deep-Scrape Pipeline...")
        debugger_address = self.gl.start()
        
        driver_path = ChromeDriverManager(driver_version="134.0.6998.35").install()
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", debugger_address)
        chrome_options.add_argument("--headless")
        
        self.driver = webdriver.Chrome(service=Service(executable_path=driver_path), options=chrome_options)
        self.dataset = []

    def extract_property_features(self, text):
        text_lower = text.lower()
        borehole = 1 if any(w in text_lower for w in ["borehole", "water supply"]) else 0
        parking = 1 if "parking" in text_lower else 0
        security = 1 if any(w in text_lower for w in ["security", "cctv", "guard", "fenced"]) else 0
        
        price = 0
        price_match = re.search(r'(?:kes|ksh|sh)\.?\s?([\d,]+)', text_lower)
        if price_match:
            price = int(price_match.group(1).replace(',', ''))
            
        sq_ft = 0
        sqft_match = re.search(r'(\d+)\s?(?:sqft|sq ft|sq\.ft|m²)', text_lower)
        if sqft_match:
            sq_ft = int(sqft_match.group(1))
            
        return {'price': price, 'sq_ft': sq_ft, 'borehole': borehole, 'parking': parking, 'security': security}

    def process_location(self, region_group, area_name):
        # Create a URL-friendly slug
        slug = area_name.lower().replace(" ", "-").replace("/", "-").replace("'", "").replace(".", "")
        url_template = f"https://jiji.co.ke/{slug}/houses-apartments-for-rent?page={{page}}"
        
        print(f"📡 Harvesting: [{region_group}] -> {area_name}...")
        page = 1
        consecutive_empty_pages = 0
        
        while True:
            url = url_template.replace("{page}", str(page))
            try:
                self.driver.get(url)
                time.sleep(5) 
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                elements = soup.find_all(['div', 'a', 'section'], class_=True)
                
                initial_count = len(self.dataset)
                for el in elements:
                    raw_text = el.get_text(separator=" ").strip()
                    keywords = ["bedsitter", "apartment", "mansion", "townhouse", "studio", "house"]
                    if any(k in raw_text.lower() for k in keywords) and len(raw_text) > 60:
                        features = self.extract_property_features(raw_text)
                        
                        topology = "Apartment"
                        if "mansion" in raw_text.lower(): topology = "Mansionette"
                        elif "townhouse" in raw_text.lower(): topology = "Townhouse"
                        elif "bedsitter" in raw_text.lower(): topology = "Bedsitter"

                        self.dataset.append({
                            'region_group': region_group,
                            'micro_area': area_name,
                            'topology': topology,
                            'price_ksh': features['price'],
                            'sq_ft': features['sq_ft'],
                            'borehole': features['borehole'],
                            'parking': features['parking'],
                            'security': features['security'],
                            'content_hash': raw_text[:150] 
                        })

                if len(self.dataset) == initial_count:
                    consecutive_empty_pages += 1
                else:
                    consecutive_empty_pages = 0

                # Stop if no data found or page limit reached
                if consecutive_empty_pages >= 1 or page >= 15:
                    break
                page += 1
            except:
                break

    def save_to_csv(self, filename="nairobi_comprehensive_dataset.csv"):
        if self.dataset:
            df = pd.DataFrame(self.dataset)
            df.drop_duplicates(subset=['content_hash'], inplace=True)
            df = df[df['price_ksh'] > 0]
            df.to_csv(filename, index=False)
            print(f"\n📁 Dataset Finalized: {len(df)} UNIQUE records saved to {filename}")

    def stop(self):
        try:
            self.driver.quit()
            self.gl.stop()
        except:
            pass

if __name__ == "__main__":
    TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NTFhY2VmNGJiOGZjMTk1M2RiNmIyNzkiLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2NTFhY2ZjMDRlOGUwMDdjZGMzMDc1YmEifQ.rQAsCmhu7qVZaGN4WybBzfs7olSbcPgTpPh5E5pI4Zo"
    PROFILE_ID = "6827282ff591376f2f31a32b" 

    nairobi_map = {
        "Westlands": ["Westlands CBD", "Parklands", "Highridge", "Mountain View", "Kangemi", "Lower Kabete", "Kitisuru", "Loresho", "Kyuna", "Lake View"],
        "Dagoretti": ["Lavington", "Kilimani", "Kawangware", "Gatina", "Riruta", "Mutuini", "Ngando", "Woodley", "Kenyatta Golf Course", "Riara"],
        "Langata": ["Karen", "Langata Estate", "South C", "Mugumoini", "Nairobi Dam", "Wilson Airport", "Otiende", "Onyonka", "Nhale", "Phenom"],
        "Kibra": ["Sarangombe", "Lindi", "Makina", "Woodley", "Lain Saba"],
        "Starehe": ["Nairobi CBD", "Ngara", "Pangani", "Ziwani", "Landimawe", "South B", "Hazina", "Kariokor", "Gikomba", "Railways"],
        "Makadara": ["Industrial Area", "Makongeni", "Maringo", "Hamza", "Viwandani", "Harambee", "Buruburu", "Jericho", "Jerusalem"],
        "Kamukunji": ["Eastleigh North", "Eastleigh South", "Airbase", "California", "Pumwani", "Shauri Moyo"],
        "Embakasi": ["Donholm", "Umoja", "Innercore", "Greenfield", "Tena", "Kayole", "Komarock", "Matopeni", "Pipeline", "Kware", "Njiru", "Ruai", "Mihango", "Utawala", "Embakasi Village", "Fedha", "Nyayo Estate", "Avenue Park"],
        "Kasarani": ["Roysambu", "Garden Estate", "Kasarani", "Mwiki", "Clay City", "Hunters", "Sunton", "Seasons"],
        "Roysambu": ["Ridgeways", "Githurai 44", "Kahawa West", "Zimmermann", "Mirema", "Jacaranda"],
        "Ruaraka": ["Baba Dogo", "Utalii", "Mathare North", "Lucky Summer", "Korogocho"],
        "Mathare": ["Mlango Kubwa", "Hospital Ward", "Kiamaiko", "Huruma", "Mabatini"],
        
        # Satellite Towns & Growth Hubs
        "Syokimau-Mlolongo": ["Syokimau", "Mlolongo", "Muthama Access Road", "Wananchi Road", "Lifestyle Gardens", "Southgate Homes"],
        "Ruaka-Kiambu": ["Ruaka", "Kiambu Town", "Tigoni", "Muchatha", "Banana", "Ndenderu"],
        "Kitengela-AthiRiver": ["Kitengela Town", "Chuna Estate", "Milimani Kitengela", "Athi River", "Greatwall Gardens", "Sabaki"],
        "Kikuyu-WaiyakiWay": ["Kikuyu Town", "Gikambura", "Thogoto", "Zambezi", "Ondiri", "Kamangu"],
        "Thika-Superhighway": ["Thika Town", "Ngoigwa", "Section 9", "Ruiru Town", "Juja", "Karatina Road", "Gatuanyaga"]
    }

    pipeline = NairobiMarketDataPipeline(TOKEN, PROFILE_ID)
    try:
        for group, areas in nairobi_map.items():
            for area in areas:
                pipeline.process_location(group, area)
        pipeline.save_to_csv()
    finally:
        pipeline.stop()