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

# --- 2. Sidebar: Data Acquisition ---
st.sidebar.header("📂 Data Acquisition")
source = st.sidebar.radio("Data Source", ["Live API", "Manual CSV"])

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

if source == "Live API":
    ticker = st.sidebar.text_input("Ticker", "AAPL").upper()
    if st.sidebar.button("Fetch Data"):
        try:
            s = yf.Ticker(ticker); i = s.info
            st.session_state['fin_data'] = {
                'ticker': ticker, 
                'mkt_cap': i.get('marketCap', 1e9), 
                'total_debt': i.get('totalDebt', 0), 
                'beta': i.get('beta', 1.0), 
                'name': i.get('longName', ticker)
            }
            st.sidebar.success(f"Loaded: {ticker}")
        except: st.sidebar.error("Ticker not found.")
else:
    u = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if u:
        df = pd.read_csv(u)
        c1 = st.sidebar.selectbox("Mkt Cap Col", df.columns)
        c2_col = st.sidebar.selectbox("Debt Col", df.columns)
        if st.sidebar.button("Analyze CSV"):
            st.session_state['fin_data'] = {
                'ticker': "Manual", 
                'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2_col].iloc[0]), 
                'beta': 1.1, 
                'name': "Manual Upload"
            }

# --- 3. Dashboard Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Global Assumptions Sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Financial Assumptions")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate (Rf)", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Cost of Debt (AAA Rating %)", 2.0, 15.0, 5.0) / 100

    # Tabs
    t1, t2, t3, t4 = st.tabs(["🎯 Optimization", "📜 Strategic Roadmap", "🔍 Sensitivity", "📊 Capital Mix"])

    # --- Calculation Engine ---
    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val if total_val > 0 else 0
    # Hamada Formula for Unlevered Beta
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap'] if d['mkt_cap'] > 0 else 0))
    
    ratios = np.linspace(0.01, 0.95, 100)
    wacc_list = []
    
    for r in ratios:
        # Dynamic Interest Rate (Rd increases as company gets riskier/more debt)
        dynamic_rd = base_rd + (r * 0.12) # 12% spread penalty at high leverage
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dynamic_rd * (1 - tax))
        wacc_list.append(wacc)
    
    min_w = min(wacc_list)
    opt_r = ratios[np.argmin(wacc_list)]
    curr_idx = np.abs(ratios - curr_dr).argmin()
    curr_wacc = wacc_list[curr_idx]

    with t1:
        st.subheader("Optimal Capital Structure Analysis")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(ratios, wacc_list, color='#0077b6', linewidth=2.5, label="WACC Curve")
        ax.axvline(curr_dr, color='orange', linestyle='--', label=f"Current: {curr_dr:.1%}")
        ax.axvline(opt_r, color='green', label=f"Optimal: {opt_r:.1%}")
        ax.set_ylabel("Cost of Capital (%)")
        ax.set_xlabel("Debt Ratio (D / Total Value)")
        ax.legend(); st.pyplot(fig)

        potential_value_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc) if curr_wacc > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Current WACC", f"{curr_wacc:.2%}")
        c2.metric("Target Min WACC", f"{min_w:.2%}")
        c3.metric("Est. Value Creation", f"{potential_value_gain:+.2%}")

    with t2:
        st.header("📜 Strategic Execution Roadmap")
        gap = opt_r - curr_dr
        
        if gap > 0.05:
            st.success("### Status: Under-Leveraged (Inefficient Balance Sheet)")
            st.write(f"The company is currently carrying too much equity. By moving toward **{opt_r:.1%}** debt, you can lower your WACC and increase firm value.")
            
            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown("#### ✅ **DO:**")
                st.write("- **Aggressive Share Buybacks:** Repurchase shares using low-cost debt to boost EPS.")
                st.markdown("- **Issue Corporate Bonds:** Lock in debt at current rates to exploit the **Interest Tax Shield**.")
                st.write("- **Special Dividends:** Return excess capital to shareholders if internal projects aren't beating WACC.")
            with c_b:
                st.markdown("#### ❌ **DON'T:**")
                st.write("- **Issue New Equity:** This is currently your most expensive form of capital.")
                st.write("- **Retain Excessive Cash:** High cash balances with zero debt creates a 'drag' on your ROE.")

        elif gap < -0.05:
            st.warning("### Status: Over-Leveraged (High Financial Risk)")
            st.write(f"The company's debt level of **{curr_dr:.1%}** is too high. The risk of financial distress is outweighing the tax benefits.")
            
            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown("#### ✅ **DO:**")
                st.write("- **De-leverage via Equity:** Issue new shares to pay down high-interest debt tranches.")
                st.write("- **Asset Sales:** Divest non-core units to improve your Debt-to-EBITDA ratio.")
                st.write("- **Debt Refinancing:** Negotiate longer maturities to reduce immediate liquidity pressure.")
            with c_b:
                st.markdown("#### ❌ **DON'T:**")
                st.write("- **Take on Short-term Loans:** Avoid adding any variable-rate debt while risk is high.")
                st.write("- **Aggressive M&A:** Do not acquire other firms using leverage until your ratio drops below 40%.")
        else:
            st.info("### Status: Optimal Structure")
            st.write("You are within the 'Optimal Zone'. Focus on operational efficiency rather than financial re-engineering.")

    with t3:
        st.subheader("Sensitivity Stress Test")
        # Grid of variations
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
        st.table(pd.DataFrame(res_matrix, index=[f"Tax {x:.0%}" for x in tax_range], columns=[f"Base Rd {x:.1%}" for x in rd_range]))

    with t4:
        st.subheader("Capital Structure Mix")
        pie_df = pd.DataFrame({"Source": ["Equity", "Debt"], "Value": [d['mkt_cap'], d['total_debt']]})
        st.plotly_chart(px.pie(pie_df, values='Value', names='Source', hole=0.5, color_discrete_sequence=['#1f77b4', '#d62728']))

else:
    st.info("Please enter data in the sidebar to begin analysis.")