import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import pandas as pd
import numpy as np
import joblib
import sqlite3
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# user session linked to query params for report saving
query_params = st.query_params

if "user_id" in query_params:
    st.session_state["user_id"] = query_params["user_id"]

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="URBANDRIVE KENYA", layout="wide", page_icon="🏠")

# ====================== CUSTOM CSS & NAVIGATION ======================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');
    
    body { font-family: 'Inter', sans-serif; }
    .logo-font { font-family: 'Space Grotesk', sans-serif; }
    
    /* 1. HIDE THE SIDEBAR AND TOP HEADER BAR */
    [data-testid="stSidebar"], header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 2. RECTANGULAR FLOATING BUTTON STYLING */
    .back-nav-container {
        position: fixed;
        top: 20px;
        left: 20px;
        z-index: 1000000;
    }

    .back-btn-rect {
        background-color: #166534;
        color: white !important;
        padding: 12px 24px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        border: 1px solid rgba(255,255,255,0.1);
    }

    .back-btn-rect:hover {
        background-color: #15803d;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        text-decoration: none;
    }

    /* 3. MAIN CONTENT SPACING */
    .main .block-container {
        padding-top: 5rem !important;
        max-width: 1200px;
    }

    .stButton>button {
        background-color: #166534;
        color: white;
        border-radius: 12px;
        height: 52px;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .input-card, .report-card {
        background-color: white;
        padding: 32px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #f1f5f9;
    }
    
    .step-container {
        display: flex; align-items: center; gap: 12px; margin: 20px 0 35px 0;
    }
    .step {
        width: 32px; height: 32px; border-radius: 50%; display: flex;
        align-items: center; justify-content: center; font-weight: 600;
        border: 3px solid #166534; background: white; color: #166534;
    }
    .step-active { background: #166534; color: white; }
    .step-line { flex: 1; height: 3px; background: linear-gradient(to right, #166534, #86efac); }
    
    .verdict-go { background-color: #d4edda; color: #155724; padding: 18px; border-radius: 12px; 
                  border-left: 6px solid #28a745; font-weight: bold; text-align: center; font-size: 20px; }
    .verdict-no { background-color: #f8d7da; color: #721c24; padding: 18px; border-radius: 12px; 
                  border-left: 6px solid #dc3545; font-weight: bold; text-align: center; font-size: 20px; }
    </style>

    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    
    <div class="back-nav-container">
        <a href="./user_dash.html" class="back-btn-rect" target="_self">
            <i class="fa-solid fa-arrow-left"></i>
            BACK TO DASHBOARD
        </a>
    </div>
    """, unsafe_allow_html=True)

# ====================== SESSION STATE ======================
if 'step' not in st.session_state:
    st.session_state.step = 1

if 'current_page' not in st.session_state:
    st.session_state.current_page = "Analysis"

if 'user_role' not in st.session_state:
    st.session_state.user_role = "user"

if "user_id" not in st.session_state:
    st.session_state.user_id = 1




# Get user_id from query params (from login.html)
query_params = st.query_params
if "user_id" in query_params:
    st.session_state["user_id"] = query_params["user_id"]
elif "user_id" not in st.session_state:
    st.session_state["user_id"] = 1  # fallback


    

# ====================== FUNCTIONS ======================
@st.cache_data(ttl=86400)
def fetch_live_market_data():
    data = {"inflation": 6.8, "pop_growth": 2.2, "usd_rate": 129.50}
    try:
        wb_url = "https://api.worldbank.org/v2/country/KEN/indicator/{}?format=json&per_page=1"
        inf_resp = requests.get(wb_url.format("FP.CPI.TOTL.ZG")).json()
        if len(inf_resp) > 1 and inf_resp[1]: 
            data["inflation"] = float(inf_resp[1][0]['value'])
        
        pop_resp = requests.get(wb_url.format("SP.POP.GROW")).json()
        if len(pop_resp) > 1 and pop_resp[1]: 
            data["pop_growth"] = float(pop_resp[1][0]['value'])

        cbk_url = "https://www.centralbank.go.ke/rates/forex-exchange-rates/"
        cbk_resp = requests.get(cbk_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(cbk_resp.content, 'html.parser')
        table = soup.find('table')
        if table:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) > 0 and 'US DOLLAR' in cols[0].text.upper():
                    data["usd_rate"] = float(cols[3].text)
                    break
    except:
        pass 
    return data

@st.cache_resource
def load_assets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    m1_model_p = os.path.join(base_dir, "nairobi_investment_model.pkl")
    m2_model_p = os.path.join(os.path.dirname(base_dir), "module2", "nairobi_house_price_model.joblib")
    db_p = os.path.join(base_dir, "housing_intelligence.db")

    if not os.path.exists(m1_model_p):
        m1_model_p = os.path.join(base_dir, "module1", "nairobi_investment_model.pkl")
        db_p = os.path.join(base_dir, "module1", "housing_intelligence.db")
        m2_model_p = os.path.join(base_dir, "module2", "nairobi_house_price_model.joblib")

    sp_model = joblib.load(m1_model_p)
    fi_model = joblib.load(m2_model_p)
    conn = sqlite3.connect(db_p)
    infra_df = pd.read_sql("SELECT * FROM investment_master", conn)
    conn.close()
    
    geolocator = Nominatim(user_agent="urbandrive_app")

    filters = {
        'transport': "highway in ['motorway', 'trunk', 'primary']", 
        'retail': "shop in ['mall', 'supermarket'] or amenity == 'marketplace'",
        'health': "amenity == 'hospital' or amenity == 'clinic'", 
        'edu': "amenity == 'university' or amenity == 'school'",
        'jobs': "office.notnull() or landuse in ['industrial', 'commercial']"
    }
    return sp_model, fi_model, infra_df, filters, geolocator

def get_professional_breakdown(p, market):
    land_rates = {
        'Westlands-Parklands': 502700000, 'Kilimani-Kileleshwa': 450000000, 'Karen': 76000000,
        'Runda': 101100000, 'Kasarani-Roysambu': 98000000, 'Embakasi-Donholm': 82000000,
        'Kikuyu-WaiyakiWay': 42000000, 'Thika-Town-Environs': 32000000, 
        'Kitengela-AthiRiver': 18800000, 'Rongai-Kajiado': 25000000
    }
    
    base_land = land_rates.get(p['region'], 25000000) * p['acres']
    duty_rate = 0.04 if p['region'] not in ['Karen', 'Runda'] else 0.02
    stamp_duty = base_land * duty_rate
    legal_fees = base_land * 0.01
    cat_a_total = base_land + stamp_duty + legal_fees + 15000

    rates = {
        'Apartment (Standard)': 55350, 'Apartment (High-Rise)': 60435, 'Apartment (Luxury)': 77910, 
        'Maisonette (Middle-Class)': 57550, 'Maisonette (Luxurious)': 75175, 'Bedsitter/Studio Block': 51800
    }
    
    base_construction = (p['units'] * p['sqm']) * rates[p['b_type']]
    site_mult = {'Flat / Firm Soil': 1.0, 'Sloping Terrain (+12%)': 1.12, 'Black Cotton / Marshy (+25%)': 1.25}[p['site']]
    site_adjusted_cost = base_construction * site_mult
    
    inf_factor = (market['inflation'] / 100) / 12
    time_escalation = site_adjusted_cost * ((1 + inf_factor) ** p['wait']) - site_adjusted_cost
    
    forex_risk = max(0, (market['usd_rate'] - 120) / 120)
    forex_buffer = site_adjusted_cost * forex_risk if p['high_end'] else 0
    
    future_hard_cost = site_adjusted_cost + time_escalation + forex_buffer
    escalated_rate = future_hard_cost / (p['units'] * p['sqm'])

    nca_levy = future_hard_cost * 0.005
    nema_license = future_hard_cost * 0.001
    county_approval = (future_hard_cost * 0.0001) + 25000 
    cat_c_total = nca_levy + nema_license + county_approval + 5000
    cat_d_total = future_hard_cost * 0.12 
    
    return {
        "total": cat_a_total + future_hard_cost + cat_c_total + cat_d_total,
        "cat_a": {"base": base_land, "duty": stamp_duty, "legal": legal_fees, "reg": 15000, "total": cat_a_total, "rate": duty_rate},
        "cat_b": {"base": base_construction, "escalation": time_escalation, "forex": forex_buffer, "total": future_hard_cost, "rate_sqm": escalated_rate},
        "cat_c": {"county": county_approval, "nca": nca_levy, "nema": nema_license, "base_fee": 5000, "total": cat_c_total},
        "cat_d": {"arch_qs": cat_d_total * 0.7, "eng": cat_d_total * 0.3, "total": cat_d_total}
    }

# ====================== MAIN CONTENT ======================
st.title("Start New Analysis")

st.markdown("""
<div class="step-container">
    <div class="step step-active">1</div>
    <div class="step-line"></div>
    <div class="step">2</div>
</div>
""", unsafe_allow_html=True)

if st.session_state.step == 1:
    st.markdown("**Step 1 of 2:** Input regional data for housing needs assessment")
    
    with st.container():
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        st.subheader("Regional Information")
        
        col1, col2 = st.columns(2)
        with col1:
            locations = ["Westlands-Parklands", "Kilimani-Kileleshwa", "Karen", "Runda", "Kasarani-Roysambu", 
                         "Embakasi-Donholm", "Kikuyu-WaiyakiWay", "Thika-Town-Environs", 
                         "Kitengela-AthiRiver", "Rongai-Kajiado"]
            region = st.selectbox("Investment Node", options=[""] + locations)
            b_type = st.selectbox("Building Type", 
                                  options=["", "Apartment (Standard)", "Apartment (High-Rise)", 
                                           "Apartment (Luxury)", "Maisonette (Middle-Class)", 
                                           "Maisonette (Luxurious)", "Bedsitter/Studio Block"])
        with col2:
            units = st.number_input("Total Units", min_value=0, step=1, value=0)
            sqm = st.number_input("Avg Unit Size (SQM)", min_value=0, step=1, value=0)
            acres = st.number_input("Land Size (Acres)", min_value=0.0, format="%.2f", value=0.0)

        st.markdown("---")
        with st.expander("⚙️ Risk & Site Variables", expanded=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                site = st.selectbox("Soil/Terrain", ["Flat / Firm Soil", "Sloping Terrain (+12%)", "Black Cotton / Marshy (+25%)"])
            with col_b:
                wait = st.slider("Commencement Lead Time (Months)", 0, 24, 0)
            with col_c:
                high_end = st.checkbox("High-End Finishes (Forex Risk)")
                security = st.checkbox("Advanced Security Systems")
        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("📍 Project Location")
    m = folium.Map(location=[-1.286389, 36.817223], zoom_start=11, tiles="cartodbpositron")
    st_folium(m, width="100%", height=420)

    if st.button("Review Data →", type="primary", use_container_width=True):
        if region and b_type and units > 0 and sqm > 0 and acres > 0:
            st.session_state.region = region
            st.session_state.b_type = b_type
            st.session_state.units = units
            st.session_state.sqm = sqm
            st.session_state.acres = acres
            st.session_state.site = site
            st.session_state.wait = wait
            st.session_state.high_end = high_end
            st.session_state.security = security
            st.session_state.step = 2
            st.rerun()
        else:
            st.warning("Please fill all required fields.")

else:
    st.subheader("Investment Analysis Report")
    market_data = fetch_live_market_data()
    sp_model, fi_model, infra_df, infra_filters, geolocator = load_assets()

    loc = geolocator.geocode(f"{st.session_state.region}, Nairobi, Kenya")
    lat, lon = (loc.latitude, loc.longitude) if loc else (-1.286, 36.817)
    
    res = get_professional_breakdown({
        'region': st.session_state.region, 'acres': st.session_state.acres, 
        'site': st.session_state.site, 'b_type': st.session_state.b_type, 
        'units': st.session_state.units, 'sqm': st.session_state.sqm, 
        'wait': st.session_state.wait, 'high_end': st.session_state.high_end
    }, market_data)
    
    topology_map = st.session_state.b_type.split()[0]
    input_df = pd.DataFrame([[st.session_state.region, st.session_state.region, topology_map, 2, 1, 1, 1 if st.session_state.security else 0]], 
                            columns=['region_cluster', 'micro_area', 'topology', 'bedrooms', 'borehole', 'parking', 'security'])
    rent = np.expm1(fi_model.predict(input_df))[0]
    roi = ((rent * st.session_state.units * 12) / res['total']) * 100

    st.subheader("📍 Project Location & Nearby Infrastructure")
    col_map, col_list = st.columns([2, 1])
    with col_map:
        m = folium.Map(location=[lat, lon], zoom_start=14)
        folium.Marker([lat, lon], icon=folium.Icon(color='blue', icon='home')).add_to(m)
        st_folium(m, width="100%", height=450)

    with col_list:
        st.write("**Nearby Facilities (3km Radius)**")
        for cat, query in infra_filters.items():
            subset = infra_df.query(query).copy()
            subset['dist'] = np.sqrt((subset.lat - lat)**2 + (subset.lon - lon)**2) * 111.32
            nearby = subset[subset.dist <= 3.0].sort_values('dist').head(2)
            if not nearby.empty:
                st.markdown(f"**{cat.upper()}**")
                for _, row in nearby.iterrows():
                    st.write(f"• {row['name']} ({row['dist']:.2f}km)")

    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.subheader("💰 Investment Analysis Report")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Investment", f"KSh {res['total']/1e6:.1f}M")
    c2.metric("Monthly Revenue", f"KSh {rent*st.session_state.units:,.0f}")
    c3.metric("Annual ROI", f"{roi:.2f}%")

    with st.expander("View Full Financial Schedule", expanded=True):
        st.write("### 1. LAND ACQUISITION & LEGAL COSTS")
        st.write(f"- Base Land Purchase Price: KSh {res['cat_a']['base']:,.0f}")
        st.write(f"- Stamp Duty Tax ({res['cat_a']['rate']*100}%): KSh {res['cat_a']['duty']:,.0f}")
        st.write(f"- Legal & Conveyancing Fees (1%): KSh {res['cat_a']['legal']:,.0f}")
        st.write(f"- Registration & Valuation: KSh 15,000")
        st.write(f"**SUB-TOTAL: KSh {res['cat_a']['total']:,.0f}**")
        
        st.write("---")
        st.write("### 2. CONSTRUCTION HARD COSTS (ESCALATED)")
        st.write(f"- Base Construction Value: KSh {res['cat_b']['base']:,.0f}")
        st.write(f"- Time-Based Material Escalation: KSh {res['cat_b']['escalation']:,.0f}")
        st.write(f"- Forex / Import Risk Buffer: KSh {res['cat_b']['forex']:,.0f}")
        st.write(f"- Escalated Rate per SQM: KSh {res['cat_b']['rate_sqm']:,.0f}")
        st.write(f"**SUB-TOTAL: KSh {res['cat_b']['total']:,.0f}**")

        st.write("---")
        st.write("### 3. STATUTORY APPROVALS & PERMITS")
        st.write(f"- Nairobi City County Approval: KSh {res['cat_c']['county']:,.0f}")
        st.write(f"- National Construction Authority Project Levy (0.5%): KSh {res['cat_c']['nca']:,.0f}")
        st.write(f"- National Environment Management Authority Environmental License: KSh {res['cat_c']['nema']:,.0f}")
        st.write(f"- Base Permit Application Fee: KSh {res['cat_c']['base_fee']:,.0f}")
        st.write(f"**SUB-TOTAL: KSh {res['cat_c']['total']:,.0f}**")

        st.write("---")
        st.write("### 4. PROFESSIONAL CONSULTANCY FEES")
        st.write(f"- Architects & Quantity Surveyors: KSh {res['cat_d']['arch_qs']:,.0f}")
        st.write(f"- Structural & MEP Engineers: KSh {res['cat_d']['eng']:,.0f}")
        st.write(f"**SUB-TOTAL: KSh {res['cat_d']['total']:,.0f}**")

    benchmark = market_data['inflation'] + 3.0
    is_go = roi > benchmark

    if is_go:
        st.markdown(f"<div class='verdict-go'>✅ INVESTMENT VERDICT: GO (ROI {roi:.1f}% > Benchmark {benchmark:.1f}%)</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='verdict-no'>❌ INVESTMENT VERDICT: NO-GO (ROI {roi:.1f}% < Benchmark {benchmark:.1f}%)</div>", unsafe_allow_html=True)

        if st.button("💾 Save Report to Database", use_container_width=True, type="primary"):
            payload = {
                "user_id": int(st.session_state.get("user_id", 1)),
                "report_title": f"{st.session_state.region} - {st.session_state.b_type} Analysis",
                "region": st.session_state.region,
                "building_type": st.session_state.b_type,
                "units": int(st.session_state.units),
                "avg_unit_size_sqm": int(st.session_state.sqm),
                "land_size_acres": float(st.session_state.acres),
                "soil_condition": st.session_state.site,
                "commencement_lead_time_months": int(st.session_state.wait),
                "high_end_finishes": bool(st.session_state.high_end),
                "advanced_security": bool(st.session_state.security),
                "gps_latitude": float(lat),
                "gps_longitude": float(lon),
                "total_investment": float(res['total']),
                "projected_monthly_revenue": float(rent * st.session_state.units),
                "annual_roi": float(roi),
                "verdict": "GO" if is_go else "NO-GO",

                "details": [
                    {"category": "LAND", "item_name": "Total Land Cost", "amount_kes": float(res['cat_a']['total'])},
                    {"category": "CONSTRUCTION", "item_name": "Hard Costs", "amount_kes": float(res['cat_b']['total'])},
                    {"category": "PERMITS", "item_name": "Statutory Fees", "amount_kes": float(res['cat_c']['total'])},
                    {"category": "CONSULTANCY", "item_name": "Professional Fees", "amount_kes": float(res['cat_d']['total'])}
                ]
            }

            try:
                response = requests.post(
                    "http://127.0.0.1:5000/save-report", 
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        report_id = result.get('report_id', 'N/A')
                        st.success(f"✅ Report saved successfully! (ID: {report_id})")
                        
                        # Direct link to Reports page
                        st.markdown(f"""
                            <a href="http://127.0.0.1:5500/user_reports.html" target="_blank" 
                            style="color:#166534; font-weight:600; text-decoration:underline;">
                                → View All My Reports
                            </a>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(result.get("message", "Failed to save report"))
                else:
                    st.error(f"Server returned status code: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to server. Make sure Flask backend is running on port 5000.")
            except Exception as e:
                st.error(f"❌ Error saving report: {str(e)}")
    
    if st.button("← Start New Analysis"):
        st.session_state.step = 1
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("© 2026 URBANDRIVE KENYA • Jomo Kenyatta University of Agriculture and Technology")