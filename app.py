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
source_option = st.sidebar.radio("Select Source", ["Live API (Yahoo Finance)", "Manual File Upload (.csv)"])

# Initialize session state for data storage
if 'fin_data' not in st.session_state:
    st.session_state['fin_data'] = None

# --- SOURCE A: LIVE API ---
if source_option == "Live API (Yahoo Finance)":
    ticker_input = st.sidebar.text_input("Enter Company Ticker", "AAPL").upper()
    if st.sidebar.button("🔍 Fetch Live Data"):
        with st.spinner('Accessing Market Data...'):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                # Check if we got valid data
                if 'marketCap' in info:
                    st.session_state['fin_data'] = {
                        'ticker': ticker_input,
                        'mkt_cap': info.get('marketCap', 0),
                        'total_debt': info.get('totalDebt', 0),
                        'beta': info.get('beta', 1.0),
                        'name': info.get('longName', ticker_input)
                    }
                    st.sidebar.success(f"Loaded: {ticker_input}")
                else:
                    st.sidebar.error("Ticker found, but market data is incomplete.")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

# --- SOURCE B: MANUAL FILE UPLOAD ---
else:
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"])
    if uploaded_file is not None:
        df_upload = pd.read_csv(uploaded_file)
        st.sidebar.info("Previewing first row of data...")
        
        # Mapping helpers
        col_mkt = st.sidebar.selectbox("Select Market Cap / Equity Column", df_upload.columns)
        col_debt = st.sidebar.selectbox("Select Total Debt / Liabilities Column", df_upload.columns)
        
        # Beta Handling (Files like yours often miss Beta)
        has_beta = st.sidebar.checkbox("My file has a Beta column", value=False)
        if has_beta:
            col_beta = st.sidebar.selectbox("Select Beta Column", df_upload.columns)
        else:
            manual_beta = st.sidebar.number_input("Enter Beta manually", value=1.1, step=0.1)
        
        if st.sidebar.button("🚀 Analyze Uploaded File"):
            try:
                # Get values from the first row of the CSV
                mkt_val = float(df_upload[col_mkt].iloc[0])
                debt_val = float(df_upload[col_debt].iloc[0])
                beta_val = float(df_upload[col_beta].iloc[0]) if has_beta else manual_beta

                st.session_state['fin_data'] = {
                    'ticker': "Custom Upload",
                    'mkt_cap': mkt_val,
                    'total_debt': debt_val,
                    'beta': beta_val,
                    'name': "Uploaded Dataset Analysis"
                }
                st.sidebar.success("File processed successfully!")
            except ValueError:
                st.sidebar.error("❌ Logic Error: You picked a column with text/dates. Please pick a column with numbers.")
            except Exception as e:
                st.sidebar.error(f"❌ Error: {e}")

# --- 3. Main Dashboard Display ---
if st.session_state['fin_data']:
    d = st.session_state['fin_data']
    
    # ROW 1: Key Metrics Summary
    st.subheader(f"Project Profile: {d['name']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Market Cap (E)", f"${d['mkt_cap']:,.0f}")
    m2.metric("Total Debt (D)", f"${d['total_debt']:,.0f}")
    m3.metric("Beta (Risk)", f"{d['beta']:.2f}")
    
    total_val = d['mkt_cap'] + d['total_debt']
    curr_ratio = d['total_debt'] / total_val if total_val > 0 else 0
    m4.metric("Current Debt Ratio", f"{curr_ratio:.1%}")

    st.markdown("---")

    # ROW 2: Inputs & Analysis
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("🛠️ Simulation Assumptions")
        tax_rate = st.slider("Tax Rate (%)", 0, 40, 25) / 100
        rf_rate = st.number_input("Risk-Free Rate (Rf)", value=0.043, step=0.001, format="%.3f")
        erp = st.slider("Equity Risk Premium (%)", 3.0, 9.0, 5.5) / 100
        rd_pre_tax = st.slider("Cost of Debt (%)", 2.0, 15.0, 6.5) / 100
        
        # CSV Export Tool
        st.markdown("---")
        results_df = pd.DataFrame([d])
        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Analysis as CSV", csv, f"WACC_{d['ticker']}.csv", "text/csv")

    with right_col:
        st.subheader("📈 Capital Structure Optimization")
        
        # MATH ENGINE: Hamada Formula & WACC
        # Calculate Unlevered Beta
        de_ratio = d['total_debt'] / d['mkt_cap'] if d['mkt_cap'] > 0 else 0
        unlevered_b = d['beta'] / (1 + (1 - tax_rate) * de_ratio)
        
        ratios = np.linspace(0.01, 0.95, 100)
        wacc_values = []
        
        for r in ratios:
            # Levered Beta for specific D/V ratio
            levered_b = unlevered_b * (1 + (1 - tax_rate) * (r / (1 - r)))
            re = rf_rate + (levered_b * erp)
            wacc = ((1 - r) * re) + (r * rd_pre_tax * (1 - tax_rate))
            wacc_values.append(wacc)
        
        # Optimization Results
        min_wacc = min(wacc_values)
        opt_ratio = ratios[np.argmin(wacc_values)]

        # Plotting the Curve
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(ratios, wacc_values, color='#0077b6', linewidth=3, label="WACC Curve")
        ax.scatter(opt_ratio, min_wacc, color='red', s=100, label=f'Optimal Debt: {opt_ratio:.1%}')
        ax.set_xlabel("Debt-to-Capital Ratio")
        ax.set_ylabel("WACC (%)")
        ax.legend()
        st.pyplot(fig)
        
        st.success(f"Minimum WACC: **{min_wacc:.2%}** at **{opt_ratio:.1%}** Debt Ratio.")
        st.info("The red dot represents the 'sweet spot' where the company's value is maximized by minimizing costs.")

else:
    st.info("👈 Use the sidebar to load data via Ticker or CSV file.")
    st.image("https://images.unsplash.com/photo-1591696208202-735c7a44e711?q=80&w=1000&auto=format&fit=crop", caption="Ready for Financial Modeling")