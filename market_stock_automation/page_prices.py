import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.title("📊 Ár-Összehasonlító Dashboard")
st.write("Hasonlítsd össze a figyelt részvényeid teljesítményét és relatív árait.")

AVAILABLE_TICKERS = st.session_state.get("AVAILABLE_TICKERS", ["TSLA", "NVDA", "AAPL"])
compare_tickers = st.multiselect("Válassz ki részvényeket az összehasonlításhoz:", options=AVAILABLE_TICKERS, default=AVAILABLE_TICKERS[:3])

if compare_tickers:
    with st.spinner("Adatok letöltése az összehasonlításhoz..."):
        fig_comp = go.Figure()
        
        for t in compare_tickers:
            try:
                # Letöltünk 1 havi adatot a trendekhez
                df_comp = yf.download(tickers=t, period="1mo", interval="1d", progress=False, multi_level_index=False)
                if not df_comp.empty:
                    df_comp.columns = [str(col) for col in df_comp.columns]
                    
                    # Bázisértékhez mérünk (százalékos növekedés, hogy a Ft és a $ összehasonlítható legyen!)
                    first_close = float(df_comp['Close'].iloc[0])
                    normalized_series = ((df_comp['Close'] - first_close) / first_close) * 100
                    
                    fig_comp.add_trace(go.Scatter(x=df_comp.index, y=normalized_series, mode="lines", name=f"{t} (Relatív elmozdulás %)"))
            except: continue
            
        fig_comp.update_layout(
            height=450, 
            template="plotly_dark", 
            xaxis_title="Dátum", 
            yaxis_title="Relatív Teljesítmény a hónap elejéhez képest (%)",
            margin=dict(l=20, r=20, t=10, b=10)
        )
        st.plotly_chart(fig_comp, width="stretch")

        # Élő árak kiírása táblázatba, valutának megfelelően
        st.markdown("### 📌 Aktuális piaci árak")
        price_rows = []
        for t in compare_tickers:
            try:
                live_data = yf.download(tickers=t, period="1d", interval="1m", progress=False, multi_level_index=False)
                if not live_data.empty:
                    live_data.columns = [str(col) for col in live_data.columns]
                    last_p = float(live_data['Close'].iloc[-1])
                    
                    # JAVÍTÁS: A 'last_p' változót használjuk a formázásban!
                    if ".BD" in t: 
                        px_fmt = f"{last_p:,.0f} Ft"
                    elif t in ["ASML", "SAP", "BMW", "DBK", "VOW3", "LVMH"]: 
                        px_fmt = f"€{last_p:.2f}"
                    else: 
                        px_fmt = f"${last_p:.2f}"
                    
                    price_rows.append({"Részvény": t, "Aktuális Piaci Ár": px_fmt})
            except: continue
            
        if price_rows:
            st.dataframe(pd.DataFrame(price_rows), width="stretch")

