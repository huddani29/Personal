import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

st.title("📈 Élő Grafikon Monitor Dashboard")

# Közös kosár beolvasása a főprogramból biztonságosan
AVAILABLE_TICKERS = st.session_state.get("AVAILABLE_TICKERS", ["TSLA", "NVDA", "AAPL", "MSFT", "PLTR"])

# --- OLDALSÁV BEÁLLÍTÁSOK ---
st.sidebar.header("Monitor Beállítások")
live_ticker = st.sidebar.selectbox("Választott Ticker:", options=AVAILABLE_TICKERS, index=0, key="live_t")
live_interval = st.sidebar.selectbox("Felbontás:", options=["1m", "5m", "15m", "1h"], index=2, key="live_i")
live_period = st.sidebar.selectbox("Időtartam:", options=["1d", "5d", "1mo"], index=1, key="live_p")
refresh_rate = st.sidebar.slider("Frissítés (mp):", min_value=10, max_value=300, value=30, key="refresh_rate_slider")

# LOCAL HÍRELEMZŐ FUNKCIÓ A SECCURE FUTÁSHOZ
def local_sentiment(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        news = ticker_obj.news
        if not news: return "Semleges 😐"
        pos, neg = 0, 0
        p_words = ["buy", "bullish", "upgrade", "growth", "profit", "beat", "surge", "higher", "success"]
        n_words = ["sell", "bearish", "downgrade", "loss", "drop", "fall", "crash", "risk", "miss", "fail"]
        for item in news[:5]:
            title = item.get("title", "").lower()
            for w in p_words: 
                if w in title: pos += 1
            for w in n_words: 
                if w in title: neg += 1
        if pos > neg: return "POZITÍV 📈"
        elif neg > pos: return "NEGATÍV 📉"
        return "Semleges 😐"
    except: return "Semleges 😐"

# ADATLEKÉRÉS ÉS INDIKÁTOROK HELYI KISZÁMÍTÁSA (Nincs aszinkron elcsúszás)
data = yf.download(tickers=live_ticker, period=live_period, interval=live_interval, progress=False, multi_level_index=False)

if data is not None and not data.empty:
    data.columns = [str(col) for col in data.columns]
    data['RSI'] = ta.rsi(close=data['Close'], length=14)
    data['SMA_20'] = ta.sma(close=data['Close'], length=20)
    
    bbands = ta.bbands(close=data['Close'], length=20, std=2)
    if bbands is not None:
        data['BBL'], data['BBU'] = bbands.iloc[:, 0], bbands.iloc[:, 2]
    
    macd_df = ta.macd(close=data['Close'], fast=12, slow=26, signal=9)
    if macd_df is not None:
        data['MACD'], data['MACD_Signal'] = macd_df.iloc[:, 0], macd_df.iloc[:, 2]

    data_clean = data.dropna(subset=['RSI', 'Close'])
    
    if not data_clean.empty:
        latest_row = data_clean.iloc[-1]
        latest_price = float(latest_row['Close'])
        rsi_val = float(latest_row['RSI'])
        sentiment_label = local_sentiment(live_ticker)
        
        # Szignál helyi ellenőrzése
        current_signal = "HOLD"
        if rsi_val < 40 and 'MACD' in data_clean.columns and float(latest_row['MACD']) > float(latest_row['MACD_Signal']):
            current_signal = "BUY (VÉTEL)"
        elif rsi_val > 60 or ('BBU' in data_clean.columns and latest_price >= float(latest_row['BBU'])):
            current_signal = "SELL (ELADÁS)"

        # Metrikák elrendezése
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"{live_ticker} Ár", f"${latest_price:.2f}")
        m2.metric("RSI (14) Index", f"{rsi_val:.2f}")
        m3.metric("AI Piaci Hangulat", sentiment_label)
        
        if "BUY" in current_signal: m4.success(f"AI: {current_signal}")
        elif "SELL" in current_signal: m4.error(f"AI: {current_signal}")
        else: m4.info(f"AI: {current_signal}")

        # 3 Panels grafikon
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=data_clean.index, open=data_clean['Open'], high=data_clean['High'], low=data_clean['Low'], close=data_clean['Close'], name="Ár"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['SMA_20'], line=dict(color='orange', width=1), name="SMA 20"), row=1, col=1)
        
        if 'BBU' in data_clean.columns:
            fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['BBU'], line=dict(color='gray', width=1, dash='dash'), name="Bollinger Felső"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['BBL'], line=dict(color='gray', width=1, dash='dash'), name="Bollinger Alsó"), row=1, col=1)

        fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['RSI'], line=dict(color='purple', width=1.5), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        if 'MACD' in data_clean.columns:
            fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['MACD'], line=dict(color='blue', width=1.2), name="MACD"), row=3, col=1)
            fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['MACD_Signal'], line=dict(color='red', width=1.2, dash='dot'), name="Signal"), row=3, col=1)
        
        fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# Automatikus frissítés
time.sleep(refresh_rate)
st.rerun()
