import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# --- 1. Page Config ---
st.set_page_config(page_title="Executive WACC Optimizer", layout="wide")
st.title("🛡️ Strategic Capital Structure & WACC Optimizer")
st.markdown("---")

# --- 2. Sidebar: Data & Global Assumptions ---
st.sidebar.header("📂 Data Acquisition")
source = st.sidebar.radio("Data Source", ["Live API", "Manual CSV"])

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# Data Loading Logic
if source == "Live API":
    ticker = st.sidebar.text_input("Ticker", "AAPL").upper()
    if st.sidebar.button("Fetch Data"):
        try:
            s = yf.Ticker(ticker); i = s.info
            st.session_state['fin_data'] = {'ticker': ticker, 'mkt_cap': i.get('marketCap', 1e9), 
                                            'total_debt': i.get('totalDebt', 0), 'beta': i.get('beta', 1.0), 'name': i.get('longName', ticker)}
        except: st.sidebar.error("Ticker not found.")
else:
    u = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if u:
        df = pd.read_csv(u)
        c1 = st.sidebar.selectbox("Mkt Cap Col", df.columns)
        c2 = st.sidebar.selectbox("Debt Col", df.columns)
        if st.sidebar.button("Analyze"):
            st.session_state['fin_data'] = {'ticker': "Upload", 'mkt_cap': float(df[c1].iloc[0]), 
                                            'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Manual Dataset"}

# --- 3. Main Interface Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Global Assumptions Sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Financial Assumptions")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Cost of Debt (%)", 2, 15, 5) / 100

    # --- Calculations ---
    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val if total_val > 0 else 0
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap'] if d['mkt_cap'] > 0 else 0))
    
    ratios = np.linspace(0.01, 0.9, 100)
    wacc_list = []
    for r in ratios:
        # Dynamic Rd (Increases as debt ratio increases)
        dynamic_rd = base_rd + (r * 0.12) 
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dynamic_rd * (1 - tax))
        wacc_list.append(wacc)
    
    min_w = min(wacc_list)
    opt_r = ratios[np.argmin(wacc_list)]
    curr_wacc = wacc_list[np.abs(ratios - curr_dr).argmin()]
    potential_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc) if curr_wacc > 0 else 0

    # SECTION 1: High Level Metrics
    st.header("📍 Current vs. Optimal Performance")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC", f"{min_w:.2%}")
    m3.metric("Optimal Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Creation Potential", f"{potential_gain:+.2%}", delta_color="normal")
    st.markdown("---")

    # SECTION 2: Visualization Grid
    st.header("📊 Analytical Overviews")
    left_plot, right_plot = st.columns(2)
    
    with left_plot:
        st.subheader("WACC Minimization Curve")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(ratios, wacc_list, color='#0077b6', linewidth=3)
        ax.axvline(curr_dr, color='orange', linestyle='--', label=f"Current: {curr_dr:.1%}")
        ax.axvline(opt_r, color='green', label=f"Optimal: {opt_r:.1%}")
        ax.set_facecolor('#f0f2f6')
        ax.legend()
        st.pyplot(fig)

    with right_plot:
        st.subheader("Current Capital Mix")
        pie_df = pd.DataFrame({"Source": ["Equity", "Debt"], "Value": [d['mkt_cap'], d['total_debt']]})
        st.plotly_chart(px.pie(pie_df, values='Value', names='Source', hole=0.5, 
                               color_discrete_sequence=['#1f77b4', '#d62728']), use_container_width=True)
    st.markdown("---")

    # SECTION 3: Strategic Roadmap (Roadmap Description)
    st.header("📜 Strategic Execution Roadmap")
    gap = opt_r - curr_dr
    
    with st.container():
        if gap > 0.05:
            st.success("### RECOMMENDATION: CAPITAL RESTRUCTURING (DEBT INCREASE)")
            st.write(f"The company is currently **Under-leveraged**. You are financing too much with expensive Equity and losing the **Tax Shield** benefits of Debt.")
            c_do, c_dont = st.columns(2)
            with c_do:
                st.markdown("#### ✅ **Strategic Actions (Do's)**")
                st.markdown("- **Issue Low-Cost Bonds:** Take advantage of the current interest rate environment to lock in long-term debt.")
                st.markdown("- **Share Repurchase Program:** Use debt proceeds to buy back shares. This reduces the number of shares outstanding and increases Earnings Per Share (EPS).")
                st.markdown("- **Optimize Tax Position:** Ensure that debt is placed in jurisdictions with the highest corporate tax rates to maximize the tax shield.")
            with c_dont:
                st.markdown("#### ❌ **Strategic Warnings (Don'ts)**")
                st.markdown("- **Avoid New Equity Issuance:** Selling more shares now will dilute existing owners and increase the weighted average cost of capital.")
                st.markdown("- **Do Not Hold Excess Cash:** Idle cash with low debt levels is a signal to markets that management is not optimizing capital efficiency.")

        elif gap < -0.05:
            st.warning("### RECOMMENDATION: DE-LEVERAGING (DEBT REDUCTION)")
            st.write(f"The company is currently **Over-leveraged**. The financial risk and the high cost of equity (due to risk) are outweighing the tax benefits of debt.")
            c_do, c_dont = st.columns(2)
            with c_do:
                st.markdown("#### ✅ **Strategic Actions (Do's)**")
                st.markdown("- **Equity Infusion:** Consider a secondary share offering to raise capital specifically for debt repayment.")
                st.markdown("- **Retain Earnings:** Temporarily reduce dividend payouts or pause buybacks to strengthen the balance sheet.")
                st.markdown("- **Asset Divestiture:** Sell off non-core or underperforming business units to pay down high-interest debt tranches.")
            with c_dont:
                st.markdown("#### ❌ **Strategic Warnings (Don'ts)**")
                st.markdown("- **Do Not Refinance with Variable Rates:** In a high-risk state, variable debt exposes the company to dangerous interest rate spikes.")
                st.markdown("- **Stop Aggressive M&A:** Do not engage in debt-funded acquisitions until the Debt/Equity ratio drops significantly.")
        else:
            st.info("### RECOMMENDATION: STABLE MAINTENANCE")
            st.write("You are operating within the 'Optimal Zone'. Focus on operational growth and cost management.")

    # SECTION 4: Sensitivity Table
    st.markdown("---")
    st.header("🔍 Sensitivity Stress Test")
    st.write("How WACC behaves if Market Conditions (Tax & Interest Rates) shift:")
    rd_range = [base_rd-0.01, base_rd, base_rd+0.01]
    tax_range = [tax-0.05, tax, tax+0.05]
    res = []
    for t in tax_range:
        row = []
        for rdb in rd_range:
            lb = unlevered_b * (1 + (1 - t) * (opt_r / (1 - opt_r)))
            w = ((1 - opt_r) * (rf + lb * erp)) + (opt_r * (rdb + opt_r*0.1) * (1 - t))
            row.append(f"{w:.2%}")
        res.append(row)
    st.table(pd.DataFrame(res, index=[f"Tax {x:.0%}" for x in tax_range], columns=[f"Base Rd {x:.1%}" for x in rd_range]))

else:
    st.info("👈 Please load data via the sidebar to generate the Strategic Report.")