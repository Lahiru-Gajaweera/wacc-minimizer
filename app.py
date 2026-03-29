import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. Page Config ---
st.set_page_config(page_title="WACC Optimization Suite", layout="wide")
st.title("🛡️ AI-Based WACC Optimization Dashboard")
st.markdown("---")

# --- 2. Sidebar: Data Source Selection ---
st.sidebar.header("📂 Data Source")
source_option = st.sidebar.radio("Select Source", ["Live API", "Manual File Upload"])

# Initialize session state for data
if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# --- SOURCE A: LIVE API ---
if source_option == "Live API":
    ticker_input = st.sidebar.text_input("Enter Company Ticker", "AAPL").upper()
    if st.sidebar.button("Fetch Live Data"):
        try:
            stock = yf.Ticker(ticker_input)
            info = stock.info
            st.session_state['fin_data'] = {
                'ticker': ticker_input,
                'mkt_cap': info.get('marketCap', 1e9),
                'total_debt': info.get('totalDebt', 0),
                'beta': info.get('beta', 1.0),
                'name': info.get('longName', ticker_input)
            }
            st.sidebar.success(f"Loaded: {ticker_input}")
        except:
            st.sidebar.error("Ticker not found.")

# --- SOURCE B: MANUAL FILE UPLOAD ---
else:
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])
    if uploaded_file is not None:
        df_upload = pd.read_csv(uploaded_file)
        st.sidebar.write("Preview of Uploaded Data:")
        st.sidebar.dataframe(df_upload.head(3))
        
        # User maps columns to variables
        st.sidebar.markdown("---")
        st.sidebar.write("Map your columns:")
        col_mkt = st.sidebar.selectbox("Market Cap Column", df_upload.columns)
        col_debt = st.sidebar.selectbox("Total Debt Column", df_upload.columns)
        col_beta = st.sidebar.selectbox("Beta Column", df_upload.columns)
        
        if st.sidebar.button("Analyze Uploaded File"):
            # We take the first row of the uploaded file for analysis
            st.session_state['fin_data'] = {
                'ticker': "Uploaded Data",
                'mkt_cap': float(df_upload[col_mkt].iloc[0]),
                'total_debt': float(df_upload[col_debt].iloc[0]),
                'beta': float(df_upload[col_beta].iloc[0]),
                'name': "Custom Dataset"
            }
            st.sidebar.success("File Processed!")

# --- 3. Main Dashboard Logic ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # ROW 1: Key Metrics
    st.subheader(f"Analysis Profile: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Market Cap", f"${d['mkt_cap']:,.0f}")
    m2.metric("Total Debt", f"${d['total_debt']:,.0f}")
    m3.metric("Beta", d['beta'])
    
    # Calculate current ratio safely
    total_val = (d['total_debt'] + d['mkt_cap'])
    current_dr = d['total_debt'] / total_val if total_val > 0 else 0
    m4.metric("Current Debt Ratio", f"{current_dr:.1%}")

    st.markdown("---")

    # ROW 2: Inputs and Visualization
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("🛠️ Simulation Inputs")
        adj_tax = st.slider("Tax Rate (%)", 0, 40, 25) / 100
        adj_rf = st.number_input("Risk-Free Rate (Rf)", value=0.043, step=0.001, format="%.3f")
        adj_erp = st.slider("Equity Risk Premium (%)", 3.0, 9.0, 5.5) / 100
        adj_rd = st.slider("Pre-tax Cost of Debt (%)", 2.0, 15.0, 6.0) / 100

    with right_col:
        st.subheader("📈 WACC Minimization Curve")
        
        # MATH ENGINE (Hamada)
        debt_equity_ratio = d['total_debt'] / d['mkt_cap'] if d['mkt_cap'] > 0 else 0
        unlevered_b = d['beta'] / (1 + (1 - adj_tax) * debt_equity_ratio)
        
        ratios = np.linspace(0.01, 0.95, 50)
        wacc_values = []
        
        for r in ratios:
            levered_b = unlevered_b * (1 + (1 - adj_tax) * (r / (1 - r)))
            re = adj_rf + (levered_b * adj_erp)
            wacc = ((1 - r) * re) + (r * adj_rd * (1 - adj_tax))
            wacc_values.append(wacc)
        
        opt_idx = np.argmin(wacc_values)
        opt_ratio = ratios[opt_idx]
        min_wacc = wacc_values[opt_idx]

        # PLOT
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(ratios, wacc_values, color='#0077b6', linewidth=3)
        ax.scatter(opt_ratio, min_wacc, color='red', s=100, label=f'Optimal: {opt_ratio:.1%}')
        ax.set_xlabel("Debt-to-Capital Ratio")
        ax.set_ylabel("WACC (%)")
        ax.legend()
        st.pyplot(fig)
        
        st.success(f"Minimum WACC of **{min_wacc:.2%}** achieved at **{opt_ratio:.1%}** debt.")
else:
    st.info("👈 Select a source and load data to begin.")