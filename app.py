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
st.title("🏛️ Strategic Capital Structure & WACC Optimizer")

if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# --- 2. Sidebar: Data Acquisition ---
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
                'name': i.get('longName', ticker_input),
                'ebit': i.get('ebit', 1e8) # Pulling EBIT for coverage tracking
            }
        except: st.sidebar.error("Ticker not found.")
else:
    u = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if u:
        df = pd.read_csv(u)
        c1 = st.sidebar.selectbox("Market Cap Column", df.columns)
        c2 = st.sidebar.selectbox("Debt Column", df.columns)
        c3 = st.sidebar.selectbox("EBIT (Optional)", ["None"] + list(df.columns))
        if st.sidebar.button("🚀 Analyze Data"):
            ebit_val = float(df[c3].iloc[0]) if c3 != "None" else 1e8
            st.session_state['fin_data'] = {
                'ticker': "Manual", 'mkt_cap': float(df[c1].iloc[0]), 
                'total_debt': float(df[c2].iloc[0]), 'beta': 1.1, 
                'name': "Strategic Analysis", 'ebit': ebit_val
            }

# --- 3. Calculation Engine ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Model Assumptions")
    tax = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
    rf = st.sidebar.number_input("Risk-Free Rate", value=0.043, format="%.4f")
    erp = st.sidebar.slider("Equity Risk Premium (%)", 3, 9, 5) / 100
    base_rd = st.sidebar.slider("Base Interest Rate (%)", 2.0, 15.0, 5.0) / 100

    total_val = d['mkt_cap'] + d['total_debt']
    curr_dr = d['total_debt'] / total_val
    unlevered_b = d['beta'] / (1 + (1 - tax) * (d['total_debt'] / d['mkt_cap']))
    
    def run_wacc_model(interest_rate):
        ratios = np.linspace(0.01, 0.9, 100)
        curve = []
        for r in ratios:
            dyn_rd = interest_rate + (r * 0.12)
            lb = unlevered_b * (1 + (1 - tax) * (r / (1 - r)))
            re = rf + (lb * erp)
            wacc = ((1 - r) * re) + (r * dyn_rd * (1 - tax))
            curve.append({'ratio': r, 'wacc': wacc, 'rd': dyn_rd})
        return pd.DataFrame(curve)

    df_res = run_wacc_model(base_rd)
    min_row = df_res.loc[df_res['wacc'].idxmin()]
    opt_r, min_w = min_row['ratio'], min_row['wacc']
    curr_wacc = df_res.iloc[(df_res['ratio']-curr_dr).abs().argsort()[:1]]['wacc'].values[0]

    # --- TABS ---
    tab1, tab2 = st.tabs(["📊 Executive Dashboard", "🧪 Scenarios & Capacity"])

    with tab1:
        # Standard KPI Dashboard
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current WACC", f"{curr_wacc:.2%}")
        m2.metric("Optimal WACC", f"{min_w:.2%}")
        m3.metric("Target Debt Ratio", f"{opt_r:.1%}")
        m4.metric("Value Potential", f"{((1/min_w)-(1/curr_wacc))/(1/curr_wacc):+.2%}")
        
        st.markdown("---")
        col_m, col_s = st.columns([2.5, 1])
        with col_m:
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(10, 4.5))
            ax.plot(df_res['ratio'], df_res['wacc'], color='#00d4ff', lw=3, label="WACC Curve")
            ax.axvline(curr_dr, color='#ff9900', ls='--', label=f"Current ({curr_dr:.1%})")
            ax.axvline(opt_r, color='#39ff14', label=f"Optimal ({opt_r:.1%})")
            ax.set_title("WACC Minimization Curve", fontweight='bold')
            ax.legend()
            fig.patch.set_alpha(0.0)
            st.pyplot(fig)
        with col_s:
            fig2, ax2 = plt.subplots(figsize=(4, 4))
            ax2.pie([d['mkt_cap'], d['total_debt']], labels=['Equity', 'Debt'], autopct='%1.1f%%', colors=['#1f77b4', '#d62728'], textprops={'color':"w"})
            ax2.set_title("Current Composition", color='white', fontweight='bold')
            fig2.patch.set_alpha(0.0)
            st.pyplot(fig2)

        # Roadmap
        st.markdown("---")
        st.subheader("📜 Strategic Roadmap")
        gap = opt_r - curr_dr
        if gap > 0.05:
            st.success("### Status: UNDER-LEVERAGED")
            st.write("Analysis: Increase debt to capture tax shields.")
        elif gap < -0.05:
            st.warning("### Status: OVER-LEVERAGED")
            st.write("Analysis: Reduce debt to lower financial risk.")
        else:
            st.info("### Status: OPTIMAL")
            st.write("Analysis: Capital structure is balanced.")

    with tab2:
        st.header("🧪 Debt Capacity & Stress Testing")
        
        # Dollar-Value Targets
        st.subheader("💰 Dollar-Value Debt Capacity")
        target_debt_total = opt_r * total_val
        debt_adjustment = target_debt_total - d['total_debt']
        
        c1, c2 = st.columns(2)
        c1.metric("Current Total Debt", f"${d['total_debt']/1e6:,.1f}M")
        c2.metric("Target Total Debt", f"${target_debt_total/1e6:,.1f}M")
        st.metric("Suggested Adjustment", f"${debt_adjustment/1e6:,.1f}M", delta_color="normal", 
                  help="Dollar amount to add/remove to reach the optimal WACC structure.")

        # Covenant Tracking
        st.markdown("---")
        st.subheader("⚠️ Covenant & Coverage Tracking")
        # Calc interest at target
        target_int_rate = base_rd + (opt_r * 0.12)
        target_interest_exp = target_debt_total * target_int_rate
        coverage_ratio = d['ebit'] / target_interest_exp # EBIT/Interest
        
        st.write(f"**Target Interest Coverage Ratio (EBIT / Interest):** {coverage_ratio:.2f}x")
        if coverage_ratio < 2.5:
            st.error("Warning: Proposed debt levels may lead to a credit rating downgrade.")
        else:
            st.success("Proposed debt levels maintain a healthy interest coverage ratio.")

        # Sensitivity Table
        st.markdown("---")
        st.write("**Interest Rate Stress Test**")
        rates = [base_rd - 0.01, base_rd, base_rd + 0.01, base_rd + 0.02]
        stress = []
        for rt in rates:
            temp = run_wacc_model(rt); t_min = temp['wacc'].min()
            stress.append({"Interest Rate": f"{rt:.1%}", "Opt. WACC": f"{t_min:.2%}", "Opt. Debt Ratio": f"{temp.loc[temp['wacc'].idxmin()]['ratio']:.1%}"})
        st.table(pd.DataFrame(stress))

    # --- 4. PDF Generator ---
    def generate_pdf(data, cw, mw, orat, adj, cov, f_curve):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Strategic Report: {data['name']}", ln=True, align='C')
        pdf.ln(5)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 10, f"Target Optimal Debt Ratio: {orat:.1%}", ln=True)
        pdf.cell(0, 10, f"Suggested Debt Adjustment: ${adj/1e6:,.1f}M", ln=True)
        pdf.cell(0, 10, f"Projected Coverage Ratio: {cov:.2f}x", ln=True)
        
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "c.png"); f_curve.patch.set_facecolor('white')
            for ax in f_curve.axes: ax.set_facecolor('white')
            f_curve.savefig(p, bbox_inches='tight')
            pdf.image(p, x=20, w=170)
        return pdf.output(dest='S').encode('latin-1')

    if st.button("📥 Download Full Technical PDF"):
        p_bytes = generate_pdf(d, curr_wacc, min_w, opt_r, debt_adjustment, coverage_ratio, fig_curve)
        st.download_button("Save PDF", p_bytes, "WACC_Report.pdf")

else:
    st.info("👈 Load data to analyze debt capacity and WACC.")