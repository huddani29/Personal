# utils.py
import pandas_ta as ta
import numpy as np
from zoneinfo import ZoneInfo
from datetime import datetime

def generate_ai_signal(df):
    """
    Központi AI / Technikai jelzésgeneráló logika a teljes rendszerhez.
    Biztosítja, hogy a Scanner, a Monitor és a Bot ugyanazt a logikát használja.
    """
    if df is None or df.empty or 'Close' not in df.columns:
        return "HOLD", False, False

    # Indikátorok biztosítása
    if 'RSI' not in df.columns:
        df['RSI'] = ta.rsi(close=df['Close'], length=14)
    
    macd_df = ta.macd(close=df['Close'], fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        macd_val = float(macd_df.iloc[-1, 0])
        macd_sig = float(macd_df.iloc[-1, 2])
    else:
        macd_val, macd_sig = 0.0, 0.0

    last_row = df.iloc[-1]
    rsi_val = float(last_row.get('RSI', 50))
    
    # Alap szignál logika (egységesítve)
    sig = "HOLD"
    if rsi_val < 40 and macd_val > macd_sig:
        sig = "BUY (VÉTEL)"
    elif rsi_val > 60:
        sig = "SELL (ELADÁS)"
        
    # Extra prediktív elemek meglétének ellenőrzése
    squeeze = bool(last_row.get('Squeeze', False))
    divergence = bool(last_row.get('Divergence', False))
    
    return sig, squeeze, divergence

def is_market_open_for_trading():
    """
    Ellenőrzi, hogy éppen nyitva van-e az Amerikai vagy Európai tőzsde főszezonja.
    Megakadályozza, hogy az automata bot éjszaka vagy hétvégén kössön.
    """
    now_b = datetime.now(ZoneInfo("Europe/Budapest"))
    c_time = now_b.strftime("%H:%M")
    is_weekday = now_b.weekday() < 5
    
    if not is_weekday:
        return False # Hétvége: zárva
        
    eu_open = "09:00" <= c_time < "17:30"
    usa_active = "15:30" <= c_time < "22:00"
    
    return eu_open or usa_active

def can_open_position(cash_balance, total_portfolio_value, desired_trade_amount, max_share=0.25):
    """
    Kockázatkezelési szűrő: Ellenőrzi, hogy a trade nem lépi-e túl a megengedett portfólió-súlyt.
    Max a tőke 25%-a lehet egyetlen részvényben (konfigurálható).
    """
    if desired_trade_amount > cash_balance:
        return False, "Nincs elegendő szabad készpénz a számlán!"
    
    if desired_trade_amount > (total_portfolio_value * max_share):
        return False, f"Túllépné a megengedett pozíciósúlyt (Max {int(max_share*100)}% / részvény)!"
        
    return True, "OK"