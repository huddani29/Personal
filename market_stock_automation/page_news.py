import streamlit as st
import yfinance as yf
import pandas as pd

st.title("📰 AI Gazdasági Híradó & Szalagcímek")
st.write("Olvasd el a figyelt részvényeidhez kapcsolódó legfrissebb nemzetközi pénzügyi híreket és elemzéseket.")

AVAILABLE_TICKERS = st.session_state.get("AVAILABLE_TICKERS", ["TSLA", "NVDA", "AAPL"])
chosen_news_ticker = st.selectbox("Válassz ki egy részvényt a hírfolyamhoz:", options=AVAILABLE_TICKERS)

if chosen_news_ticker:
    with st.spinner(f"A(z) {chosen_news_ticker} legfrissebb híreinek letöltése..."):
        try:
            tick_obj = yf.Ticker(chosen_news_ticker)
            news_list = tick_obj.news
            
            if news_list:
                for item in news_list[:8]: # Legfrissebb 8 hír
                    # JAVÍTÁS: Intelligens kulcs-ellenőrzés a Yahoo Finance új API struktúrájához
                    title = item.get("headline", item.get("title", "Nincs cím"))
                    publisher = item.get("source", item.get("publisher", "Ismeretlen forrás"))
                    link = item.get("link", "#")
                    
                    with st.container():
                        st.markdown(f"#### 🌐 [{title}]({link})")
                        st.write(f"✍️ **Forrás:** {publisher}")
                        st.markdown("---")
            else:
                st.info(f"Jelenleg nincsenek friss hírek a(z) {chosen_news_ticker} részvényhez.")
        except:
            st.error("Nem sikerült letölteni a híreket a Yahoo Finance-ről.")
