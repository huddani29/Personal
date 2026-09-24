import streamlit as st
import yfinance as yf
import pandas as pd

st.title("🏆 TOP 10 Legnyereségesebb és Legveszteségesebb Részvény")
st.write("Tekintsd át a mai nap legnagyobb mozgásait földrajzi piacok szerint lebontva.")

# Fixen definiált piaci listák az összehasonlításhoz
MARKET_GROUPS = {
    "🇺🇸 Amerikai Piac": ["TSLA", "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "AMD", "COIN", "NIO", "PLTR", "SOFI", "PLUG", "RIVN"],
    "🇪🇺 Európai Piac": ["ASML", "SAP", "BMW", "DBK", "VOW3", "LVMH", "IWDA.AS", "EMIM.AS"],
    "🇭🇺 Magyar Piac (Revoluton kívüli referencia)": ["OTP.BD", "MOL.BD", "RICHT.BD", "4IG.BD"]
}

selected_market = st.selectbox("Válassz ki egy piacot:", options=list(MARKET_GROUPS.keys()))
ticker_list = MARKET_GROUPS[selected_market]

if st.button("📊 RANGSOR FRISSÍTÉSE", use_container_width=True):
    with st.spinner("Adatok letöltése a tőzsdéről..."):
        ranking_data = []
        try:
            # Kötegelt letöltés a sebesség érdekében
            raw_data = yf.download(tickers=ticker_list, period="2d", interval="1d", progress=False, group_by='ticker')
            
            for t in ticker_list:
                try:
                    if len(ticker_list) > 1: df = raw_data[t].copy()
                    else: df = raw_data.copy()
                    
                    df_clean = df.dropna(subset=['Close'])
                    if len(df_clean) >= 2:
                        prev_close = float(df_clean['Close'].iloc[-2])
                        last_close = float(df_clean['Close'].iloc[-1])
                        daily_change = ((last_close - prev_close) / prev_close) * 100
                        
                        if ".BD" in t:
                            currency_formatted = f"{last_close:,.0f} Ft"
                        elif t in ["ASML", "SAP", "BMW", "DBK", "VOW3", "LVMH"]:
                            currency_formatted = f"€{last_close:.2f}"
                        else:
                            currency_formatted = f"${last_close:.2f}"


                        ranking_data.append({
                            "Részvény (Ticker)": t,
                            "Aktuális Ár": currency_formatted,
                            "Napi Változás (%)": round(daily_change, 2)
                        })
                except: continue
        except:
            st.error("Hálózati hiba történt az adatok letöltésekor.")

        if ranking_data:
            df_all = pd.DataFrame(ranking_data)
            
            # Kettéosztjuk nyertesekre és vesztesekre
            df_winners = df_all.sort_values(by="Napi Változás (%)", ascending=False).head(10).reset_index(drop=True)
            df_losers = df_all.sort_values(by="Napi Változás (%)", ascending=True).head(10).reset_index(drop=True)
            
            def color_picker(val):
                if val > 0: return 'color: #2ecc71; font-weight: bold;'
                if val < 0: return 'color: #e74c3c; font-weight: bold;'
                return ''

            c1,  c2 = st.columns(2)
            with c1:
                st.markdown("### 🟢 TOP 10 Legnyereségesebb (Bullish)")
                st.dataframe(df_winners.style.map(color_picker, subset=['Napi Változás (%)']), use_container_width=True)
            with c2:
                st.markdown("### 🔴 TOP 10 Legveszteségesebb (Bearish)")
                st.dataframe(df_losers.style.map(color_picker, subset=['Napi Változás (%)']), use_container_width=True)
        else:
            st.warning("Jelenleg nem elérhetőek adatok ehhez a piachoz.")
