
import requests


payload = {
    "user_id": int(st.session_state.get("user_id", 1)),
    "report_title": f"{st.session_state.region} - {st.session_state.b_type} Analysis",
    "total_investment": float(res['total']),
    "annual_roi": float(roi),
    "verdict": "GO" if roi > (market_data['inflation'] + 3.0) else "NO-GO",
    "details": [
        {"category": "LAND", "amount_kes": float(res['cat_a']['total'])},
        {"category": "CONSTRUCTION", "amount_kes": float(res['cat_b']['total'])}
    ]
}


try:
    response = requests.post("http://127.0.0.1:5000/save-report", json=payload, timeout=10)
    if response.status_code == 200 and response.json().get("success"):
        st.success(f"✅ Report saved successfully! ID: {response.json().get('report_id')}")
except requests.exceptions.ConnectionError:
    st.error("❌ Transmission failed. Connection to backend database cluster lost.")