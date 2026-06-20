import pandas as pd
import joblib
import sqlite3
from scipy.spatial import cKDTree
from geopy.geocoders import Nominatim
import numpy as np

class InvestmentOracle:
    def __init__(self, model_path="nairobi_investment_model.pkl", db_path="housing_intelligence.db"):
        print("Loading Nairobi Infrastructure Intelligence...")
        self.model = joblib.load(model_path)
        self.conn = sqlite3.connect(db_path)
        self.infra_df = pd.read_sql("SELECT * FROM investment_master", self.conn)
        self.geolocator = Nominatim(user_agent="nairobi_investment_app")
        
        # Define 5 Infrastructure Pillars with Major vs Minor logic
        self.categories = {
            'transport': "highway in ['motorway', 'trunk', 'primary'] or amenity == 'bus_station'",
            'retail': "shop in ['mall', 'supermarket'] or amenity == 'marketplace'",
            'jobs': "office.notnull() or landuse == 'industrial' or landuse == 'commercial'",
            'health': "amenity == 'hospital'", # Specifically excludes 'clinic' for major list
            'edu': "amenity == 'university' or (amenity == 'school' and name.str.contains('High|Secondary', na=False))"
        }
        
        self.trees = {}
        self.category_data = {}
        for cat, query in self.categories.items():
            filtered = self.infra_df.query(query).copy().reset_index(drop=True)
            if not filtered.empty:
                self.trees[cat] = cKDTree(filtered[['lat', 'lon']].values)
                self.category_data[cat] = filtered

    def get_report(self, area_name):
        search_query = f"{area_name}, Nairobi, Kenya"
        location = self.geolocator.geocode(search_query)
        if not location: return print("Location not found.")
        
        lat, lon = location.latitude, location.longitude
        features = {}
        unique_landmarks = {}

        # 1. Spatial Analysis with Deduplication Logic
        for cat, tree in self.trees.items():
            # We query 10 neighbors (k=10) to give us a "buffer" to filter duplicates
            distances, indices = tree.query([[lat, lon]], k=10)
            dist_km = distances[0] * 111.32
            
            found_unique = []
            seen_names = set()

            for i in range(len(indices[0])):
                row = self.category_data[cat].iloc[indices[0][i]]
                name = row.get('name') or f"Major {cat.capitalize()} Arterial"
                
                # Deduplication: Only add if we haven't seen this name for this category
                if name not in seen_names:
                    found_unique.append({"name": name, "dist": round(dist_km[i], 2)})
                    seen_names.add(name)
                
                # Stop once we have 2 distinct major landmarks
                if len(found_unique) == 2:
                    break
            
            unique_landmarks[cat] = found_unique
            
            # Keep the first 5 distances for the AI model (consistency)
            for i in range(5):
                features[f'dist_{cat}_{i+1}'] = dist_km[i]

        # 2. AI Investment Potential Prediction
        feature_df = pd.DataFrame([features])[self.model.get_booster().feature_names]
        score = self.model.predict(feature_df)[0]

        # 3. Print the Dossier
        print(f"\n{'='*60}")
        print(f" INVESTMENT DOSSIER: {area_name.upper()}")
        print(f" AI CONFIDENCE SCORE: {score:.1f}%")
        print(f"{'='*60}")

        icon_map = {'transport': '🛣️ ROADS/TRANSIT', 'retail': '🛍️ RETAIL HUBS', 
                    'jobs': '🏢 JOB CENTRES', 'health': '🏥 MEDICAL', 'edu': '🎓 EDUCATION'}

        for cat, landmarks in unique_landmarks.items():
            print(f"\n{icon_map[cat]}:")
            if landmarks:
                for i, item in enumerate(landmarks):
                    print(f"  {i+1}. {item['name']} ({item['dist']} km)")
            else:
                print("  (No major infrastructure detected in this category)")

        print(f"\n{'='*60}")
        # Verdict logic stays the same...
        
        search_query = f"{area_name}, Nairobi, Kenya"
        location = self.geolocator.geocode(search_query)
        if not location: return print("Location not found.")
        
        lat, lon = location.latitude, location.longitude
        features = {}
        major_landmarks = {}

        # 1. Spatial Analysis for 25 features (for the AI) and Top 2 (for the User)
        for cat, tree in self.trees.items():
            # Get 5 for the model to ensure high accuracy
            distances, indices = tree.query([[lat, lon]], k=5)
            dist_km = distances[0] * 111.32
            
            # Store Top 2 Major Landmarks for the Report
            found = []
            for i in range(2):
                row = self.category_data[cat].iloc[indices[0][i]]
                name = row.get('name') or f"Major {cat.capitalize()} Arterial"
                found.append({"name": name, "dist": round(dist_km[i], 2)})
            major_landmarks[cat] = found
            
            # Populate features for the XGBoost model
            for i in range(5):
                features[f'dist_{cat}_{i+1}'] = dist_km[i]

        # 2. AI Investment Potential Prediction
        feature_df = pd.DataFrame([features])[self.model.get_booster().feature_names]
        score = self.model.predict(feature_df)[0]

        # 3. Print Professional Investment Dossier
        print(f"\n{'='*60}")
        print(f" INVESTMENT DOSSIER: {area_name.upper()}")
        print(f" COORDINATES: {lat:.4f}, {lon:.4f} | SCORE: {score:.1f}%")
        print(f"{'='*60}")

        icon_map = {'transport': '🛣️ ROADS/TRANSIT', 'retail': '🛍️ RETAIL HUBS', 
                    'jobs': '🏢 JOB CENTRES', 'health': '🏥 MEDICAL', 'edu': '🎓 EDUCATION'}

        for cat, landmarks in major_landmarks.items():
            print(f"\n{icon_map[cat]}:")
            for i, item in enumerate(landmarks):
                print(f"  {i+1}. {item['name']} ({item['dist']} km away)")

        print(f"\n{'='*60}")
        if score > 75:
            print("STRATEGIC VERDICT: TIER-1 GROWTH ASSET (BUY/DEVELOP)")
        elif score > 55:
            print("STRATEGIC VERDICT: STABLE RESIDENTIAL YIELD")
        else:
            print("STRATEGIC VERDICT: SPECULATIVE / LONG-TERM HOLD")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    oracle = InvestmentOracle()
    area = input("Enter Area (e.g., Upper Hill, Kasarani, Karen): ")
    oracle.get_report(area)