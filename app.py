import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from fpdf import FPDF
import io

# --- 1. Page Config ---
st.set_page_config(page_title="Executive WACC Optimizer", layout="wide")
st.title("🏛️ Strategic Capital Structure & WACC Optimizer")
st.markdown("---")

# --- 2. Sidebar: Data & Assumptions ---
st.sidebar.header("📂 Data Acquisition")
source = st.sidebar.radio("Data Source", ["Live API", "Manual CSV Upload"])

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# --- LIVE API SECTION ---
if source == "Live API":
    st.sidebar.subheader("Select or Type Ticker")
    preset = st.sidebar.selectbox("Quick Load", ["Custom", "AAPL", "TSLA", "GOOGL", "MSFT", "NVDA", "AMZN"])
    ticker_input = st.sidebar.text_input("Ticker Symbol", value="" if preset == "Custom" else preset).upper()
    
    if st.sidebar.button("🔍 Fetch Market Data"):
        try:
            s = yf.Ticker(ticker_input); i = s.info
            st.session_state['fin_data'] = {
                'ticker': ticker_input, 'mkt_cap': i.get('marketCap', 1e9), 
                'total_debt': i.get('totalDebt', 0), 'beta': i.get('beta', 1.0), 
                'name': i.get('longName', ticker_input)
            }
        except: st.sidebar.error("Ticker not found.")

# --- MANUAL CSV SECTION ---
else:
    u = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if u:
        df = pd.read_csv(u)
        c1 = st.sidebar.selectbox("Market Cap Column", df.columns)
        c2 = st.sidebar.selectbox("Debt Column", df.columns)
        if st.sidebar.button("🚀 Analyze Data"):
            st.session_state['fin_data'] = {
                'ticker': "Manual", 'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Manual Upload"
            }

# --- 3. Main Dashboard ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Financial Assumptions
    st.sidebar.markdown("---")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Interest Rate (%)", 2, 15, 5) / 100

    # Math Logic
    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap']))
    
    ratios = np.linspace(0.01, 0.9, 100)
    wacc_list = []
    for r in ratios:
        dyn_rd = base_rd + (r * 0.12)
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dyn_rd * (1 - tax))
        wacc_list.append(wacc)
    
    min_w = min(wacc_list); opt_r = ratios[np.argmin(wacc_list)]
    curr_wacc = wacc_list[np.abs(ratios - curr_dr).argmin()]
    val_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc)

    # 1. Dashboard Metrics
    st.header(f"Analysis: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC", f"{min_w:.2%}")
    m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Potential", f"{val_gain:+.2%}")
    
    # 2. Charts
    st.markdown("---")
    st.subheader("WACC Minimization Analysis")
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(ratios, wacc_list, color='#0077b6', linewidth=2.5)
    ax.axvline(curr_dr, color='orange', linestyle='--', label="Current")
    ax.axvline(opt_r, color='green', label="Optimal")
    ax.legend(); st.pyplot(fig)

    st.plotly_chart(px.pie(pd.DataFrame({"S": ["Equity", "Debt"], "V": [d['mkt_cap'], d['total_debt']]}), 
                           values='V', names='S', hole=0.5, title="Current Capital Mix"), use_container_width=True)

    # 3. Strategy Roadmap (Description Mode)
    st.markdown("---")
    st.header("📜 Strategic Execution Roadmap")
    gap = opt_r - curr_dr
    
    strategy_text = ""
    if gap > 0.05:
        status = "UNDER-LEVERAGED"
        st.success(f"### {status}")
        strategy_text = "The firm should increase leverage to capture tax shields and lower cost of capital."
        dos = "DO: Issue long-term bonds, initiate share buybacks, and optimize interest tax shields."
        donts = "DON'T: Issue new equity or maintain high cash balances that dilute Return on Equity (ROE)."
    elif gap < -0.05:
        status = "OVER-LEVERAGED"
        st.warning(f"### {status}")
        strategy_text = "The firm is over-leveraged. High financial risk is driving up the cost of equity."
        dos = "DO: De-leverage via equity infusion, sell non-core assets, and focus on debt repayment."
        donts = "DON'T: Take on new variable-rate debt or engage in aggressive debt-funded acquisitions."
    else:
        status = "OPTIMAL"
        st.info(f"### {status}")
        strategy_text = "Operating at peak efficiency. No structural changes required."
        dos = "DO: Focus on operational growth."; donts = "DON'T: Change the capital mix."

    st.write(f"**Action Plan:** {strategy_text}")
    st.write(f"✅ **Strategic Do's:** {dos}")
    st.write(f"❌ **Strategic Don'ts:** {donts}")

    # 4. Advanced PDF Generator
    def generate_full_pdf(d, cw, mw, orat, stat, desc, d1, d2):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(200, 15, f"Financial Analysis Report: {d['name']}", ln=True, align='C')
        pdf.set_font("Arial", 'B', 12)
        pdf.ln(10)
        pdf.cell(0, 10, f"Ticker: {d['ticker']} | Market Cap: ${d['mkt_cap']:,.0f}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", '', 11)
        pdf.cell(100, 10, f"Current WACC: {cw:.2%}")
        pdf.cell(100, 10, f"Target Optimal WACC: {mw:.2%}", ln=True)
        pdf.cell(100, 10, f"Current Debt Ratio: {curr_dr:.1%}")
        pdf.cell(100, 10, f"Optimal Debt Ratio: {orat:.1%}", ln=True)
        pdf.ln(10); pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, f"Strategic Status: {stat}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 10, f"Analysis: {desc}")
        pdf.ln(5)
        pdf.set_text_color(0, 128, 0) # Green
        pdf.multi_cell(0, 10, f"Recommended Actions: {d1}")
        pdf.set_text_color(255, 0, 0) # Red
        pdf.multi_cell(0, 10, f"Risk Warnings: {d2}")
        return pdf.output(dest='S').encode('latin-1')

    st.markdown("---")
    if st.button("📥 Download Comprehensive Analysis (PDF)"):
        pdf_out = generate_full_pdf(d, curr_wacc, min_w, opt_r, status, strategy_text, dos, donts)
        st.download_button("Click to Download PDF", pdf_out, f"WACC_Analysis_{d['ticker']}.pdf", "application/pdf")