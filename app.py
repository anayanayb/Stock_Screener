import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import io
import time
from streamlit_autorefresh import st_autorefresh

# Configure the Streamlit page
st.set_page_config(page_title="Market Screener", layout="wide", initial_sidebar_state="expanded")

# Inject Custom CSS for Inter font and Jony Ive inspired aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    .stApp {
        background-color: #000000;
        color: #f5f5f7;
    }

    h1, h2, h3 {
        font-weight: 300 !important;
        letter-spacing: -0.02em !important;
        color: #f5f5f7;
    }
    
    h1 {
        padding-bottom: 20px;
        background: -webkit-linear-gradient(45deg, #f5f5f7, #a1a1a6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .metric-container {
        background: rgba(255, 255, 255, 0.04);
        border-radius: 20px;
        padding: 30px;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
        margin-bottom: 24px;
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    .metric-container:hover {
        background: rgba(255, 255, 255, 0.06);
        transform: translateY(-4px) scale(1.01);
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
    }

    /* DataFrame styling */
    [data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 16px;
        padding: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Buttons */
    .stButton>button {
        border-radius: 24px !important;
        font-weight: 500 !important;
        background-color: #1d1d1f !important;
        color: #f5f5f7 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        padding: 8px 24px !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        background-color: #2c2c2e !important;
        border-color: rgba(255,255,255,0.3) !important;
        transform: scale(1.02);
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: rgba(20, 20, 22, 0.8) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_us_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_html(io.StringIO(response.text))[0]
        # Clean symbol: BRK.B -> BRK-B (yfinance format)
        tickers = df['Symbol'].str.replace('.', '-').tolist()
        return tickers
    except Exception as e:
        st.sidebar.error(f"Failed to fetch S&P 500: {e}")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]

@st.cache_data(ttl=3600)
def get_in_tickers():
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = requests.get(url, headers=headers, timeout=10)
        if req.status_code == 200:
            df = pd.read_csv(io.StringIO(req.text))
            return [f"{t}.NS" for t in df['Symbol'].tolist()]
    except Exception:
        pass
        
    try:
        url = "https://en.wikipedia.org/wiki/NIFTY_50"
        df = pd.read_html(url)[1]
        return [f"{t}.NS" for t in df['Symbol'].tolist()]
    except Exception as e:
        st.sidebar.error(f"Failed to fetch Nifty tickers: {e}")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]

def get_pe_ratio(ticker):
    """Fetch trailing P/E. Returns inf if unavailable to filter it out."""
    try:
        info = yf.Ticker(ticker).info
        pe = info.get('trailingPE')
        if pe is None:
            pe = info.get('forwardPE')
        return pe if pe is not None else float('inf')
    except:
        return float('inf')

@st.cache_data(ttl=60) # Cache for 1 min to allow manual refresh within a minute block
def screen_stocks(tickers, max_pe=20, min_vol_ratio=2.0, min_rsi=50):
    if not tickers: return pd.DataFrame()
    
    # yf.download is heavily optimized for bulk fetching. 
    # Period 3mo provides enough history for 20d MA and 14d RSI.
    data = yf.download(tickers, period="3mo", group_by="ticker", threads=True, progress=False)
    
    passed_technical = []
    
    for t in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                try:
                    df = data[t].copy()
                except KeyError:
                    continue
            else:
                df = data.copy()
                
            df.dropna(inplace=True)
            if len(df) < 20: continue
            
            # Calculate 20d moving average of volume
            df['Vol_MA_20'] = df['Volume'].rolling(window=20).mean()
            
            # Calculate RSI (14)
            df.ta.rsi(length=14, append=True)
            rsi_cols = [c for c in df.columns if 'RSI' in c]
            if not rsi_cols: continue
            rsi_col = rsi_cols[0]
            
            # Get latest values
            latest = df.iloc[-1]
            current_price = latest['Close']
            current_vol = latest['Volume']
            vol_ma = latest['Vol_MA_20']
            rsi = latest[rsi_col]
            
            vol_ratio = current_vol / vol_ma if vol_ma > 0 else 0
            
            # First pass: Filter strictly on technicals (Volume & RSI)
            if vol_ratio > min_vol_ratio and rsi > min_rsi:
                # Cast the price to float safely. Sometimes yfinance returns Series.
                price_val = float(current_price.iloc[0]) if isinstance(current_price, pd.Series) else float(current_price)
                vol_ratio_val = float(vol_ratio.iloc[0]) if isinstance(vol_ratio, pd.Series) else float(vol_ratio)
                rsi_val = float(rsi.iloc[0]) if isinstance(rsi, pd.Series) else float(rsi)

                passed_technical.append({
                    'Ticker': t,
                    'Price': round(price_val, 2),
                    'Volume Ratio': round(vol_ratio_val, 2),
                    'RSI': round(rsi_val, 2)
                })
        except Exception as e:
            continue
            
    # Second pass: Fetch P/E ONLY for the few stocks that passed technicals.
    # This prevents getting IP banned by Yahoo Finance.
    final_results = []
    for item in passed_technical:
        pe = get_pe_ratio(item['Ticker'])
        if pe < max_pe:
            item['P/E Ratio'] = round(pe, 2)
            final_results.append(item)
            
    return pd.DataFrame(final_results)

def main():
    st.title("Market Screener")
    st.markdown("<p style='color: #86868b; font-size: 1.1rem; margin-top: -10px; margin-bottom: 30px;'>Discover momentum in beautiful clarity.</p>", unsafe_allow_html=True)
    
    # --- Sidebar ---
    st.sidebar.header("Configuration")
    market = st.sidebar.radio("Market", ["US (S&P 500)", "India (Nifty 500)"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Auto-Refresh Settings")
    
    # Adjustable auto-refresh
    refresh_options = {
        "Off": 0,
        "1 Minute": 60 * 1000,
        "5 Minutes": 5 * 60 * 1000,
        "15 Minutes": 15 * 60 * 1000
    }
    refresh_rate = st.sidebar.selectbox("Refresh Interval", list(refresh_options.keys()), index=2)
    
    if refresh_options[refresh_rate] > 0:
        st_autorefresh(interval=refresh_options[refresh_rate], key="datarefresh")
        st.sidebar.caption(f"App will refresh every {refresh_rate.lower()}.")
    else:
        st.sidebar.caption("Auto-refresh is disabled.")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")
    max_pe = st.sidebar.slider("Max P/E Ratio", 5.0, 50.0, 20.0, 0.5)
    min_vol = st.sidebar.slider("Min Volume Ratio (x 20d MA)", 1.0, 5.0, 2.0, 0.1)
    min_rsi = st.sidebar.slider("Min RSI", 20, 80, 50)
    
    # Manual refresh button clears the streamit cache
    if st.sidebar.button("Manual Refresh", use_container_width=True):
        st.cache_data.clear()
        
    # --- Main Content ---
    with st.spinner("Fetching market data..."):
        if "US" in market:
            tickers = get_us_tickers()
        else:
            tickers = get_in_tickers()
            
        results_df = screen_stocks(tickers, max_pe, min_vol, min_rsi)
        
    if results_df.empty:
        st.markdown("""
        <div class="metric-container" style="text-align: center;">
            <h3 style="color: #86868b;">No stocks match your strict criteria today.</h3>
            <p>Try adjusting your filters in the sidebar.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Sort by Volume Ratio descending as default momentum indicator
        results_df = results_df.sort_values(by="Volume Ratio", ascending=False).reset_index(drop=True)
        results_df.index += 1 # 1-indexed for display
        
        # Reorder columns for better UX
        cols = ['Ticker', 'Price', 'P/E Ratio', 'Volume Ratio', 'RSI']
        results_df = results_df[cols]
        
        st.markdown(f"<div class='metric-container'><h3>{len(results_df)} Opportunities Found</h3></div>", unsafe_allow_html=True)
        
        # Display as a dataframe with built-in sorting and nice styling
        st.dataframe(
            results_df, 
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", help="Stock Symbol"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f" if "US" in market else "₹%.2f"),
                "P/E Ratio": st.column_config.NumberColumn("P/E Ratio", format="%.2f", help="Trailing P/E < 20"),
                "Volume Ratio": st.column_config.NumberColumn("Volume Ratio", format="%.2fx", help="Volume vs 20d MA"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.2f", help="Relative Strength Index > 50"),
            }
        )

if __name__ == "__main__":
    main()
