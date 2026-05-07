#  Market Momentum Screener

A premium, high-performance stock screening application designed with a minimalist "Jony Ive" inspired aesthetic. This tool identifies high-momentum opportunities in both the **US (S&P 500)** and **Indian (Nifty 500)** markets using real-time data.

##  Key Features

- **Dual-Market Intelligence:** Toggle between S&P 500 and Nifty 500 instantly.
- **Smart Momentum Filtering:** Identifies stocks with:
  - **P/E Ratio < 20:** Focus on value-backed growth.
  - **Volume Ratio > 2x:** Spot unusual institutional activity (20-day MA).
  - **RSI > 50:** Confirm bullish strength.
- **Real-Time Responsiveness:** Adjustable auto-refresh intervals and manual refresh capabilities.
- **Premium UI:** Designed with the Inter font family, glassmorphic containers, and a sleek dark-mode interface.

##  Deployment

This app is optimized for **Streamlit Community Cloud**.

1. **Fork/Clone** this repository.
2. Connect your GitHub to [Streamlit Share](https://share.streamlit.io).
3. Deploy using `app.py` as the entry point.

##  Tech Stack

- **Python 3.x**
- **Streamlit:** UI Framework
- **yfinance:** Financial Data API
- **Pandas TA:** Technical Analysis Library
---
