import pandas as pd
import json

def extract_knowledge():
    files = ['nairobi_full_market_data2.csv', 'nairobi_comprehensive_dataset.csv', 'nairobi_market_dataset.csv']
    all_dfs = []
    
    # Define possible column names for regions and prices
    region_aliases = ['region_cluster', 'location', 'area', 'micro_area']
    price_aliases = ['price_ksh', 'price', 'rent']

    for f in files:
        try:
            df = pd.read_csv(f)
            # Rename columns to a standard name if they match our aliases
            df.columns = [col.lower().strip() for col in df.columns]
            
            # Smart renaming to 'region_cluster' and 'price_ksh'
            for alias in region_aliases:
                if alias in df.columns:
                    df = df.rename(columns={alias: 'region_cluster'})
                    break
            for alias in price_aliases:
                if alias in df.columns:
                    df = df.rename(columns={alias: 'price_ksh'})
                    break
            
            # Only keep what we need to save memory
            if 'region_cluster' in df.columns and 'price_ksh' in df.columns:
                all_dfs.append(df[['region_cluster', 'price_ksh']])
            
        except Exception as e:
            print(f"Skipping {f} due to error: {e}")

    # Combine everything
    master_df = pd.concat(all_dfs, ignore_index=True)

    # --- CLEANING THE MESS ---
    # 1. Force everything to uppercase string
    master_df['region_cluster'] = master_df['region_cluster'].astype(str).str.upper().str.strip()
    
    # 2. Drop the "NAN", "NONE", and empty strings
    garbage = ['NAN', 'NONE', '', 'UNKNOWN', 'N/A', 'UNDEFINED']
    master_df = master_df[~master_df['region_cluster'].isin(garbage)]
    
    # 3. Final Grouping (Including every valid unique name)
    region_avgs = master_df.groupby('region_cluster')['price_ksh'].mean().to_dict()
    
    # Default Land Rates for your report logic
    land_rates = {
        'WESTLANDS-PARKLANDS': 502700000, 'KILIMANI-KILELESHWA': 450000000,
        'KAREN': 76000000, 'RUNDA': 101100000, 'KASARANI-ROYSAMBU': 98000000,
        'EMBAKASI-DONHOLM': 82000000, 'KIKUYU-WAIYAKIWAY': 42000000,
        'THIKA-TOWN-ENVIRONS': 32000000, 'KITENGELA-ATHIRIVER': 18800000,
        'RONGAI-KAJIADO': 25000000
    }

    # Save the "Brain"
    knowledge = {
        'region_cluster': region_avgs,
        'topology': {'APARTMENT': 65000, 'MAISONETTE': 110000, 'BEDSITTER': 15000}, # Defaults
        'land_rates': land_rates
    }

    with open('location_knowledge.json', 'w') as f:
        json.dump(knowledge, f, indent=4)

    print(f"Success! {len(region_avgs)} unique locations found across all files.")

if __name__ == "__main__":
    extract_knowledge()