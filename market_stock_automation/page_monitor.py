import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plyer import notification
import time

fetch_and_analyze = st.session_state["fetch_and_analyze"]
AVAILABLE_TICKERS = st.session_state["AVAILABLE_TICKERS"]

st.title("📈 Élő Grafikon Monitor Dashboard")

# --- OLDALSÁV BEÁLLÍTÁSOK ---
st.sidebar.header("Monitor Beállítások")
live_ticker = st.sidebar.selectbox("Választott Ticker:", options=AVAILABLE_TICKERS, index=0, key="live_t")
live_interval = st.sidebar.selectbox("Felbontás:", options=["1m", "5m", "15m", "1h"], index=2, key="live_i")
live_period = st.sidebar.selectbox("Időtartam:", options=["1d", "5d", "1mo"], index=1, key="live_p")
refresh_rate = st.sidebar.slider("Frissítés (mp):", min_value=10, max_value=300, value=30, key="refresh_rate_slider")

# Adatok letöltése
data = fetch_and_analyze(live_ticker, live_period, live_interval)

if data is not None and not data.empty:
    data_clean = data.dropna(subset=['RSI', 'Close', 'MACD'])
    
    if not data_clean.empty:
        latest_row = data_clean.iloc[-1]
        latest_time = data_clean.index[-1]
        latest_price = float(latest_row['Close'])
        current_signal = latest_row['Signal']
        rsi_val = float(latest_row['RSI'])
        
        # Metrikák elrendezése
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"{live_ticker} Aktuális Ár", f"${latest_price:.2f}")
        m2.metric("RSI (14) Index", f"{rsi_val:.2f}")
        if "BUY" in current_signal: m3.success(f"AI JELZÉS: {current_signal}")
        elif "SELL" in current_signal: m3.error(f"AI JELZÉS: {current_signal}")
        else: m3.info(f"AI JELZÉS: {current_signal}")
        m4.write(f"**Frissítve:** {latest_time.strftime('%H:%M:%S')}")

        # 3 Panels grafikon (Gyertyák + Bollinger, RSI, MACD)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25], vertical_spacing=0.05)
        
        # 1. Panel: Árak + SMA 20 + Bollinger Szalagok
        fig.add_trace(go.Candlestick(x=data_clean.index, open=data_clean['Open'], high=data_clean['High'], low=data_clean['Low'], close=data_clean['Close'], name="Ár"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['SMA_20'], line=dict(color='orange', width=1), name="SMA 20"), row=1, col=1)
        
        # Bollinger vonalak felvétele a grafikonra
        if 'BBU' in data_clean.columns and 'BBL' in data_clean.columns:
            fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['BBU'], line=dict(color='gray', width=1, dash='dash'), name="Bollinger Felső"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['BBL'], line=dict(color='gray', width=1, dash='dash'), name="Bollinger Alsó"), row=1, col=1)

        # 2. Panel: RSI
        fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['RSI'], line=dict(color='purple', width=1.5), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        # 3. Panel: MACD
        fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['MACD'], line=dict(color='blue', width=1.2), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['MACD_Signal'], line=dict(color='red', width=1.2, dash='dot'), name="Signal"), row=3, col=1)
        
        fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# Automatikus frissítés időzítője
time.sleep(refresh_rate)
st.rerun()