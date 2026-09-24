import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

# Globális oldalbeállítás - MINDENNEK a legtetején kell lennie!
st.set_page_config(page_title="AI Tőzsde Központ Pro", layout="wide", page_icon="📊")

# --- TARTÓS FÁJLMENTÉS (ADATBÁZISOK) ---
PORTFOLIO_FILE = "portfolio_db.json"
HISTORY_FILE = "trade_history_db.csv"
TICKERS_FILE = "tickers_db.json"

DEFAULT_TICKERS = ["TSLA", "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "AMD", "COIN", "NIO", "PLTR", "SOFI", "IWDA.AS", "EMIM.AS", "UST"]

if "AVAILABLE_TICKERS" not in st.session_state:
    if os.path.exists(TICKERS_FILE):
        try:
            with open(TICKERS_FILE, "r") as f: st.session_state.AVAILABLE_TICKERS = json.load(f)
        except: st.session_state.AVAILABLE_TICKERS = DEFAULT_TICKERS.copy()
    else: st.session_state.AVAILABLE_TICKERS = DEFAULT_TICKERS.copy()

if "portfolio" not in st.session_state:
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f: st.session_state.portfolio = json.load(f)
        except: st.session_state.portfolio = {"balance": 10000.0, "shares": {}}
    else: st.session_state.portfolio = {"balance": 10000.0, "shares": {}}

if "trade_history" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            st.session_state.trade_history = pd.read_csv(HISTORY_FILE).to_dict(orient="records")
        except:
            st.session_state.trade_history = []
    else:
        st.session_state.trade_history = []


def save_portfolio_to_disk():
    with open(PORTFOLIO_FILE, "w") as f: json.dump(st.session_state.portfolio, f)

def save_history_to_disk():
    if st.session_state.trade_history: pd.DataFrame(st.session_state.trade_history).to_csv(HISTORY_FILE, index=False)

def save_tickers_to_disk():
    with open(TICKERS_FILE, "w") as f: json.dump(st.session_state.AVAILABLE_TICKERS, f)

st.session_state["save_portfolio_to_disk"] = save_portfolio_to_disk
st.session_state["save_history_to_disk"] = save_history_to_disk
st.session_state["save_tickers_to_disk"] = save_tickers_to_disk

if "signals_memory" not in st.session_state: st.session_state.signals_memory = {}
if "buy_prices_memory" not in st.session_state: st.session_state.buy_prices_memory = {}
if "equity_history" not in st.session_state: st.session_state.equity_history = [{"Idő": datetime.now(ZoneInfo("Europe/Budapest")).strftime("%H:%M:%S"), "Teljes Vagyon": st.session_state.portfolio["balance"]}]
if "last_market_phases" not in st.session_state: st.session_state.last_market_phases = {"EU": "", "USA": ""}
if "last_network_fetch_time" not in st.session_state: st.session_state.last_network_fetch_time = 0
if "cached_all_data" not in st.session_state: st.session_state.cached_all_data = None

if "paper_persistent" not in st.session_state: st.session_state.paper_persistent = False
if "autotrader_persistent" not in st.session_state: st.session_state.autotrader_persistent = False
if "hide_hold_persistent" not in st.session_state: st.session_state.hide_hold_persistent = False

st.session_state.paper_active = st.session_state.paper_persistent
st.session_state.autotrader_active = st.session_state.autotrader_persistent
st.session_state.hide_hold = st.session_state.hide_hold_persistent

if "discord_webhook" not in st.session_state:
    try: st.session_state.discord_webhook = st.secrets["DISCORD_WEBHOOK"]
    except: st.session_state.discord_webhook = ""

def send_discord_message(message):
    if st.session_state.discord_webhook and st.session_state.discord_webhook.startswith("https://discord.com"):
        payload = {"content": message}
        try: requests.post(st.session_state.discord_webhook, json=payload, timeout=5)
        except: pass

st.session_state["send_discord_message"] = send_discord_message

# --- ⏱️ PIACFAZISOK ---
def get_market_phases():
    now_budapest = datetime.now(ZoneInfo("Europe/Budapest"))
    current_time_str = now_budapest.strftime("%H:%M")
    is_weekday = now_budapest.weekday() < 5
    eu_phase, usa_phase = "ZÁRVA 🔴", "ZÁRVA 🔴"
    if is_weekday:
        if "09:00" <= current_time_str < "17:30": eu_phase = "NYITVA (Kereskedés) 🟢"
        if "15:30" <= current_time_str < "16:30": usa_phase = "NYITÓ ŐRÜLET 🚀"
        elif "16:30" <= current_time_str < "19:30": usa_phase = "EBÉDSZÜNET (Oldalazás) ☕"
        elif "19:30" <= current_time_str < "22:00": usa_phase = "ZÁRÓ HAJRÁ 🏁"
    return eu_phase, usa_phase

eu_now, usa_now = get_market_phases()

if eu_now != st.session_state.last_market_phases["EU"]:
    send_discord_message(f"🇪🇺 **EURÓPAI PIAC ÁLLAPOT VÁLTOZÁS:** `{eu_now}`")
    st.session_state.last_market_phases["EU"] = eu_now

if usa_now != st.session_state.last_market_phases["USA"]:
    send_discord_message(f"🇺🇸 **AMERIKAI PIAC ÁLLAPOT VÁLTOZÁS:** `{usa_now}`")
    st.session_state.last_market_phases["USA"] = usa_now

# --- OPTIMALIZÁLT INDIKÁTOR MOTOR ---
def process_indicators(df_ticker):
    if df_ticker.empty or len(df_ticker) < 20: return None
    try:
        df_ticker['RSI'] = ta.rsi(close=df_ticker['Close'], length=14)
        df_ticker['SMA_20'] = ta.sma(close=df_ticker['Close'], length=20)
        bbands = ta.bbands(close=df_ticker['Close'], length=20, std=2)
        if bbands is not None: df_ticker['BBL'], df_ticker['BBU'] = bbands.iloc[:, 0], bbands.iloc[:, 2]
        else: df_ticker['BBL'], df_ticker['BBU'] = df_ticker['Close'], df_ticker['Close']
        macd_df = ta.macd(close=df_ticker['Close'], fast=12, slow=26, signal=9)
        if macd_df is not None: df_ticker['MACD'], df_ticker['MACD_Signal'] = macd_df.iloc[:, 0], macd_df.iloc[:, 2]
        else: df_ticker['MACD'], df_ticker['MACD_Signal'] = 0, 0
            
        df_ticker['Signal'] = "HOLD"
        buy_condition = (df_ticker['RSI'] < 40) & (df_ticker['MACD'] > df_ticker['MACD_Signal']) & (df_ticker['Close'] <= df_ticker['BBL'] * 1.01)
        df_ticker.loc[buy_condition, 'Signal'] = "BUY (VÉTEL)"
        sell_condition = (df_ticker['RSI'] > 60) & (df_ticker['MACD'] < df_ticker['MACD_Signal']) | (df_ticker['Close'] >= df_ticker['BBU'] * 0.99)
        df_ticker.loc[sell_condition, 'Signal'] = "SELL (ELADÁS)"
        return df_ticker
    except: return None

def fetch_and_analyze(ticker, period, interval):
    # Biztonsági hálózati időkorlát (timeout=3 mp), hogy ha a Yahoo tilt, ne fagyassza le az oldalt!
    try:
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False, multi_level_index=False, timeout=3)
        if data.empty: return None
        data.columns = [str(col) for col in data.columns]
        return process_indicators(data)
    except: return None

st.session_state["fetch_and_analyze"] = fetch_and_analyze

# --- 🤖 FAGYÁSBIZTOS HÁTTÉR-MOTOR ---
current_interval = st.session_state.get("live_i", "15m")
current_period = st.session_state.get("live_p", "5d")
current_time_now = time.time()

if st.session_state.AVAILABLE_TICKERS:
    # Csak 180 másodpercenként (3 perc) engedünk új hálózati kérést a letiltás ellen
    if st.session_state.cached_all_data is None or (current_time_now - st.session_state.last_network_fetch_time) > 180:
        try:
            # Maximális várakozási időkorlát bevezetése (timeout=5)
            st.session_state.cached_all_data = yf.download(tickers=st.session_state.AVAILABLE_TICKERS, period=current_period, interval=current_interval, progress=False, group_by='ticker', timeout=5)
            st.session_state.last_network_fetch_time = current_time_now
        except: pass

    all_data = st.session_state.cached_all_data

    # Ha van adatunk, feldolgozzuk, ha hálózati hiba van, csendben átugorjuk (Nincs fagyás!)
    if all_data is not None and not all_data.empty:
        for ticker in st.session_state.AVAILABLE_TICKERS:
            if ticker not in st.session_state.signals_memory:
                st.session_state.signals_memory[ticker] = {"last_signal": "HOLD", "last_notified_time": "", "last_trade_time": None}

            try:
                if len(st.session_state.AVAILABLE_TICKERS) > 1: bg_data = all_data[ticker].copy()
                else: bg_data = all_data.copy()
                bg_data.columns = [str(col) for col in bg_data.columns]
            except: continue
            
            bg_data_analyzed = process_indicators(bg_data)
            if bg_data_analyzed is not None:
                bg_data_clean = bg_data_analyzed.dropna(subset=['RSI', 'Close'])
                if not bg_data_clean.empty:
                    latest_bg_row = bg_data_clean.iloc[-1]
                    bg_time = str(bg_data_clean.index[-1]) 
                    bg_price = float(latest_bg_row['Close'])
                    bg_signal = latest_bg_row['Signal']
                    bg_owned = st.session_state.portfolio["shares"].get(ticker, 0)
                    
                    if bg_signal != "HOLD":
                        if st.session_state.signals_memory[ticker]["last_signal"] != bg_signal and st.session_state.signals_memory[ticker]["last_notified_time"] != bg_time:
                            msg = f"🔔 **AI JELZÉS:** `{ticker}` -> **{bg_signal}** | Ár: `${bg_price:.2f}`"
                            send_discord_message(msg)
                            st.session_state.signals_memory[ticker]["last_signal"] = bg_signal
                            st.session_state.signals_memory[ticker]["last_notified_time"] = bg_time
                    else:
                        st.session_state.signals_memory[ticker]["last_signal"] = "HOLD"

                    # --- 1. KOCKÁZATKEZELÉS (STOP-LOSS / TAKE-PROFIT) ---
                    # JAVÍTÁS: Elsőként a feltételeken kívül kiszámítjuk a százalékos elmozdulást, hogy MINDIG létezzen a változó!
                    buy_price = st.session_state.buy_prices_memory.get(ticker, bg_price)
                    price_change_pct = ((bg_price - buy_price) / buy_price) * 100
                    current_sl = st.session_state.get("stop_loss_pct", 2.0)
                    current_tp = st.session_state.get("take_profit_pct", 5.0)

                    # Csak akkor futtatjuk le a Stop-Loss/Take-Profit eladást, ha valóban van nyitott pozíciónk
                    if st.session_state.paper_persistent and bg_owned > 0:
                        # A) STOP-LOSS AUTOMATIKUS KIVÁLTÁS
                        if price_change_pct <= -current_sl:
                            revenue = bg_owned * bg_price
                            st.session_state.portfolio['balance'] += revenue
                            st.session_state.trade_history.append({"Idő": datetime.now(ZoneInfo("Europe/Budapest")).strftime("%H:%M:%S"), "Ticker": ticker, "Típus": "🚨 STOP-LOSS ELADÁS", "Ár": f"${bg_price:.2f}", "Darab": bg_owned, "Összesen": f"${revenue:.2f}"})
                            save_portfolio_to_disk()
                            save_history_to_disk()
                            send_discord_message(f"🚨 **STOP-LOSS ELADVA!** {ticker} {price_change_pct:.2f}% | Ár: ${bg_price:.2f}")
                            st.session_state.portfolio["shares"][ticker] = 0
                            del st.session_state.portfolio["shares"][ticker]
                            if ticker in st.session_state.buy_prices_memory: del st.session_state.buy_prices_memory[ticker]
                            continue

                        # B) TAKE-PROFIT AUTOMATIKUS KIVÁLTÁS
                        elif price_change_pct >= current_tp:
                            revenue = bg_owned * bg_price
                            st.session_state.portfolio['balance'] += revenue
                            st.session_state.trade_history.append({"Idő": datetime.now(ZoneInfo("Europe/Budapest")).strftime("%H:%M:%S"), "Ticker": ticker, "Típus": "💰 TAKE-PROFIT ELADÁS", "Ár": f"${bg_price:.2f}", "Darab": bg_owned, "Összesen": f"${revenue:.2f}"})
                            save_portfolio_to_disk()
                            save_history_to_disk()
                            send_discord_message(f"💰 **TAKE-PROFIT REALIZÁLVA!** {ticker} +{price_change_pct:.2f}% | Ár: ${bg_price:.2f}")
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
                                st.session_state.trade_history.append({"Idő": datetime.now(ZoneInfo("Europe/Budapest")).strftime("%H:%M:%S"), "Ticker": ticker, "Típus": "🤖 AUTO-VÉTEL", "Ár": f"${bg_price:.2f}", "Darab": 1, "Összesen": f"${bg_price:.2f}"})
                                
                                save_portfolio_to_disk()
                                save_history_to_disk()
                                
                                st.session_state.signals_memory[ticker]["last_trade_time"] = bg_time
                                send_discord_message(f"🤖 **AUTO-TRADER VÉTEL:** 1 db {ticker} -> ${bg_price:.2f}")
                                st.toast(f"🤖 Auto-Trader vett: {ticker}")
                                
                        elif bg_signal == "SELL (ELADÁS)" and bg_owned > 0:
                            revenue = bg_owned * bg_price
                            st.session_state.portfolio['balance'] += revenue
                            st.session_state.trade_history.append({"Idő": datetime.now(ZoneInfo("Europe/Budapest")).strftime("%H:%M:%S"), "Ticker": ticker, "Típus": "🤖 AUTO-ELADÁS", "Ár": f"${bg_price:.2f}", "Darab": bg_owned, "Összesen": f"${revenue:.2f}"})
                            
                            save_portfolio_to_disk()
                            save_history_to_disk()
                            
                            st.session_state.signals_memory[ticker]["last_trade_time"] = bg_time
                            send_discord_message(f"🤖 **AUTO-TRADER ELADÁS:** {bg_owned} db {ticker} -> ${bg_price:.2f}")
                            st.session_state.portfolio["shares"][ticker] = 0
                            del st.session_state.portfolio["shares"][ticker]
                            if ticker in st.session_state.buy_prices_memory: del st.session_state.buy_prices_memory[ticker]
# --- VAGYONTÖRTÉNET MENTÉSE ---
if st.session_state.paper_persistent and 'all_data' in locals() and all_data is not None and not all_data.empty:
    calc_shares_value = 0.0
    for t, qty in st.session_state.portfolio["shares"].items():
        if qty > 0:
            try:
                if isinstance(all_data.columns, pd.MultiIndex):
                    if t in all_data.columns.levels[0]: 
                        calc_shares_value += qty * float(all_data[t]['Close'].dropna().iloc[-1])
                else:
                    if t in all_data.columns: 
                        calc_shares_value += qty * float(all_data['Close'].dropna().iloc[-1])
            except: 
                pass
                
    total_net_worth = st.session_state.portfolio['balance'] + calc_shares_value
    
    if not st.session_state.equity_history or st.session_state.equity_history[-1]["Teljes Vagyon"] != total_net_worth:
        st.session_state.equity_history.append({
            "Idő": datetime.now(ZoneInfo("Europe/Budapest")).strftime("%H:%M:%S"), 
            "Teljes Vagyon": round(total_net_worth, 2)
        })
# --- MULTI-PAGE RENDSZER ---
page_monitor = st.Page("page_monitor.py", title="📈 Élő Grafikon Monitor", icon="📉")
page_broker = st.Page("page_broker.py", title="🏦 Bróker Számla & Portfólió", icon="💰")
page_scanner = st.Page("page_scanner.py", title="🔍 Többrészes AI Scanner", icon="⚡")
page_prices = st.Page("page_prices.py", title="📊 Ár-Összehasonlító", icon="📊")
page_config = st.Page("page_config.py", title="⚙️ Figyelt Részvények Beállítása", icon="⚙️")
page_top10 = st.Page("page_top10.py", title="🏆 TOP 10 Nyertes & Vesztes", icon="🏆")
page_news = st.Page("page_news.py", title="📰 AI Gazdasági Híradó", icon="📰")

pg = st.navigation([page_monitor, page_broker, page_scanner, page_prices, page_top10, page_news, page_config])
pg.run()
