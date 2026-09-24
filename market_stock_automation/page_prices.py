import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

AVAILABLE_TICKERS = st.session_state["AVAILABLE_TICKERS"]

st.title("📊 Részvényárak Összehasonlító Dashboard")
st.write("Kövesd és hasonlítsd össze a kiválasztott Revolut-részvények áralakulását és százalékos teljesítményét.")

# --- BEÁLLÍTÁSOK ---
st.sidebar.header("Grafikon Beállítások")
selected_compare_tickers = st.multiselect("Válaszd ki az összehasonlítandó részvényeket:", options=AVAILABLE_TICKERS, default=["TSLA", "NVDA", "AAPL", "PLTR"])
chart_interval = st.sidebar.selectbox("Grafikon felbontása:", options=["5m", "15m", "1h", "1d"], index=2, key="comp_i")
chart_period = st.sidebar.selectbox("Időtartam (Múltbeli adatok):", options=["1d", "5d", "1mo", "3mo", "1y"], index=2, key="comp_p")
chart_mode = st.sidebar.radio("Megjelenítési mód:", options=["Tényleges Ár ($)", "Százalékos Teljesítmény (%)"], index=0)

if selected_compare_tickers:
    fig = go.Figure()
    progress_bar = st.progress(0)
    
    # Adatok letöltése és ábrázolása
    for idx, ticker in enumerate(selected_compare_tickers):
        progress_bar.progress((idx + 1) / len(selected_compare_tickers))
        
        try:
            # Tisztított adatlekérés MultiIndex nélkül
            df = yf.download(ticker, period=chart_period, interval=chart_interval, progress=False, multi_level_index=False)
            if not df.empty:
                df.columns = [str(col) for col in df.columns]
                df_clean = df.dropna(subset=['Close'])
                
                if not df_clean.empty:
                    if chart_mode == "Tényleges Ár ($)":
                        # Sima dollár ár ábrázolása
                        fig.add_trace(go.Scatter(x=df_clean.index, y=df_clean['Close'], mode='lines', name=ticker, line=dict(width=1.8)))
                    else:
                        # Százalékos változás a periódus legelső záróárához képest
                        initial_price = float(df_clean['Close'].iloc[0])
                        pct_change = ((df_clean['Close'] - initial_price) / initial_price) * 100
                        fig.add_trace(go.Scatter(x=df_clean.index, y=pct_change, mode='lines', name=f"{ticker} (%)", line=dict(width=1.8)))
        except:
            continue
            
    progress_bar.empty()
    
    # Grafikon stílusának testreszabása
    y_axis_title = "Árfolyam (USD)" if chart_mode == "Tényleges Ár ($)" else "Teljesítmény a kezdőnaphoz képest (%)"
    fig.update_layout(
        height=600,
        template="plotly_dark",
        xaxis_title="Időpont",
        yaxis_title=y_axis_title,
        margin=dict(l=20, r=20, t=20, b=20),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Kérlek, válassz ki legalább egy részvényt a fenti listából!")
