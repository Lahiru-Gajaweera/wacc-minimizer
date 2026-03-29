import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="AI WACC Minimizer", layout="wide")
st.title("📊 AI-Based WACC Minimizer")

# --- Sidebar for Real Data Loading ---
st.sidebar.header("1. Load Market Data")
ticker_input = st.sidebar.text_input("Enter Ticker (e.g., NVDA, MSFT, TSLA)", "AAPL").upper()

if st.sidebar.button("Fetch Real Data"):
    with st.spinner(f'Loading data for {ticker_input}...'):
        stock = yf.Ticker(ticker_input)
        info = stock.info
        
        # Store data in "Session State" so it stays loaded
        st.session_state['mkt_cap'] = info.get('marketCap')
        st.session_state['total_debt'] = info.get('totalDebt')
        st.session_state['beta'] = info.get('beta', 1.0)
        st.session_state['ticker'] = ticker_input
        st.success(f"Loaded data for {ticker_input}!")

# --- Display Loaded Data ---
if 'mkt_cap' in st.session_state:
    st.subheader(f"Real-Time Metrics for {st.session_state['ticker']}")
    
    # Create a nice table for the user
    data_df = pd.DataFrame({
        "Metric": ["Market Cap", "Total Debt", "Beta (Risk)"],
        "Value": [
            f"${st.session_state['mkt_cap']:,.0f}", 
            f"${st.session_state['total_debt']:,.0f}", 
            st.session_state['beta']
        ]
    })
    st.table(data_df)

    # --- Optimization Section ---
    st.sidebar.header("2. Optimization Settings")
    tax_rate = st.sidebar.slider("Tax Rate", 0.0, 0.4, 0.25)
    
    if st.sidebar.button("Run Minimizer"):
        # Logic for WACC (Same as before but using the loaded data)
        mkt_cap = st.session_state['mkt_cap']
        total_debt = st.session_state['total_debt']
        beta = st.session_state['beta']
        
        # Calculations...
        unlevered_beta = beta / (1 + (1 - tax_rate) * (total_debt / mkt_cap))
        ratios = np.linspace(0, 0.9, 50)
        wacc_list = []
        
        for r in ratios:
            # Hamada Equation
            levered_beta = unlevered_beta * (1 + (1 - tax_rate) * (r / (1 - r + 0.0001)))
            re = 0.04 + (levered_beta * 0.055) # Rf + Beta * ERP
            wacc = ((1 - r) * re) + (r * 0.06 * (1 - tax_rate))
            wacc_list.append(wacc)
            
        # Plotting
        fig, ax = plt.subplots()
        ax.plot(ratios, wacc_list, label="WACC Curve", color='blue')
        st.pyplot(fig)

        # Create a CSV version of the data
csv = data_df.to_csv(index=False).encode('utf-8')

# Check if the data has been loaded before showing the button
if 'mkt_cap' in st.session_state:
    # Re-create the dataframe so the button can "see" it
    data_df = pd.DataFrame({
        "Metric": ["Market Cap", "Total Debt", "Beta (Risk)"],
        "Value": [
            f"${st.session_state['mkt_cap']:,.0f}", 
            f"${st.session_state['total_debt']:,.0f}", 
            st.session_state['beta']
        ]
    })
    
    # 1. Create the CSV
    csv_data = data_df.to_csv(index=False).encode('utf-8')

    # 2. Show the button
    st.download_button(
        label="📥 Download Market Data as CSV",
        data=csv_data,
        file_name=f"{st.session_state['ticker']}_market_data.csv",
        mime="text/csv",
    )