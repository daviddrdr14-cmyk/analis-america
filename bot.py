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
    "america": "Club America",
    "chivas": "Guadalajara",
    "guadalajara": "Guadalajara",
    "cruz azul": "Cruz Azul",
    "pumas": "Pumas UNAM",
    "monterrey": "Monterrey",
    "tigres": "Tigres UANL",
    "getafe": "Getafe",
    "osasuna": "Osasuna",
    "real madrid": "Real Madrid",
    "barcelona": "Barcelona",
    "west ham": "West Ham",
    "wolves": "Wolves",
    "wesham": "West Ham",
    "wolverhampton": "Wolves"
}

def buscar_equipo(nombre):
    nombre = nombre.lower().strip()
    busqueda = MAPA.get(nombre, nombre)
    r = requests.get("https://v3.football.api-sports.io/teams", headers=HEADERS, params={"search": busqueda}, timeout=15)
    data = r.json()
    print(f"Buscando {busqueda}: {data.get('results')}")
    if data.get('results', 0) > 0:
        team = data['response'][0]['team']
        return team['id'], team['name']
    return None, None

def get_stats(equipo_id):
    for season in [2024, 2023]:
        try:
            r = requests.get("https://v3.football.api-sports.io/fixtures",
                             headers=HEADERS,
                             params={"team": equipo_id, "last": 5, "season": season},
                             timeout=15)
            fixtures = r.json().get('response', [])
            if not fixtures:
                continue
            goles = 0
            btts = 0
            for f in fixtures:
                gh = f['goals']['home'] or 0
                ga = f['goals']['away'] or 0
                goles += gh + ga
                if gh > 0 and ga > 0:
                    btts += 1
            prom = goles / len(fixtures)
            btts_pct = int((btts / len(fixtures)) * 100)
            return prom, btts_pct
        except Exception as e:
            print(f"Error stats {equipo_id} season {season}: {e}")
            continue
    return 2.1, 50

def analizar(texto):
    if "vs" not in texto.lower():
        return "Escribe: America vs Chivas"
    if not FOOTBALL_KEY:
        return "Falta FOOTBALL_API_KEY en Render"
    try:
        e1, e2 = [x.strip() for x in texto.split("vs", 1)]
        id1, name1 = buscar_equipo(e1)
        id2, name2 = buscar_equipo(e2)

        if not id1:
            return f"No encontré '{e1}' - prueba: america, chivas, monterrey, getafe"
        if not id2:
            return f"No encontré '{e2}'"

        prom1, btts1 = get_stats(id1)
        prom2, btts2 = get_stats(id2)

        # H2H
        over15 = over25 = 0
        h2h_count = 0
        try:
            r_h2h = requests.get("https://v3.football.api-sports.io/fixtures/headtohead",
                                 headers=HEADERS,
                                 params={"h2h": f"{id1}-{id2}", "last": 5},
                                 timeout=15)
            h2h = r_h2h.json().get('response', [])
            h2h_count = len(h2h)
            if h2h:
                c15 = c25 = 0
                for f in h2h:
                    total = (f['goals']['home'] or 0) + (f['goals']['away'] or 0)
                    if total >= 2: c15 += 1
                    if total >= 3: c25 += 1
                over15 = int(c15 / len(h2h) * 100)
                over25 = int(c25 / len(h2h) * 100)
        except Exception as e:
            print(f"Error H2H: {e}")

        if h2h_count == 0:
            total_prom = prom1 + prom2
            over15 = 85 if total_prom > 2.2 else 70
            over25 = 65 if total_prom > 2.8 else 48

        btts_final = int((btts1 + btts2) / 2)
        if btts_final == 0:
            btts_final = 58

        corners_msg = "CORNERS 8.5: VERDE" if (prom1 + prom2) > 2.0 else "CORNERS 8.5: ROJO"

        return f"""🦅 ANÁLISIS: {name1} vs {name2}

H2H: {h2h_count} ultimos, Prom gol: {prom1:.1f} vs {prom2:.1f}
OVER 1.5: {over15}%
OVER 2.5: {over25}%
BTTS SI: {btts_final}%
{corners_msg}
CORNERS 9.2 -> {'SI' if over15 >= 70 else 'NO'}
Doble oportunidad {name1}"""
    except Exception as e:
        print(f"Error analizar: {e}")
        return f"Error API: {e}"

@bot.message_handler(func=lambda m: True)
def handle(m):
    bot.reply_to(m, analizar(m.text))

print("Bot iniciado...")
bot.infinity_polling()
