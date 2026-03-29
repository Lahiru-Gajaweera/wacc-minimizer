import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. UI Setup ---
st.set_page_config(page_title="Pro WACC Optimizer", layout="wide", initial_sidebar_state="expanded")
st.title("⚖️ Professional WACC Optimization Suite")
st.markdown("---")

# --- 2. Sidebar Controls ---
st.sidebar.header("🛠️ Data Controls")
ticker_input = st.sidebar.text_input("Stock Ticker", "AAPL").upper()

# --- 3. Persistent Data Storage ---
if 'data' not in st.session_state:
    st.session_state['data'] = None

if st.sidebar.button("🔍 Load Market Data"):
    with st.spinner('Accessing Bloomberg/Yahoo APIs...'):
        try:
            stock = yf.Ticker(ticker_input)
            info = stock.info
            st.session_state['data'] = {
                'ticker': ticker_input,
                'mkt_cap': info.get('marketCap', 0),
                'total_debt': info.get('totalDebt', 0),
                'beta': info.get('beta', 1.0),
                'name': info.get('longName', ticker_input)
            }
            st.sidebar.success(f"Successfully loaded {ticker_input}")
        except:
            st.sidebar.error("Could not find ticker. Please check the symbol.")

# --- 4. Main App Logic ---
if st.session_state['data']:
    d = st.session_state['data']
    
    # Create Layout Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Market Overview", "📈 WACC Optimization", "📑 Documentation"])

    with tab1:
        st.subheader(f"Financial Profile: {d['name']}")
        
        # Metric Cards for better UI
        col1, col2, col3 = st.columns(3)
        col1.metric("Market Cap", f"${d['mkt_cap']:,.0f}")
        col2.metric("Total Debt", f"${d['total_debt']:,.0f}")
        col3.metric("Beta (Risk)", d['beta'])
        
        st.markdown("---")
        st.write("### Adjust Inputs for Simulation")
        st.info("You can override the market data below to test different scenarios.")
        
        # User Friendly Input Grid
        c1, c2 = st.columns(2)
        sim_beta = c1.number_input("Target Beta", value=float(d['beta']), step=0.1)
        sim_debt = c2.number_input("Manual Debt Override ($)", value=float(d['total_debt']), step=1000000.0)

    with tab2:
        st.subheader("Optimization Engine")
        
        # Sidebar-based assumptions
        st.sidebar.markdown("---")
        st.sidebar.header("📝 Assumptions")
        tax_rate = st.sidebar.slider("Tax Rate (%)", 0, 40, 25) / 100
        rf_rate = st.sidebar.number_input("Risk-Free Rate (e.g. 0.04)", value=0.043, format="%.3f")
        erp = st.sidebar.slider("Equity Risk Premium (%)", 3.0, 8.0, 5.5) / 100
        cost_of_debt = st.sidebar.slider("Pre-tax Cost of Debt (%)", 2.0, 15.0, 6.0) / 100

        # Run Analysis
        if st.button("🚀 Run WACC Minimization Search"):
            mkt_val = d['mkt_cap'] + sim_debt
            unlevered_beta = sim_beta / (1 + (1 - tax_rate) * (sim_debt / d['mkt_cap']))
            
            ratios = np.linspace(0.0, 0.95, 100)
            wacc_curve = []
            
            for r in ratios:
                # Hamada Equation
                l_beta = unlevered_beta * (1 + (1 - tax_rate) * (r / (1 - r + 0.00001)))
                re = rf_rate + (l_beta * erp)
                wacc = ((1 - r) * re) + (r * cost_of_debt * (1 - tax_rate))
                wacc_curve.append(wacc)
            
            # Findings
            opt_idx = np.argmin(wacc_curve)
            opt_ratio = ratios[opt_idx]
            min_wacc = wacc_curve[opt_idx]
            
            st.success(f"Optimal Capital Structure Found at **{opt_ratio:.1%} Debt**")
            
            # Plotting
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(ratios, wacc_curve, color='#2ecc71', linewidth=3, label='WACC')
            ax.scatter(opt_ratio, min_wacc, color='red', s=100, zorder=5, label='Optimal Point')
            ax.set_title(f"Cost of Capital Minimization: {d['ticker']}", fontsize=14)
            ax.set_xlabel("Debt-to-Capital Ratio", fontsize=12)
            ax.set_ylabel("WACC (%)", fontsize=12)
            ax.grid(alpha=0.3)
            ax.legend()
            st.pyplot(fig)
            
            # Summary Table
            res_df = pd.DataFrame({
                "Scenario": ["Current Structure", "Optimal Structure"],
                "Debt Ratio": [f"{(sim_debt / mkt_val):.1%}", f"{opt_ratio:.1%}"],
                "WACC Estimate": ["---", f"{min_wacc:.2%}"]
            })
            st.table(res_df)

    with tab3:
        st.markdown("""
        ### How it Works
        1. **CAPM:** We calculate the Cost of Equity ($Re$) using the Capital Asset Pricing Model.
        2. **Hamada Equation:** As you add debt, financial risk increases. We adjust the Beta to reflect this.
        3. **WACC:** We find the weighted average of Equity and Debt costs, adjusted for the **Tax Shield**.
        """)

else:
    st.warning("👈 Please enter a ticker and click 'Load Market Data' to begin.")