import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# --- 1. Page Config ---
st.set_page_config(page_title="WACC Optimizer", layout="wide")
st.title("📊 Strategic Capital Structure & WACC Optimizer")
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
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Manual Upload Analysis"
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

    # UI: Header & Metrics
    st.header(f"Results for {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC", f"{min_w:.2%}")
    m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Potential", f"{val_gain:+.2%}")
    
    # UI: Charts (Refined Visibility)
    st.markdown("---")
    col_left, col_right = st.columns([2.5, 1])

    with col_left:
        # High-Contrast WACC Curve
        plt.style.use('dark_background')
        fig_curve, ax_curve = plt.subplots(figsize=(10, 5))
        ax_curve.plot(ratios, wacc_list, color='#00d4ff', linewidth=3, label="WACC Curve")
        ax_curve.axvline(curr_dr, color='#ff9900', linestyle='--', linewidth=2, label=f"Current Mix ({curr_dr:.1%})")
        ax_curve.axvline(opt_r, color='#39ff14', linestyle='-', linewidth=2, label=f"Optimal Target ({opt_r:.1%})")
        
        ax_curve.set_title("WACC Minimization Analysis", fontsize=14, fontweight='bold', pad=20)
        ax_curve.set_xlabel("Debt-to-Capital Ratio", fontsize=10)
        ax_curve.set_ylabel("Cost of Capital (%)", fontsize=10)
        ax_curve.legend(loc='upper right', frameon=True, facecolor='#262730', edgecolor='white')
        
        fig_curve.patch.set_alpha(0.0) # Transparent background for Streamlit
        st.pyplot(fig_curve)
        st.caption("**Curve Analysis:** The lowest point on the blue line represents the capital structure that maximizes firm value.")

    with col_right:
        # High-Contrast Pie
        fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
        ax_pie.pie([d['mkt_cap'], d['total_debt']], 
                   labels=['Equity', 'Debt'], 
                   autopct='%1.1f%%', 
                   startangle=140, 
                   colors=['#1f77b4', '#ff4b4b'],
                   textprops={'color':"w", 'weight':'bold'})
        ax_pie.set_title("Current Capital Mix", fontsize=12, fontweight='bold', color='white')
        fig_pie.patch.set_alpha(0.0)
        st.pyplot(fig_pie)
        
        # ADDED DESCRIPTION UNDER PIE
        st.markdown(f"""
        **Composition Breakdown:**
        The firm currently carries **{d['total_debt']/(total_val):.1%}** debt relative to equity. 
        To reach the optimal cost of capital, a shift towards **{opt_r:.1%}** leverage is recommended.
        """)

    # UI: Strategy Roadmap
    st.markdown("---")
    st.subheader("📜 Strategic Roadmap & Analysis")
    gap = opt_r - curr_dr
    if gap > 0.05:
        status, desc = "UNDER-LEVERAGED", "The firm is not utilizing enough debt. Increasing leverage will create an interest tax shield, effectively lowering the cost of capital."
        dos = "Issue long-term debt, use proceeds for share buybacks."
        donts = "Avoid issuing new equity or holding large idle cash balances."
    elif gap < -0.05:
        status, desc = "OVER-LEVERAGED", "The firm's debt level is exceeding its optimal capacity. High leverage is driving up the cost of equity."
        dos = "Prioritize debt repayment and consider an equity infusion."
        donts = "Take on new high-interest debt or aggressive expansions."
    else:
        status, desc = "OPTIMAL", "The capital structure is currently balanced for maximum firm value."
        dos = "Maintain current debt-to-equity targets."; donts = "Significantly alter the leverage ratio."

    st.write(f"**Current Status:** {status}")
    st.write(f"**Analysis:** {desc}")
    st.write(f"✅ **Do's:** {dos}")
    st.write(f"❌ **Don'ts:** {donts}")

    # --- PDF GENERATOR ---
    def generate_full_pdf(d, cw, mw, orat, stat, desc, d1, d2, f_curve):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, f"Strategic WACC Report: {d['name']}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Status: {stat}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 8, f"Summary: {desc}\n\nRecommended: {d1}\nAvoid: {d2}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            curve_path = os.path.join(tmpdir, "curve.png")
            # Temporarily reset to white for PDF printing
            f_curve.patch.set_facecolor('white')
            f_curve.savefig(curve_path, bbox_inches='tight')
            pdf.ln(10)
            pdf.image(curve_path, x=15, w=180)
        return pdf.output(dest='S').encode('latin-1')

    if st.button("📥 Download Analysis (PDF)"):
        pdf_out = generate_full_pdf(d, curr_wacc, min_w, opt_r, status, desc, dos, donts, fig_curve)
        st.download_button("Save Report", pdf_out, f"WACC_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Load a ticker or upload data to begin.")