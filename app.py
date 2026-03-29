import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. Page Config ---
st.set_page_config(page_title="WACC Optimization Suite", layout="wide")
st.title("🛡️ AI-Based WACC Optimization Dashboard")
st.markdown("---")

# --- 2. Sidebar: Global Controls ---
st.sidebar.header("📡 Data Acquisition")
ticker_input = st.sidebar.text_input("Enter Company Ticker", "AAPL").upper()

# Initialize data in state
if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

if st.sidebar.button("Fetch Live Market Data"):
    with st.spinner('Accessing Financial APIs...'):
        try:
            stock = yf.Ticker(ticker_input)
            info = stock.info
            st.session_state['fin_data'] = {
                'ticker': ticker_input,
                'mkt_cap': info.get('marketCap', 1e9), # Default to 1B if missing
                'total_debt': info.get('totalDebt', 0),
                'beta': info.get('beta', 1.0),
                'name': info.get('longName', ticker_input)
            }
            st.sidebar.success(f"Data Loaded: {ticker_input}")
        except:
            st.sidebar.error("Ticker not found. Try AAPL, TSLA, or MSFT.")

# --- 3. Main Dashboard Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # ROW 1: Key Metrics
    st.subheader(f"Analysis Profile: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Market Cap", f"${d['mkt_cap']:,.0f}")
    m2.metric("Total Debt", f"${d['total_debt']:,.0f}")
    m3.metric("Current Beta", d['beta'])
    current_dr = d['total_debt'] / (d['total_debt'] + d['mkt_cap'])
    m4.metric("Current Debt Ratio", f"{current_dr:.1%}")

    st.markdown("---")

    # ROW 2: Inputs and Visualization
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("🛠️ Simulation Inputs")
        # Manual Overrides
        adj_tax = st.slider("Corporate Tax Rate (%)", 0, 40, 25) / 100
        adj_rf = st.number_input("Risk-Free Rate (Rf)", value=0.043, step=0.001, format="%.3f")
        adj_erp = st.slider("Equity Risk Premium (%)", 3.0, 9.0, 5.5) / 100
        adj_rd = st.slider("Pre-tax Cost of Debt (%)", 2.0, 15.0, 6.0) / 100
        
        st.markdown("---")
        # Download Section
        st.subheader("📥 Export Results")
        data_to_save = pd.DataFrame({
            "Metric": ["Ticker", "Market Cap", "Total Debt", "Beta", "Tax Rate"],
            "Value": [d['ticker'], d['mkt_cap'], d['total_debt'], d['beta'], adj_tax]
        })
        csv = data_to_save.to_csv(index=False).encode('utf-8')
        st.download_button("Download Analysis (CSV)", csv, f"{d['ticker']}_report.csv", "text/csv")

    with right_col:
        st.subheader("📈 WACC Minimization Curve")
        
        # MATH ENGINE
        # Calculate Unlevered Beta (Hamada)
        unlevered_b = d['beta'] / (1 + (1 - adj_tax) * (d['total_debt'] / d['mkt_cap']))
        
        ratios = np.linspace(0.0, 0.9, 50)
        wacc_values = []
        
        for r in ratios:
            # Re-lever Beta for this specific point on the curve
            levered_b = unlevered_b * (1 + (1 - adj_tax) * (r / (1 - r + 0.0001)))
            re = adj_rf + (levered_b * adj_erp)
            wacc = ((1 - r) * re) + (r * adj_rd * (1 - adj_tax))
            wacc_values.append(wacc)
        
        # Find Minimum
        opt_idx = np.argmin(wacc_values)
        opt_ratio = ratios[opt_idx]
        min_wacc = wacc_values[opt_idx]

        # PLOT
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(ratios, wacc_values, color='#0077b6', linewidth=3, label='WACC')
        ax.axvline(opt_ratio, color='#d00000', linestyle='--', alpha=0.7)
        ax.scatter(opt_ratio, min_wacc, color='#d00000', s=100, label=f'Optimal: {opt_ratio:.1%}')
        
        ax.set_facecolor('#f8f9fa')
        ax.set_xlabel("Debt-to-Capital Ratio")
        ax.set_ylabel("WACC (%)")
        ax.legend()
        st.pyplot(fig)
        
        st.info(f"💡 To minimize capital costs, this company should aim for a debt ratio of **{opt_ratio:.1%}**. At this point, the WACC is estimated at **{min_wacc:.2%}**.")

else:
    # Welcome Screen
    st.info("👈 Please enter a stock ticker in the sidebar and click 'Fetch Live Market Data' to generate the dashboard.")
    st.image("https://images.unsplash.com/photo-1611974717482-58a00f63bc0d?auto=format&fit=crop&q=80&w=1000", caption="WACC Minimization Engine")