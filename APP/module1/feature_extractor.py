import pandas as pd
import sqlite3
from scipy.spatial import cKDTree
import numpy as np

class SpatialIntelligenceExtractor:
    def __init__(self, db_name="housing_intelligence.db"):
        self.conn = sqlite3.connect(db_name)
        # Load the 24,882 infrastructure points
        self.infra_df = pd.read_sql("SELECT * FROM investment_master", self.conn)
        
    def get_category_coords(self, category_filter):
        """Filters the data and returns coordinates for the spatial tree."""
        try:
            filtered = self.infra_df.query(category_filter).copy()
            return filtered[['lat', 'lon']].values
        except Exception as e:
            print(f"Filter Error: {e}")
            return np.array([])

    def extract_features(self, grid_file="nairobi_investment_grid.csv"):
        print("--- Starting Enhanced Spatial Intelligence Extraction ---")
        grid_df = pd.read_csv(grid_file)
        grid_coords = grid_df[['lat', 'lon']].values

        # Defined 5 Investment Pillars
        categories = {
            'jobs': "industrial.notnull() or landuse == 'industrial' or office.notnull() or landuse == 'commercial'",
            'edu': "amenity == 'school' or amenity == 'university'",
            'health': "amenity == 'hospital' or amenity == 'clinic'",
            'retail': "shop.notnull() or landuse == 'retail' or amenity == 'marketplace'",
            'transport': "highway.notnull() or amenity == 'bus_station'" # Now capturing the roads!
        }

        # For each category, find the nearest 5 neighbors
        for cat_name, query in categories.items():
            print(f"Calculating proximity to: {cat_name}...")
            ref_coords = self.get_category_coords(query)
            
            if len(ref_coords) > 0:
                tree = cKDTree(ref_coords)
                # Find 5 closest infrastructure points for every grid coordinate
                distances, _ = tree.query(grid_coords, k=5)
                
                # Convert degrees to KM (approx 111.32km per degree at equator)
                distances_km = distances * 111.32
                
                for i in range(5):
                    grid_df[f'dist_{cat_name}_{i+1}'] = distances_km[:, i]
            else:
                print(f"Warning: No infrastructure found for {cat_name}")

        # Save the master feature set
        grid_df.to_csv("master_training_features.csv", index=False)
        print(f"Success! Master Feature Matrix saved with {len(grid_df)} sites and road data.")
        self.conn.close()

if __name__ == "__main__":
    extractor = SpatialIntelligenceExtractor()
    extractor.extract_features()