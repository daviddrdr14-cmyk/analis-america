from flask import Flask
import threading, os, telebot, requests

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot funcionando todas las ligas!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
FOOTBALL_KEY = os.environ.get("FOOTBALL_API_KEY")
bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"x-apisports-key": FOOTBALL_KEY}

MAPA = {
    "america": "America",
    "chivas": "Guadalajara",
    "boca": "Boca Juniors",
    "river": "River Plate",
    "real madrid": "Real Madrid",
    "barcelona": "Barcelona",
    "getafe": "Getafe",
    "osasuna": "Osasuna",
    "west ham": "West Ham",
    "wolves": "Wolves",
    "arsenal": "Arsenal",
    "liverpool": "Liverpool"
}

def buscar_equipo(nombre):
    nombre = nombre.lower().strip()
    busqueda = MAPA.get(nombre, nombre)
    r = requests.get("https://v3.football.api-sports.io/teams", headers=HEADERS, params={"search": busqueda}, timeout=15)
    data = r.json()
    if data.get("results", 0) > 0:
        team = data["response"][0]["team"]
        return team["id"], team["name"]
    return None, None

def get_stats_universal(equipo_id):
    ligas = [39, 140, 128, 262]
    temporadas = [2023, 2024]
    for liga in ligas:
        for temp in temporadas:
            try:
                r = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params={"team": equipo_id, "league": liga, "season": temp}, timeout=15)
                fixtures = r.json().get("response", [])
                if len(fixtures) < 3:
                    continue
                fixtures = fixtures[-5:]
                goles = 0
                btts = 0
                for f in fixtures:
                    gh = f["goals"]["home"] or 0
                    ga = f["goals"]["away"] or 0
                    goles = goles + gh + ga
                    if gh > 0 and ga > 0:
                        btts = btts + 1
                prom = round(goles / len(fixtures), 2)
                btts_pct = int((btts / len(fixtures)) * 100)
                print(f"OK {equipo_id} liga {liga} prom {prom}")
                return prom, btts_pct
            except:
                continue
    return 2.2, 55

def analizar(texto):
    txt = texto.lower().replace(" s ", " vs ")
    if "vs" not in txt:
        return "Escribe: America vs Chivas"
    try:
        e1, e2 = [x.strip() for x in txt.split("vs", 1)]
        id1, name1 = buscar_equipo(e1)
        id2, name2 = buscar_equipo(e2)
        if not id1:
            return f"No encontre {e1}"
        if not id2:
            return f"No encontre {e2}"
        prom1, btts1 = get_stats_universal(id1)
        prom2, btts2 = get_stats_universal(id2)
        over15 = 85
        if prom1 + prom2 < 2.5:
            over15 = 70
        over25 = 68
        if prom1 + prom2 < 3.0:
            over25 = 50
        btts_final = int((btts1 + btts2) / 2)
        return f"ANALISIS: {name1} vs {name2}\nProm gol: {prom1} vs {prom2}\nOVER 1.5: {over15}%\nOVER 2.5: {over25}%\nBTTS SI: {btts_final}%\nCORNERS 8.5: VERDE"
    except Exception as e:
        return f"Error: {e}"

@bot.message_handler(func=lambda m: True)
def handle(m):
    bot.reply_to(m, analizar(m.text))

bot.infinity_polling()
