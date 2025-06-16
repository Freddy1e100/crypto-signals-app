import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import ta
import datetime
import os
import telegram
from io import BytesIO
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
bot = telegram.Bot(token=TELEGRAM_TOKEN)

def fetch_data(symbol: str, interval="1h", lookback="3 day"):
    klines = client.get_historical_klines(symbol, interval, lookback)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "Open", "High", "Low", "Close", "Volume", "Close_time",
        "Quote_asset_volume", "Number_of_trades", "Taker_buy_base_volume",
        "Taker_buy_quote_volume", "Ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    df.set_index("timestamp", inplace=True)
    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    return df

def analyze(df):
    df["EMA50"] = ta.trend.ema_indicator(df["Close"], window=50)
    df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
    stoch_rsi = ta.momentum.StochRSIIndicator(df["Close"], window=14)
    df["StochRSI"] = stoch_rsi.stochrsi()
    latest = df.iloc[-1]

    if latest["Close"] > latest["EMA50"] and latest["RSI"] > 50 and latest["StochRSI"] > 0.8:
        return "LONG", latest
    elif latest["Close"] < latest["EMA50"] and latest["RSI"] < 50 and latest["StochRSI"] < 0.2:
        return "SHORT", latest
    return "NO SIGNAL", latest

def plot_chart(df, symbol):
    fig, ax = plt.subplots(figsize=(10, 4))
    df["Close"].plot(ax=ax, label="Close Price")
    df["EMA50"].plot(ax=ax, label="EMA50")
    ax.set_title(f"{symbol} - Close & EMA50")
    ax.legend()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf

def send_telegram_message(symbol, signal, price, chart_img):
    message = f"""📈 *{symbol}*
✅ Сигнал: *{signal}*
💰 Цена входа: *{price:.2f}*
⏱️ Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
📍 Стоп/тейк: Стоп: -2%, Тейк: +4%"""
    bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=chart_img, caption=message, parse_mode="Markdown")

st.title("📈 Крипто-сигналы (Binance)")
st.write("Получай простые технические сигналы по ключевым парам.")

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "PAXGUSDT"]

for symbol in symbols:
    st.subheader(symbol.replace("USDT", "/USDT"))
    try:
        df = fetch_data(symbol)
        signal, latest = analyze(df)
        st.image(plot_chart(df, symbol), caption=symbol)
        st.markdown(f"✅ **Сигнал:** {signal}")
        st.markdown(f"💰 **Цена входа:** {latest['Close']:.2f}")
        st.markdown(f"⏱️ **Время сигнала:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.markdown(f"📍 **Стоп/Тейк:** Стоп: -2%, Тейк: +4%")
        if signal != "NO SIGNAL":
            chart_img = plot_chart(df, symbol)
            send_telegram_message(symbol, signal, latest['Close'], chart_img)
    except Exception as e:
        st.error(f"Ошибка: {e}")
