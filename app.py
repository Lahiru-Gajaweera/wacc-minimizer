import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

# --- Web Page Config ---
st.set_page_config(page_title="AI WACC Minimizer", layout="wide")
st.title("📊 AI-Based WACC Minimizer")
st.markdown("Optimize capital structure using real-time market data.")

# --- Sidebar Inputs ---
ticker = st.sidebar.text_input("Enter Stock Ticker (e.g., TSLA, AAPL, GOOGL)", "AAPL")
tax_rate = st.sidebar.slider("Corporate Tax Rate", 0.0, 0.4, 0.25)
rf_rate = st.sidebar.number_input("Risk-Free Rate (e.g., 0.04 for 4%)", value=0.04)

if st.sidebar.button("Run Optimization"):
    with st.spinner('Fetching real-time data...'):
        # 1. Fetch Data
        stock = yf.Ticker(ticker)
        info = stock.info
        
        mkt_cap = info.get('marketCap', 1)
        total_debt = info.get('totalDebt', 1)
        beta = info.get('beta', 1.0)
        
        # 2. Logic: Hamada & WACC
        unlevered_beta = beta / (1 + (1 - tax_rate) * (total_debt / mkt_cap))
        ratios = np.linspace(0, 0.9, 50)
        wacc_list = []
        
        erp = 0.055 # Equity Risk Premium
        rd = 0.06   # Assumed cost of debt
        
        for r in ratios:
            levered_beta = unlevered_beta * (1 + (1 - tax_rate) * (r / (1 - r + 0.0001)))
            re = rf_rate + (levered_beta * erp)
            wacc = ((1 - r) * re) + (r * rd * (1 - tax_rate))
            wacc_list.append(wacc)
            
        # 3. Display Results
        min_wacc = min(wacc_list)
        opt_debt = ratios[wacc_list.index(min_wacc)]
        
        col1, col2 = st.columns(2)
        col1.metric("Optimal Debt Ratio", f"{opt_debt:.1%}")
        col2.metric("Minimum WACC", f"{min_wacc:.2%}")
        
        # 4. Plotting
        fig, ax = plt.subplots()
        ax.plot(ratios, wacc_list, color='#1f77b4', linewidth=2)
        ax.axvline(opt_debt, color='red', linestyle='--', label='Optimal')
        ax.set_xlabel("Debt-to-Capital Ratio")
        ax.set_ylabel("WACC")
        ax.set_title(f"Optimization Curve for {ticker}")
        st.pyplot(fig)
        