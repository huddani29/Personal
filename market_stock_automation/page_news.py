import streamlit as st
import yfinance as yf
import pandas as pd

st.title("📰 AI Gazdasági Híradó & Szalagcímek")
st.write("Olvasd el a figyelt részvényeidhez kapcsolódó legfrissebb nemzetközi pénzügyi híreket.")

AVAILABLE_TICKERS = st.session_state.get("AVAILABLE_TICKERS", ["TSLA", "NVDA", "AAPL"])
chosen_news_ticker = st.selectbox("Válassz ki egy részvényt a hírfolyamhoz:", options=AVAILABLE_TICKERS)

if chosen_news_ticker:
    with st.spinner(f"A(z) {chosen_news_ticker} legfrissebb híreinek letöltése..."):
        try:
            tick_obj = yf.Ticker(chosen_news_ticker)
            news_list = tick_obj.news
            
            # --- 🛠️ DEBUG BLOKK INDÍTÁSA ---
            st.markdown("### 🪲 Rendszer-Diagnosztika (Debug info)")
            st.write(f"Letöltött adatok típusa: `{type(news_list)}`")
            st.write(f"Talált elemek száma: `{len(news_list) if news_list else 0}`")
            
            # Kiírjuk a nyers adatokat az első elemből, hogy lássuk a kulcsokat
            if news_list and len(news_list) > 0:
                st.markdown("**Nyers első hír-objektum szerkezete:**")
                st.json(news_list[0])
            else:
                st.warning("⚠️ Figyelem: A Yahoo Finance üres listát küldött vissza a hírekre! (Lehetséges hálózati tiltás vagy API változás)")
            st.markdown("---")
            # --- 🛠️ DEBUG BLOKK VÉGE ---
            
            if news_list:
                for item in news_list[:8]:
                    title = item.get("headline", item.get("title", "Nincs cím"))
                    publisher = item.get("source", item.get("publisher", "Ismeretlen forrás"))
                    link = item.get("link", "#")
                    
                    with st.container():
                        st.markdown(f"#### 🌐 [{title}]({link})")
                        st.write(f"✍️ **Forrás:** {publisher}")
                        st.markdown("---")
        except Exception as e:
            st.error(f"Nem sikerült letölteni a híreket. Hibaüzenet: `{str(e)}`")
