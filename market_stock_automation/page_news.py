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
            
            if news_list:
                for item in news_list[:8]:
                    # 1. Ha van 'content' réteg, beljebb kell menni
                    content = item.get("content", item)
                    
                    # 2. Cím lekérése az új kulcsok alapján
                    title = content.get("title", item.get("title", "Nincs cím"))
                    
                    # 3. Forrás lekérése (provider -> displayName)
                    provider = content.get("provider", {})
                    publisher = provider.get("displayName", item.get("publisher", "Ismeretlen forrás"))
                    
                    # 4. Link lekérése (clickThroughUrl vagy canonicalUrl vagy közvetlen link)
                    click_url = content.get("clickThroughUrl", {})
                    canonical_url = content.get("canonicalUrl", {})
                    link = click_url.get("url", canonical_url.get("url", item.get("link", "#")))
                    
                    # Opcionális: Dátum/idő kiolvasása is hasznos lehet
                    pub_date = content.get("pubDate", "")
                    
                    with st.container():
                        st.markdown(f"#### 🌐 [{title}]({link})")
                        st.write(f"✍️ **Forrás:** {publisher} {f'({pub_date[:10]})' if pub_date else ''}")
                        st.markdown("---")
            else:
                st.warning("⚠️ Figyelem: A Yahoo Finance üres listát küldött vissza a hírekre!")
                
        except Exception as e:
            st.error(f"Nem sikerült letölteni a híreket. Hibaüzenet: `{str(e)}`")