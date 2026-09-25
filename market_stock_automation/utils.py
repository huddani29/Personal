# utils.py
import pandas_ta as ta
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo
from datetime import datetime
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

def generate_ai_signal(df):
    """
    Központi AI / Technikai jelzésgeneráló logika a teljes rendszerhez.
    """
    if df is None or df.empty or 'Close' not in df.columns:
        return "HOLD", False, False

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
    
    sig = "HOLD"
    if rsi_val < 40 and macd_val > macd_sig:
        sig = "BUY (VÉTEL)"
    elif rsi_val > 60:
        sig = "SELL (ELADÁS)"
        
    squeeze = bool(last_row.get('Squeeze', False))
    divergence = bool(last_row.get('Divergence', False))
    
    return sig, squeeze, divergence

def calculate_ichimoku(df):
    """
    Kiszámítja az Ichimoku Cloud indikátort a pandas_ta segítségével.
    """
    if df is None or df.empty:
        return df
    
    # pandas_ta ichimoku hívás
    ichimoku_df, span_df = ta.ichimoku(df['High'], df['Low'], df['Close'], tenkan=9, kijun=26, senkou=52)
    if ichimoku_df is not None and not ichimoku_df.empty:
        df = pd.concat([df, ichimoku_df], axis=1)
    return df

def run_ml_price_prediction(df):
    """
    Gépi tanulásos (Machine Learning) árbecslő modell Ridge regresszióval.
    Megbecsüli a következő időszak záróárát a múltbeli adatok és indikátorok alapján.
    """
    if df is None or len(df) < 50:
        return None, 0.0, "Nincs elég adat a ML modell betanításához (min. 50 sor szükséges)."

    work_df = df.copy()
    # Feature-ök építése
    work_df['Returns'] = work_df['Close'].pct_change()
    work_df['SMA_5'] = work_df['Close'].rolling(5).mean()
    work_df['SMA_20'] = work_df['Close'].rolling(20).mean()
    if 'RSI' not in work_df.columns:
        work_df['RSI'] = ta.rsi(close=work_df['Close'], length=14)
        
    work_df = work_df.dropna()
    if len(work_df) < 20:
        return None, 0.0, "Nem maradt elegendő adat az adatszűrés után."

    features = ['Returns', 'SMA_5', 'SMA_20', 'RSI', 'Volume'] if 'Volume' in work_df.columns else ['Returns', 'SMA_5', 'SMA_20', 'RSI']
    
    X = work_df[features].values
    # Cél: a következő nap / periódus záróára
    y = work_df['Close'].shift(-1).dropna().values
    X = X[:-1] # Igazítjuk a hosszokat

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = Ridge(alpha=1.0)
    model.fit(X_scaled, y)

    # Predikció a legfrissebb adatsorra
    latest_features = scaler.transform(X[-1].reshape(1, -1))
    predicted_price = float(model.predict(latest_features)[0])
    current_price = float(work_df['Close'].iloc[-1])
    
    return predicted_price, current_price, "Sikeres ML becslés"

def is_market_open_for_trading():
    now_b = datetime.now(ZoneInfo("Europe/Budapest"))
    c_time = now_b.strftime("%H:%M")
    is_weekday = now_b.weekday() < 5
    if not is_weekday:
        return False
    eu_open = "09:00" <= c_time < "17:30"
    usa_active = "15:30" <= c_time < "22:00"
    return eu_open or usa_active

def can_open_position(cash_balance, total_portfolio_value, desired_trade_amount, max_share=0.25):
    if desired_trade_amount > cash_balance:
        return False, "Nincs elegendő szabad készpénz a számlán!"
    if desired_trade_amount > (total_portfolio_value * max_share):
        return False, f"Túllépné a megengedett pozíciósúlyt (Max {int(max_share*100)}% / részvény)!"
    return True, "OK"

def get_currency_symbol(ticker: str) -> str:
    """Visszaadja a ticker alapján a megfelelő valutajelzést vagy kódot."""
    ticker_upper = ticker.upper()
    if ".BD" in ticker_upper or ".BU" in ticker_upper:
        return "HUF"
    elif ".AS" in ticker_upper or ".DE" in ticker_upper or ".F" in ticker_upper:
        return "EUR"
    elif "-USD" in ticker_upper:
        return "USD"
    else:
        # Alapértelmezett, ha amerikai részvény vagy nincs specifikus utótag
        return "USD"

def format_price(price: float, currency: str) -> str:
    """Szépen formázza az árat a valuta függvényében."""
    if currency == "HUF":
        return f"{price:,.0f} Ft"  # Forintnál általában nem kell tizedesjegy
    elif currency == "EUR":
        return f"€{price:,.2f}"
    else:
        return f"${price:,.2f}"