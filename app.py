import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
import os

# --- 1. Page Config & Setup ---
st.set_page_config(page_title="Strategic WACC Optimizer", layout="wide")
st.title("Strategic Capital Structure & WACC Optimizer")

# Initialize session state for data persistence
if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# --- 2. Sidebar: Data Acquisition & Assumptions ---
st.sidebar.header("📂 Data Acquisition")
source = st.sidebar.radio("Data Source", ["Live API", "Manual CSV Upload"])

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
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 'name': "Strategic Analysis"
            }

# --- 3. Calculation Engine & Main Dashboard ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # Global Assumptions Sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Model Assumptions")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate (Rf)", value=0.043, format="%.4f")
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Interest Rate (%)", 2.0, 15.0, 5.0) / 100

    # Core Math Logic
    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap']))
    
    def run_wacc_model(interest_rate):
        ratios = np.linspace(0.01, 0.9, 100)
        curve = []
        for r in ratios:
            dyn_rd = interest_rate + (r * 0.12) # Risk penalty for high leverage
            lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
            re = rf + (lb * erp)
            wacc = ((1 - r) * re) + (r * dyn_rd * (1 - tax))
            curve.append({'ratio': r, 'wacc': wacc})
        return pd.DataFrame(curve)

    df_res = run_wacc_model(base_rd)
    min_row = df_res.loc[df_res['wacc'].idxmin()]
    opt_r, min_w = min_row['ratio'], min_row['wacc']
    curr_wacc = df_res.iloc[(df_res['ratio']-curr_dr).abs().argsort()[:1]]['wacc'].values[0]
    val_gain = ((1/min_w) - (1/curr_wacc)) / (1/curr_wacc)

    # --- TABBED INTERFACE ---
    tab1, tab2 = st.tabs(["📊 Executive Dashboard", "🧪 Scenario Analysis"])

    with tab1:
        # Metrics Header
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current WACC", f"{curr_wacc:.2%}")
        m2.metric("Optimal WACC", f"{min_w:.2%}")
        m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
        m4.metric("Value Potential", f"{val_gain:+.2%}")
        
        st.markdown("---")
        col_main, col_side = st.columns([2.5, 1])

        with col_main:
            # WACC Curve Chart (Fixed visibility)
            plt.style.use('dark_background')
            fig_curve, ax_curve = plt.subplots(figsize=(10, 4.5))
            ax_curve.plot(df_res['ratio'], df_res['wacc'], color='#00d4ff', linewidth=3, label="WACC Curve")
            ax_curve.axvline(curr_dr, color='#ff9900', linestyle='--', linewidth=2, label=f"Current ({curr_dr:.1%})")
            ax_curve.axvline(opt_r, color='#39ff14', linestyle='-', linewidth=2, label=f"Target ({opt_r:.1%})")
            ax_curve.set_title("Capital Structure Optimization", fontweight='bold', fontsize=14)
            ax_curve.set_xlabel("Debt Ratio")
            ax_curve.set_ylabel("WACC (%)")
            ax_curve.legend(facecolor='#1e1e1e')
            fig_curve.patch.set_alpha(0.0)
            st.pyplot(fig_curve)

        with col_side:
            # Pie Chart
            fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
            ax_pie.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], autopct='%1.1f%%', colors=['#1f77b4', '#d62728'], textprops={'color':"w"})
            ax_pie.set_title("Current Mix", color='white', fontweight='bold')
            fig_pie.patch.set_alpha(0.0)
            st.pyplot(fig_pie)
            st.write(f"**Debt Change Needed:** {((opt_r - curr_dr) * total_val / 1e6):+,.1f}M")

        # --- RESTORED STRATEGIC ROADMAP ---
        st.markdown("---")
        st.subheader("📜 Strategic Roadmap & Action Plan")
        gap = opt_r - curr_dr
        if gap > 0.05:
            status, desc = "UNDER-LEVERAGED", "Increase debt to capture tax shields and lower cost of capital."
            st.success(f"### Current Status: {status}")
            st.write(f"**Analysis:** {desc}")
            st.write("✅ **Do's:** Issue long-term bonds, conduct share buybacks.")
            st.write("❌ **Don'ts:** Issue new equity, maintain high idle cash.")
        elif gap < -0.05:
            status, desc = "OVER-LEVERAGED", "Reduce debt to lower financial risk and cost of equity."
            st.warning(f"### Current Status: {status}")
            st.write(f"**Analysis:** {desc}")
            st.write("✅ **Do's:** Asset divestment, equity infusion, prioritize debt repayment.")
            st.write("❌ **Don'ts:** High-dividend payouts, new variable-rate loans.")
        else:
            status, desc = "OPTIMAL", "Capital structure is efficiently balanced."
            st.info(f"### Current Status: {status}")
            st.write("✅ **Action:** Maintain current leverage and focus on operational alpha.")

    with tab2:
        st.header("🧪 Interest Rate Sensitivity Analysis")
        st.write("Determine how your optimal target shifts if market interest rates move.")
        
        # Sensitivity Table
        test_rates = [base_rd - 0.01, base_rd, base_rd + 0.01, base_rd + 0.02, base_rd + 0.03]
        results = []
        for r_test in test_rates:
            temp_df = run_wacc_model(r_test)
            t_min = temp_df['wacc'].min()
            t_opt = temp_df.loc[temp_df['wacc'].idxmin()]['ratio']
            results.append({"Base Int. Rate": f"{r_test:.1%}", "Opt. WACC": f"{t_min:.2%}", "Opt. Debt Ratio": f"{t_opt:.1%}"})
        
        st.table(pd.DataFrame(results))
        st.info("The table above helps you understand if you should 'lock in' debt now or wait based on rate expectations.")

    # --- 4. ADVANCED PDF GENERATOR ---
    def generate_full_pdf(data, cw, mw, orat, tax, rf, erp, f_curve):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(0, 15, f"TECHNICAL WACC REPORT: {data['name']}", ln=True, align='C')
        pdf.ln(5)

        # Metrics Table
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 10, "1. Executive Summary Metrics", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 10, f"Current WACC: {cw:.2%}", border=1); pdf.cell(95, 10, f"Optimal WACC: {mw:.2%}", border=1, ln=True)
        pdf.cell(95, 10, f"Target Debt Ratio: {orat:.1%}", border=1); pdf.cell(95, 10, f"Tax Rate: {tax:.0%}", border=1, ln=True)

        # Methodology
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. Strategic Optimization Methodology", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 8, f"Analysis based on Unlevered Beta of {unlevered_b:.2f}. "
                            f"Model utilizes Risk-Free Rate of {rf:.2%} and Equity Risk Premium of {erp:.2%}. "
                            "Optimization is achieved via the Trade-off Theory of Capital Structure.")

        # Chart (Resetting for PDF White Background)
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "p.png")
            f_curve.patch.set_facecolor('white')
            for ax in f_curve.axes: 
                ax.set_facecolor('white')
                ax.title.set_color('black'); ax.xaxis.label.set_color('black'); ax.yaxis.label.set_color('black')
                for t in ax.get_xticklabels() + ax.get_yticklabels(): t.set_color('black')
            f_curve.savefig(p, bbox_inches='tight')
            pdf.ln(10)
            pdf.image(p, x=20, w=170)
            
        return pdf.output(dest='S').encode('latin-1')

    st.markdown("---")
    if st.button("📥 Download Advanced Technical PDF"):
        pdf_bytes = generate_full_pdf(d, curr_wacc, min_w, opt_r, tax, rf, erp, fig_curve)
        st.download_button("Save Report", pdf_bytes, f"Executive_Report_{d['ticker']}.pdf", "application/pdf")

else:
    st.info("👈 Enter a ticker or upload a CSV in the sidebar to generate the analysis.")