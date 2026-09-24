import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime

AVAILABLE_TICKERS = st.session_state.get("AVAILABLE_TICKERS", ["TSLA", "NVDA", "AAPL"])

st.title("🔍 Többrészes AI Scanner Dashboard")
st.write("Futtass le egy teljes piaci elemzést a figyelt részvénykosáron.")

selected_tickers = st.multiselect("Szkennelendő részvények:", options=AVAILABLE_TICKERS, default=AVAILABLE_TICKERS)
scan_interval = st.selectbox("Idősík választás:", options=["5m", "15m", "1h", "1d"], index=1)

st.session_state.hide_hold = st.checkbox("Csak az aktív szignálok mutatása (HOLD elrejtése)", value=st.session_state.hide_hold)

if st.button("🚀 PIACI SCANNER INDÍTÁSA", use_container_width=True):
    results = []
    progress_bar = st.progress(0)
    scan_period = "5d" if scan_interval in ["5m", "15m"] else "3mo"
    
    for idx, t in enumerate(selected_tickers):
        progress_bar.progress((idx + 1) / len(selected_tickers))
        
        try:
            scan_data = yf.download(tickers=t, period=scan_period, interval=scan_interval, progress=False, multi_level_index=False)
            if not scan_data.empty:
                scan_data.columns = [str(col) for col in scan_data.columns]
                scan_data['RSI'] = ta.rsi(close=scan_data['Close'], length=14)
                
                macd_df = ta.macd(close=scan_data['Close'], fast=12, slow=26, signal=9)
                macd_val, macd_sig = 0.0, 0.0
                if macd_df is not None:
                    macd_val = float(macd_df.iloc[-1, 0])
                    macd_sig = float(macd_df.iloc[-1, 2])
                
                scan_data_clean = scan_data.dropna(subset=['RSI', 'Close'])
                if not scan_data_clean.empty:
                    last_r = scan_data_clean.iloc[-1]
                    rsi_val = float(last_r['RSI'])
                    last_close_val = float(last_r['Close'])
                    
                    sig = "HOLD"
                    if rsi_val < 40 and macd_val > macd_sig: sig = "BUY (VÉTEL)"
                    elif rsi_val > 60: sig = "SELL (ELADÁS)"
                    
                    # INTELLIGENS VALUTAFELISMERŐ FORMÁZÁS
                    if ".BD" in t:
                        price_formatted = f"{last_close_val:,.0f} Ft"
                    else:
                        price_formatted = f"${last_close_val:.2f}"
                    
                    results.append({
                        "Részvény (Ticker)": t, 
                        "Aktuális Ár": price_formatted,
                        "RSI (14)": round(rsi_val, 2), 
                        "AI Ajánlás": sig,
                        "Legutóbbi Frissítés": scan_data_clean.index[-1].strftime("%Y-%m-%d %H:%M")
                    })
        except: continue
        time.sleep(0.05)
        
    progress_bar.empty()
    
    if results:
        df_res = pd.DataFrame(results)
        if st.session_state.hide_hold:
            df_res = df_res[df_res['AI Ajánlás'] != "HOLD"]
        
        def color_signals(val):
            if "BUY" in val: return 'background-color: #2ecc71; color: black; font-weight: bold;'
            if "SELL" in val: return 'background-color: #e74c3c; color: white; font-weight: bold;'
            return ''
            
        st.markdown("### 📊 Elemzési Jelentés")
        if not df_res.empty:
            st.dataframe(df_res.style.map(color_signals, subset=['AI Ajánlás']), use_container_width=True)
            st.markdown("---")
            csv_scan = df_res.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Szkennelési Jelentés Letöltése (CSV)", data=csv_scan, file_name=f"ai_scanner_riport.csv", mime="text/csv", use_container_width=True)
        else:
            st.info("Nincs aktív trigger.")
