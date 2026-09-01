from flask import Flask
import threading, os, telebot, requests

app = Flask(__name__)
@app.route('/')
def home(): return "Bot funcionando todas las ligas!"

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
    "racing": "Racing Club",
    "independiente": "Independiente",
    "san lorenzo": "San Lorenzo",
    "talleres": "Talleres",
    "real madrid": "Real Madrid",
    "barcelona": "Barcelona",
    "atletico": "Atletico Madrid",
    "sevilla": "Sevilla",
    "betis": "Real Betis",
    "getafe": "Getafe",
    "osasuna": "Osasuna",
    "valencia": "Valencia",
    "villarreal": "Villarreal",
    "west ham": "West Ham",
    "wolves": "Wolves",
    "arsenal": "Arsenal",
    "chelsea": "Chelsea",
    "liverpool": "Liverpool",
    "city": "Manchester City"
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
    ligas = [39, 140, 128, 262, 135, 2, 3]
    temporadas = [2024, 2023, 2022]
    for liga in ligas:
        for temp in temporadas:
            try:
                r = requests.get("https://v3.football.api-sports.io/fixtures",
                                 headers=HEADERS,
                                 params={"team": equipo_id, "league": liga, "season": temp, "last": 5},
                                 timeout=12)
                fixtures = r.json().get("response", [])
                if len(fixtures) < 2:
                    continue
                goles = 0
                btts = 0
                for f in fixtures:
                    gh = f["goals"]["home"] or 0
                    ga = f["goals"]["away"] or 0
                    goles += gh + ga
                    if gh > 0 and ga > 0:
                        btts += 1
                prom = round(goles / len(fixtures), 2)
                btts_pct = int((btts / len(fixtures)) * 100)
                print(f"OK {equipo_id} liga {liga} temp {temp} prom {prom}")
                return prom, btts_pct
