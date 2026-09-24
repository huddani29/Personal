import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

AVAILABLE_TICKERS = st.session_state["AVAILABLE_TICKERS"]
send_discord_message = st.session_state["send_discord_message"]

st.title("🏦 Virtuális Bróker Számla & Portfólió")

# --- FÜGGVÉNYEK A KAPCSOLÓK ÁLLAPOTÁNAK MENTÉSÉRE ---
def update_paper():
    st.session_state.paper_persistent = st.session_state.paper_widget
    if not st.session_state.paper_widget:
        st.session_state.autotrader_persistent = False

def update_auto():
    st.session_state.autotrader_persistent = st.session_state.auto_widget

# --- JAVÍTOTT OLDALSÁV VEZÉRLÉS ---
st.sidebar.header("Szimulátor Beállítások")

# A widgeteket egyedi kulccsal látjuk el, és változáskor azonnal mentjük a háttérmemóriába
st.sidebar.checkbox("Paper Trading Aktiválása", value=st.session_state.paper_persistent, key="paper_widget", on_change=update_paper)
st.sidebar.checkbox("🤖 Auto-Trader Bot Bekapcsolása", value=st.session_state.autotrader_persistent, key="auto_widget", on_change=update_auto, disabled=not st.session_state.paper_persistent)

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Kockázatkezelés (Risk)")
st.sidebar.slider("Stop-Loss (Veszteségzárás %):", min_value=0.5, max_value=10.0, step=0.5, key="stop_loss_pct")
st.sidebar.slider("Take-Profit (Célár profit %):", min_value=1.0, max_value=25.0, step=0.5, key="take_profit_pct")

st.sidebar.markdown("---")
st.sidebar.header("💬 Értesítések")
st.sidebar.text_input("Discord Webhook URL:", value=st.session_state.discord_webhook, key="discord_webhook")

if st.sidebar.button("🧪 Discord Teszt Üzenet", use_container_width=True, disabled=not st.session_state.discord_webhook):
    send_discord_message("🧪 **AI Tőzsde Bot:** Sikeres Discord webhook integráció! A rendszer készen áll a riasztások küldésére.")
    st.sidebar.success("Teszt üzenet elküldve a Discordra!")

# --- BRÓKER SZÁMLA MEGJELENÍTÉSE ---
if st.session_state.paper_persistent:
    total_shares_value = 0.0
    portfolio_rows = []
    
    for ticker, qty in st.session_state.portfolio["shares"].items():
        if qty > 0:
            try:
                t_data = yf.download(ticker, period="1d", interval="1m", progress=False, multi_level_index=False)
                if not t_data.empty:
                    t_data.columns = [str(col) for col in t_data.columns]
                    current_price = float(t_data['Close'].iloc[-1])
                    total_shares_value += qty * current_price
                    
                    buy_px = st.session_state.buy_prices_memory.get(ticker, current_price)
                    profit_pct = ((current_price - buy_px) / buy_px) * 100
                    
                    portfolio_rows.append({
                        "Részvény": ticker, "Mennyiség (db)": qty, 
                        "Bekerülési Ár": f"${buy_px:.2f}",       # JAVÍTVA: \($ helyett $
                        "Aktuális Ár": f"${current_price:.2f}",   # JAVÍTVA: \)$ helyett $
                        "Aktuális Profit (%)": f"{profit_pct:+.2f}%", 
                        "Érték összesen": f"${qty * current_price:.2f}" # JAVÍTVA: \$ helyett $
                    })

            except: pass

    current_portfolio_value = st.session_state.portfolio['balance'] + total_shares_value

    c1, c2, c3 = st.columns(3)
    c1.metric("Szabad Készpénz Egyenleg", f"\${st.session_state.portfolio['balance']:.2f}")
    c2.metric("Részvények Összértéke", f"\${total_shares_value:.2f}")
    c3.metric("Teljes Portfólió Érték (Net Worth)", f"\${current_portfolio_value:.2f}")

    st.markdown("### 💼 Nyitott Pozícióid")
    if portfolio_rows: st.dataframe(pd.DataFrame(portfolio_rows), use_container_width=True)
    else: st.info("Jelenleg nincs nyitott pozíciód.")

    st.markdown("### ⚡ Kézi Gyors-Kereskedés")
    trade_ticker = st.selectbox("Kereskedni kívánt részvény:", options=AVAILABLE_TICKERS)
    trade_qty = st.number_input("Darabszám:", min_value=1, value=1, step=1)
    
    try:
        px_data = yf.download(trade_ticker, period="1d", interval="1m", progress=False, multi_level_index=False)
        live_px = float(px_data['Close'].iloc[-1]) if not px_data.empty else 1.0
    except: live_px = 1.0
    
    st.write(f"Kiválasztott eszköz aktuális piaci ára: **${live_px:.2f}** | Tervezett ügylet értéke: **${live_px * trade_qty:.2f}**")

    b1, b2, _ = st.columns(3)
    if b1.button(f"🔴 VÉTEL: {trade_qty} db {trade_ticker}", use_container_width=True):
        cost = trade_qty * live_px
        if st.session_state.portfolio['balance'] >= cost:
            st.session_state.portfolio['balance'] -= cost
            st.session_state.portfolio['shares'][trade_ticker] = st.session_state.portfolio['shares'].get(trade_ticker, 0) + trade_qty
            st.session_state.buy_prices_memory[trade_ticker] = live_px 
            
            # JAVÍTVA: Teljesen tiszta dollárjel formázás, zárójelek és visszaperjelek NÉLKÜL
            st.session_state.trade_history.append({
                "Idő": datetime.now().strftime("%H:%M:%S"), 
                "Ticker": trade_ticker, 
                "Típus": "KÉZI VÉTEL", 
                "Ár": f"${live_px:.2f}", 
                "Darab": trade_qty, 
                "Összesen": f"${cost:.2f}"
            })
            st.session_state["save_portfolio_to_disk"]()
            st.session_state["save_history_to_disk"]()
            st.rerun()
        else: st.error("Nincs elég szabad egyenleged!")

    if b2.button(f"🟢 ELADÁS: {trade_qty} db {trade_ticker}", use_container_width=True):
        owned = st.session_state.portfolio['shares'].get(trade_ticker, 0)
        if owned >= trade_qty:
            revenue = trade_qty * live_px
            st.session_state.portfolio['balance'] += revenue
            st.session_state.portfolio['shares'][trade_ticker] -= trade_qty
            if st.session_state.portfolio['shares'][trade_ticker] == 0: 
                del st.session_state.portfolio['shares'][trade_ticker]
                if trade_ticker in st.session_state.buy_prices_memory: del st.session_state.buy_prices_memory[trade_ticker]
            
            st.session_state.trade_history.append({
                "Idő": datetime.now().strftime("%H:%M:%S"), 
                "Ticker": trade_ticker, 
                "Típus": "KÉZI ELADÁS", 
                "Ár": f"${live_px:.2f}", 
                "Darab": trade_qty, 
                "Összesen": f"${revenue:.2f}"
            })
            st.session_state["save_portfolio_to_disk"]()
            st.session_state["save_history_to_disk"]()
            st.rerun()
        else: st.error("Nincs ennyi részvényed!")

    # --- PORTFÓLIÓ VAGYONTÖRTÉNET GRAFIKON (EQUITY CURVE) ---
    if "equity_history" in st.session_state and len(st.session_state.equity_history) > 1:
        st.markdown("### 📈 Portfólió Vagyonnövekedés (Equity Curve)")
        df_equity = pd.DataFrame(st.session_state.equity_history)
        
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(x=df_equity["Idő"], y=df_equity["Teljes Vagyon"], mode="lines+markers", name="Net Worth", line=dict(color="#2ecc71", width=2.5)))
        fig_equity.update_layout(height=300, template="plotly_dark", xaxis_title="Időpont", yaxis_title="Tőke (USD)", margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig_equity, use_container_width=True)

    # HISTORIKUS TRANZAKCIÓS NAPLÓ + LETÖLTÉS
    if st.session_state.trade_history:
        st.markdown("### 📜 Számla Tranzakciós Előzmények (Log)")
        df_history = pd.DataFrame(st.session_state.trade_history)
        st.dataframe(df_history, use_container_width=True)
        
        csv_data = df_history.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Tranzakciós Napló Letöltése (CSV)",
            data=csv_data,
            file_name=f"tozsde_naplo_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
else:
    st.info("A Bróker Számla megtekintéséhez kapcsold be a bal oldali menüben a 'Paper Trading Aktiválása' opciót!")

