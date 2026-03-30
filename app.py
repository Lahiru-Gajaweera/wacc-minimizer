import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# --- 1. Page Config & Blue Theme ---
st.set_page_config(page_title="Executive WACC Optimizer", layout="wide")

st.markdown("""
    <style>
    .stButton>button { background-color: #003366; color: white; border-radius: 5px; }
    .stMetric { background-color: #f0f5f9; padding: 15px; border-radius: 10px; border-left: 5px solid #003366; }
    h1, h2, h3 { color: #003366; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏛️ Strategic Capital Structure & WACC Optimizer")
st.markdown("---")

# --- 2. Sidebar ---
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
                'ticker': "Analysis", 'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Financial Portfolio Report"
            }

# --- 3. Main Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    st.sidebar.markdown("---")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Interest Rate (%)", 2, 15, 5) / 100

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

    # UI: Header & Metrics
    st.header(f"Analysis For: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC", f"{min_w:.2%}")
    m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Potential", f"{val_gain:+.2%}")
    
    # UI: Visuals (Side-by-Side)
    st.markdown("---")
    col_chart, col_pie = st.columns([3, 1])

    with col_chart:
        fig_curve, ax_curve = plt.subplots(figsize=(10, 4))
        ax_curve.plot(ratios, wacc_list, color='#004d99', linewidth=3)
        ax_curve.axvline(curr_dr, color='orange', linestyle='--', label="Current")
        ax_curve.axvline(opt_r, color='green', label="Optimal")
        ax_curve.set_title("Cost of Capital Minimization", fontweight='bold')
        ax_curve.legend()
        fig_curve.patch.set_alpha(0.0)
        st.pyplot(fig_curve, transparent=True)

    with col_pie:
        fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
        ax_pie.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], autopct='%1.1f%%', colors=['#003366', '#6699cc'], startangle=140)
        ax_pie.set_title("Capital Mix", fontweight='bold')
        fig_pie.patch.set_alpha(0.0)
        st.pyplot(fig_pie, transparent=True)

    # UI: Roadmap (RE-ADDED IMPORTANT DESCRIPTIONS)
    st.markdown("---")
    st.subheader("📜 Strategic Roadmap")
    gap = opt_r - curr_dr
    if gap > 0.05:
        status, desc = "UNDER-LEVERAGED", "The firm is currently under-utilizing debt. Increasing leverage will create a tax shield and lower the overall cost of capital."
        dos = "Issue long-term debt, initiate share buybacks, and optimize interest tax shields."
        donts = "Avoid new equity issuance or holding excess cash that dilutes Return on Equity (ROE)."
    elif gap < -0.05:
        status, desc = "OVER-LEVERAGED", "The firm's debt levels are too high, increasing financial risk and the cost of equity. De-leveraging is required to stabilize."
        dos = "Raise equity capital, sell non-core assets, and prioritize debt repayment."
        donts = "Take on new variable-rate loans or engage in aggressive debt-funded acquisitions."
    else:
        status, desc = "OPTIMAL", "The capital structure is currently balanced for maximum firm value."
        dos = "Maintain current ratios and focus on operational growth."; donts = "Significantly shift the debt-to-equity mix."

    st.info(f"**Current Status:** {status}")
    st.write(f"**Strategic Analysis:** {desc}")
    st.write(f"✅ **Do's:** {dos}")
    st.write(f"❌ **Don'ts:** {donts}")

    # --- PDF GENERATOR (RE-ADDED FULL ANALYSIS) ---
    def generate_full_pdf(d, cw, mw, orat, stat, desc, d1, d2, f_curve):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_fill_color(0, 51, 102)
        pdf.rect(0, 0, 210, 35, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 15, f"EXECUTIVE WACC REPORT: {d['name']}", ln=True, align='C')
        
        pdf.set_text_color(0, 0, 0)
        pdf.ln(25)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. Financial Summary", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(95, 10, f"Current WACC: {cw:.2%}", border=1)
        pdf.cell(95, 10, f"Optimal WACC: {mw:.2%}", border=1, ln=True)
        pdf.cell(95, 10, f"Target Debt Ratio: {orat:.1%}", border=1, ln=True)

        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"2. Strategy: {stat}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 8, f"Analysis: {desc}")
        pdf.ln(2)
        pdf.multi_cell(0, 8, f"Actions: {d1}")
        pdf.multi_cell(0, 8, f"Risks: {d2}")

        with tempfile.TemporaryDirectory() as tmpdir:
            curve_path = os.path.join(tmpdir, "curve.png")
            f_curve.patch.set_alpha(1.0) # Ensure visible on PDF
            f_curve.savefig(curve_path, bbox_inches='tight')
            pdf.ln(5)
            pdf.image(curve_path, x=15, w=180)
            
        return pdf.output(dest='S').encode('latin-1')

    st.markdown("---")
    if st.button("📥 Download Comprehensive Blue Report (PDF)"):
        pdf_out = generate_full_pdf(d, curr_wacc, min_w, opt_r, status, desc, dos, donts, fig_curve)
        st.download_button("Save Analysis as PDF", pdf_out, f"WACC_Report_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Please load data to view the full analysis.")