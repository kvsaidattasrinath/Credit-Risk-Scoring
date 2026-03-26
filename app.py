import streamlit as st
import pandas as pd
import joblib
import plotly.graph_objects as go
from io import BytesIO

# -------------------------------
# Load model + columns
# -------------------------------
model = joblib.load("credit_risk_model.pkl")
columns = list(joblib.load("model_columns.pkl"))

# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(page_title="Credit Risk App", layout="centered")

st.title("💳 Credit Risk Prediction App")
st.markdown("### Predict probability of loan default")
st.caption("⚠ Enter realistic financial values for accurate prediction")

# -------------------------------
# User Inputs (REALISTIC DEFAULTS)
# -------------------------------
income = st.number_input("Annual Income (₹)", min_value=10000, max_value=50000000, value=2500000)
credit = st.number_input("Credit Amount (₹)", min_value=1000, max_value=50000000, value=100000)  # ✅ fixed default
age = st.number_input("Age", min_value=18, max_value=70, value=30)
years = st.number_input("Years Employed", min_value=0, max_value=40, value=3)

# -------------------------------
# Prediction
# -------------------------------
if st.button("Predict"):

    # -------------------------------
    # VALIDATION
    # -------------------------------
    if years > age:
        st.error("❌ Years employed cannot exceed age")
        st.stop()

    if credit < 1000:
        st.error("❌ Credit amount must be at least ₹1000")
        st.stop()

    if income <= 0:
        st.error("❌ Income must be greater than 0")
        st.stop()

    # Warning (non-blocking)
    if credit > income * 5:
        st.warning("⚠ Credit is extremely high compared to income")

    # -------------------------------
    # Dynamic EXT_SOURCE (improved)
    # -------------------------------
    ratio = credit / income

    if ratio < 0.05:
        ext_score = 0.95
    elif ratio < 0.1:
        ext_score = 0.85
    elif ratio < 0.3:
        ext_score = 0.65
    elif ratio < 0.6:
        ext_score = 0.45
    else:
        ext_score = 0.2

    # -------------------------------
    # Input dictionary
    # -------------------------------
    input_dict = {
        'AMT_INCOME_TOTAL': income,
        'AMT_CREDIT': credit,
        'DAYS_BIRTH': -age * 365,
        'YEARS_EMPLOYED': years,
        'EXT_SOURCE_1': ext_score,
        'EXT_SOURCE_2': ext_score,
        'EXT_SOURCE_3': ext_score,
    }

    # Convert to DataFrame
    input_df = pd.DataFrame([input_dict])

    # Feature Engineering
    input_df['CREDIT_INCOME_RATIO'] = ratio
    input_df['EMPLOYED_TO_BIRTH_RATIO'] = years / age
    input_df['INCOME_CREDIT_DIFF'] = income - credit

    # Encoding
    input_df = pd.get_dummies(input_df)

    # Align with training columns
    input_df = input_df.reindex(columns=columns, fill_value=0)

    # Prediction
    prob = model.predict_proba(input_df)[0][1]

    # -------------------------------
    # OUTPUT
    # -------------------------------
    st.markdown("---")
    st.subheader(f"📊 Default Risk: {prob*100:.2f}%")

    # Gauge Chart
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=prob * 100,
        title={'text': "Risk Level"},
        gauge={
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 30], 'color': "green"},
                {'range': [30, 60], 'color': "yellow"},
                {'range': [60, 100], 'color': "red"},
            ],
        }
    ))
    st.plotly_chart(fig, use_container_width=True)

    # Risk category
    if prob < 0.3:
        st.success("✅ Low Risk Customer")
    elif prob < 0.6:
        st.warning("⚠️ Medium Risk Customer")
    else:
        st.error("🚨 High Risk Customer")

    # -------------------------------
    # INSIGHTS
    # -------------------------------
    st.markdown("###  Key Insights")

    if ratio > 0.5:
        st.write("⚠ High credit relative to income increases risk.")
    else:
        st.write("✔ Healthy credit-to-income ratio.")

    if years < 2:
        st.write("⚠ Low employment stability increases risk.")
    else:
        st.write("✔ Stable employment history.")

    st.write(f"ℹ Estimated external risk score used: {ext_score:.2f}")


    result_df = pd.DataFrame({
        "Income": [income],
        "Credit": [credit],
        "Age": [age],
        "Years Employed": [years],
        "Credit/Income Ratio": [ratio],
        "Estimated EXT Score": [ext_score],
        "Default Risk (%)": [prob * 100]
    })

    buffer = BytesIO()
    result_df.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "📥 Download Report",
        buffer,
        "credit_risk_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )