import pandas as pd
import numpy as np

def generate_nairobi_grid(step_size=0.005): # ~500m intervals
    """Generates a grid of coordinates across the Nairobi Metropolitan Area."""
    # Bounds for Nairobi County
    lat_min, lat_max = -1.46, -1.17
    lon_min, lon_max = 36.67, 37.21
    
    lats = np.arange(lat_min, lat_max, step_size)
    lons = np.arange(lon_min, lon_max, step_size)
    
    grid_points = []
    for lat in lats:
        for lon in lons:
            grid_points.append({'lat': lat, 'lon': lon})
            
    df_grid = pd.DataFrame(grid_points)
    df_grid.to_csv("nairobi_investment_grid.csv", index=False)
    print(f"Grid Generated: {len(df_grid)} potential investment sites created.")
    return df_grid

if __name__ == "__main__":
    generate_nairobi_grid()