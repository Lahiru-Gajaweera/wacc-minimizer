import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import os
from fpdf import FPDF

# --- 1. Page Config ---
st.set_page_config(page_title="Strategic WACC Advisor", layout="wide")
st.title("🛡️ Strategic Capital Structure & WACC Advisor")
st.markdown("---")

# --- 2. Sidebar: Data & Controls ---
st.sidebar.header("📂 Data & Controls")
source = st.sidebar.radio("Data Source", ["Live API", "Manual CSV Upload"])

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

if source == "Live API":
    preset = st.sidebar.selectbox("Quick Load", ["Custom", "AAPL", "TSLA", "GOOGL", "MSFT", "NVDA"])
    ticker_input = st.sidebar.text_input("Ticker Symbol", value="" if preset == "Custom" else preset).upper()
    if st.sidebar.button("🔍 Fetch Data"):
        try:
            with st.spinner(f"Accessing market data for {ticker_input}..."):
                s = yf.Ticker(ticker_input); i = s.info
                st.session_state['fin_data'] = {
                    'ticker': ticker_input, 'mkt_cap': i.get('marketCap', 1e9), 
                    'total_debt': i.get('totalDebt', 0), 'beta': i.get('beta', 1.0), 
                    'name': i.get('longName', ticker_input)
                }
                st.sidebar.success(f"Loaded: {ticker_input}")
        except: st.sidebar.error("Ticker not found.")
else:
    u = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if u:
        df = pd.read_csv(u)
        c1 = st.sidebar.selectbox("Market Cap Column", df.columns)
        c2 = st.sidebar.selectbox("Debt Column", df.columns)
        if st.sidebar.button("Analyze Upload"):
            st.session_state['fin_data'] = {
                'ticker': "Analysis", 'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Financial Portfolio Report"
            }

# --- 3. Main Reporting Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Global Assumptions Sidebar
    st.sidebar.markdown("---")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate (e.g., 10Y)", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Interest Rate (%)", 2.0, 15.0, 5.0) / 100

    # Math Logic (Trade-off Model)
    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val
    # Hamada Formula for Unlevered Beta
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap']))
    
    ratios = np.linspace(0.01, 0.9, 100)
    wacc_list = []
    for r in ratios:
        dyn_rd = base_rd + (r * 0.12) # Dynamic Credit Risk Penalty
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dyn_rd * (1 - tax))
        wacc_list.append(wacc)
    
    min_w = min(wacc_list); opt_r = ratios[np.argmin(wacc_list)]
    curr_wacc = wacc_list[np.abs(ratios - curr_dr).argmin()]
    potential_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc)

    # UI: Report Header & Key Metrics
    st.header(f"WACC Summary: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC (Goal)", f"{min_w:.2%}")
    m3.metric("Optimal Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Creation Potential", f"{potential_gain:+.2%}")
    st.markdown("---")

    # --- ADVANCED LAYOUT: Charts & Mix Descriptions (NEW LOOK) ---
    col_strategy, col_chart, col_mix = st.columns([1, 2.5, 1.2]) # Compact strategy, Large Curve, Informative Mix

    with col_chart:
        # 1. WACC Curve (High Legibility)
        fig_curve, ax_curve = plt.subplots(figsize=(10, 5))
        ax_curve.plot(ratios, wacc_list, color='#004d99', linewidth=3)
        ax_curve.axvline(curr_dr, color='orange', linestyle='--', linewidth=2.5, label=f"Current Mix ({curr_dr:.1%})")
        ax_curve.axvline(opt_r, color='green', linestyle='-', linewidth=2.5, label=f"Optimal Target ({opt_r:.1%})")
        
        # LEGIBILITY UPDATES
        ax_curve.set_title("Weighted Average Cost of Capital Minimization Curve", fontsize=16, fontweight='bold', pad=15)
        ax_curve.set_ylabel("WACC (%)", fontsize=12)
        ax_curve.set_xlabel("Debt-to-Capital Ratio (Leverage)", fontsize=12)
        ax_curve.legend(fontsize=11)
        st.pyplot(fig_curve)
        
        st.caption(f"**Description (WACC Curve):** The green line marks the capital structure that minimizes the firm's financing costs and maximizes Enterprise Value by balancing interest tax shields against financial distress costs.")

    with col_mix:
        # 2. Capital Mix (Compact Pie & Advanced Descriptions)
        fig_pie, ax_pie = plt.subplots(figsize=(3, 3))
        ax_pie.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], autopct='%1.1f%%', colors=['#1f77b4', '#d62728'], startangle=140)
        
        # LEGIBILITY UPDATES
        ax_pie.set_title("Current Composition", fontsize=14, fontweight='bold', pad=10)
        st.pyplot(fig_pie)
        
        # ADDED DESCRIPTIONS
        st.info(f"#### Structuring Insights")
        st.markdown(f"""
        **Current Mix Description:**
        Your business is operating with {d['mkt_cap']/(total_val):.1%} equity and {d['total_debt']/(total_val):.1%} debt. This mix has a high reliance on equity, which is your most expensive form of capital.

        **Target Mix Description:**
        The model recommends moving toward **{opt_r:.1%} debt**. This will significantly reduce your weighted average cost by capitalizing on the tax deductibility of interest.
        """)

    with col_strategy:
        # 3. Strategy Snapshot (Moved to 1st Column)
        st.subheader("📜 Executive Roadmap")
        gap = opt_r - curr_dr
        if gap > 0.05:
            status, desc = "UNDER-LEVERAGED", "Increase leverage to capture tax shields."
            d1 = "DO: Issue Bonds, share buybacks."
            d2 = "DON'T: New equity issue, high cash."
        elif gap < -0.05:
            status, desc = "OVER-LEVERAGED", "Reduce debt to lower financial risk."
            d1 = "DO: Equity infusion, asset sales."
            d2 = "DON'T: Variable loans, M&A."
        else:
            status, desc = "OPTIMAL", "Structure is balanced."
            d1 = "DO: Operational efficiency."; d2 = "DON'T: Shift the mix."
            
        st.warning(f"### Status: {status}") if status == "OVER-LEVERAGED" else st.success(f"### Status: {status}") if status == "UNDER-LEVERAGED" else st.info(f"### Status: {status}")
        st.write(f"**Analysis:** {desc}")
        st.write(d1)
        st.write(d2)

    # --- 4. ADVANCED PDF Report Generator ---
    def generate_pdf(data, c_wacc, m_wacc, o_ratio, stat, desc, d1, d2, f_curve):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(200, 15, f"Executive WACC Analysis: {data['name']}", ln=True, align='C')
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 10, f"Ticker: {data['ticker']}", ln=True, align='C')
        pdf.ln(5)

        # KPIs
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. Key Financial Indicators", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(95, 10, f"Current WACC: {c_wacc:.2%}", border=1)
        pdf.cell(95, 10, f"Target Minimal WACC: {m_wacc:.2%}", border=1, ln=True)
        pdf.cell(95, 10, f"Target Debt Ratio: {o_ratio:.1%}", border=1)
        pdf.cell(95, 10, f"Value creation Potential: {val_gain:+.2%}", border=1, ln=True)
        
        # Strategy
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"2. Strategic Action Plan: {stat}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 8, f"Analysis: {desc}")
        pdf.multi_cell(0, 8, f"Actions: {d1}")
        pdf.multi_cell(0, 8, f"Risks: {d2}")

        # Curve Chart
        with tempfile.TemporaryDirectory() as tmpdir:
            curve_path = os.path.join(tmpdir, "curve.png")
            f_curve.patch.set_alpha(1.0) # Ensure visible on PDF
            f_curve.savefig(curve_path, bbox_inches='tight')
            pdf.ln(5)
            pdf.image(curve_path, x=15, w=180)
            
        return pdf.output(dest='S').encode('latin-1')

    st.markdown("---")
    if st.button("📥 Generate Comprehensive Analysis (PDF)"):
        pdf_bytes = generate_pdf(d, curr_wacc, min_w, opt_r, status, desc, dos, donts, fig_curve)
        st.download_button("Save Analysis as PDF", pdf_bytes, f"WACC_Report_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Load data via the sidebar to generate the Strategic Report.")