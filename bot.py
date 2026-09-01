from flask import Flask
import threading
import os
import telebot
import pandas as pd
import requests

# --- SERVIDOR FALSO PARA RENDER FREE ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot America funcionando! 🦅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()
# --- FIN SERVIDOR ---

# --- TU BOT ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: No hay BOT_TOKEN en las variables de Render")
else:
    bot = telebot.TeleBot(BOT_TOKEN)

    @bot.message_handler(commands=['start', 'help'])
    def start(message):
        bot.reply_to(message, "¡Hola Águila! 🦅💛\nSoy tu bot del América.\nUsa /analisis para analizar")

    @bot.message_handler(commands=['analisis'])
    def analisis(message):
        bot.reply_to(message, "Aquí va tu análisis del América... (aquí pones tu lógica)")

    @bot.message_handler(func=lambda m: True)
    def echo(message):
        bot.reply_to(message, f"Recibí: {message.text} 🦅")

    print("Bot iniciado...")
    bot.infinity_polling()
