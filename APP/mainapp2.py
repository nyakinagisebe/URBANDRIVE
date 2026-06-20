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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    
    /* GLOBAL BODY & GLASS BASE */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #1e293b;
    }
    .logo-font { font-family: 'Space Grotesk', sans-serif; }
    
    /* HIDE STREAMLIT APP CHROMES */
    [data-testid="stSidebar"], header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* MAIN PLATFORM WORKSPACE CONTAINER */
    .main .block-container {
        padding-top: 5.5rem !important;
        max-width: 1220px;
    }

    /* PREMIUM NAVIGATION LINK CHIP */
    .back-nav-container {
        position: fixed;
        top: 24px;
        left: 24px;
        z-index: 1000000;
    }
    .back-btn-rect {
        background: rgba(22, 101, 52, 0.95);
        backdrop-filter: blur(8px);
        color: white !important;
        padding: 12px 26px;
        border-radius: 14px;
        text-decoration: none;
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 10px 25px -5px rgba(22, 101, 52, 0.4);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(255,255,255,0.1);
    }
    .back-btn-rect:hover {
        background-color: #15803d;
        transform: translateY(-2px);
        box-shadow: 0 14px 30px -5px rgba(21, 128, 61, 0.5);
        text-decoration: none;
    }

    /* GLASSMORPHISM INTERFACE PANELS */
    .input-card, .report-card {
        background: rgba(255, 255, 255, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        padding: 40px;
        border-radius: 24px;
        box-shadow: 0 20px 40px -15px rgba(15, 23, 42, 0.05), 0 1px 3px rgba(15, 23, 42, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.6);
        margin-bottom: 2.5rem;
    }

    /* ROUNDED MAP WRAPPER TO FIX SHARP BOUNDARIES */
    .rounded-map-container {
        border-radius: 24px !important;
        overflow: hidden !important;
        box-shadow: 0 12px 30px -10px rgba(15, 23, 42, 0.1);
        border: 1px solid rgba(226, 232, 240, 0.8);
        margin-bottom: 20px;
    }
    
    /* MODULAR GLASS-LIKE INFRASTRUCTURE CHIPS */
    .facility-box {
        background: rgba(248, 250, 252, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 12px;
        transition: transform 0.2s ease;
    }
    .facility-box:hover {
        transform: scale(1.02);
        background: rgba(241, 245, 249, 0.8);
    }

    /* PREMIUM INVESTMENT COST SCHEDULE CARDS */
    .cost-schedule-card {
        background: rgba(248, 250, 252, 0.65);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-left: 5px solid #166534;
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 20px;
    }
    .cost-title {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 16px;
        color: #0f172a;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .cost-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px dashed rgba(226, 232, 240, 0.8);
        font-size: 14px;
        color: #475569;
    }
    .cost-item:last-child {
        border-bottom: none;
    }
    .cost-value {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        color: #1e293b;
    }
    .cost-total-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid #cbd5e1;
        font-weight: 700;
        color: #166534;
    }
    .cost-total-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 16px;
    }

    /* ROUNDED SOFT FORM CONTROLS */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 14px !important;
        border: 1px solid #cbd5e1 !important;
        padding-top: 6px !important;
        padding-bottom: 6px !important;
        background-color: #ffffff !important;
    }
    
    /* BUTTON STYLING OVERRIDES */
    .stButton>button {
        background: linear-gradient(135deg, #166534 0%, #15803d 100%) !important;
        color: white !important;
        border-radius: 16px !important;
        height: 54px !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        border: none !important;
        box-shadow: 0 10px 20px -5px rgba(22, 101, 52, 0.3) !important;
        transition: all 0.25s ease !important;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #15803d 0%, #166534 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 14px 25px -5px rgba(21, 128, 61, 0.4) !important;
    }
    
    /* SMOOTH STEPPER INDICATORS */
    .step-container {
        display: flex; 
        align-items: center; 
        gap: 16px; 
        margin: 25px 0 45px 0;
        background: rgba(241, 245, 249, 0.6);
        padding: 16px 28px;
        border-radius: 20px;
        border: 1px solid #e2e8f0;
    }
    .step {
        width: 36px; 
        height: 36px; 
        border-radius: 50%; 
        display: flex;
        align-items: center; 
        justify-content: center; 
        font-weight: 700;
        font-size: 14px;
        border: 2px solid #cbd5e1; 
        background: white; 
        color: #64748b;
    }
    .step-active { 
        background: #166534; 
        color: white; 
        border-color: #166534;
        box-shadow: 0 0 0 5px rgba(22, 101, 52, 0.15);
    }
    .step-line { 
        flex: 1; 
        height: 4px; 
        background: #cbd5e1;
        border-radius: 10px;
    }
    .step-line-active {
        background: linear-gradient(to right, #166534, #86efac);
    }
    
    /* METRICS TILES GRADIENTS */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%) !important;
        border: 1px solid #e2e8f0 !important;
        padding: 24px !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.01) !important;
    }
    div[data-testid="stMetricValue"] {
        color: #166534 !important;
        font-weight: 700 !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    
    /* LIQUID STATUS ACCENT STRIPS */
    .verdict-go { 
        background: linear-gradient(145deg, #f0fdf4 0%, #dcfce7 100%); 
        color: #14532d; 
        padding: 22px; 
        border-radius: 18px; 
        border: 1px solid #bbf7d0;
        border-left: 6px solid #22c55e; 
        font-weight: 700; 
        text-align: center; 
        font-size: 20px;
        box-shadow: 0 10px 20px -5px rgba(34, 197, 94, 0.1);
        margin: 24px 0;
    }
    .verdict-no { 
        background: linear-gradient(145deg, #fef2f2 0%, #fee2e2 100%); 
        color: #7f1d1d; 
        padding: 22px; 
        border-radius: 18px; 
        border: 1px solid #fecaca;
        border-left: 6px solid #ef4444; 
        font-weight: 700; 
        text-align: center; 
        font-size: 20px;
        box-shadow: 0 10px 20px -5px rgba(239, 68, 68, 0.1);
        margin: 24px 0;
    }

    /* STRIP STYLING FROM ACCORDIONS */
    .stMain .element-container div[data-testid="stExpander"] {
        border: none !important;
        background: transparent !important;
    }
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

# Dynamically updates stepper graphics via CSS states
step1_active = "step-active" if st.session_state.step >= 1 else ""
step2_active = "step-active" if st.session_state.step == 2 else ""
line_active = "step-line-active" if st.session_state.step == 2 else ""

st.markdown(f"""
<div class="step-container">
    <div class="step {step1_active}">1</div>
    <div class="step-line {line_active}"></div>
    <div class="step {step2_active}">2</div>
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
    st.markdown('<div class="rounded-map-container">', unsafe_allow_html=True)
    m = folium.Map(location=[-1.286389, 36.817223], zoom_start=11, tiles="cartodbpositron")
    st_folium(m, width="100%", height=420)
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown('<div class="rounded-map-container">', unsafe_allow_html=True)
        m = folium.Map(location=[lat, lon], zoom_start=14)
        folium.Marker([lat, lon], icon=folium.Icon(color='blue', icon='home')).add_to(m)
        st_folium(m, width="100%", height=450)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_list:
        st.write("**Nearby Facilities (3km Radius)**")
        for cat, query in infra_filters.items():
            subset = infra_df.query(query).copy()
            subset['dist'] = np.sqrt((subset.lat - lat)**2 + (subset.lon - lon)**2) * 111.32
            nearby = subset[subset.dist <= 3.0].sort_values('dist').head(2)
            if not nearby.empty:
                st.markdown(f"<span style='font-size:12px; font-weight:700; color:#475569; letter-spacing:0.5px;'>{cat.upper()}</span>", unsafe_allow_html=True)
                for _, row in nearby.iterrows():
                    st.markdown(f"""
                    <div class="facility-box">
                        <span style="font-weight:600; font-size:14px; color:#0f172a;"><i class="fa-solid fa-location-dot" style="color:#166534; margin-right:6px;"></i> {row['name']}</span><br/>
                        <span style="font-size:12px; color:#64748b; margin-left:18px;">Distance: {row['dist']:.2f} km</span>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.subheader("💰 Investment Analysis Report")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Investment", f"KSh {res['total']/1e6:.1f}M")
    c2.metric("Monthly Revenue", f"KSh {rent*st.session_state.units:,.0f}")
    c3.metric("Annual ROI", f"{roi:.2f}%")

    # ==================== RESTORED & UPGRADED COST ANALYSIS CONTAINER ====================
    with st.expander("✨ View Premium Financial Schedule", expanded=True):
        st.markdown(f"""
        <div class="cost-schedule-card" style="border-left-color: #0284c7;">
            <div class="cost-title"><i class="fa-solid fa-map-location-dot" style="color:#0284c7;"></i> 1. Land Acquisition & Legal Costs</div>
            <div class="cost-item">
                <span>Base Land Purchase Price</span>
                <span class="cost-value">KSh {res['cat_a']['base']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>Stamp Duty Tax ({res['cat_a']['rate']*100}%)</span>
                <span class="cost-value">KSh {res['cat_a']['duty']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>Legal & Conveyancing Fees (1%)</span>
                <span class="cost-value">KSh {res['cat_a']['legal']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>Registration & Valuation</span>
                <span class="cost-value">KSh 15,000</span>
            </div>
            <div class="cost-total-row" style="color:#0284c7;">
                <span>SUB-TOTAL</span>
                <span class="cost-total-value">KSh {res['cat_a']['total']:,.0f}</span>
            </div>
        </div>

        <div class="cost-schedule-card" style="border-left-color: #f59e0b;">
            <div class="cost-title"><i class="fa-solid fa-helmet-safety" style="color:#f59e0b;"></i> 2. Construction Hard Costs (Escalated)</div>
            <div class="cost-item">
                <span>Base Construction Value</span>
                <span class="cost-value">KSh {res['cat_b']['base']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>Time-Based Material Escalation</span>
                <span class="cost-value">KSh {res['cat_b']['escalation']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>Forex / Import Risk Buffer</span>
                <span class="cost-value">KSh {res['cat_b']['forex']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>Escalated Rate per SQM</span>
                <span class="cost-value">KSh {res['cat_b']['rate_sqm']:,.0f}</span>
            </div>
            <div class="cost-total-row" style="color:#f59e0b;">
                <span>SUB-TOTAL</span>
                <span class="cost-total-value">KSh {res['cat_b']['total']:,.0f}</span>
            </div>
        </div>

        <div class="cost-schedule-card" style="border-left-color: #b45309;">
            <div class="cost-title"><i class="fa-solid fa-file-invoice-dollar" style="color:#b45309;"></i> 3. Statutory Approvals & Permits</div>
            <div class="cost-item">
                <span>Nairobi City County Approval</span>
                <span class="cost-value">KSh {res['cat_c']['county']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>National Construction Authority Project Levy (0.5%)</span>
                <span class="cost-value">KSh {res['cat_c']['nca']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>National Environment Management Authority License</span>
                <span class="cost-value">KSh {res['cat_c']['nema']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>Base Permit Application Fee</span>
                <span class="cost-value">KSh {res['cat_c']['base_fee']:,.0f}</span>
            </div>
            <div class="cost-total-row" style="color:#b45309;">
                <span>SUB-TOTAL</span>
                <span class="cost-total-value">KSh {res['cat_c']['total']:,.0f}</span>
            </div>
        </div>

        <div class="cost-schedule-card" style="border-left-color: #6366f1;">
            <div class="cost-title"><i class="fa-solid fa-compass-drafting" style="color:#6366f1;"></i> 4. Professional Consultancy Fees</div>
            <div class="cost-item">
                <span>Architects & Quantity Surveyors</span>
                <span class="cost-value">KSh {res['cat_d']['arch_qs']:,.0f}</span>
            </div>
            <div class="cost-item">
                <span>Structural & MEP Engineers</span>
                <span class="cost-value">KSh {res['cat_d']['eng']:,.0f}</span>
            </div>
            <div class="cost-total-row" style="color:#6366f1;">
                <span>SUB-TOTAL</span>
                <span class="cost-total-value">KSh {res['cat_d']['total']:,.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    benchmark = market_data['inflation'] + 3.0
    is_go = roi > benchmark

    if is_go:
        st.markdown(f"<div class='verdict-go'>✅ INVESTMENT VERDICT: GO (ROI {roi:.1f}% > Benchmark {benchmark:.1f}%)</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='verdict-no'>❌ INVESTMENT VERDICT: NO-GO (ROI {roi:.1f}% < Benchmark {benchmark:.1f}%)</div>", unsafe_allow_html=True)

    # ==================== INDENTATION FIXED: SAVES FOR BOTH GO AND NO-GO ====================
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