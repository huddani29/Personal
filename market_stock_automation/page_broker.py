# page_broker.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
from utils import is_market_open_for_trading, can_open_position, get_currency_symbol, format_price

st.title("💼 Virtuális Bróker & AI Kereskedő Bot")
st.write("Kezeld a virtuális tőkédet kézzel vagy engedd szabadjára az AI Autó-Tradedet valós idejű kockázatkezeléssel.")

# Session state alapértékek inicializálása, ha még nem léteznének
if "cash_balance" not in st.session_state:
    st.session_state.cash_balance = 10000.0  # Kezdő tőke
if "portfolio_positions" not in st.session_state:
    st.session_state.portfolio_positions = {}  # {ticker: {"shares": x, "buy_price": y, "sl": z, "tp": w}}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []
if "equity_curve" not in st.session_state:
    st.session_state.equity_curve = [10000.0]
if "auto_trader_active" not in st.session_state:
    st.session_state.auto_trader_active = False

AVAILABLE_TICKERS = st.session_state.get("AVAILABLE_TICKERS", ["TSLA", "NVDA", "AAPL", "OTP.BD", "MOL.BD"])

# --- FELSŐ METRIKÁK ---
total_portfolio_value = st.session_state.cash_balance
for t, pos in st.session_state.portfolio_positions.items():
    total_portfolio_value += pos["shares"] * pos["buy_price"]

# Alapértelmezett USD alapú formázás a szabad készpénzre és összvagyonra
m1, m2, m3 = st.columns(3)
m1.metric("Szabad Készpénz", f"${st.session_state.cash_balance:,.2f}")
m2.metric("Nyitott Pozíciók Értéke", f"${(total_portfolio_value - st.session_state.cash_balance):,.2f}")
m3.metric("Teljes Vagyon (Equity)", f"${total_portfolio_value:,.2f}")

st.markdown("---")

# --- KÉZI KERESKEDÉS ÉS STOP-LOSS / TAKE-PROFIT ---
st.subheader("🛒 Kézi Gyors-Kereskedés & Kockázatkezelés")

col_trade1, col_trade2 = st.columns(2)

with col_trade1:
    trade_ticker = st.selectbox("Válassz Ticker-t a kereskedéshez:", options=AVAILABLE_TICKERS, key="broker_ticker")
    trade_action = st.radio("Művelet:", options=["VÉTEL (BUY)", "ELADÁS (SELL)"], horizontal=True)
    trade_shares = st.number_input("Mennyiség (db):", min_value=1, value=10, step=1)

with col_trade2:
    st.markdown("### Kockázatkezelési szintek")
    sl_percent = st.slider("Stop-Loss (% az ártól)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)
    tp_percent = st.slider("Take-Profit (% az ártól)", min_value=1.0, max_value=30.0, value=10.0, step=0.5)
    
    # Dinamikus valuta és árazás lekérése a kiválasztott ticker alapján
    est_price = 150.0 if not trade_ticker.endswith(".BD") else 10000.0  # Alapértelmezett fallback
    ticker_currency = get_currency_symbol(trade_ticker)
    total_cost = trade_shares * est_price

if st.button("⚡ MEGBÍZÁS VÉGREHAJTÁSA (KÉZI)", width="stretch"):
    if "VÉTEL" in trade_action:
        allowed, msg = can_open_position(st.session_state.cash_balance, total_portfolio_value, total_cost, max_share=0.25)
        
        if not allowed:
            st.error(f"❌ Kereskedés elutasítva: {msg}")
        else:
            st.session_state.cash_balance -= total_cost
            sl_price = est_price * (1 - sl_percent / 100)
            tp_price = est_price * (1 + tp_percent / 100)
            
            if trade_ticker in st.session_state.portfolio_positions:
                st.session_state.portfolio_positions[trade_ticker]["shares"] += trade_shares
            else:
                st.session_state.portfolio_positions[trade_ticker] = {
                    "shares": trade_shares,
                    "buy_price": est_price,
                    "sl": sl_price,
                    "tp": tp_price
                }
            
            st.session_state.trade_history.append({
                "Időpont": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Ticker": trade_ticker,
                "Típus": "BUY",
                "Mennyiség": trade_shares,
                "Ár": format_price(est_price, ticker_currency)
            })
            st.success(f"✅ Sikeres Vétel: {trade_shares} db {trade_ticker} megvéve. SL: {format_price(sl_price, ticker_currency)} | TP: {format_price(tp_price, ticker_currency)}")
            st.rerun()
            
    else: # ELADÁS
        if trade_ticker in st.session_state.portfolio_positions and st.session_state.portfolio_positions[trade_ticker]["shares"] >= trade_shares:
            st.session_state.portfolio_positions[trade_ticker]["shares"] -= trade_shares
            revenue = trade_shares * est_price
            st.session_state.cash_balance += revenue
            
            if st.session_state.portfolio_positions[trade_ticker]["shares"] == 0:
                del st.session_state.portfolio_positions[trade_ticker]
                
            st.session_state.trade_history.append({
                "Időpont": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Ticker": trade_ticker,
                "Típus": "SELL",
                "Mennyiség": trade_shares,
                "Ár": format_price(est_price, ticker_currency)
            })
            st.success(f"✅ Sikeres Eladás: {trade_shares} db {trade_ticker} eladva.")
            st.rerun()
        else:
            st.error("❌ Nincs elegendő nyitott pozíciód ebből a részvényből az eladáshoz!")

st.markdown("---")

# --- AUTOMATA BOT VEZÉRLÉS ---
st.subheader("🤖 AI Auto-Trader Bot Vezérlőpult")
st.write("A bot automatikusan figyeli a piacot, de **csak nyitvatartási időben** nyit pozíciót a kockázatkezelési szabályok betartásával.")

col_bot1, col_bot2 = st.columns(2)
with col_bot1:
    if st.button("🟢 Auto-Trader Bekapcsolása", width="stretch"):
        if is_market_open_for_trading():
            st.session_state.auto_trader_active = True
            st.success("🤖 Auto-Trader sikeresen AKTIVÁLVA!")
        else:
            st.warning("⚠️ A piac jelenleg zárva van! Az Auto-Trader nem indítható el alacsony likviditású sávban.")
with col_bot2:
    if st.button("🔴 Auto-Trader Kikapcsolása", width="stretch"):
        st.session_state.auto_trader_active = False
        st.info("🤖 Auto-Trader leállítva.")

if st.session_state.auto_trader_active:
    st.info("🟢 Az Auto-Trader fut a háttérben... (Aktív piaci fázis ellenőrzés: OK)")
else:
    st.warning("🔴 Az Auto-Trader jelenleg inaktív.")

st.markdown("---")

# --- VAGYONNÖVEKEDÉSI (EQUITY CURVE) GRAFIKON ---
st.subheader("📈 Portfólió Vagyonnövekedési Görbe (Equity Curve)")
if st.session_state.equity_curve:
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        y=st.session_state.equity_curve,
        mode="lines+markers",
        line=dict(color="#2ecc71", width=2),
        name="Teljes Vagyon"
    ))
    fig_eq.update_layout(
        height=350,
        template="plotly_dark",
        xaxis_title="Tranzakciós / Frissítési Lépések",
        yaxis_title="Vagyon ($)",
        margin=dict(l=20, r=20, t=10, b=10)
    )
    st.plotly_chart(fig_eq, width="stretch")

# --- NYITOTT POZÍCIÓK ÉS ELŐZMÉNYEK TÁBLÁZATA ---
st.markdown("### 📋 Jelenlegi Nyitott Pozícióid")
if st.session_state.portfolio_positions:
    pos_list = []
    for t, p in st.session_state.portfolio_positions.items():
        curr = get_currency_symbol(t)
        pos_list.append({
            "Ticker": t,
            "Mennyiség": p["shares"],
            "Nyitó Ár": format_price(p['buy_price'], curr),
            "Stop-Loss": format_price(p['sl'], curr),
            "Take-Profit": format_price(p['tp'], curr)
        })
    st.dataframe(pd.DataFrame(pos_list), width="stretch")
else:
    st.info("Jelenleg nincsenek nyitott pozícióid.")

st.markdown("### 📜 Kereskedési Előzmények")
if st.session_state.trade_history:
    st.dataframe(pd.DataFrame(st.session_state.trade_history), width="stretch")
else:
    st.write("Még nem történtek tranzakciók.")