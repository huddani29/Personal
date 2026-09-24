import streamlit as st
import pandas as pd
import time
from datetime import datetime

fetch_and_analyze = st.session_state["fetch_and_analyze"]
AVAILABLE_TICKERS = st.session_state["AVAILABLE_TICKERS"]

st.title("🔍 Többrészes AI Scanner Dashboard")
st.write("Futtass le egy teljes piaci elemzést a Revolut-kompatibilis részvénykosáron.")

selected_tickers = st.multiselect("Szkennelendő részvények:", options=AVAILABLE_TICKERS, default=AVAILABLE_TICKERS)
scan_interval = st.selectbox("Idősík választás:", options=["5m", "15m", "1h", "1d"], index=1)

st.session_state.hide_hold = st.checkbox("Csak az aktív szignálok mutatása (HOLD elrejtése)", value=st.session_state.hide_hold)

if st.button("🚀 PIACI SCANNER INDÍTÁSA", use_container_width=True):
    results = []
    progress_bar = st.progress(0)
    scan_period = "5d" if scan_interval in ["5m", "15m"] else "3mo"
    
    for idx, t in enumerate(selected_tickers):
        progress_bar.progress((idx + 1) / len(selected_tickers))
        scan_data = fetch_and_analyze(t, scan_period, scan_interval)
        
        if scan_data is not None and not scan_data.empty:
            scan_data_clean = scan_data.dropna(subset=['RSI', 'Close', 'MACD'])
            if not scan_data_clean.empty:
                last_r = scan_data_clean.iloc[-1]
                try:
                    results.append({
                        "Részvény (Ticker)": t, 
                        "Aktuális Ár": f"${float(last_r['Close']):.2f}",
                        "RSI (14)": round(float(last_r['RSI']), 2), 
                        "AI Ajánlás": last_r['Signal'],
                        "Legutóbbi Frissítés": scan_data_clean.index[-1].strftime("%Y-%m-%d %H:%M")
                    })
                except: continue
        time.sleep(0.1)
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
            
            # --- ÚJÍTÁS: EXCEL / CSV RIASZTÁSI JELENTÉS LETÖLTÉSE ---
            st.markdown("---")
            csv_scan = df_res.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Szkennelési Jelentés Letöltése (CSV)",
                data=csv_scan,
                file_name=f"ai_scanner_riport_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("A megadott szűrők alapján jelenleg egyetlen részvényen sincs aktív trigger.")
    else:
        st.error("Hálózati hiba: Nem sikerült adatokat lekérni.")