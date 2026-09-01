from flask import Flask
import threading
import os
import telebot
import requests

# --- SERVIDOR PARA RENDER ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot America funcionando! 🦅"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
threading.Thread(target=run_flask).start()

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
FOOTBALL_KEY = os.environ.get("FOOTBALL_API_KEY") # <--- TIENES QUE AGREGAR ESTA VARIABLE EN RENDER

bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"x-apisports-key": FOOTBALL_KEY}

def buscar_equipo(nombre):
    url = "https://v3.football.api-sports.io/teams"
    r = requests.get(url, headers=HEADERS, params={"search": nombre})
    data = r.json()
    if data['results'] > 0:
        return data['response'][0]['team']['id'], data['response'][0]['team']['name']
    return None, None

def analizar_partido(texto):
    try:
        if "vs" not in texto.lower():
            return "Escribe así: America vs Monterrey"
        equipo1, equipo2 = [x.strip() for x in texto.lower().split("vs")]
        id1, name1 = buscar_equipo(equipo1)
        id2, name2 = buscar_equipo(equipo2)

        if not id1 or not id2:
            return f"No encontré {texto}, verifica nombres"

        # Estadísticas simples de ejemplo - aquí va tu lógica real de corners
        # Puedes mejorar esto con más endpoints
        return f"""🦅 ANÁLISIS: {name1} vs {name2}

📊 ESTIMADO:
OVER 1.5: 85%
OVER 2.5: 62%
BTTS: 55%
CORNERS 9.2
CORNERS 8.5: SI
CORNERS 9.5: PROBABLE

⚽️ Ambos anotan y corners altas.
¡Aguante América!"""
    except Exception as e:
        return f"Error: {e}"

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🦅 Bot América listo!\nEscribe: America vs Monterrey\nO: Getafe vs Osasuna")

@bot.message_handler(func=lambda m: True)
def handle(m):
    res = analizar_partido(m.text)
    bot.reply_to(m, res)

print("Bot iniciado...")
bot.infinity_polling()
