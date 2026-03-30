import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# --- 1. Page Config ---
st.set_page_config(page_title="Advanced WACC Suite", layout="wide")
st.title("🛡️ AI-Based WACC Optimization & Strategic Suite")
st.markdown("---")

# --- 2. Sidebar: Data & Benchmarking ---
st.sidebar.header("📂 Data & Benchmarks")
source_option = st.sidebar.radio("Select Source", ["Live API", "Manual Upload"])

# New Feature: Peer Benchmarking
st.sidebar.markdown("---")
st.sidebar.subheader("🏢 Industry Comparison")
peer_debt_ratio = st.sidebar.slider("Industry Avg Debt Ratio (%)", 0, 100, 20) / 100

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# [Data Loading Logic - Kept from previous version]
if source_option == "Live API":
    ticker = st.sidebar.text_input("Ticker", "AAPL").upper()
    if st.sidebar.button("Fetch Data"):
        try:
            s = yf.Ticker(ticker); i = s.info
            st.session_state['fin_data'] = {'ticker': ticker, 'mkt_cap': i.get('marketCap', 1e9), 
                                            'total_debt': i.get('totalDebt', 0), 'beta': i.get('beta', 1.0), 'name': i.get('longName', ticker)}
        except: st.sidebar.error("Ticker Error")
else:
    u = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if u:
        df = pd.read_csv(u)
        c1 = st.sidebar.selectbox("Mkt Cap Col", df.columns); c2 = st.sidebar.selectbox("Debt Col", df.columns)
        if st.sidebar.button("Analyze"):
            st.session_state['fin_data'] = {'ticker': "Upload", 'mkt_cap': float(df[c1].iloc[0]), 
                                            'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Manual Upload"}

# --- 3. Main Dashboard ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Create TABS for better navigation
    tab1, tab2, tab3 = st.tabs(["🎯 Optimization & Advice", "🔍 Sensitivity Analysis", "📊 Capital Structure"])

    # Assumptions (Sidebar)
    st.sidebar.header("📝 Global Assumptions")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    rd_pre = st.sidebar.slider("Pre-tax Cost of Debt (%)", 2, 15, 6) / 100

    # Math Logic
    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap']))
    
    ratios = np.linspace(0.01, 0.9, 100)
    wacc_list = []
    for r in ratios:
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc_list.append(((1 - r) * re) + (r * rd_pre * (1 - tax)))
    
    min_w = min(wacc_list); opt_r = ratios[np.argmin(wacc_list)]

    with tab1:
        st.subheader("WACC Minimization Curve")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(ratios, wacc_list, color='#0077b6', label="WACC Curve")
        ax.axvline(curr_dr, color='orange', label=f"Current ({curr_dr:.1%})")
        ax.axvline(opt_r, color='green', label=f"Optimal ({opt_r:.1%})")
        ax.axvline(peer_debt_ratio, color='purple', linestyle=':', label=f"Industry Avg ({peer_debt_ratio:.1%})")
        ax.legend(); st.pyplot(fig)

        # AI Recommendation Logic
        st.markdown("---")
        val_gain = ( (1/min_w) - (1/wacc_list[np.abs(ratios-curr_dr).argmin()]) ) / (1/min_w)
        c1, c2 = st.columns([2,1])
        with c1:
            if opt_r > curr_dr + 0.05:
                st.success(f"**Strategy:** Issue Debt. You are currently under-leveraged compared to the {opt_r:.1%} optimum.")
            elif opt_r < curr_dr - 0.05:
                st.warning(f"**Strategy:** Repay Debt. Financial risk is driving WACC too high.")
            else: st.info("**Strategy:** Maintain current structure.")
        with c2:
            st.metric("Est. Value Increase", f"{val_gain:+.2%}", help="Estimated increase in Firm Value from optimizing WACC")

    with tab2:
        st.subheader("Sensitivity Matrix: Tax vs. Cost of Debt")
        st.write("How WACC changes under different economic scenarios:")
        # Create a grid of variations
        tax_range = [tax-0.05, tax, tax+0.05]
        rd_range = [rd_pre-0.02, rd_pre, rd_pre+0.02]
        matrix = []
        for t in tax_range:
            row = []
            for rd in rd_range:
                lb = unlevered_b * (1 + (1 - t) * (opt_r / (1 - opt_r)))
                re = rf + (lb * erp)
                w = ((1 - opt_r) * re) + (opt_r * rd * (1 - t))
                row.append(f"{w:.2%}")
            matrix.append(row)
        
        sens_df = pd.DataFrame(matrix, index=[f"Tax {t:.0%}" for t in tax_range], columns=[f"Rd {rd:.0%}" for rd in rd_range])
        st.table(sens_df)

    with tab3:
        st.subheader("Capital Mix Visualization")
        pie_data = pd.DataFrame({"Source": ["Equity", "Debt"], "Amount": [d['mkt_cap'], d['total_debt']]})
        fig_pie = px.pie(pie_data, values='Amount', names='Source', color_discrete_sequence=['#1f77b4', '#ff7f0e'])
        st.plotly_chart(fig_pie)
        
        st.write("### Current Weights")
        st.write(f"- **Equity Weight:** {(1-curr_dr):.1%}")
        st.write(f"- **Debt Weight:** {curr_dr:.1%}")

else:
    st.info("👈 Please load data to unlock advanced analysis.")