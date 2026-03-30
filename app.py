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
        if st.sidebar.button("Analyze Upload"):
            st.session_state['fin_data'] = {
                'ticker': "Analysis", 'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Financial Report"
            }

# --- 3. Main Reporting Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    st.sidebar.markdown("---")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate", value=0.043)
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Interest Rate (%)", 2.0, 15.0, 5.0) / 100

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

    # UI: Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current WACC", f"{curr_wacc:.2%}")
    m2.metric("Optimal WACC", f"{min_w:.2%}")
    m3.metric("Optimal Debt Ratio", f"{opt_r:.1%}")
    m4.metric("Value Potential", f"{val_gain:+.2%}")
    
    st.markdown("---")
    col_strategy, col_chart, col_mix = st.columns([1.2, 2.5, 1.2])

    with col_strategy:
        st.subheader("📜 Roadmap")
        gap = opt_r - curr_dr
        if gap > 0.05:
            status, desc = "UNDER-LEVERAGED", "Increase debt to capture tax shields."
            dos, donts = "✅ DO: Issue Bonds / Buybacks", "❌ DON'T: Issue new Equity"
            st.success(f"### {status}")
        elif gap < -0.05:
            status, desc = "OVER-LEVERAGED", "Reduce debt to lower financial risk."
            dos, donts = "✅ DO: Equity Infusion / Asset Sales", "❌ DON'T: New variable loans"
            st.warning(f"### {status}")
        else:
            status, desc = "OPTIMAL", "Structure is balanced."
            dos, donts = "✅ DO: Maintain current ratio", "❌ DON'T: Significant shifts"
            st.info(f"### {status}")
        
        st.write(f"**Analysis:** {desc}")
        st.write(dos)
        st.write(donts)

    with col_chart:
        # WACC Curve - Forced High Visibility
        fig_curve, ax_curve = plt.subplots(figsize=(10, 5))
        ax_curve.plot(ratios, wacc_list, color='#00d4ff', linewidth=3)
        ax_curve.axvline(curr_dr, color='orange', linestyle='--', linewidth=2, label="Current Mix")
        ax_curve.axvline(opt_r, color='#39ff14', linestyle='-', linewidth=2, label="Optimal Target")
        
        # Fixing text visibility for dark mode
        plt.rcParams.update({'text.color': "white", 'axes.labelcolor': "white"})
        ax_curve.set_title("WACC Minimization Curve", fontsize=16, fontweight='bold', color="white")
        ax_curve.set_ylabel("Cost of Capital (%)", color="white")
        ax_curve.set_xlabel("Debt Ratio", color="white")
        ax_curve.tick_params(colors='white')
        ax_curve.legend(facecolor='#1e1e1e', labelcolor='white')
        fig_curve.patch.set_alpha(0.0)
        ax_curve.patch.set_alpha(0.0)
        st.pyplot(fig_curve, transparent=True)
        st.caption("**Insight:** The lowest point on this curve represents the maximum efficiency for your capital structure.")

    with col_mix:
        st.subheader("📊 Capital Mix")
        fig_pie, ax_pie = plt.subplots(figsize=(3, 3))
        # Better color contrast for the pie
        ax_pie.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], autopct='%1.1f%%', colors=['#0077b6', '#cc0000'], textprops={'color':"white"})
        fig_pie.patch.set_alpha(0.0)
        st.pyplot(fig_pie, transparent=True)
        
        st.markdown(f"""
        **Composition Description:**
        Your current debt ratio is **{curr_dr:.1%}**. To reach the optimal point shown on the chart, you should move toward **{opt_r:.1%}**.
        """)

    # --- PDF Generator ---
    def generate_pdf(data, cw, mw, orat, stat, desc, d1, d2, f_curve):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, f"Analysis: {data['name']}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Financial Status: {stat}", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 8, f"Summary: {desc}\n{d1}\n{d2}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "c.png")
            f_curve.patch.set_facecolor('white') # Reset for PDF
            f_curve.savefig(p, bbox_inches='tight')
            pdf.image(p, x=15, w=180)
        return pdf.output(dest='S').encode('latin-1')

    if st.button("📥 Download PDF Report"):
        pdf_bytes = generate_pdf(d, curr_wacc, min_w, opt_r, status, desc, dos, donts, fig_curve)
        st.download_button("Save PDF", pdf_bytes, f"Report_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Load data in the sidebar to begin.")