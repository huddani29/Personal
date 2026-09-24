import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import os
import time
from datetime import datetime

# Globális oldalbeállítás (MINDEN előtt le kell futnia!)
st.set_page_config(page_title="AI Tőzsde Központ Pro", layout="wide", page_icon="📊")

# --- KÖZÖS RÉSZVÉNYKOSÁR ---
AVAILABLE_TICKERS = ["TSLA", "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "AMD", "COIN", "NIO", "CAN", "GPRO", "HMY", "RIVN", "PLUG", "CRSP", "PLTR", "SOFI", "IWDA.AS", "EMIM.AS", "UST"]

# --- TARTÓS FÁJLMENTÉS (ADATBÁZIS CSERE) ---
PORTFOLIO_FILE = "portfolio_db.json"
HISTORY_FILE = "trade_history_db.csv"

# A) Portfólió betöltése lemezről vagy inicializálása
if "portfolio" not in st.session_state:
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                st.session_state.portfolio = json.load(f)
        except:
            st.session_state.portfolio = {"balance": 10000.0, "shares": {}}
    else:
        st.session_state.portfolio = {"balance": 10000.0, "shares": {}}

# B) Tranzakciós napló betöltése lemezről vagy inicializálása
if "trade_history" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            st.session_state.trade_history = pd.read_csv(HISTORY_FILE).to_dict(orient="records")
        except:
            st.session_state.trade_history = []
    else:
        st.session_state.trade_history = []

# Mentési funkciók deklarálása
def save_portfolio_to_disk():
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(st.session_state.portfolio, f)

def save_history_to_disk():
    if st.session_state.trade_history:
        pd.DataFrame(st.session_state.trade_history).to_csv(HISTORY_FILE, index=False)

st.session_state["save_portfolio_to_disk"] = save_portfolio_to_disk
st.session_state["save_history_to_disk"] = save_history_to_disk

# C) Egyéb technikai memóriák kötelező indítása (Megszünteti a KeyError-t!)
if "signals_memory" not in st.session_state: st.session_state.signals_memory = {}
if "buy_prices_memory" not in st.session_state: st.session_state.buy_prices_memory = {}
if "equity_history" not in st.session_state: 
    st.session_state.equity_history = [{"Idő": datetime.now().strftime("%H:%M:%S"), "Teljes Vagyon": st.session_state.portfolio["balance"]}]

if "paper_persistent" not in st.session_state: st.session_state.paper_persistent = False
if "autotrader_persistent" not in st.session_state: st.session_state.autotrader_persistent = False
if "hide_hold_persistent" not in st.session_state: st.session_state.hide_hold_persistent = False

st.session_state.paper_active = st.session_state.paper_persistent
st.session_state.autotrader_active = st.session_state.autotrader_persistent
st.session_state.hide_hold = st.session_state.hide_hold_persistent

# ---- BIZTONSÁGOS DISCORD WEBHOOK BEOLVASÁS ----
if "discord_webhook" not in st.session_state:
    try: st.session_state.discord_webhook = st.secrets["DISCORD_WEBHOOK"]
    except: st.session_state.discord_webhook = ""

def send_discord_message(message):
    if st.session_state.discord_webhook and st.session_state.discord_webhook.startswith("https://discord.com"):
        payload = {"content": message}
        try: requests.post(st.session_state.discord_webhook, json=payload, timeout=5)
        except: pass

st.session_state["send_discord_message"] = send_discord_message

# --- OPTIMALIZÁLT ADATFELDOLGOZÓ MOTOR ---
def process_indicators(df_ticker):
    if df_ticker.empty or len(df_ticker) < 20: return None
    df_ticker['RSI'] = ta.rsi(close=df_ticker['Close'], length=14)
    df_ticker['SMA_20'] = ta.sma(close=df_ticker['Close'], length=20)
    
    bbands = ta.bbands(close=df_ticker['Close'], length=20, std=2)
    if bbands is not None:
        df_ticker['BBL'], df_ticker['BBU'] = bbands.iloc[:, 0], bbands.iloc[:, 2]
    else:
        df_ticker['BBL'], df_ticker['BBU'] = df_ticker['Close'], df_ticker['Close']

    macd_df = ta.macd(close=df_ticker['Close'], fast=12, slow=26, signal=9)
    if macd_df is not None:
        df_ticker['MACD'], df_ticker['MACD_Signal'] = macd_df.iloc[:, 0], macd_df.iloc[:, 2]
    else:
        df_ticker['MACD'], df_ticker['MACD_Signal'] = 0, 0
        
    df_ticker['Signal'] = "HOLD"
    buy_condition = (df_ticker['RSI'] < 40) & (df_ticker['MACD'] > df_ticker['MACD_Signal']) & (df_ticker['Close'] <= df_ticker['BBL'] * 1.01)
    df_ticker.loc[buy_condition, 'Signal'] = "BUY (VÉTEL)"
    
    sell_condition = (df_ticker['RSI'] > 60) & (df_ticker['MACD'] < df_ticker['MACD_Signal']) | (df_ticker['Close'] >= df_ticker['BBU'] * 0.99)
    df_ticker.loc[sell_condition, 'Signal'] = "SELL (ELADÁS)"
    return df_ticker

def fetch_and_analyze(ticker, period, interval):
    data = yf.download(tickers=ticker, period=period, interval=interval, progress=False, multi_level_index=False)
    if data.empty: return None
    data.columns = [str(col) for col in data.columns]
    return process_indicators(data)

st.session_state["fetch_and_analyze"] = fetch_and_analyze
st.session_state["AVAILABLE_TICKERS"] = AVAILABLE_TICKERS

# --- 🤖 CENTRALIZÁLT HÁTTÉR-MOTOR ---
current_interval = st.session_state.get("live_i", "15m")
current_period = st.session_state.get("live_p", "5d")

try: all_data = yf.download(tickers=AVAILABLE_TICKERS, period=current_period, interval=current_interval, progress=False, group_by='ticker')
except: all_data = None

if all_data is not None and not all_data.empty:
    for ticker in AVAILABLE_TICKERS:
        if ticker not in st.session_state.signals_memory:
            st.session_state.signals_memory[ticker] = {"last_signal": "HOLD", "last_notified_time": "", "last_trade_time": None}

        try:
            if len(AVAILABLE_TICKERS) > 1: bg_data = all_data[ticker].copy()
            else: bg_data = all_data.copy()
            bg_data.columns = [str(col) for col in bg_data.columns]
        except: continue
        
        bg_data_analyzed = process_indicators(bg_data)
        if bg_data_analyzed is not None:
            bg_data_clean = bg_data_analyzed.dropna(subset=['RSI', 'Close', 'MACD'])
            if not bg_data_clean.empty:
                latest_bg_row = bg_data_clean.iloc[-1]
                bg_time = str(bg_data_clean.index[-1]) 
                bg_price = float(latest_bg_row['Close'])
                bg_signal = latest_bg_row['Signal']
                bg_owned = st.session_state.portfolio["shares"].get(ticker, 0)
                
                # Értesítések kezelése
                if bg_signal != "HOLD":
                    if st.session_state.signals_memory[ticker]["last_signal"] != bg_signal and st.session_state.signals_memory[ticker]["last_notified_time"] != bg_time:
                        msg = f"🔔 **AI JELZÉS:** `{ticker}` -> **{bg_signal}** | Ár: `${bg_price:.2f}`"
                        send_discord_message(msg)
                        st.session_state.signals_memory[ticker]["last_signal"] = bg_signal
                        st.session_state.signals_memory[ticker]["last_notified_time"] = bg_time
                else:
                    st.session_state.signals_memory[ticker]["last_signal"] = "HOLD"

                # Kockázatkezelés (Stop-Loss / Take-Profit)
                if st.session_state.paper_persistent and bg_owned > 0:
                    buy_price = st.session_state.buy_prices_memory.get(ticker, bg_price)
                    price_change_pct = ((bg_price - buy_price) / buy_price) * 100
                    current_sl = st.session_state.get("stop_loss_pct", 2.0)
                    current_tp = st.session_state.get("take_profit_pct", 5.0)
                    
                    if price_change_pct <= -current_sl:
                        revenue = bg_owned * bg_price
                        st.session_state.portfolio['balance'] += revenue
                        st.session_state.trade_history.append({"Idő": datetime.now().strftime("%H:%M:%S"), "Ticker": ticker, "Típus": "🚨 STOP-LOSS ELADÁS", "Ár": f"${bg_price:.2f}", "Darab": bg_owned, "Összesen": f"${revenue:.2f}"})
                        save_portfolio_to_disk()
                        save_history_to_disk()
                        send_discord_message(f"🚨 **STOP-LOSS ELADVA!** `{ticker}` Veszteség: `{price_change_pct:.2f}%` | Ár: `${bg_price:.2f}`")
                        st.session_state.portfolio["shares"][ticker] = 0
                        del st.session_state.portfolio["shares"][ticker]
                        if ticker in st.session_state.buy_prices_memory: del st.session_state.buy_prices_memory[ticker]
                        continue

                    elif price_change_pct >= current_tp:
                        revenue = bg_owned * bg_price
                        st.session_state.portfolio['balance'] += revenue
                        st.session_state.trade_history.append({"Idő": datetime.now().strftime("%H:%M:%S"), "Ticker": ticker, "Típus": "💰 TAKE-PROFIT ELADÁS", "Ár": f"${bg_price:.2f}", "Darab": bg_owned, "Összesen": f"${revenue:.2f}"})
                        save_portfolio_to_disk()
                        save_history_to_disk()
                        send_discord_message(f"💰 **TAKE-PROFIT REALIZÁLVA!** `{ticker}` Profit: `+{price_change_pct:.2f}%` | Ár: `${bg_price:.2f}`")
                        st.session_state.portfolio["shares"][ticker] = 0
                        del st.session_state.portfolio["shares"][ticker]
                        if ticker in st.session_state.buy_prices_memory: del st.session_state.buy_prices_memory[ticker]
                        continue

                # Auto-Trader Bot
                if st.session_state.paper_persistent and st.session_state.autotrader_persistent:
                    if st.session_state.signals_memory[ticker]["last_trade_time"] != bg_time:
                        if bg_signal == "BUY (VÉTEL)" and bg_owned == 0:
                            if st.session_state.portfolio['balance'] >= bg_price:
                                st.session_state.portfolio['balance'] -= bg_price
                                st.session_state.portfolio['shares'][ticker] = 1
                                st.session_state.buy_prices_memory[ticker] = bg_price
                                st.session_state.trade_history.append({
                                    "Idő": datetime.now().strftime("%H:%M:%S"), "Ticker": ticker, 
                                    "Típus": "🤖 AUTO-VÉTEL", "Ár": f"\({bg_price:.2f}", "Darab": 1, "Összesen": f"\){bg_price:.2f}"
                                })
                                save_portfolio_to_disk()
                                save_history_to_disk()
                                st.session_state.signals_memory[ticker]["last_trade_time"] = bg_time
                                send_discord_message(f"🤖 **AUTO-TRADER VÉTEL:** 1 db `{ticker}` -> `${bg_price:.2f}`")
                                st.toast(f"🤖 Auto-Trader vett: {ticker}")
                                
                        elif bg_signal == "SELL (ELADÁS)" and bg_owned > 0:
                            revenue = bg_owned * bg_price
                            st.session_state.portfolio['balance'] += revenue
                            st.session_state.trade_history.append({
                                "Idő": datetime.now().strftime("%H:%M:%S"), "Ticker": ticker, 
                                "Típus": "🤖 AUTO-ELADÁS", "Ár": f"\({bg_price:.2f}", "Darab": bg_owned, "Összesen": f"\){revenue:.2f}"
                            })
                            save_portfolio_to_disk()
                            save_history_to_disk()
                            st.session_state.signals_memory[ticker]["last_trade_time"] = bg_time
                            send_discord_message(f"🤖 **AUTO-TRADER ELADÁS:** {bg_owned} db `{ticker}` -> `${bg_price:.2f}`")
                            st.session_state.portfolio["shares"][ticker] = 0
                            del st.session_state.portfolio["shares"][ticker]
                            
                            if ticker in st.session_state.buy_prices_memory: 
                                del st.session_state.buy_prices_memory[ticker]
# --- VAGYONTÖRTÉNET MENTÉSE ---
if st.session_state.paper_persistent:
    calc_shares_value = 0.0
    for t, qty in st.session_state.portfolio["shares"].items():
        if qty > 0:
            try:
                t_df = yf.download(t, period="1d", interval="1m", progress=False, multi_level_index=False)
                if not t_df.empty:
                    t_df.columns = [str(col) for col in t_df.columns]
                    calc_shares_value += qty * float(t_df['Close'].iloc[-1])
            except: 
                pass
                
    total_net_worth = st.session_state.portfolio['balance'] + calc_shares_value
    
    if not st.session_state.equity_history or st.session_state.equity_history[-1]["Teljes Vagyon"] != total_net_worth:
        st.session_state.equity_history.append({
            "Idő": datetime.now().strftime("%H:%M:%S"), 
            "Teljes Vagyon": round(total_net_worth, 2)
        })
# --- MULTI-PAGE RENDSZER ---
page_monitor = st.Page("page_monitor.py", title="📈 Élő Grafikon Monitor", icon="📉")
page_broker = st.Page("page_broker.py", title="🏦 Bróker Számla & Portfólió", icon="💰")
page_scanner = st.Page("page_scanner.py", title="🔍 Többrészes AI Scanner", icon="⚡")
page_prices = st.Page("page_prices.py", title="📊 Ár-Összehasonlító", icon="📊")

pg = st.navigation([page_monitor, page_broker, page_scanner, page_prices])
pg.run()
