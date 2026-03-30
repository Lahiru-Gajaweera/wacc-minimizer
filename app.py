import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# --- 1. Page Config ---
st.set_page_config(page_title="Executive WACC Suite", layout="wide")
st.title("🏛️ Strategic Capital structure & WACC Optimizer")
st.markdown("---")

# --- 2. Sidebar: Controls ---
st.sidebar.header("📂 Data & Controls")
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
        if st.sidebar.button("Analyze Data"):
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
        dynamic_rd = base_rd + (r * 0.12) # Risk premium for high leverage
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dynamic_rd * (1 - tax))
        wacc_list.append(wacc)
    
    min_w = min(wacc_list)
    opt_r = ratios[np.argmin(wacc_list)]
    curr_wacc = wacc_list[np.abs(ratios - curr_dr).argmin()]
    potential_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc) if curr_wacc > 0 else 0

    # SECTION 1: Key Performance Indicators
    st.header("📍 Executive Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Target Min WACC", f"{min_w:.2%}")
    m3.metric("Optimal Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Creation Gain", f"{potential_gain:+.2%}")
    st.markdown("---")

    # SECTION 2: Optimization Curve (Full Width)
    st.subheader("📈 WACC Minimization Curve")
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(ratios, wacc_list, color='#0077b6', linewidth=3)
    ax.fill_between(ratios, wacc_list, alpha=0.1, color='#0077b6')
    ax.axvline(curr_dr, color='orange', linestyle='--', label=f"Current Structure: {curr_dr:.1%}")
    ax.axvline(opt_r, color='green', label=f"Optimal Structure: {opt_r:.1%}")
    ax.set_ylabel("Weighted Average Cost of Capital (%)")
    ax.set_xlabel("Debt-to-Capital Ratio")
    ax.set_facecolor('#f8f9fa')
    ax.legend()
    st.pyplot(fig)

    # SECTION 3: Capital Mix (Now Under the Curve)
    st.markdown("---")
    st.subheader("📊 Current Capital Composition")
    pie_col1, pie_col2 = st.columns([1, 1.5])
    with pie_col1:
        pie_df = pd.DataFrame({"Source": ["Equity", "Debt"], "Value": [d['mkt_cap'], d['total_debt']]})
        st.plotly_chart(px.pie(pie_df, values='Value', names='Source', hole=0.5, 
                               color_discrete_sequence=['#1f77b4', '#d62728']), use_container_width=True)
    with pie_col2:
        st.write("### Structure Breakdown")
        st.info(f"""
        - **Total Enterprise Value:** ${total_val:,.0f}
        - **Equity Weight:** {(1-curr_dr):.1%} (${d['mkt_cap']:,.0f})
        - **Debt Weight:** {curr_dr:.1%} (${d['total_debt']:,.0f})
        """)
        st.write("The current mix reflects the company's existing financing strategy. The goal of this analysis is to shift these weights to reach the 'Green Line' shown in the curve above.")

    # SECTION 4: Advanced Strategic Advice
    st.markdown("---")
    st.header("📜 Strategic Execution Roadmap")
    gap = opt_r - curr_dr
    
    if gap > 0.05:
        st.success("### STATUS: UNDER-LEVERAGED (SUB-OPTIMAL VALUE)")
        st.markdown(f"**Analysis:** The firm is operating with excessive equity. Since equity is more expensive than debt, the overall cost of capital is too high. You are currently missing out on an estimated **{potential_gain:.2%}** increase in firm value.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ✅ **STRATEGIC DO'S (Action Plan)**")
            st.write("1. **Recapitalization:** Issue long-term corporate bonds and use the proceeds to repurchase shares. This shifts the weight from Equity to Debt.")
            st.write("2. **Utilize Tax Shields:** Leverage the interest expense to lower taxable income, effectively letting the government subsidize part of your capital costs.")
            st.write("3. **Special Dividends:** If no high-ROI projects are available, return the newly borrowed capital to shareholders to boost ROE.")
        with c2:
            st.markdown("#### ❌ **STRATEGIC DON'TS (Risk Mitigation)**")
            st.write("1. **No Secondary Offerings:** Do not issue new shares; this will only dilute ownership and drive WACC higher.")
            st.write("2. **Avoid High Cash Hoarding:** Keeping large amounts of cash on the balance sheet while debt is low signals poor capital allocation to investors.")

    elif gap < -0.05:
        st.warning("### STATUS: OVER-LEVERAGED (HIGH FINANCIAL RISK)")
        st.markdown(f"**Analysis:** The firm's debt level is in the 'Danger Zone'. The risk of bankruptcy or financial distress is causing the Cost of Equity to skyrocket, making the total WACC inefficient.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ✅ **STRATEGIC DO'S (Action Plan)**")
            st.write("1. **Equity Injection:** Consider a rights issue or private placement to raise equity and pay down high-interest debt tranches.")
            st.write("2. **Asset Rationalization:** Sell non-core assets to generate immediate cash for de-leveraging.")
            st.markdown("3. **Operational Focus:** Shift management focus toward improving **EBITDA margins** to increase the Interest Coverage Ratio.")
        with c2:
            st.markdown("#### ❌ **STRATEGIC DON'TS (Risk Mitigation)**")
            st.write("1. **No Variable Rate Debt:** Do not take on any debt that isn't fixed-rate; you cannot afford interest rate volatility.")
            st.write("2. **Pause M&A:** Stop all acquisition activities. Adding more complexity and debt right now could lead to a credit rating downgrade.")
    else:
        st.info("### STATUS: OPTIMAL (MAXIMIZING VALUE)")
        st.write("The company is perfectly positioned. No major financial engineering is required. Continue to monitor market interest rates.")

    # SECTION 5: Sensitivity Stress Test
    st.markdown("---")
    st.header("🔍 Macro-Economic Sensitivity Matrix")
    st.write("This table shows how the **Optimal WACC** would change if the economy shifts (Tax rates vs. Interest rates).")
    rd_range = [base_rd-0.01, base_rd, base_rd+0.01]
    tax_range = [tax-0.05, tax, tax+0.05]
    res_matrix = []
    for t in tax_range:
        row = []
        for rdb in rd_range:
            lb = unlevered_b * (1 + (1 - t) * (opt_r / (1 - opt_r)))
            w = ((1 - opt_r) * (rf + lb * erp)) + (opt_r * (rdb + opt_r*0.1) * (1 - t))
            row.append(f"{w:.2%}")
        res_matrix.append(row)
    st.table(pd.DataFrame(res_matrix, index=[f"Tax {x:.0%}" for x in tax_range], columns=[f"Base Int. Rate {x:.1%}" for x in rd_range]))

else:
    st.info("👈 Please load data to view the Strategic Report.")