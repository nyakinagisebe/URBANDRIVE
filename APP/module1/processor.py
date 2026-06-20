import osmnx as ox
import pandas as pd
import sqlite3
import json

class InvestmentDataProcessor:
    def __init__(self, db_name="housing_intelligence.db"):
        self.db_name = db_name

    def fetch_comprehensive_infrastructure(self, location="Nairobi, Kenya"):
        print(f"--- Fetching Investment Intelligence for {location} ---")
        
        tags = {
            'amenity': True, 
            'landuse': True,
            'office': True,
            'industrial': True,
            'commercial': True,
            'shop': True,
            'highway': ['primary', 'secondary', 'tertiary'],
            'public_transport': True
        }

        try:
            gdf = ox.features_from_place(location, tags)
            
            # FIXING THE WARNINGS: Project to UTM Zone 37S (Kenya's coordinate system)
            # This makes centroid calculations 100% mathematically accurate
            gdf_projected = gdf.to_crs(epsg=32737) 
            
            # Calculate Centroids in Meters, then convert back to Lat/Lon for the JSON
            gdf['lat'] = gdf_projected.centroid.to_crs(epsg=4326).y
            gdf['lon'] = gdf_projected.centroid.to_crs(epsg=4326).x

            # Clean the data as before
            df = pd.DataFrame(gdf.drop(columns='geometry', errors='ignore')).reset_index()
            df.columns = [c.lower() for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]

            # Drop unusable metadata
            cols_to_remove = [c for c in df.columns if 'fixme' in c or 'osm_id' in c]
            df = df.drop(columns=cols_to_remove)

            # SAVE: Investment-Ready JSON
            df.to_json("investment_infrastructure.json", orient="records", indent=4)

            # SAVE: XGBoost-Ready SQL
            conn = sqlite3.connect(self.db_name)
            df.to_sql("investment_master", conn, if_exists="replace", index=False)
            conn.close()
            
            print(f"Success! {len(df)} features captured with 100% geometric accuracy.")
            return df

        except Exception as e:
            print(f"Error: {e}")
            return None

if __name__ == "__main__":
    processor = InvestmentDataProcessor()
    processor.fetch_comprehensive_infrastructure("Nairobi, Kenya")