import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="Credit Risk Decision System", layout="wide")

# Loading the model and column mapping
@st.cache_resource
def load_model():
    # Ensure these files are in the same directory as app.py
    model = joblib.load("credit_risk_model.pkl")
    cols = list(joblib.load("model_columns.pkl"))
    return model, cols

model, columns = load_model()

# Custom UI Styling
st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #020617 0%, #0b1a2b 100%); color: #e6edf3; }
.header-card { background: linear-gradient(135deg, #0b1f3a, #122a4a); padding: 25px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px; }
.stButton>button { background: linear-gradient(135deg, #1d4ed8, #2563eb); color: white; border-radius: 10px; width: 100%; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-card">
    <h1> Credit Risk Decision System</h1>
    <p>Enterprise-grade predictive analytics for loan risk assessment.</p>
</div>
""", unsafe_allow_html=True)

# Helper Functions
def safe_div(a, b):
    return a / b if b != 0 else 0

def calculate_credit_score(prob):
    """
    Applies non-linear mapping: Score = max(300, 900 - (Probability * 1200))
    """
    score = 900 - (prob * 1200)
    return int(max(300, score))

def determine_risk_category(prob):
    """
    Strict Banking Thresholds:
    - Low Risk: < 5% (Approve)
    - Medium Risk: 5% - 10% (Review)
    - High Risk: > 10% (Reject)
    """
    if prob < 0.05:
        return "Low", "APPROVE"
    elif prob < 0.10:
        return "Medium", "REVIEW"
    else:
        return "High", "REJECT"

# Sidebar Reset
if st.sidebar.button("🔄 Reset Application"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# Application Form
st.markdown("### Loan Application Details")
with st.form("loan_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        income = st.number_input("Annual Income (₹)", min_value=0, value=500000)
        age = st.number_input("Age (Years)", min_value=18, max_value=100, value=30)

    with col2:
        credit_amt = st.number_input("Requested Credit Amount (₹)", min_value=0, value=100000)
        years_emp = st.number_input("Years Employed", min_value=0, max_value=60, value=5)
        term_years = st.selectbox("Loan Term (Years)", [1, 3, 5, 10, 15], index=1)

    submit = st.form_submit_button("Run Risk Assessment")

if submit:
    if years_emp > age:
        st.error("Invalid Input: Years employed cannot exceed age.")
        st.stop()

    # Feature Engineering (Aligned with Training Script)
    annuity = (credit_amt / term_years) * 1.1 
    
    row = {
        'AMT_INCOME_TOTAL': income,
        'AMT_CREDIT': credit_amt,
        'AMT_ANNUITY': annuity,
        'DAYS_BIRTH': -age * 365,
        'DAYS_EMPLOYED': -years_emp * 365,
        'YEARS_EMPLOYED': years_emp,
        'AGE': age,
        'CREDIT_INCOME_RATIO': safe_div(credit_amt, income),
        'ANNUITY_INCOME_RATIO': safe_div(annuity, income),
        'INCOME_CREDIT_RATIO': safe_div(income, credit_amt),
        'EMPLOYED_AGE_RATIO': safe_div(years_emp, age),
        'EXT_SOURCE_1': 0.35, # Conservative baseline for unverified applicants
        'EXT_SOURCE_2': 0.35,
        'EXT_SOURCE_3': 0.35,
    }

    # Dataframe Alignment
    df_input = pd.DataFrame([row])
    df_input = pd.get_dummies(df_input)
    df_input = df_input.reindex(columns=columns, fill_value=0)

    # Prediction
    prob = model.predict_proba(df_input)[0][1]
    score = calculate_credit_score(prob)
    risk_level, decision = determine_risk_category(prob)

    # Results Display
    st.markdown("---")
    st.markdown("### Risk Assessment Results")
    
    res1, res2, res3 = st.columns(3)
    # Fixed precision issue from image_0cde7f.png
    res1.metric("Default Probability", f"{prob*100:.2f}%")
    res2.metric("Calculated Credit Score", score)
    res3.metric("Decision Status", decision)

    if decision == "APPROVE":
        st.success(f"✅ Application Approved: This profile shows {risk_level} risk.")
    elif decision == "REVIEW":
        st.warning(f"⚠ Manual Review Required: Profile shows {risk_level} risk.")
    else:
        st.error(f"🚫 Application Rejected: Profile shows {risk_level} risk.")

    # Visualization
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=prob*100,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Risk Percentage", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#1d4ed8"},
            'steps': [
                {'range': [0, 5], 'color': "#065f46"},
                {'range': [5, 10], 'color': "#92400e"},
                {'range': [10, 100], 'color': "#991b1b"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': prob*100
            }
        }
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig, use_container_width=True)

    # Export Logic
    report_data = pd.DataFrame([row])
    report_data['Risk_Prob'] = prob
    report_data['Final_Score'] = score
    report_data['Final_Decision'] = decision
    
    buffer = BytesIO()
    report_data.to_excel(buffer, index=False)
    st.download_button("📥 Download Full Analysis (Excel)", buffer.getvalue(), "risk_report.xlsx")
