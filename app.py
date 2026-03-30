import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# --- 1. Page Config & Custom Blue CSS ---
st.set_page_config(page_title="Executive WACC Optimizer", layout="wide")

# Corrected parameter: unsafe_allow_html=True
st.markdown("""
    <style>
    /* Main title color */
    h1 {
        color: #003366;
    }
    /* Professional Blue button */
    .stButton>button {
        background-color: #003366;
        color: white;
        border-radius: 5px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #004d99;
        color: white;
    }
    /* Metric Card Styling */
    [data-testid="stMetricValue"] {
        color: #003366;
    }
    .stMetric {
        background-color: #f0f5f9;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #003366;
    }
    </style>
    """, unsafe_allow_html=True)

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
                'ticker': "Analysis", 'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Financial Portfolio"
            }

# --- 3. Main Dashboard ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Financial Assumptions
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Model Parameters")
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
    st.header(f"Strategic Report: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC", f"{min_w:.2%}")
    m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Potential", f"{val_gain:+.2%}")
    
    # CHARTS (Shared for Screen and PDF)
    # WACC Curve
    fig_curve, ax_curve = plt.subplots(figsize=(10, 4))
    ax_curve.plot(ratios, wacc_list, color='#004d99', linewidth=3, label="Cost of Capital")
    ax_curve.axvline(curr_dr, color='#ff9900', linestyle='--', label="Current Mix")
    ax_curve.axvline(opt_r, color='#33cc33', linewidth=2, label="Optimal Target")
    ax_curve.set_facecolor('#f4f7f9')
    ax_curve.set_title("WACC Minimization Analysis", color='#003366', fontweight='bold')
    ax_curve.legend()
    st.pyplot(fig_curve)

    # Pie Chart
    fig_pie, ax_pie = plt.subplots(figsize=(6, 4))
    ax_pie.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], 
               autopct='%1.1f%%', colors=['#003366', '#6699cc'], startangle=140, explode=(0.05, 0))
    ax_pie.set_title("Current Capital Composition", color='#003366', fontweight='bold')
    st.pyplot(fig_pie)

    # Strategy Roadmap
    st.markdown("---")
    gap = opt_r - curr_dr
    if gap > 0.05:
        status, desc = "UNDER-LEVERAGED", "The firm should increase leverage to capture interest tax shields."
        dos = "Issue long-term debt, initiate share buybacks, and optimize capital structure for tax efficiency."
        donts = "Avoid new equity issuance or maintaining excessive cash reserves."
    elif gap < -0.05:
        status, desc = "OVER-LEVERAGED", "The firm's high debt load is driving up financial distress costs."
        dos = "Raise equity capital, divest non-core assets, and focus on debt reduction."
        donts = "Engage in new debt-funded acquisitions or use variable-rate financing."
    else:
        status, desc = "OPTIMAL", "Operating at peak financial efficiency."
        dos = "Focus on operational growth and cost control."; donts = "Alter the capital weights."

    st.write(f"**Strategic Status:** {status}")
    st.write(f"**Analysis:** {desc}")
    st.write(f"✅ **Do's:** {dos}")
    st.write(f"❌ **Don'ts:** {donts}")

    # --- BLUE THEMED PDF GENERATOR ---
    def generate_full_pdf(d, cw, mw, orat, stat, desc, d1, d2, f_curve, f_pie):
        pdf = FPDF()
        pdf.add_page()
        
        # Header Box
        pdf.set_fill_color(0, 51, 102) # Dark Blue
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 20)
        pdf.cell(190, 20, f"EXECUTIVE STRATEGY REPORT", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 10, f"{d['name']} ({d['ticker']})", ln=True, align='C')
        
        pdf.set_text_color(0, 0, 0)
        pdf.ln(20)

        # Metrics
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, "1. Key Financial Indicators", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(95, 10, f"Current WACC: {cw:.2%}", border='B')
        pdf.cell(95, 10, f"Optimal WACC: {mw:.2%}", border='B', ln=True)
        pdf.cell(95, 10, f"Current Debt Ratio: {curr_dr:.1%}", border='B')
        pdf.cell(95, 10, f"Optimal Debt Ratio: {orat:.1%}", border='B', ln=True)
        
        # Roadmap
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, f"2. Strategic Roadmap: {stat}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 8, f"Core Analysis: {desc}")
        pdf.ln(2)
        pdf.multi_cell(0, 8, f"Actionable Do's: {d1}")
        pdf.multi_cell(0, 8, f"Critical Don'ts: {d2}")

        # Images
        with tempfile.TemporaryDirectory() as tmpdir:
            curve_path = os.path.join(tmpdir, "curve.png")
            pie_path = os.path.join(tmpdir, "pie.png")
            f_curve.savefig(curve_path, bbox_inches='tight', dpi=150)
            f_pie.savefig(pie_path, bbox_inches='tight', dpi=150)
            
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(0, 51, 102)
            pdf.cell(0, 10, "3. Visual Optimization Data", ln=True)
            pdf.image(curve_path, x=10, w=190)
            pdf.ln(10)
            pdf.image(pie_path, x=50, w=110)
            
        return pdf.output(dest='S').encode('latin-1')

    st.markdown("---")
    if st.button("📥 Download Executive Blue Report (PDF)"):
        pdf_out = generate_full_pdf(d, curr_wacc, min_w, opt_r, status, desc, dos, donts, fig_curve, fig_pie)
        st.download_button("Save Analysis as PDF", pdf_out, f"Strategic_Report_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Please load data via the sidebar to generate your Blue Executive Report.")