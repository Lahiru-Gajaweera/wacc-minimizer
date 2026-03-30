import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

# --- 1. Page Config ---
st.set_page_config(page_title="Strategic WACC Optimizer", layout="wide")
st.title("🏛️ Professional Strategic Capital Optimizer")
st.markdown("---")

# --- 2. Sidebar: Data & Assumptions ---
st.sidebar.header("📂 Data Acquisition")
source = st.sidebar.radio("Data Source", ["Live API", "Manual CSV"])

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# [Standard Loading Logic]
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
        c1 = st.sidebar.selectbox("Mkt Cap Col", df.columns); c2 = st.sidebar.selectbox("Debt Col", df.columns)
        if st.sidebar.button("Analyze CSV"):
            st.session_state['fin_data'] = {'ticker': "Manual", 'mkt_cap': float(df[c1].iloc[0]), 
                                            'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Manual Upload"}

# --- 3. Dashboard Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Global Assumptions
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Financial Assumptions")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate (Rf)", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Cost of Debt (AAA Rating %)", 2.0, 10.0, 5.0) / 100

    # Tabs
    t1, t2, t3, t4 = st.tabs(["🎯 Optimization", "📜 Strategic Roadmap", "🔍 Sensitivity", "📊 Capital Mix"])

    # --- Calculation Engine ---
    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap']))
    
    ratios = np.linspace(0.01, 0.95, 100)
    wacc_list = []
    
    for r in ratios:
        # ADVANCED: Dynamic Interest Rate (Interest increases as Debt Ratio increases)
        # We assume Rd increases by 0.5% for every 10% increase in debt
        dynamic_rd = base_rd + (r * 0.15) 
        
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dynamic_rd * (1 - tax))
        wacc_list.append(wacc)
    
    min_w = min(wacc_list)
    opt_r = ratios[np.argmin(wacc_list)]
    curr_wacc = wacc_list[np.abs(ratios - curr_dr).argmin()]

    with t1:
        st.subheader("Optimal Capital Structure Curve")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(ratios, wacc_list, color='#0077b6', linewidth=2)
        ax.fill_between(ratios, wacc_list, alpha=0.1, color='#0077b6')
        ax.axvline(curr_dr, color='orange', label=f"Current ({curr_dr:.1%})")
        ax.axvline(opt_r, color='green', label=f"Optimal ({opt_r:.1%})")
        ax.set_ylabel("WACC (%)")
        ax.set_xlabel("Debt Ratio (D/V)")
        ax.legend(); st.pyplot(fig)

        # Value Impact Calculation
        # Firm Value = Free Cash Flow / WACC. (Assume constant FCF for growth)
        potential_value_gain = ( (1/min_w) - (1/curr_wacc) ) / (1/curr_wacc)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Current WACC", f"{curr_wacc:.2%}")
        c2.metric("Target Min WACC", f"{min_wacc:.2%}")
        c3.metric("Est. Value Creation", f"{potential_value_gain:+.2%}")

    with t2:
        st.header("📜 Strategic Execution Roadmap")
        
        if opt_r > curr_dr + 0.05:
            st.success("### Status: Under-Leveraged")
            st.markdown(f"**Strategy:** Capital Recapping. You are missing out on **{(opt_r - curr_dr):.1%}** in potential tax shields.")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("✅ **What to DO:**")
                st.write("- **Issue Corporate Bonds:** Take advantage of low rates to buy back expensive equity.")
                st.write("- **Share Buybacks:** Use new debt to retire outstanding shares and boost EPS.")
                st.write("- **Increase Dividends:** Signal confidence by returning more cash to shareholders.")
            with col_b:
                st.write("❌ **What NOT to Do:**")
                st.write("- **Issue New Shares:** This will further dilute equity and increase WACC.")
                st.write("- **Hoard Excess Cash:** Sitting on cash while having zero debt is inefficient for shareholders.")

        elif opt_r < curr_dr - 0.05:
            st.warning("### Status: Over-Leveraged")
            st.markdown(f"**Strategy:** De-leveraging. Financial distress risk is currently outweighing tax benefits.")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("✅ **What to DO:**")
                st.write("- **Equity Infusion:** Issue new shares to pay down high-interest debt.")
                st.write("- **Asset Divestiture:** Sell non-core business units to raise cash for debt repayment.")
                st.write("- **Retain Earnings:** Suspend dividends temporarily to strengthen the balance sheet.")
            with col_b:
                st.write("❌ **What NOT to Do:**")
                st.write("- **Take More Loans:** Even at low rates, your 'Risk Beta' is already too high.")
                st.write("- **Aggressive M&A:** Do not acquire other companies using debt right now.")

        else:
            st.info("### Status: Optimal Structure")
            st.write("The company is perfectly balanced. Focus on operational growth rather than financial engineering.")

    with t3:
        st.subheader("Stress Test: Interest Rate Sensitivity")
        # Sensitivty of WACC to changes in Base Rd and Tax
        rd_grid = [base_rd-0.01, base_rd, base_rd+0.01]
        tax_grid = [tax-0.05, tax, tax+0.05]
        res = []
        for t in tax_grid:
            row = []
            for rdb in rd_grid:
                # Recalculate WACC at optimum for each scenario
                dyn_rd = rdb + (opt_r * 0.15)
                lb = unlevered_b * (1 + (1 - t) * (opt_r / (1 - opt_r)))
                w = ((1 - opt_r) * (rf + lb * erp)) + (opt_r * dyn_rd * (1 - t))
                row.append(f"{w:.2%}")
            res.append(row)
        st.table(pd.DataFrame(res, index=[f"Tax {x:.0%}" for x in tax_grid], columns=[f"Base Rd {x:.1%}" for x in rd_grid]))

    with t4:
        st.subheader("Capital Composition")
        pdf = pd.DataFrame({"Component": ["Equity", "Debt"], "Value": [d['mkt_cap'], d['total_debt']]})
        st.plotly_chart(px.pie(pdf, values='Value', names='Component', hole=0.4, color_discrete_sequence=['#1f77b4', '#d62728']))

else:
    st.info("Please load data to start the Strategic Advisor.")