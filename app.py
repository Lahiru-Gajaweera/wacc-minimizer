import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. Web Page Configuration ---
st.set_page_config(page_title="AI WACC Minimizer", layout="wide")
st.title("📊 AI-Based WACC Minimizer")
st.markdown("Optimize capital structure using real-time market data.")

# --- 2. Sidebar: Data Entry ---
st.sidebar.header("1. Load Market Data")
ticker_input = st.sidebar.text_input("Enter Ticker (e.g., AAPL, TSLA, NVDA)", "AAPL").upper()

if st.sidebar.button("Fetch Real Data"):
    with st.spinner(f'Fetching data for {ticker_input}...'):
        try:
            stock = yf.Ticker(ticker_input)
            info = stock.info
            
            # Store data in Session State so it persists during clicks
            st.session_state['mkt_cap'] = info.get('marketCap', 0)
            st.session_state['total_debt'] = info.get('totalDebt', 0)
            st.session_state['beta'] = info.get('beta', 1.0)
            st.session_state['ticker'] = ticker_input
            st.sidebar.success(f"Loaded {ticker_input}!")
        except Exception as e:
            st.sidebar.error(f"Error fetching data: {e}")

# --- 3. Main Display: Data Table & Download ---
if 'mkt_cap' in st.session_state:
    st.subheader(f"Current Metrics for {st.session_state['ticker']}")
    
    # Define the DataFrame inside the check to avoid NameErrors
    data_df = pd.DataFrame({
        "Metric": ["Market Cap", "Total Debt", "Beta (Risk)"],
        "Value": [
            f"${st.session_state['mkt_cap']:,.0f}", 
            f"${st.session_state['total_debt']:,.0f}", 
            st.session_state['beta']
        ]
    })
    
    st.table(data_df)

    # Prepare CSV for download
    csv_data = data_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv_data,
        file_name=f"{st.session_state['ticker']}_data.csv",
        mime="text/csv",
    )

    # --- 4. Optimization Section ---
    st.divider()
    st.subheader("WACC Minimization Analysis")
    
    tax_rate = st.sidebar.slider("Corporate Tax Rate", 0.0, 0.4, 0.25)
    rf_rate = 0.04  # 4% Risk-Free Rate
    erp = 0.055     # 5.5% Equity Risk Premium
    rd_pre_tax = 0.06 # 6% Cost of Debt assumption
    
    if st.button("Run WACC Minimizer"):
        mkt_cap = st.session_state['mkt_cap']
        total_debt = st.session_state['total_debt']
        beta = st.session_state['beta']
        
        # Calculate Unlevered Beta
        unlevered_beta = beta / (1 + (1 - tax_rate) * (total_debt / mkt_cap))
        
        # Simulate different Debt-to-Capital ratios
        ratios = np.linspace(0.01, 0.9, 50)
        wacc_list = []
        
        for r in ratios:
            # Re-lever Beta using Hamada Equation
            levered_beta = unlevered_beta * (1 + (1 - tax_rate) * (r / (1 - r)))
            re = rf_rate + (levered_beta * erp)
            # WACC Formula
            wacc = ((1 - r) * re) + (r * rd_pre_tax * (1 - tax_rate))
            wacc_list.append(wacc)
            
        # Results calculation
        min_wacc = min(wacc_list)
        optimal_debt_ratio = ratios[wacc_list.index(min_wacc)]
        
        col1, col2 = st.columns(2)
        col1.metric("Optimal Debt Ratio", f"{optimal_debt_ratio:.1%}")
        col2.metric("Minimum WACC", f"{min_wacc:.2%}")
        
        # Plotting the Curve
        fig, ax = plt.subplots()
        ax.plot(ratios, wacc_list, label="WACC Curve", color='#1f77b4', linewidth=2)
        ax.axvline(optimal_debt_ratio, color='red', linestyle='--', label=f'Optimal ({optimal_debt_ratio:.1%})')
        ax.set_xlabel("Debt-to-Capital Ratio")
        ax.set_ylabel("WACC (%)")
        ax.set_title(f"Optimization Curve for {st.session_state['ticker']}")
        ax.legend()
        st.pyplot(fig)
else:
    st.info("Please enter a ticker in the sidebar and click 'Fetch Real Data' to begin.")