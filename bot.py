from flask import Flask
import threading, os, telebot, requests

app = Flask(__name__)
@app.route('/')
def home(): return "Bot America funcionando! 🦅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
threading.Thread(target=run_flask).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
FOOTBALL_KEY = os.environ.get("FOOTBALL_API_KEY")
bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"x-apisports-key": FOOTBALL_KEY}

# MAPA COMPLETO PARA TODAS LAS LIGAS
MAPA = {
    # MEXICO
    "america": "Club America", "chivas": "Guadalajara", "guadalajara": "Guadalajara",
    "cruz azul": "Cruz Azul", "pumas": "Pumas UNAM", "monterrey": "Monterrey",
    "tigres": "Tigres UANL", "toluca": "Toluca", "leon": "Leon", "santos": "Santos Laguna",
    # ARGENTINA - LIGA ARGENTINA
    "boca": "Boca Juniors", "boca juniors": "Boca Juniors", "river": "River Plate",
    "river plate": "River Plate", "racing": "Racing Club", "racing club": "Racing Club",
    "independiente": "Independiente", "san lorenzo": "San Lorenzo", "talleres": "Talleres Cordoba",
    "estudiantes": "Estudiantes La Plata", "velez": "Velez Sarsfield", "argentinos": "Argentinos Juniors",
    "lanus": "Lanus", "rosario": "Rosario Central", "newells": "Newells Old Boys",
    # ESPAÑA - LA LIGA
    "real madrid": "Real Madrid", "real": "Real Madrid", "barcelona": "Barcelona", "barca": "Barcelona",
    "atletico": "Atletico Madrid", "atletico madrid": "Atletico Madrid", "atleti
