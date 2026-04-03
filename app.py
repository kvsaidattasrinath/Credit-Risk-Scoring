import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.graph_objects as go
from io import BytesIO
st.set_page_config(page_title="Credit Risk System", layout="wide")

# Loading the model
@st.cache_resource
def load_model():
    model = joblib.load("credit_risk_model.pkl")
    cols = list(joblib.load("model_columns.pkl"))
    return model, cols

model, columns = load_model()
# UI
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #020617 0%, #0b1a2b 100%);
    color: #e6edf3;
}
.block-container {
    padding-top: 1.5rem;
    max-width: 1100px;
}
.header-card {
    background: linear-gradient(135deg, #0b1f3a, #122a4a);
    padding: 25px;
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.08);
}
.card {
    background: #0f1e33;
    padding: 18px;
    border-radius: 15px;
    border: 1px solid rgba(255,255,255,0.08);
}
.stButton>button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb);
    color: white;
    border-radius: 10px;
    height: 45px;
}
section[data-testid="stSidebar"] {
    background-color: #020617;
}
</style>
""", unsafe_allow_html=True)

#Header
st.markdown("""
<div class="header-card">
    <h1>🏦 Credit Risk Decision System</h1>
    <p>AI-powered loan approval & risk assessment</p>
</div>
""", unsafe_allow_html=True)

#Reset
def reset_fields():
    for key in ["income", "credit", "age", "years"]:
        st.session_state[key] = ""
    st.rerun()

if st.sidebar.button("🔄 Reset"):
    reset_fields()

#Functions
def parse(x, name):
    if x == "":
        st.error(f"{name} required")
        st.stop()
    return float(x)

def safe_div(a,b):
    return a/b if b!=0 else 0

def credit_score(prob):
    return int(900 - prob*600)

def risk(prob):
    if prob < 0.3:
        return "Low", "APPROVE"
    elif prob < 0.6:
        return "Medium", "REVIEW"
    return "High", "REJECT"

#Inputs
st.markdown("### Loan Application")

with st.form("form"):
    col1, col2 = st.columns(2)

    with col1:
        income = st.text_input("Annual Income (₹)", key="income")
        age = st.text_input("Age", key="age")

    with col2:
        credit = st.text_input("Credit Amount (₹)", key="credit")
        years = st.text_input("Years Employed", key="years")

    submit = st.form_submit_button("Assess Risk")

#Prediction
if submit:

    income = parse(income, "Income")
    credit = parse(credit, "Credit")
    age = int(parse(age, "Age"))
    years = int(parse(years, "Years"))

    if years > age:
        st.error("Years employed cannot exceed age")
        st.stop()

    ratio = safe_div(credit, income)

    row = {
        'AMT_INCOME_TOTAL': income,
        'AMT_CREDIT': credit,
        'DAYS_BIRTH': -age*365,
        'YEARS_EMPLOYED': years,
        'CREDIT_INCOME_RATIO': ratio,
        'EMPLOYED_AGE_RATIO': safe_div(years, age),
        'INCOME_CREDIT_RATIO': safe_div(income, credit),
        'EXT_SOURCE_1': 0.5,
        'EXT_SOURCE_2': 0.5,
        'EXT_SOURCE_3': 0.5,
    }

    df = pd.DataFrame([row])
    df = pd.get_dummies(df)
    df = df.reindex(columns=columns, fill_value=0)

    prob = model.predict_proba(df)[0][1]
    score = credit_score(prob)
    r, decision = risk(prob)

#Outputs
    st.markdown("### Results")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Default Risk", f"{prob*100:.2f}%")

    with c2:
        st.metric("Credit Score", score)

    with c3:
        st.metric("Decision", decision)

    # Decision Highlight
    if decision == "APPROVE":
        st.success("✅ Loan Approved")
    elif decision == "REVIEW":
        st.warning("⚠ Needs Review")
    else:
        st.error("🚫 Loan Rejected")

# Gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=prob*100,
        title={'text': "Risk Level"},
        gauge={'axis': {'range': [0,100]}}
    ))
    st.plotly_chart(fig, use_container_width=True)

#Download the report
    result = pd.DataFrame({
        "Income":[income],
        "Credit":[credit],
        "Risk %":[prob*100],
        "Score":[score],
        "Decision":[decision]
    })

    buffer = BytesIO()
    result.to_excel(buffer, index=False)

    st.download_button("📥 Download Report", buffer, "credit_report.xlsx")
