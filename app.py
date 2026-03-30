import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# --- 1. Page Config ---
st.set_page_config(page_title="Advanced WACC Optimizer", layout="wide")
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
                'ticker': "Manual", 'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Financial Portfolio Analysis"
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
    wacc_results = []
    for r in ratios:
        dyn_rd = base_rd + (r * 0.12)
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dyn_rd * (1 - tax))
        wacc_results.append({'ratio': r, 'wacc': wacc, 're': re, 'rd': dyn_rd * (1-tax)})
    
    df_res = pd.DataFrame(wacc_results)
    min_row = df_res.loc[df_res['wacc'].idxmin()]
    opt_r, min_w = min_row['ratio'], min_row['wacc']
    curr_wacc = df_res.iloc[(df_res['ratio']-curr_dr).abs().argsort()[:1]]['wacc'].values[0]
    val_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc)

    # UI: Header & Metrics
    st.header(f"Executive Report: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC", f"{min_w:.2%}")
    m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Improvement", f"{val_gain:+.2%}")
    
    st.markdown("---")
    col_left, col_right = st.columns([2.5, 1])

    with col_left:
        plt.style.use('dark_background')
        fig_curve, ax_curve = plt.subplots(figsize=(10, 5))
        ax_curve.plot(df_res['ratio'], df_res['wacc'], color='#00d4ff', linewidth=3, label="WACC Curve")
        ax_curve.axvline(curr_dr, color='#ff9900', linestyle='--', label=f"Current Mix ({curr_dr:.1%})")
        ax_curve.axvline(opt_r, color='#39ff14', linestyle='-', label=f"Optimal Target ({opt_r:.1%})")
        ax_curve.set_title("WACC Minimization Analysis", fontsize=14, fontweight='bold', color='white')
        ax_curve.legend(facecolor='#1e1e1e', labelcolor='white')
        fig_curve.patch.set_alpha(0.0)
        st.pyplot(fig_curve)

    with col_right:
        fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
        ax_pie.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], autopct='%1.1f%%', colors=['#1f77b4', '#ff4b4b'], textprops={'color':"w"})
        ax_pie.set_title("Current Composition", color='white', fontweight='bold')
        fig_pie.patch.set_alpha(0.0)
        st.pyplot(fig_pie)
        st.write(f"Current Leverage: **{curr_dr:.1%}**")
        st.write(f"Target Leverage: **{opt_r:.1%}**")

    # --- RESTORED ROADMAP SECTION ---
    st.markdown("---")
    st.subheader("📜 Strategic Roadmap")
    gap = opt_r - curr_dr
    if gap > 0.05:
        status, roadmap_text = "UNDER-LEVERAGED", "The firm is currently under-utilizing debt. Increasing leverage will create a tax shield and lower the overall cost of capital."
        actions = "✅ **Action Plan:** Issue long-term debt, initiate share buybacks, and optimize interest tax shields."
        risks = "❌ **Avoid:** New equity issuance or holding excess cash that dilutes ROE."
        st.success(f"**Current Status:** {status}")
    elif gap < -0.05:
        status, roadmap_text = "OVER-LEVERAGED", "The firm's debt levels are too high, increasing financial risk and the cost of equity. De-leveraging is required to stabilize."
        actions = "✅ **Action Plan:** Raise equity capital, sell non-core assets, and prioritize debt repayment."
        risks = "❌ **Avoid:** Variable-rate loans or aggressive debt-funded acquisitions."
        st.warning(f"**Current Status:** {status}")
    else:
        status, roadmap_text = "OPTIMAL", "The capital structure is currently balanced for maximum firm value."
        actions = "✅ **Action Plan:** Maintain current ratios and focus on operational growth."
        risks = "❌ **Avoid:** Significantly shifting the debt-to-equity mix."
        st.info(f"**Current Status:** {status}")

    st.write(f"**Analysis:** {roadmap_text}")
    st.write(actions)
    st.write(risks)

    # --- ADVANCED PDF GENERATOR ---
    def generate_detailed_pdf(d, cw, mw, orat, tax, rf, erp, status, roadmap, act, rsk, f_curve):
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(0, 15, "TECHNICAL CAPITAL STRUCTURE ANALYSIS", ln=True, align='C')
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 5, f"Prepared for: {d['name']} ({d['ticker']})", ln=True, align='C')
        pdf.ln(10)

        # KPIs Section
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, "1. Executive Summary & KPIs", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 10, f"Current WACC: {cw:.2%}", border=1)
        pdf.cell(95, 10, f"Optimal WACC: {mw:.2%}", border=1, ln=True)
        pdf.cell(95, 10, f"Current Debt Ratio: {curr_dr:.1%}", border=1)
        pdf.cell(95, 10, f"Target Debt Ratio: {orat:.1%}", border=1, ln=True)

        # Strategic Roadmap Section
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"2. Strategic Roadmap: {status}", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 8, f"Summary Analysis: {roadmap}")
        pdf.ln(2)
        pdf.multi_cell(0, 8, f"{act}")
        pdf.multi_cell(0, 8, f"{rsk}")

        # Methodology & Chart
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "3. Optimization Methodology", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, "This report utilizes a dynamic WACC model incorporating the Hamada equation to account for financial risk. The cost of debt is adjusted dynamically based on leverage-induced credit risk premiums.")

        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "curve.png")
            f_curve.patch.set_facecolor('white') # Prepare for white background PDF
            for ax in f_curve.axes: 
                ax.set_facecolor('white')
                ax.title.set_color('black')
                ax.xaxis.label.set_color('black')
                ax.yaxis.label.set_color('black')
                for t in ax.get_xticklabels() + ax.get_yticklabels(): t.set_color('black')
            f_curve.savefig(p, bbox_inches='tight')
            pdf.image(p, x=20, w=170)
            
        return pdf.output(dest='S').encode('latin-1')

    if st.button("📥 Download Advanced Technical Report"):
        pdf_out = generate_detailed_pdf(d, curr_wacc, min_w, opt_r, tax, rf, erp, status, roadmap_text, actions, risks, fig_curve)
        st.download_button("Save Advanced PDF", pdf_out, f"WACC_Analysis_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Please load a ticker or upload a file to view the roadmap and analysis.")