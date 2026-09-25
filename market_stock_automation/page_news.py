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
                    if not isinstance(item, dict):
                        continue
                    
                    # Biztonságos tartalom lekérés
                    content = item.get("content")
                    if not isinstance(content, dict):
                        content = item # Ha nincs content, az itemet használjuk fallbackként
                    
                    # 1. Cím biztonságos kinyerése
                    title = content.get("title") if isinstance(content, dict) else None
                    if not title:
                        title = item.get("title", "Nincs cím")
                    
                    # 2. Forrás (provider -> displayName) biztonságos kinyerése
                    publisher = "Ismeretlen forrás"
                    if isinstance(content, dict):
                        provider = content.get("provider")
                        if isinstance(provider, dict):
                            publisher = provider.get("displayName", "Ismeretlen forrás")
                    
                    # 3. Link biztonságos kinyerése
                    link = "#"
                    if isinstance(content, dict):
                        click_url = content.get("clickThroughUrl")
                        if isinstance(click_url, dict):
                            link = click_url.get("url", "#")
                        
                        if link == "#":
                            canonical_url = content.get("canonicalUrl")
                            if isinstance(canonical_url, dict):
                                link = canonical_url.get("url", "#")
                    
                    if link == "#":
                        link = item.get("link", "#")
                    
                    # Dátum
                    pub_date = content.get("pubDate", "") if isinstance(content, dict) else ""
                    
                    with st.container():
                        st.markdown(f"#### 🌐 [{title}]({link})")
                        st.write(f"✍️ **Forrás:** {publisher} {f'({pub_date[:10]})' if pub_date else ''}")
                        st.markdown("---")
            else:
                st.warning("⚠️ Figyelem: A Yahoo Finance üres listát küldött vissza a hírekre!")
                
        except Exception as e:
            st.error(f"Nem sikerült letölteni a híreket. Hibaüzenet: `{str(e)}`")