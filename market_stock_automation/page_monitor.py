import streamlit as st
import plotly.graph_objects as go
from zoneinfo import ZoneInfo
from datetime import datetime
from plotly.subplots import make_subplots
import time

fetch_and_analyze = st.session_state["fetch_and_analyze"]
AVAILABLE_TICKERS = st.session_state["AVAILABLE_TICKERS"]

def get_market_phases_local():
    now_b = datetime.now(ZoneInfo("Europe/Budapest"))
    c_time = now_b.strftime("%H:%M")
    is_w = now_b.weekday() < 5
    eu, usa = "ZÁRVA 🔴", "ZÁRVA 🔴"
    if is_w:
        if "09:00" <= c_time < "17:30": eu = "NYITVA 🟢"
        if "15:30" <= c_time < "16:30": usa = "NYITÓ ŐRÜLET 🚀"
        elif "16:30" <= c_time < "19:30": usa = "EBÉDSZÜNET ☕"
        elif "19:30" <= c_time < "22:00": usa = "ZÁRÓ HAJRÁ 🏁"
    return eu, usa

eu_status, usa_status = get_market_phases_local()

c_eu, c_usa = st.columns(2)
c_eu.info(f"🇪🇺 **Európai Piac:** {eu_status}")
c_usa.warning(f"🇺🇸 **Amerikai Piac:** {usa_status}")

st.title("📈 Élő Grafikon Monitor Dashboard")

st.sidebar.header("Monitor Beállítások")
live_ticker = st.sidebar.selectbox("Választott Ticker:", options=AVAILABLE_TICKERS, index=0, key="live_t")
live_interval = st.sidebar.selectbox("Felbontás:", options=["1m", "5m", "15m", "1h"], index=2, key="live_i")
refresh_rate = st.sidebar.slider("Frissítés (mp):", min_value=10, max_value=300, value=30, key="refresh_rate_slider")

data = fetch_and_analyze(live_ticker, "1mo", live_interval)

if data is not None and not data.empty:
    data_clean = data.dropna(subset=['RSI', 'Close'])
    if not data_clean.empty:
        data_clean.index = data_clean.index.tz_localize('UTC').tz_convert('Europe/Budapest') if data_clean.index.tz is None else data_clean.index.tz_convert('Europe/Budapest')
        
        latest_row = data_clean.iloc[-1]
        latest_price = float(latest_row['Close'])
        rsi_val = float(latest_row['RSI'])
        current_signal = latest_row['Signal']

        if ".BD" in live_ticker: price_formatted = f"{latest_price:,.0f} Ft"
        elif live_ticker in ["ASML", "SAP", "BMW", "DBK", "VOW3", "LVMH"]: price_formatted = f"€{latest_price:.2f}"
        else: price_formatted = f"${latest_price:.2f}"

        m1, m2, m3 = st.columns(3)
        m1.metric(f"{live_ticker} Aktuális Ár", price_formatted)
        m2.metric("RSI (14) Index", f"{rsi_val:.2f}")
        
        # Prediktív státusz kijelzése szövegesen is
        status_text = current_signal
        if bool(latest_row['Squeeze']): status_text += " | ⚡ ROOBANÁS ELŐTTI SQUEEZE"
        if bool(latest_row['Divergence']): status_text += " | 🔮 BIKA DIVERGENCIA"
        
        if "BUY" in current_signal: m3.success(f"AI STATE: {status_text}")
        elif "SELL" in current_signal: m3.error(f"AI STATE: {status_text}")
        else: m3.info(f"AI STATE: {status_text}")

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=data_clean.index, open=data_clean['Open'], high=data_clean['High'], low=data_clean['Low'], close=data_clean['Close'], name="Ár"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['SMA_20'], line=dict(color='orange', width=1), name="SMA 20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_clean.index, y=data_clean['SMA_200'], line=dict(color='red', width=2), name="SMA 200 (Trend)"), row=1, col=1)
        
        # --- ÚJ: VIZUÁLIS PREDREDIKTÍV MARKEREK A CHARTON ---
        # A) Zöld vételi nyilak kirajzolása pontosan a gyertyák alá
        buys = data_clean[data_clean['Signal'] == "BUY (VÉTEL)"]
        if not buys.empty:
            fig.add_trace(go.Scatter(x=buys.index, y=buys['Low'] * 0.99, mode="markers", marker=dict(symbol="triangle-up", size=12, color="#2ecc71"), name="VÉTELI MARKER (▲)"), row=1, col=1)
            
        # B) Piros eladási nyilak kirajzolása pontosan a gyertyák fölé
        sells = data_clean[data_clean['Signal'] == "SELL (ELADÁS)"]
        if not sells.empty:
            fig.add_trace(go.Scatter(x=sells.index, y=sells['High'] * 1.01, mode="markers", marker=dict(symbol="triangle-down", size=12, color="#e74c3c"), name="ELADÁSI MARKER (▼)"), row=1, col=1)

        # C) Squeeze (Robbanás előtti) zónák sárga kiemelése a SuperTrend helyett
        squeeze_zones = data_clean[data_clean['Squeeze'] == True]
        if not squeeze_zones.empty:
            fig.add_trace(go.Scatter(x=squeeze_zones.index, y=squeeze_zones['Close'], mode="markers", marker=dict(symbol="circle-open", size=6, color="#f1c40f"), name="⚡ Squeeze Robbanás Sáv"), row=1, col=1)

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
        st.plotly_chart(fig, width="stretch")

time.sleep(refresh_rate)
st.rerun()