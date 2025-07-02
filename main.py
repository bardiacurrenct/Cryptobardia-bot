from flask import Flask
from threading import Thread
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    JobQueue
)
from analyzer import get_klines, analyze, generate_signal

# Bot credentials
BOT_TOKEN = "7759661638:AAFgDptQJPX_i7snlrG9cq8EHUq_Z19hzrg"
CHAT_ID = 7361896149

# Flask server for uptime
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is alive and running."

def run():
    flask_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run)
    thread.start()

# /start command with keyboard
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["/start", "/price", "/signal"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🚀 Crypto Signal Bot is active and ready.\nTap a command below:",
        reply_markup=reply_markup
    )

# /price command
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
        data = requests.get(url).json()
        btc = data["bitcoin"]["usd"]
        eth = data["ethereum"]["usd"]
        msg = f"💰 Current Prices:\n• BTC: ${btc}\n• ETH: ${eth}"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching price: {e}")

# /signal command
async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_signals(context, manual=True, reply_func=update.message.reply_text)

# Signal logic
async def send_signals(context, manual=False, reply_func=None):
    symbols = ["BTCUSDT", "ETHUSDT"]
    for symbol in symbols:
        try:
            df = get_klines(symbol, "15m", 250)
            df = analyze(df)
            if df.empty:
                msg = f"{symbol}: No data available after analysis."
                if reply_func:
                    await reply_func(msg)
                continue

            signal, reasons, confidence = generate_signal(df)
            print(f"{symbol} → {signal or 'No Signal'} ({confidence}%)")

            if signal:
                price = df["close"].iloc[-1]
                message = (
                    f"📊 *Signal Alert*: *{symbol}* (15m)\n\n"
                    f"🔹 *Type*: {signal}\n"
                    f"🔹 *Confidence*: {confidence}%\n"
                    f"🔹 *Entry*: {price:.2f} USDT\n"
                    f"🔹 *Targets*:\n"
                    f"• TP1: {price * 1.004:.2f}\n"
                    f"• TP2: {price * 1.008:.2f}\n"
                    f"• TP3: {price * 1.012:.2f}\n"
                    f"🛑 *Stop Loss*: {price * 0.995:.2f}\n\n"
                    f"🧠 *Reasons*:\n" + "\n".join(f"• {r}" for r in reasons)
                )

                if manual and reply_func:
                    await reply_func(message, parse_mode='Markdown')
                elif not manual:
                    await context.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
            else:
                if manual and reply_func:
                    await reply_func(f"{symbol}: No valid signal at the moment ⚖️")
        except Exception as e:
            error_msg = f"{symbol}: Error during analysis → {e}"
            if manual and reply_func:
                await reply_func(error_msg)
            else:
                print(error_msg)

# Launch bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))

    keep_alive()

    job_queue: JobQueue = app.job_queue
    job_queue.run_repeating(lambda context: send_signals(context, manual=False), interval=900, first=10)

    app.run_polling()
