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
st.title("🏛️ Advanced Capital Structure & WACC Optimizer")
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
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Strategic Portfolio Analysis"
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
    # Hamada Formula: Unlevering Beta
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap']))
    
    ratios = np.linspace(0.01, 0.9, 100)
    wacc_results = []
    for r in ratios:
        dyn_rd = base_rd + (r * 0.12)
        lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
        re = rf + (lb * erp)
        wacc = ((1 - r) * re) + (r * dyn_rd * (1 - tax))
        wacc_results.append({'ratio': r, 'wacc': wacc, 'cost_equity': re, 'cost_debt': dyn_rd * (1-tax)})
    
    df_results = pd.DataFrame(wacc_results)
    min_row = df_results.loc[df_results['wacc'].idxmin()]
    opt_r = min_row['ratio']
    min_w = min_row['wacc']
    
    curr_wacc = df_results.iloc[(df_results['ratio']-curr_dr).abs().argsort()[:1]]['wacc'].values[0]
    val_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc)

    # UI: Header & Metrics
    st.header(f"Strategic Report: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Minimum WACC", f"{min_w:.2%}")
    m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Enterprise Value 𝚫", f"{val_gain:+.2%}")
    
    st.markdown("---")
    col_left, col_right = st.columns([2.5, 1])

    with col_left:
        plt.style.use('dark_background')
        fig_curve, ax_curve = plt.subplots(figsize=(10, 5))
        ax_curve.plot(df_results['ratio'], df_results['wacc'], color='#00d4ff', linewidth=3, label="WACC Curve")
        ax_curve.axvline(curr_dr, color='#ff9900', linestyle='--', label=f"Current ({curr_dr:.1%})")
        ax_curve.axvline(opt_r, color='#39ff14', linestyle='-', label=f"Optimal ({opt_r:.1%})")
        ax_curve.set_title("Capital Structure Cost Minimization", fontsize=14, fontweight='bold')
        ax_curve.set_xlabel("Debt Ratio (D / D+E)")
        ax_curve.set_ylabel("WACC (%)")
        ax_curve.legend()
        fig_curve.patch.set_alpha(0.0)
        st.pyplot(fig_curve)

    with col_right:
        fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
        ax_pie.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], autopct='%1.1f%%', colors=['#1f77b4', '#ff4b4b'])
        ax_pie.set_title("Current Composition", color='white', fontweight='bold')
        fig_pie.patch.set_alpha(0.0)
        st.pyplot(fig_pie)
        
        st.info(f"**Insight:** To reach optimal efficiency, the firm requires a **{abs(opt_r-curr_dr):.1%}** shift in leverage.")

    # --- ADVANCED PDF GENERATOR ---
    def generate_detailed_pdf(d, cw, mw, orat, tax, rf, erp, ub, vg, f_curve):
        pdf = FPDF()
        pdf.add_page()
        
        # Header Section
        pdf.set_font("Arial", 'B', 20)
        pdf.cell(0, 15, "STRATEGIC CAPITAL STRUCTURE REPORT", ln=True, align='C')
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 5, f"Subject: {d['name']} ({d['ticker']})", ln=True, align='C')
        pdf.ln(10)

        # 1. Executive Summary Table
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, "1. Key Performance Indicators (KPIs)", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        
        data = [
            ["Metric", "Value", "Metric", "Value"],
            ["Current WACC", f"{cw:.2%}", "Optimal WACC", f"{mw:.2%}"],
            ["Current Debt Ratio", f"{curr_dr:.1%}", "Target Debt Ratio", f"{orat:.1%}"],
            ["Value Opportunity", f"{vg:+.2%}", "Unlevered Beta", f"{ub:.3f}"]
        ]
        
        for row in data:
            pdf.cell(47.5, 8, row[0], border=1)
            pdf.cell(47.5, 8, row[1], border=1)
            pdf.cell(47.5, 8, row[2], border=1)
            pdf.cell(47.5, 8, row[3], border=1, ln=True)

        # 2. Methodology & Assumptions
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. Financial Assumptions & Methodology", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, f"The analysis utilizes the Trade-off Theory of Capital Structure. We deleverage the market beta using the Hamada Equation to isolate operating risk ($ {ub:.2f} $) and re-leverage it at various intervals to find the point where interest tax shields are maximized without incurring excessive distress costs.\n\n"
                            f"Assumed Marginal Tax Rate: {tax*100}% | Risk-Free Rate: {rf*100}% | ERP: {erp*100}%")

        # 3. Visualization
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "chart.png")
            f_curve.patch.set_facecolor('white') # Set white for print
            for ax in f_curve.axes: 
                ax.set_facecolor('white')
                ax.title.set_color('black')
                ax.xaxis.label.set_color('black')
                ax.yaxis.label.set_color('black')
                for t in ax.get_xticklabels() + ax.get_yticklabels(): t.set_color('black')
            f_curve.savefig(p, bbox_inches='tight')
            pdf.ln(5)
            pdf.image(p, x=20, w=170)

        # 4. Strategic Roadmap
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "3. Strategic Implementation Roadmap", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        
        gap = orat - curr_dr
        if gap > 0.05:
            msg = "UNDER-LEVERAGED: The firm should seek to increase debt through bond issuance or debt-funded share buybacks to capture significant tax shields."
        elif gap < -0.05:
            msg = "OVER-LEVERAGED: Financial risk is currently suppressing equity value. Prioritize debt reduction via asset divestment or equity infusion."
        else:
            msg = "OPTIMAL: The current structure is efficient. Focus on operational alpha rather than financial engineering."
        
        pdf.multi_cell(0, 8, msg)
        
        return pdf.output(dest='S').encode('latin-1')

    st.markdown("---")
    if st.button("📥 Generate Full Technical Report (PDF)"):
        pdf_out = generate_detailed_pdf(d, curr_wacc, min_w, opt_r, tax, rf, erp, unlevered_b, val_gain, fig_curve)
        st.download_button("Download Advanced Report", pdf_out, f"Technical_WACC_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Please enter financial data in the sidebar.")