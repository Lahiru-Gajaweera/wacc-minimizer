import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. Page Config ---
st.set_page_config(page_title="WACC Optimization Suite", layout="wide")
st.title("🛡️ AI-Based WACC Optimization & Advisor")
st.markdown("---")

# --- 2. Sidebar: Data Source Selection ---
st.sidebar.header("📂 Data Source")
source_option = st.sidebar.radio("Select Source", ["Live API (Yahoo Finance)", "Manual File Upload (.csv)"])

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# --- DATA LOADING LOGIC (Same as before) ---
if source_option == "Live API (Yahoo Finance)":
    ticker_input = st.sidebar.text_input("Enter Company Ticker", "AAPL").upper()
    if st.sidebar.button("🔍 Fetch Live Data"):
        try:
            stock = yf.Ticker(ticker_input)
            info = stock.info
            st.session_state['fin_data'] = {
                'ticker': ticker_input,
                'mkt_cap': info.get('marketCap', 1e9),
                'total_debt': info.get('totalDebt', 0),
                'beta': info.get('beta', 1.0),
                'name': info.get('longName', ticker_input)
            }
            st.sidebar.success(f"Loaded: {ticker_input}")
        except:
            st.sidebar.error("Ticker not found.")

else:
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])
    if uploaded_file is not None:
        df_upload = pd.read_csv(uploaded_file)
        col_mkt = st.sidebar.selectbox("Market Cap Column", df_upload.columns)
        col_debt = st.sidebar.selectbox("Total Debt Column", df_upload.columns)
        has_beta = st.sidebar.checkbox("My file has a Beta column", value=False)
        if has_beta:
            col_beta = st.sidebar.selectbox("Beta Column", df_upload.columns)
        else:
            manual_beta = st.sidebar.number_input("Enter Beta manually", value=1.1, step=0.1)
        
        if st.sidebar.button("🚀 Analyze Uploaded File"):
            try:
                st.session_state['fin_data'] = {
                    'ticker': "Custom",
                    'mkt_cap': float(df_upload[col_mkt].iloc[0]),
                    'total_debt': float(df_upload[col_debt].iloc[0]),
                    'beta': float(df_upload[col_beta].iloc[0]) if has_beta else manual_beta,
                    'name': "Uploaded Dataset"
                }
                st.sidebar.success("Processed!")
            except:
                st.sidebar.error("Check column selections.")

# --- 3. Dashboard & Advisory Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    st.subheader(f"Analysis for {d['name']}")
    
    # Assumptions
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Assumptions")
    tax_rate = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf_rate = st.sidebar.number_input("Risk-Free Rate", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3.0, 9.0, 5.5) / 100
    rd_pre_tax = st.sidebar.slider("Cost of Debt (%)", 2.0, 15.0, 6.5) / 100

    # Math
    de_ratio = d['total_debt'] / d['mkt_cap']
    unlevered_b = d['beta'] / (1 + (1 - tax_rate) * de_ratio)
    ratios = np.linspace(0.01, 0.9, 100)
    wacc_values = []
    for r in ratios:
        levered_b = unlevered_b * (1 + (1 - tax_rate) * (r / (1 - r)))
        re = rf_rate + (levered_b * erp)
        wacc = ((1 - r) * re) + (r * rd_pre_tax * (1 - tax_rate))
        wacc_values.append(wacc)
    
    min_wacc = min(wacc_values)
    opt_ratio = ratios[np.argmin(wacc_values)]
    current_ratio = d['total_debt'] / (d['total_debt'] + d['mkt_cap'])

    # Display Graph
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(ratios, wacc_values, color='#0077b6', label="WACC Curve")
    ax.axvline(current_ratio, color='orange', linestyle='--', label=f"Current: {current_ratio:.1%}")
    ax.axvline(opt_ratio, color='green', linestyle='-', label=f"Optimal: {opt_ratio:.1%}")
    ax.legend()
    st.pyplot(fig)

    # --- NEW FEATURE: STRATEGIC ADVISORY SECTION ---
    st.markdown("---")
    st.header("💡 AI Strategic Recommendation")
    
    advice_col, metric_col = st.columns([2, 1])
    
    with metric_col:
        # Show the "Gap"
        gap = opt_ratio - current_ratio
        st.metric("Structure Gap", f"{gap:+.1%}", help="Difference between current and optimal debt levels.")
        st.metric("Potential Min WACC", f"{min_wacc:.2%}")

    with advice_col:
        if gap > 0.05:
            st.success("### Recommendation: INCREASE LEVERAGE")
            st.write(f"The company is currently **Under-leveraged**. By increasing debt from {current_ratio:.1%} to {opt_ratio:.1%}, the firm can benefit from a larger **Interest Tax Shield**, which lowers the overall cost of capital.")
        elif gap < -0.05:
            st.warning("### Recommendation: DECREASE LEVERAGE")
            st.write(f"The company is currently **Over-leveraged**. The financial risk (Beta) is too high. Reducing the debt ratio to {opt_ratio:.1%} will lower the cost of equity and improve the company's valuation.")
        else:
            st.info("### Recommendation: MAINTAIN STRUCTURE")
            st.write("The company is operating at or very near its **Optimal Capital Structure**. No major changes in debt/equity mix are recommended at this time.")

else:
    st.info("👈 Load data to see the AI Advisor.")