import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from fpdf import FPDF

# --- 1. Page Config ---
st.set_page_config(page_title="Executive WACC Optimizer", layout="wide")
st.title("🛡️ Strategic Capital Structure & WACC Optimizer")
st.markdown("---")

# --- 2. Sidebar: Data & Assumptions ---
st.sidebar.header("📂 Data Acquisition")
source = st.sidebar.radio("Data Source", ["Live API (Yahoo Finance)", "Manual CSV Upload"])

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# --- SOURCE A: LIVE API (With Pre-load Option) ---
if source == "Live API (Yahoo Finance)":
    st.sidebar.subheader("Select or Type Ticker")
    preset = st.sidebar.selectbox("Quick Load Top Stocks", ["Custom", "AAPL", "TSLA", "GOOGL", "MSFT", "NVDA", "AMZN"])
    ticker_input = st.sidebar.text_input("Ticker Symbol", value="" if preset == "Custom" else preset).upper()
    
    if st.sidebar.button("🔍 Fetch Market Data"):
        try:
            with st.spinner(f"Accessing data for {ticker_input}..."):
                s = yf.Ticker(ticker_input); i = s.info
                st.session_state['fin_data'] = {
                    'ticker': ticker_input, 'mkt_cap': i.get('marketCap', 1e9), 
                    'total_debt': i.get('totalDebt', 0), 'beta': i.get('beta', 1.0), 
                    'name': i.get('longName', ticker_input)
                }
                st.sidebar.success(f"Loaded: {ticker_input}")
        except: st.sidebar.error("Ticker not found.")

# --- SOURCE B: MANUAL CSV ---
else:
    u = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if u:
        df = pd.read_csv(u)
        c1 = st.sidebar.selectbox("Select Market Cap/Equity Column", df.columns)
        c2 = st.sidebar.selectbox("Select Total Debt/Liabilities Column", df.columns)
        if st.sidebar.button("🚀 Analyze Uploaded Data"):
            try:
                st.session_state['fin_data'] = {
                    'ticker': "Custom", 'mkt_cap': float(df[c1].iloc[0]), 
                    'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Uploaded Dataset"
                }
                st.sidebar.success("Data Processed!")
            except: st.sidebar.error("Error: Ensure selected columns contain numbers.")

# --- 3. Main Reporting Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Financial Assumptions (Sidebar)
    st.sidebar.markdown("---")
    st.sidebar.header("📝 Financial Assumptions")
    tax = st.sidebar.slider("Corporate Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate (e.g. 10Y Treasury)", value=0.043, format="%.3f")
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3.0, 9.0, 5.5) / 100
    base_rd = st.sidebar.slider("Base Interest Rate (AAA Debt) %", 2.0, 15.0, 5.0) / 100

    # --- MATH ENGINE ---
    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val if total_val > 0 else 0
    # Hamada Formula for Unlevered Beta
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap'] if d['mkt_cap'] > 0 else 0))
    
    ratios = np.linspace(0.01, 0.95, 100)
    wacc_list = []
    for r in ratios:
        dyn_rd = base_rd + (r * 0.12) # Dynamic Credit Risk Penalty
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dyn_rd * (1 - tax))
        wacc_list.append(wacc)
    
    min_w = min(wacc_list); opt_r = ratios[np.argmin(wacc_list)]
    curr_wacc = wacc_list[np.abs(ratios - curr_dr).argmin()]
    val_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc) if curr_wacc > 0 else 0

    # DISPLAY: KPIs
    st.header(f"Executive Report: {d['name']}")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current WACC", f"{curr_wacc:.2%}")
    k2.metric("Minimum WACC", f"{min_w:.2%}")
    k3.metric("Optimal Debt Ratio", f"{opt_r:.1%}")
    k4.metric("Value Creation", f"{val_gain:+.2%}")
    st.markdown("---")

    # DISPLAY: VISUALS
    st.subheader("📈 WACC Minimization Curve")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(ratios, wacc_list, color='#0077b6', linewidth=3, label="WACC Curve")
    ax.axvline(curr_dr, color='orange', linestyle='--', label=f"Current: {curr_dr:.1%}")
    ax.axvline(opt_r, color='green', label=f"Optimal: {opt_r:.1%}")
    ax.set_ylabel("WACC %"); ax.set_xlabel("Debt-to-Capital Ratio")
    ax.legend(); st.pyplot(fig)

    st.markdown("---")
    st.subheader("📊 Capital Composition (Current)")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.plotly_chart(px.pie(pd.DataFrame({"S": ["Equity", "Debt"], "V": [d['mkt_cap'], d['total_debt']]}), 
                               values='V', names='S', hole=0.5, color_discrete_sequence=['#1f77b4', '#d62728']))
    with c2:
        st.write("#### Structure Breakdown")
        st.info(f"Equity: ${d['mkt_cap']:,.0f} | Debt: ${d['total_debt']:,.0f}")
        st.write("The current weights are used as the baseline. To reach the green line (Optimal), the weights must be adjusted through recapitalization.")

    # DISPLAY: STRATEGY
    st.markdown("---")
    st.header("📜 Strategic Execution Roadmap")
    gap = opt_r - curr_dr
    if gap > 0.05:
        st.success("### STATUS: UNDER-LEVERAGED")
        st.write("Company is using too much equity. Strategy: Increase debt to lower WACC.")
        do, dont = st.columns(2)
        with do: st.markdown("#### ✅ DO:\n- Issue Bonds\n- Share Buybacks\n- Special Dividends")
        with dont: st.markdown("#### ❌ DON'T:\n- Issue new shares\n- Hold excess cash")
    elif gap < -0.05:
        st.warning("### STATUS: OVER-LEVERAGED")
        st.write("Company is at financial risk. Strategy: Decrease debt to stabilize WACC.")
        do, dont = st.columns(2)
        with do: st.markdown("#### ✅ DO:\n- Equity infusion\n- Asset sales\n- Retain earnings")
        with dont: st.markdown("#### ❌ DON'T:\n- New loans\n- Debt-funded M&A")

    # DISPLAY: GLOSSARY
    with st.expander("📖 Project Glossary & Formulas"):
        st.markdown("""
        - **WACC:** Weighted Average Cost of Capital. The average rate a business pays to finance its assets.
        - **Beta (Risk):** Measures volatility. **Unlevered Beta** removes the effect of debt to show pure business risk.
        - **Hamada Formula:** Used to determine how Beta changes when a company adds or removes debt.
        - **Tax Shield:** The reduction in income taxes that results from the deductibility of interest expense.
        """)

    # DOWNLOAD PDF
    def get_pdf(d, cw, mw, orat):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, f"Executive WACC Report: {d['name']}", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.ln(10)
        pdf.cell(200, 10, f"Current WACC: {cw:.2%}", ln=True)
        pdf.cell(200, 10, f"Optimal WACC: {mw:.2%}", ln=True)
        pdf.cell(200, 10, f"Target Debt Ratio: {orat:.1%}", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    if st.button("📥 Generate Executive PDF"):
        pdf_bytes = get_pdf(d, curr_wacc, min_w, opt_r)
        st.download_button("Download PDF", pdf_bytes, f"Report_{d['ticker']}.pdf", "application/pdf")
else:
    st.info("👈 Select a Ticker or Upload a CSV in the sidebar to start the analysis.")