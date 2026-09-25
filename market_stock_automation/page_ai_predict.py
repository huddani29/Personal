# page_ai_predict.py
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from utils import calculate_ichimoku, run_ml_price_prediction

AVAILABLE_TICKERS = st.session_state.get("AVAILABLE_TICKERS", ["TSLA", "NVDA", "AAPL"])

st.title("🧠 AI Gépi Tanulásos Előrejelzés & Ichimoku Cloud Elemző")
st.write("Használj prediktív statisztikai modelleket és a klasszikus japán Ichimoku felhőt a pontosabb piaci képért.")

col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    selected_ticker = st.selectbox("Válassz Ticker-t az AI elemzéshez:", options=AVAILABLE_TICKERS, key="ai_pred_ticker")
with col_sel2:
    selected_period = st.selectbox("Történelmi időszak:", options=["3mo", "6mo", "1y"], index=1, key="ai_pred_period")

if st.button("🚀 AI & Ichimoku Elemzés Futtatása", width="stretch"):
    with st.spinner("Adatletöltés és AI modell betanítása folyamatban..."):
        df = yf.download(tickers=selected_ticker, period=selected_period, interval="1d", progress=False, multi_level_index=False)
        
        if df is not None and not df.empty:
            df.columns = [str(col) for col in df.columns]
            
            # 1. Ichimoku számítás
            df_ichi = calculate_ichimoku(df)
            
            # 2. Gépi tanulásos árbecslés
            pred_price, curr_price, msg = run_ml_price_prediction(df)
            
            st.markdown("---")
            st.subheader(f"📊 Eredmények: {selected_ticker}")
            
            if pred_price is not None:
                diff_pct = ((pred_price - curr_price) / curr_price) * 100
                m1, m2, m3 = st.columns(3)
                m1.metric("Jelenlegi Záróár", f"${curr_price:,.2f}")
                m2.metric("AI Becsült Következő Ár", f"${pred_price:,.2f}", f"{diff_pct:+.2f}%")
                
                if diff_pct > 0:
                    m3.success("📈 AI Irányvárakozás: BIKA (EMELKEDÉS)")
                else:
                    m3.error("📉 AI Irányvárakozás: MEDVE (CSÖKKENÉS)")
            else:
                st.warning(f"AI Előrejelzés figyelmeztetés: {msg}")
                
            st.markdown("---")
            st.subheader("☁️ Ichimoku Cloud & Árfolyam Grafikon")
            
            # Plotly Ichimoku ábra építése
            fig = go.Figure()
            
            # Alap árfolyam gyertyák vagy vonal
            fig.add_trace(go.Scatter(x=df_ichi.index, y=df_ichi['Close'], mode='lines', name='Záróár', line=dict(color='white', width=1.5)))
            
            # Ichimoku vonalak keresése a oszlop nevek alapján (pandas_ta elnevezések)
            cols = df_ichi.columns
            tenkan_col = [c for c in cols if 'ITS_' in c or 'Tenkan' in c or 'ISA_' in c]
            
            # Ha léteznek Ichimoku oszlopok, kirajzoljuk a felhőt
            # Keresés a span vonalakra
            span_a_cols = [c for c in cols if 'ISA_' in c or 'SpanA' in c or 'ITS_' in c]
            span_b_cols = [c for c in cols if 'ISB_' in c or 'SpanB' in c]
            
            if len(span_a_cols) > 0 and len(span_b_cols) > 0:
                s_a = df_ichi[span_a_cols[0]]
                s_b = df_ichi[span_b_cols[0]]
                
                fig.add_trace(go.Scatter(x=df_ichi.index, y=s_a, mode='lines', name='Senkou Span A', line=dict(color='green', width=0.8), showlegend=False))
                fig.add_trace(go.Scatter(x=df_ichi.index, y=s_b, mode='lines', name='Senkou Span B', line=dict(color='red', width=0.8), fill='tonexty', fillcolor='rgba(128,128,128,0.2)', showlegend=False))

            fig.update_layout(
                template="plotly_dark",
                height=500,
                title=f"{selected_ticker} - Technikai Ichimoku Elemzés",
                xaxis_title="Dátum",
                yaxis_title="Ár ($)"
            )
            st.plotly_chart(fig, width="stretch")
            
        else:
            st.error("Nem sikerült adatokat letölteni ehhez a Ticker-hez.")