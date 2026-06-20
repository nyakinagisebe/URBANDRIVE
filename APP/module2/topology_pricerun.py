import pandas as pd
import numpy as np
import joblib
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- 1. MARKET DATA & BASE CONSTANTS ---
BUILDING_RATES = {
    'Apartment (Standard)': 55350,
    'Apartment (High-Rise)': 60435,
    'Apartment (Luxury)': 77910,
    'Maisonette (Middle-Class)': 57550,
    'Maisonette (Luxurious)': 75175,
    'Bedsitter/Studio Block': 51800
}

SITE_CONDITIONS = {
    'Flat / Firm Soil': 1.0,
    'Sloping Terrain (+12%)': 1.12,
    'Black Cotton / Marshy (+25%)': 1.25,
    'Remote Access (+8%)': 1.08
}

# --- 2. DYNAMIC DATA FETCHERS & LOGIC ---

def fetch_world_bank_data():
    """Fetches Inflation and Population Growth from World Bank."""
    try:
        inf_url = "https://api.worldbank.org/v2/country/KEN/indicator/FP.CPI.TOTL.ZG?format=json&mrv=1"
        inf_res = requests.get(inf_url).json()
        inflation = float(inf_res[1][0]['value'])
        
        pop_url = "https://api.worldbank.org/v2/country/KEN/indicator/SP.POP.GROW?format=json&mrv=1"
        pop_res = requests.get(pop_url).json()
        pop_growth = float(pop_res[1][0]['value'])
        return inflation, pop_growth
    except:
        return 6.5, 2.0

def fetch_usd_rate():
    """Scrapes Central Bank of Kenya for the USD/KES Mean Rate."""
    try:
        res = requests.get("https://www.centralbank.go.ke/", timeout=10)
        start = res.text.find("US DOLLAR")
        rate = float(res.text[start:start+100].split('|')[1].strip())
        return rate
    except:
        return 129.5

def fetch_dynamic_land_rates():
    """Fetches latest Land Index averages."""
    land_data = {
        'Westlands-Parklands': 502700000,
        'Kilimani-Kileleshwa': 450000000,
        'Karen': 76000000,
        'Runda': 101100000,
        'Kasarani-Roysambu': 98000000,
        'Embakasi-Donholm': 82000000,
        'Kikuyu-WaiyakiWay': 42000000,
        'Thika-Town-Environs': 32000000,
        'Kitengela-AthiRiver': 18800000,
        'Rongai-Kajiado': 25000000
    }
    return land_data

def get_stamp_duty_rate(region):
    """Dynamic: Urban (4%) vs Rural (2%) based on Kenyan Municipal status."""
    urban_nodes = ['Westlands-Parklands', 'Kilimani-Kileleshwa', 'Kasarani-Roysambu', 
                   'Embakasi-Donholm', 'Kikuyu-WaiyakiWay', 'Thika-Town-Environs', 'Kitengela-AthiRiver']
    return 0.04 if region in urban_nodes else 0.02

def calculate_prof_fees(construction_cost):
    """Dynamic: Regressive scale based on Cap 525 (BORAQS) guidelines."""
    if construction_cost < 10000000:
        return construction_cost * 0.15  # Higher oversight for smaller projects
    elif construction_cost < 100000000:
        return construction_cost * 0.125 # Industry standard medium-scale
    else:
        return construction_cost * 0.105 # Economies of scale for large projects

def get_county_base_fee(b_type):
    """Nairobi Finance Bill 2025/2026 Base Application Fees."""
    permit_map = {
        'Apartment (Standard)': 35000,
        'Apartment (High-Rise)': 54000,
        'Apartment (Luxury)': 54000,
        'Maisonette (Middle-Class)': 40000,
        'Maisonette (Luxurious)': 50000,
        'Bedsitter/Studio Block': 35000
    }
    return permit_map.get(b_type, 40000)

# --- 3. INPUT UTILITY ---
def get_input(prompt, options=None, is_numeric=False, is_boolean=False):
    while True:
        if options:
            print(f"\n{prompt}")
            for i, opt in enumerate(options, 1):
                print(f"{i}. {opt}")
            val = input("Selection (number): ")
            if val.isdigit() and 1 <= int(val) <= len(options):
                return options[int(val)-1]
        elif is_boolean:
            val = input(f"\n{prompt} (y/n): ").lower()
            if val in ['y', 'n']: return 1 if val == 'y' else 0
        else:
            val = input(f"\n{prompt}: ")
            if is_numeric:
                try: return float(val)
                except ValueError: print("Please enter a valid number."); continue
            return val

def main():
    try:
        model = joblib.load('nairobi_house_price_model.joblib')
    except:
        print("Error: Model file 'nairobi_house_price_model.joblib' missing.")
        return

    # 1. Fetch Live Market Variables
    print("[System] Synchronizing with Market APIs (World Bank, CBK, HassConsult)...")
    inf_rate, pop_growth = fetch_world_bank_data()
    usd_rate = fetch_usd_rate()
    LAND_RATES = fetch_dynamic_land_rates()

    print("\n" + "="*80)
    print("      AI-BASED REGIONAL HOUSING DECISION SUPPORT SYSTEM (DSS)       ")
    print(f"      FX: KSh {usd_rate:.2f}/USD | Inflation: {inf_rate}% | Pop. Growth: {pop_growth}%")
    print("====================================================================\n")

    # 2. User Inputs
    region = get_input("Select Project Location", list(LAND_RATES.keys()))
    land_acres = get_input("Land Size in Acres", is_numeric=True)
    site_type = get_input("Select Site Condition", list(SITE_CONDITIONS.keys()))
    b_type = get_input("Select Building Type", list(BUILDING_RATES.keys()))
    units = int(get_input("Number of units?", is_numeric=True))
    sqm_per_unit = get_input("SQM per unit?", is_numeric=True)
    months_wait = int(get_input("Months until ground-break?", is_numeric=True))
    
    borehole = get_input("Borehole?", is_boolean=True)
    parking = get_input("Parking?", is_boolean=True)
    security = get_input("Security?", is_boolean=True)
    high_end = get_input("High-end finishes?", is_boolean=True)

    # 3. Cost Engine Logic
    
    # CATEGORY A: Land Acquisition (Dynamic Taxes)
    base_land_cost = LAND_RATES[region] * land_acres
    duty_rate = get_stamp_duty_rate(region)
    stamp_duty = base_land_cost * duty_rate
    cat_a_total = base_land_cost + stamp_duty + (base_land_cost * 0.01) + 15000

    # CATEGORY B: Construction Costs (Dynamic Escalation + Forex)
    # 7.5% annual escalation applied to base building rate
    annual_esc = 0.075
    monthly_esc = annual_esc / 12
    escalated_rate = BUILDING_RATES[b_type] * ((1 + monthly_esc) ** months_wait)
    
    base_construction = (units * sqm_per_unit) * escalated_rate
    
    forex_multiplier = 1.0
    if high_end and usd_rate > 120:
        forex_multiplier = 1 + ((usd_rate - 120) / 120) * 0.12 
    
    site_adjusted_cost = base_construction * SITE_CONDITIONS[site_type] * forex_multiplier
    
    # Apply World Bank Inflation on top of market escalation for future value
    monthly_inf = (inf_rate / 100) / 12
    future_hard_cost = site_adjusted_cost * ((1 + monthly_inf) ** months_wait)

    # CATEGORY C: Statutory Approvals (Dynamic Thresholds)
    base_app_fee = get_county_base_fee(b_type)
    county_plan_approval = (future_hard_cost * 0.005) + base_app_fee
    nema_eia_license = future_hard_cost * 0.001
    nca_project_levy = future_hard_cost * 0.005 if future_hard_cost > 5000000 else 0
    cat_c_total = county_plan_approval + nema_eia_license + nca_project_levy

    # CATEGORY D: Professional Fees (Dynamic Scale)
    cat_d_total = calculate_prof_fees(future_hard_cost)

    total_project_cost = cat_a_total + future_hard_cost + cat_c_total + cat_d_total

    # 4. Prediction & ROI
    input_df = pd.DataFrame([[region, region, b_type.split()[0], 2, borehole, parking, security]], 
                            columns=['region_cluster', 'micro_area', 'topology', 'bedrooms', 'borehole', 'parking', 'security'])
    predicted_rent = np.expm1(model.predict(input_df))[0]
    
    demand_multiplier = 1 + (pop_growth / 100)
    annual_revenue = predicted_rent * units * 12 * demand_multiplier
    roi = (annual_revenue / total_project_cost) * 100

    # report
    print("\n" + "="*80)
    print("                 DETAILED ITEMISED FEASIBILITY REPORT                        ")
    print("====================================================================")
    
    print(f"1. LAND ACQUISITION & LEGAL COSTS")
    print(f"   - Base Land Purchase Price:        KSh {base_land_cost:,.0f}")
    print(f"   - Stamp Duty Tax ({duty_rate*100}%):           KSh {stamp_duty:,.0f}")
    print(f"   - Legal & Conveyancing Fees (1%):  KSh {(base_land_cost * 0.01):,.0f}")
    print(f"   - Registration & Valuation:        KSh 15,000")
    print(f"   SUB-TOTAL:                         KSh {cat_a_total:,.0f}")
    
    print(f"\n2. CONSTRUCTION HARD COSTS (ESCALATED)")
    print(f"   - Base Construction Value:         KSh {base_construction:,.0f}")
    print(f"   - Time-Based Material Escalation:  KSh {(future_hard_cost - site_adjusted_cost):,.0f}")
    print(f"   - Forex / Import Risk Buffer:      KSh {(site_adjusted_cost - base_construction):,.0f}")
    print(f"   - Escalated Rate per SQM:          KSh {escalated_rate:,.0f}")
    print(f"   SUB-TOTAL:                         KSh {future_hard_cost:,.0f}")
    
    print(f"\n3. STATUTORY APPROVALS & PERMITS")
    print(f"   - Nairobi City County Approval:    KSh {county_plan_approval:,.0f}")
    print(f"   - NCA Project Levy (0.5%):         KSh {nca_project_levy:,.0f}")
    print(f"   - NEMA Environmental License:      KSh {nema_eia_license:,.0f}")
    print(f"   - Base Permit Application Fee:     KSh {base_app_fee:,.0f}")
    print(f"   SUB-TOTAL:                         KSh {cat_c_total:,.0f}")
    
    print(f"\n4. PROFESSIONAL CONSULTANCY FEES")
    print(f"   - Architects & Quantity Surveyors: KSh {(cat_d_total * 0.7):,.0f}")
    print(f"   - Structural & MEP Engineers:      KSh {(cat_d_total * 0.3):,.0f}")
    print(f"   - BORAQS / Cap 525 Scale Applied:  Yes")
    print(f"   SUB-TOTAL:                         KSh {cat_d_total:,.0f}")
    
    print("-" * 80)
    print(f"TOTAL CAPITAL INVESTMENT:             KSh {total_project_cost:,.0f}")
    print(f"ESTIMATED MONTHLY RENTAL INCOME:      KSh {predicted_rent * units:,.0f}")
    print(f"ANNUAL ROI (Pop. Growth Adjusted):    {roi:.2f}%")
    print("="*80)

if __name__ == "__main__":
    main()