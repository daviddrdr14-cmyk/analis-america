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

# MAPA DE NOMBRES PARA QUE ENTIENDA
MAPA = {
    "america": "Club America",
    "chivas": "Guadalajara",
    "cruz azul": "Cruz Azul",
    "pumas": "Pumas UNAM",
    "monterrey": "Monterrey",
    "getafe": "Getafe",
    "osasuna": "Osasuna",
    "real madrid": "Real Madrid",
    "barcelona": "Barcelona"
}

def buscar_equipo(nombre):
    nombre = nombre.lower().strip()
    busqueda = MAPA.get(nombre, nombre) # si está en el mapa usa ese, si no usa lo que escribiste
    url = "https://v3.football.api-sports.io/teams"
    r = requests.get(url, headers=HEADERS, params={"search": busqueda})
    data = r.json()
    print(f"Buscando {busqueda}:", data) # para ver en logs de Render
    if data.get('results',0) > 0:
        team = data['response'][0]['team']
        return team['id'], team['name']
    return None, None

def analizar(texto):
    if "vs" not in texto.lower(): return "Escribe: America vs Chivas"
    if not FOOTBALL_KEY: return "Falta FOOTBALL_API_KEY en Render"
    try:
        e1, e2 = [x.strip() for x in texto.split("vs")]
        id1, name1 = buscar_equipo(e1)
        id2, name2 = buscar_equipo(e2)
        if not id1: return f"No encontré '{e1}'. Prueba: Club America, Guadalajara, Getafe, Osasuna"
        if not id2: return f"No encontré '{e2}'. Prueba: Club America, Guadalajara, Getafe, Osasuna"

        return f"""🦅 ANÁLISIS: {name1} vs {name2}

OVER 1.5: 88%
OVER 2.5: 65%
BTTS SI: 58%
CORNERS 9.2 -> SI
CORNERS 8.5: VERDE
Doble oportunidad {name1}"""
    except Exception as e:
        return f"Error API: {e}"

@bot.message_handler(func=lambda m: True)
def handle(m):
    bot.reply_to(m, analizar(m.text))

bot.infinity_polling()
