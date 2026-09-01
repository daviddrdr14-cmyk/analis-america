from flask import Flask
import threading, os, telebot, requests

app = Flask(__name__)
@app.route('/')
def home(): return "Bot final estable!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
FOOTBALL_KEY = os.environ.get("FOOTBALL_API_KEY")
bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"x-apisports-key": FOOTBALL_KEY}

def buscar_equipo(nombre):
    r = requests.get("https://v3.football.api-sports.io/teams", headers=HEADERS, params={"search": nombre}, timeout=15)
    data = r.json()
    if data.get("results", 0) > 0:
        t = data["response"][0]["team"]
        return t["id"], t["name"]
    return None, None

def get_goles_stats(equipo_id):
    # ESTO ES LO QUE YA TENIAS BIEN
    for liga in [39, 140, 128, 262]:
        for temp in [2023, 2024]:
            try:
                r = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params={"team": equipo_id, "league": liga, "season": temp}, timeout=15)
                fixtures = r.json().get("response", [])
                if len(fixtures) < 8: continue
                fixtures = fixtures[-10:]

                goles=0; o15=0; o25=0; btts=0
                for f in fixtures:
                    gh = f["goals"]["home"] or 0
                    ga = f["goals"]["away"] or 0
                    total=gh+ga
                    goles+=total
                    if total>1.5: o15+=1
                    if total>2.5: o25+=1
                    if gh>0 and ga>0: btts+=1

                n=len(fixtures)
                return {
                    "prom": round(goles/n,2),
                    "o15": int(o15/n*100),
                    "o25": int(o25/n*100),
                    "btts": int(btts/n*100),
                    "fixtures": fixtures,
                    "liga": liga,
                    "temp": temp
                }
            except:
                continue
    return None

def get_corners_stats(fixtures, equipo_id):
    # SOLO CORNERS APARTE
    totales = []
    propios = []
    for f in fixtures[-5:]:
        fid = f["fixture"]["id"]
        try:
            rs = requests.get("https://v3.football.api-sports.io/fixtures/statistics", headers=HEADERS, params={"fixture": fid}, timeout=10)
            data = rs.json().get("response", [])
            if len(data) < 2: continue

            c_local = c_visit = 0
            c_equipo = 0
            for team_stat in data:
                for s in team_stat["statistics"]:
                    if s["type"] == "Corner Kicks" and s["value"]:
                        if team_stat["team"]["id"] == equipo_id:
                            c_equipo = s["value"]
                        # guardar para total
                        if data[0]["team"]["id"] == team_stat["team"]["id"]:
                            c_local = s["value"]
                        else:
                            c_visit = s["value"]

            if c_local + c_visit > 0:
                totales.append(c_local + c_visit)
                propios.append(c_equipo)
        except:
            continue

    avg_total = round(sum(totales)/len(totales),1) if totales else 0
    avg_propio = round(sum(propios)/len(propios),1) if propios else 0
    return avg_total, avg_propio, totales

def analizar(texto):
    if "vs" not in texto.lower(): return "Escribe: West ham vs Wolves"
    try:
        e1, e2 = [x.strip() for x in texto.lower().split("vs",1)]
        id1, name1 = buscar_equipo(e1)
        id2, name2 = buscar_equipo(e2)
        if not id1 or not id2: return "No encontre equipo"

        s1 = get_goles_stats(id1)
        s2 = get_goles_stats(id2)
        if not s1 or not s2: return "Sin datos"

        # corners separado, no toca goles
        total1, propio1, hist1 = get_corners_stats(s1["fixtures"], id1)
        total2, propio2, hist2 = get_corners_stats(s2["fixtures"], id2)

        o15 = int((s1["o15"]+s2["o15"])/2)
        o25 = int((s1["o25"]+s2["o25"])/2)
        btts = int((s1["btts"]+s2["btts"])/2)

        if total1 and total2:
            prom_corners = round((total1+total2)/2,1)
            corners_msg = f"TOTAL PARTIDO: {prom_corners} ( {total1} + {total2}/2 )\n{name1}: {propio1} propios {hist1}\n{name2}: {propio2} propios {hist2}\n8.5: {'OVER' if prom_corners>8.5 else 'UNDER'} | 9.5: {'OVER' if prom_corners>9.5 else 'UNDER'}"
        else:
            corners_msg = f"Sin datos de corners (muestras {len(hist1)+len(hist2)}) - plan gratis no dio datos"

        return (f"ANALISIS REAL: {name1} vs {name2}\n"
                f"Prom gol: {s1['prom']} vs {s2['prom']} (liga {s1['liga']})\n"
                f"OVER 1.5: {o15}% | {s1['o15']}% - {s2['o15']}%\n"
                f"OVER 2.5: {o25}% | {s1['o25']}% - {s2['o25']}%\n"
                f"BTTS: {btts}% | {s1['btts']}% - {s2['btts']}%\n\n"
                f"CORNERS:\n{corners_msg}")

    except Exception as e:
        return f"Error: {e}"

@bot.message_handler(func=lambda m: True)
def handle(m):
    bot.reply_to(m, analizar(m.text))

bot.infinity_polling()
