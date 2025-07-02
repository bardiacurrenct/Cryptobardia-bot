import requests
import pandas as pd
import ta

# Fetch historical data from Binance
def get_klines(symbol="BTCUSDT", interval="15m", limit=250):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "num_trades",
        "taker_base", "taker_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

# Calculate indicators
def analyze(df):
    if df.empty:
        return df

    df["ema20"] = ta.trend.EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema50"] = ta.trend.EMAIndicator(close=df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
    macd = ta.trend.MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    return df.dropna()

# Generate signal with confidence and strength
def generate_signal(df):
    if df.empty:
        return None, [], 0

    last = df.iloc[-1]
    score = 0
    reasons = []

    if last["ema20"] > last["ema50"]:
        score += 1
        reasons.append("EMA20 > EMA50 (trend up)")

    if last["macd"] > last["macd_signal"]:
        score += 1
        reasons.append("MACD > Signal (momentum up)")

    if 40 < last["rsi"] < 75:
        score += 1
        reasons.append("RSI in bullish zone")

    if score >= 2:
        signal_type = "LONG"
        confidence = int((score / 3) * 100)
        signal_strength = "Strong" if score == 3 else "Weak"
        signal = f"{signal_strength} {signal_type}"
        return signal, reasons, confidence

    # Check for SHORT signal
    score = 0
    reasons = []

    if last["ema20"] < last["ema50"]:
        score += 1
        reasons.append("EMA20 < EMA50 (trend down)")

    if last["macd"] < last["macd_signal"]:
        score += 1
        reasons.append("MACD < Signal (momentum down)")

    if last["rsi"] < 60:
        score += 1
        reasons.append("RSI in bearish zone")

    if score >= 2:
        signal_type = "SHORT"
        confidence = int((score / 3) * 100)
        signal_strength = "Strong" if score == 3 else "Weak"
        signal = f"{signal_strength} {signal_type}"
        return signal, reasons, confidence

    return None, [], 0
