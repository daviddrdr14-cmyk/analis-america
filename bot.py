from flask import Flask
import threading, os, telebot, requests

app = Flask(__name__)
@app.route('/')
def home(): return "Bot con % reales!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
FOOTBALL_KEY = os.environ.get("FOOTBALL_API_KEY")
bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"x-apisports-key": FOOTBALL_KEY}

MAPA = {
    "america": "America", "chivas": "Guadalajara",
    "boca": "Boca Juniors", "river": "River Plate",
    "real madrid": "Real Madrid", "barcelona": "Barcelona",
    "west ham": "West Ham", "wolves": "Wolves"
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

def get_stats_reales(equipo_id):
    ligas = [39, 140, 128, 262]
    for liga in ligas:
        for temp in [2023, 2024]:
            try:
                r = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params={"team": equipo_id, "league": liga, "season": temp}, timeout=15)
                fixtures = r.json().get("response", [])
                if len(fixtures) < 3: continue
                fixtures = fixtures[-10:] # ultimos 10 para % mas real

                total_goles = 0
                over15 = 0
                over25 = 0
                btts = 0
                over35 = 0

                for f in fixtures:
                    gh = f["goals"]["home"] or 0
                    ga = f["goals"]["away"] or 0
                    total = gh + ga
                    total_goles += total
                    if total > 1.5: over15 += 1
                    if total > 2.5: over25 += 1
                    if total > 3.5: over35 += 1
                    if gh > 0 and ga > 0: btts += 1

                n = len(fixtures)
                return {
                    "prom": round(total_goles / n, 2),
                    "o15": int(over15 / n * 100),
                    "o25": int(over25 / n * 100),
                    "o35": int(over35 / n * 100),
                    "btts": int(btts / n * 100)
                }
            except:
                continue
    return None

def analizar(texto):
    txt = texto.lower().replace(" s ", " vs ")
    if "vs" not in txt:
        return "Escribe: West ham vs Wolves"
    try:
        e1, e2 = [x.strip() for x in txt.split("vs", 1)]
        id1, name1 = buscar_equipo(e1)
        id2, name2 = buscar_equipo(e2)
        if not id1 or not id2:
            return f"No encontre equipo"

        s1 = get_stats_reales(id1)
        s2 = get_stats_reales(id2)
        if not s1 or not s2:
            return "Sin datos reales para ese equipo"

        # % REAL combinado = promedio de los 2 equipos
        o15_real = int((s1["o15"] + s2["o15"]) / 2)
        o25_real = int((s1["o25"] + s2["o25"]) / 2)
        btts_real = int((s1["btts"] + s2["btts"]) / 2)
        prom_real = round((s1["prom"] + s2["prom"]) / 2, 2)

        return (f"ANALISIS REAL: {name1} vs {name2}\n"
                f"Promedio gol ult 10: {s1['prom']} vs {s2['prom']} (Partido: {prom_real})\n"
                f"OVER 1.5: {o15_real}% | {name1} {s1['o15']}% - {name2} {s2['o15']}%\n"
                f"OVER 2.5: {o25_real}% | {name1} {s1['o25']}% - {name2} {s2['o25']}%\n"
                f"BTTS SI: {btts_real}% | {name1} {s1['btts']}% - {name2} {s2['btts']}%\n"
                f"CORNERS 8.5: Analisis pendiente")
    except Exception as e:
        return f"Error: {e}"

@bot.message_handler(func=lambda m: True)
def handle(m):
    bot.reply_to(m, analizar(m.text))

bot.infinity_polling()
