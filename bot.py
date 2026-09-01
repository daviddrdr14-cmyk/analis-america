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

MAPA = {
    "america": "Club America", "chivas": "Guadalajara", "cruz azul": "Cruz Azul",
    "pumas": "Pumas UNAM", "monterrey": "Monterrey", "tigres": "Tigres UANL",
    "getafe": "Getafe", "osasuna": "Osasuna", "real madrid": "Real Madrid",
    "barcelona": "Barcelona", "west ham": "West Ham", "wolves": "Wolves",
    "wesham": "West Ham", "wolverhampton": "Wolves"
}

def buscar_equipo(nombre):
    nombre = nombre.lower().strip()
    busqueda = MAPA.get(nombre, nombre)
    r = requests.get("https://v3.football.api-sports.io/teams", headers=HEADERS, params={"search": busqueda}, timeout=10)
    data = r.json()
    if data.get('results',0) > 0:
        team = data['response'][0]['team']
        return team['id'], team['name']
    return None, None

def get_stats(equipo_id):
    # ultimos 5 partidos
    r = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params={"team": equipo_id, "last": 5}, timeout=10)
    fixtures = r.json().get('response', [])
    goles = 0
    btts = 0
    for f in fixtures:
        g_home = f['goals']['home'] or 0
        g_away = f['goals']['away'] or 0
        goles += g_home + g_away
        if g_home > 0 and g_away > 0:
            btts += 1
    if not fixtures: return 0, 0
    prom_gol = goles / len(fixtures)
    btts_pct = int((btts / len(fixtures)) * 100)
    return prom_gol, btts_pct

def analizar(texto):
    if "vs" not in texto.lower(): return "Escribe: America vs Chivas"
    if not FOOTBALL_KEY: return "Falta FOOTBALL_API_KEY en Render"
    try:
        e1, e2 = [x.strip() for x in texto.split("vs", 1)]
        id1, name1 = buscar_equipo(e1)
        id2, name2 = buscar_equipo(e2)
        if not id1: return f"No encontré '{e1}'"
        if not id2: return f"No encontré '{e2}'"

        # Estadisticas reales
        prom1, btts1 = get_stats(id1)
        prom2, btts2 = get_stats(id2)

        # H2H
        r_h2h = requests.get("https://v3.football.api-sports.io/fixtures/headtohead", headers=HEADERS, params={"h2h": f"{id1}-{id2}", "last": 5}, timeout=10)
        h2h = r_h2h.json().get('response', [])
        over15 = over25 = 0
        if h2h:
            for f in h2h:
                total = (f['goals']['home'] or 0) + (f['goals']['away'] or 0)
                if total >= 2: over15 += 1
                if total >= 3: over25 += 1
            over15 = int(over15 / len(h2h) * 100)
            over25 = int(over25 / len(h2h) * 100)
        else:
            # si no hay H2H, usa promedio de goles
            promedio_total = (prom1 + prom2)
            over15 = 88 if promedio_total > 1.8 else 65
            over25 = 68 if promedio_total > 2.4 else 45

        btts_final = int((btts1 + btts2) / 2)

        # Corners aproximado por liga (La API gratis no da corners sin plan pro)
        corners_msg = "CORNERS 8.5: VERDE" if (prom1+prom2) > 2 else "CORNERS 8.5: ROJO"

        return f"""🦅 ANÁLISIS: {name1} vs {name2}

H2H: {len(h2h)} ultimos, Prom gol: {prom1:.1f} vs {prom2:.1f}
OVER 1.5: {over15}%
OVER 2.5: {over25}%
BTTS SI: {btts_final}%
{corners_msg}
CORNERS 9.2 -> {'SI' if over15 > 70 else 'NO'}
Doble oportunidad {name1}"""
    except Exception as e:
        print(f"Error: {e}")
        return f"Error API: {e}"

@bot.message_handler(func=lambda m: True)
def handle(m):
    bot.reply_to(m, analizar(m.text))

bot.infinity_polling()
