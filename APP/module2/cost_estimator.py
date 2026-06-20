import pandas as pd  # Python Data Analysis Library
import numpy as np   # Numerical Python Library
import joblib

# --- UPDATED DATA CONSTANTS ---

BUILDING_RATES = {
    'Apartment (Standard)': 61610,
    'Apartment (High-Rise)': 68290,
    'Mansionette (Middle-Class)': 61070,
    'Mansionette (Luxurious)': 94270,
    'Bedsitter/Studio Block': 58000
}

LAND_RATES = {
    'Westlands-Parklands': 487000000,
    'Kilimani-Kileleshwa': 361000000,
    'Kasarani-Roysambu': 95000000,
    'Embakasi-Donholm': 78000000,
    'Kikuyu-WaiyakiWay': 38000000,
    'Thika-Town-Environs': 29000000,
    'Kitengela-AthiRiver': 15000000,
    'Rongai-Kajiado': 25000000
}

CIPI_DATA = {
    'Glass_and_Putty': 126.35 # Source: Kenya National Bureau of Statistics
}

def get_input(prompt, options=None, is_numeric=False):
    while True:
        if options:
            print(f"\n{prompt}")
            for i, opt in enumerate(options, 1):
                print(f"{i}. {opt}")
            val = input("Selection (number): ")
            if val.isdigit() and 1 <= int(val) <= len(options):
                return options[int(val)-1]
        else:
            val = input(f"\n{prompt}: ")
            if is_numeric:
                try:
                    return float(val)
                except ValueError:
                    print("Error: Please enter a valid number.")
                    continue
            return val
        print("Invalid selection.")

def main():
    try:
        model = joblib.load('nairobi_house_price_model.joblib')
    except:
        print("Error: Model file not found.")
        return

    print("--- KENYA PROPERTY FEASIBILITY TOOL (RELIABLE VERSION) ---")

    # 1. Location & Land
    regions = list(LAND_RATES.keys())
    region = get_input("Select Region", regions)
    land_acres = get_input("Land Size in Acres (e.g. 0.125)", is_numeric=True)
    
    # 2. Building Scale
    build_types = list(BUILDING_RATES.keys())
    b_type = get_input("Building Type", build_types)
    units = int(get_input("Number of Units", is_numeric=True))
    sqm_per_unit = get_input("Avg SQM per Unit", is_numeric=True)
    bedrooms = int(get_input("Bedrooms per unit", is_numeric=True))

    # --- CALCULATIONS ---

    # A. Costs
    land_cost = (LAND_RATES[region] * land_acres) * 1.04 # Price + 4% Stamp Duty
    
    # Pure Construction Cost adjusted by Glass Index
    glass_factor = (CIPI_DATA['Glass_and_Putty'] / 100) * 0.05
    base_construction = (units * sqm_per_unit) * BUILDING_RATES[b_type] * (1 + glass_factor)
    
    # Soft Costs & Fees
    gov_fees = base_construction * 0.02 # NCA 0.5% + NEMA 0.1% + County ~1.4%
    pro_fees = base_construction * 0.12 # Architects/Engineers
    
    total_investment = land_cost + base_construction + gov_fees + pro_fees

    # B. Income (Predictions)
    input_data = pd.DataFrame([[
        region, region, b_type.split()[0], bedrooms, 1, 1, 1
    ]], columns=['region_cluster', 'micro_area', 'topology', 'bedrooms', 'borehole', 'parking', 'security'])
    
    pred_rent = np.expm1(model.predict(input_data))[0]
    
    # C. NEW: Realistic Operating Deductions
    gross_annual = pred_rent * units * 12
    vacancy_loss = gross_annual * 0.10 # 10% vacancy/bad debt
    effective_gross = gross_annual - vacancy_loss
    
    # Operating Expenses (Maintenance, Management, Security, Insurance)
    opex = effective_gross * 0.15 # Standard 15% for OPEX
    land_rates_annual = land_cost * 0.001 # Estimated annual county rates
    
    # Statutory Tax (KRA Residential Rental Income Tax)
    kra_tax = effective_gross * 0.075 
    
    # Final Net Profit
    net_annual_profit = effective_gross - opex - land_rates_annual - kra_tax
    
    # D. Metrics
    roi_percent = (net_annual_profit / total_investment) * 100
    payback_years = total_investment / net_annual_profit

    print("\n" + "="*50)
    print(f"INVESTMENT SUMMARY FOR {region.upper()}")
    print("="*50)
    print(f"Total Project Capital:   KSh {total_investment:,.0f}")
    print(f"Pure Construction Cost:  KSh {base_construction:,.0f}")
    print(f"Monthly Rent (Per Unit): KSh {pred_rent:,.0f}")
    print("-" * 50)
    print(f"Net Annual Profit:       KSh {net_annual_profit:,.0f}")
    print(f"Return on Investment:    {roi_percent:.2f}% per year")
    print(f"PAYBACK PERIOD:          {payback_years:.1f} YEARS")
    print("="*50)
    print("Note: This includes 15% Operating Expenses and 10% Vacancy.")

if __name__ == "__main__":
    main()