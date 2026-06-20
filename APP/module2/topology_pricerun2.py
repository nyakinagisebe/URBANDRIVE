import pandas as pd
import numpy as np
import joblib
import requests
import json
from datetime import datetime

# --- 1. MARKET DATA CONSTANTS ---
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

# --- 2. DYNAMIC DATA FETCHERS ---
def fetch_world_bank_data():
    try:
        inf_url = "https://api.worldbank.org/v2/country/KEN/indicator/FP.CPI.TOTL.ZG?format=json&mrv=1"
        inf_res = requests.get(inf_url).json()
        inflation = float(inf_res[1][0]['value'])
        pop_url = "https://api.worldbank.org/v2/country/KEN/indicator/SP.POP.GROW?format=json&mrv=1"
        pop_res = requests.get(pop_url).json()
        pop_growth = float(pop_res[1][0]['value'])
        return inflation, pop_growth
    except: return 6.5, 2.0

def fetch_usd_rate():
    try:
        res = requests.get("https://www.centralbank.go.ke/", timeout=10)
        start = res.text.find("US DOLLAR")
        rate = float(res.text[start:start+100].split('|')[1].strip())
        return rate
    except: return 129.5

def get_stamp_duty_rate(region):
    urban_nodes = ['WESTLANDS-PARKLANDS', 'KILIMANI-KILELESHWA', 'KASARANI-ROYSAMBU', 
                   'EMBAKASI-DONHOLM', 'KIKUYU-WAIYAKIWAY', 'THIKA-TOWN-ENVIRONS', 'KITENGELA-ATHIRIVER']
    return 0.04 if region.upper() in urban_nodes else 0.02

def calculate_prof_fees(construction_cost):
    """Regressive scale based on BORAQS / Cap 525 guidelines."""
    if construction_cost < 10000000: return construction_cost * 0.15
    elif construction_cost < 100000000: return construction_cost * 0.125
    else: return construction_cost * 0.105

# --- 3. INPUT UTILITY ---
def get_input(prompt, options=None, is_numeric=False, is_boolean=False):
    while True:
        if options:
            print(f"\n{prompt}")
            for i, opt in enumerate(options, 1): print(f"{i}. {opt}")
            val = input("Selection (number): ")
            if val.isdigit() and 1 <= int(val) <= len(options): return options[int(val)-1]
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
    # 1. Load Model & Knowledge Base
    try:
        model = joblib.load('final_nairobi_price_model.joblib')
        with open('location_knowledge.json', 'r') as f:
            KNOWLEDGE = json.load(f)
    except Exception as e:
        print(f"Error loading system files: {e}")
        return

    # 2. Fetch Live Market Variables
    print("[System] Synchronizing with Market APIs (World Bank, CBK)...")
    inf_rate, pop_growth = fetch_world_bank_data()
    usd_rate = fetch_usd_rate()

    print("\n" + "="*80)
    print("      AI-BASED REGIONAL HOUSING DECISION SUPPORT SYSTEM (DSS)       ")
    print(f"      FX: KSh {usd_rate:.2f}/USD | Inflation: {inf_rate}% | Pop. Growth: {pop_growth}%")
    print("====================================================================\n")

    # 3. User Inputs
    available_regions = sorted(list(KNOWLEDGE['region_cluster'].keys()))
    region = get_input("Select Project Location", available_regions)
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

    # 4. Feature Processing for AI Prediction
    region_upper = region.upper().strip()
    topology_upper = b_type.split()[0].upper().strip()
    
    reg_avg = KNOWLEDGE['region_cluster'].get(region_upper, 50000)
    topo_avg = KNOWLEDGE['topology'].get(topology_upper, 60000)

    input_df = pd.DataFrame([{
        'region_cluster': region_upper,
        'micro_area': region_upper,
        'topology': topology_upper,
        'region_cluster_avg_price': reg_avg,
        'micro_area_avg_price': reg_avg,
        'topology_avg_price': topo_avg,
        'borehole': borehole,
        'parking': parking,
        'security': security
    }])

    for col in ['region_cluster', 'micro_area', 'topology']:
        input_df[col] = input_df[col].astype('category')

    # AI Prediction (Rent)
    predicted_rent = np.expm1(model.predict(input_df))[0]

    # --- 5. COST ENGINE CALCULATIONS ---
    
    # CATEGORY A: Land & Legal
    land_rate = KNOWLEDGE['land_rates'].get(region_upper, 25000000) 
    base_land_cost = land_rate * land_acres
    duty_rate = get_stamp_duty_rate(region_upper)
    stamp_duty = base_land_cost * duty_rate
    legal_fees = base_land_cost * 0.01
    cat_a_total = base_land_cost + stamp_duty + legal_fees + 15000

    # CATEGORY B: Construction Hard Costs
    annual_esc = 0.075
    monthly_esc = annual_esc / 12
    escalated_rate = BUILDING_RATES[b_type] * ((1 + monthly_esc) ** months_wait)
    
    base_construction = (units * sqm_per_unit) * escalated_rate
    forex_multiplier = 1 + ((usd_rate - 120) / 120) * 0.12 if (high_end and usd_rate > 120) else 1.0
    
    site_adjusted_cost = base_construction * SITE_CONDITIONS[site_type] * forex_multiplier
    monthly_inf = (inf_rate / 100) / 12
    future_hard_cost = site_adjusted_cost * ((1 + monthly_inf) ** months_wait)

    # CATEGORY C: Statutory Fees
    # (NCA 0.5%, NEMA 0.1%, County ~0.5%)
    cat_c_total = (future_hard_cost * 0.011) + 40000 

    # CATEGORY D: Professional Fees
    cat_d_total = calculate_prof_fees(future_hard_cost)

    # SUMMATION
    total_project_cost = cat_a_total + future_hard_cost + cat_c_total + cat_d_total
    
    # ROI Logic
    demand_multiplier = 1 + (pop_growth / 100)
    annual_revenue = predicted_rent * units * 12 * demand_multiplier
    roi = (annual_revenue / total_project_cost) * 100

    # --- 6. FINAL ITEMIZED FEASIBILITY REPORT ---
    print("\n" + "="*80)
    print("                ITEMIZED CAPITAL INVESTMENT BREAKDOWN                       ")
    print("====================================================================")
    
    print(f"1. LAND ACQUISITION & LEGAL (CAT A):  KSh {cat_a_total:,.2f}")
    print(f"   - Purchase Price: KSh {base_land_cost:,.0f}")
    print(f"   - Taxes & Fees:   KSh {(stamp_duty + legal_fees):,.0f}")
    
    print(f"\n2. CONSTRUCTION HARD COSTS (CAT B):   KSh {future_hard_cost:,.2f}")
    print(f"   - Escalated Rate: KSh {escalated_rate:,.0f} per SQM")
    print(f"   - Incl. Site Condition & Forex Risk Adjustments")
    
    print(f"\n3. STATUTORY FEES & PERMITS (CAT C):  KSh {cat_c_total:,.2f}")
    print(f"   - NCA Project Levy, NEMA License, County Plan Approval")
    
    print(f"\n4. PROFESSIONAL CONSULTANCY (CAT D):  KSh {cat_d_total:,.2f}")
    print(f"   - Architect, QS, Engineers (Cap 525 Scale)")
    
    print("-" * 80)
    print(f"TOTAL CAPITAL INVESTMENT:             KSh {total_project_cost:,.2f}")
    print(f"ESTIMATED MONTHLY RENT (PER UNIT):    KSh {predicted_rent:,.2f}")
    print(f"ESTIMATED TOTAL MONTHLY INCOME:       KSh {predicted_rent * units:,.2f}")
    print(f"PROJECTED ANNUAL ROI:                 {roi:.2f}%")
    print("="*80)
    
    # Decision Matrix
    if roi > 12:
        print("DECISION: HIGHLY FEASIBLE - ROI exceeds Kenyan real estate benchmark (12%).")
    elif roi > 8:
        print("DECISION: FEASIBLE - Average market performance.")
    else:
        print("DECISION: MARGINAL - ROI below threshold; check land cost or density.")
    print("="*80)

if __name__ == "__main__":
    main()