import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# --- 1. Page Config ---
st.set_page_config(page_title="Executive WACC Optimizer", layout="wide")
st.title("🏛️ Strategic Capital Structure & WACC Optimizer")
st.markdown("---")

# --- 2. Sidebar: Data Acquisition ---
st.sidebar.header("📂 Data Acquisition")
source = st.sidebar.radio("Data Source", ["Live API", "Manual CSV Upload"])

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

if source == "Live API":
    preset = st.sidebar.selectbox("Quick Load", ["Custom", "AAPL", "TSLA", "GOOGL", "MSFT", "NVDA"])
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
else:
    u = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if u:
        df = pd.read_csv(u)
        c1 = st.sidebar.selectbox("Market Cap Column", df.columns)
        c2 = st.sidebar.selectbox("Debt Column", df.columns)
        if st.sidebar.button("🚀 Analyze Data"):
            st.session_state['fin_data'] = {
                'ticker': "Dataset", 'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Financial Analysis Report"
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

    # Dashboard Metrics
    st.header(f"Report: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC", f"{min_w:.2%}")
    m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Potential", f"{val_gain:+.2%}")
    
    # CHARTS (Shared for Screen and PDF)
    # WACC Curve
    fig_curve, ax_curve = plt.subplots(figsize=(10, 4))
    ax_curve.plot(ratios, wacc_list, color='#0077b6', linewidth=2.5)
    ax_curve.axvline(curr_dr, color='orange', linestyle='--', label="Current")
    ax_curve.axvline(opt_r, color='green', label="Optimal")
    ax_curve.set_title("WACC Minimization Curve")
    ax_curve.legend()
    st.pyplot(fig_curve)

    # Pie Chart
    fig_pie, ax_pie = plt.subplots(figsize=(6, 4))
    ax_pie.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], autopct='%1.1f%%', colors=['#1f77b4', '#d62728'], startangle=140)
    ax_pie.set_title("Capital Structure Mix")
    st.pyplot(fig_pie)

    # Strategy Roadmap
    st.markdown("---")
    gap = opt_r - curr_dr
    if gap > 0.05:
        status, desc = "UNDER-LEVERAGED", "The firm should increase leverage to capture tax shields."
        dos = "Issue long-term bonds, initiate share buybacks, and optimize interest tax shields."
        donts = "Issue new equity or maintain high cash balances that dilute ROE."
    elif gap < -0.05:
        status, desc = "OVER-LEVERAGED", "The firm is over-leveraged; high financial risk is driving up costs."
        dos = "De-leverage via equity infusion, sell non-core assets, and focus on debt repayment."
        donts = "Take on new variable-rate debt or engage in aggressive debt-funded acquisitions."
    else:
        status, desc = "OPTIMAL", "Operating at peak efficiency."
        dos = "Focus on operational growth."; donts = "Change the capital mix."

    st.write(f"**Action Plan:** {desc}")
    st.write(f"✅ **Do's:** {dos}")
    st.write(f"❌ **Don'ts:** {donts}")

    # --- ADVANCED PDF GENERATOR ---
    def generate_full_pdf(d, cw, mw, orat, stat, desc, d1, d2, f_curve, f_pie):
        pdf = FPDF()
        pdf.add_page()
        
        # Heading
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(200, 15, f"Strategic Analysis: {d['name']}", ln=True, align='C')
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 10, f"Ticker/Reference: {d['ticker']}", ln=True, align='C')
        pdf.ln(5)

        # Metrics Table
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. Executive Summary Metrics", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(95, 10, f"Current WACC: {cw:.2%}", border=1)
        pdf.cell(95, 10, f"Optimal WACC: {mw:.2%}", border=1, ln=True)
        pdf.cell(95, 10, f"Current Debt Ratio: {curr_dr:.1%}", border=1)
        pdf.cell(95, 10, f"Target Debt Ratio: {orat:.1%}", border=1, ln=True)
        
        # Strategy Section
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"2. Strategic Roadmap: {stat}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 8, f"Analysis: {desc}")
        pdf.ln(2)
        pdf.multi_cell(0, 8, f"Action Plan: {d1}")
        pdf.multi_cell(0, 8, f"Risks to Avoid: {d2}")

        # Adding Images
        with tempfile.TemporaryDirectory() as tmpdir:
            curve_path = os.path.join(tmpdir, "curve.png")
            pie_path = os.path.join(tmpdir, "pie.png")
            f_curve.savefig(curve_path, bbox_inches='tight')
            f_pie.savefig(pie_path, bbox_inches='tight')
            
            pdf.ln(5)
            pdf.cell(0, 10, "3. Visual Data Analysis", ln=True)
            pdf.image(curve_path, x=15, w=180)
            pdf.ln(5)
            pdf.image(pie_path, x=60, w=90)
            
        return pdf.output(dest='S').encode('latin-1')

    st.markdown("---")
    if st.button("📥 Download Final Report (PDF)"):
        pdf_out = generate_full_pdf(d, curr_wacc, min_w, opt_r, status, desc, dos, donts, fig_curve, fig_pie)
        st.download_button("Click to Download", pdf_out, f"Report_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Load a ticker or upload data to begin.")