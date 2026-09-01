from flask import Flask
import threading, os, telebot, requests

app = Flask(__name__)
@app.route('/')
def home(): return "Bot con corners reales!"

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

def get_stats_con_corners(equipo_id):
    ligas = [39, 140, 128, 262]
    for liga in ligas:
        for temp in [2023, 2024]:
            try:
                r = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params={"team": equipo_id, "league": liga, "season": temp}, timeout=15)
                fixtures = r.json().get("response", [])
                if len(fixtures) < 3: continue
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

                # CORNERS REALES - 3 ultimos partidos
                total_corners=0
                corners_count=0
                corners_partidos=0
                for f in fixtures[-3:]:
                    fid = f["fixture"]["id"]
                    try:
                        rs = requests.get("https://v3.football.api-sports.io/fixtures/statistics", headers=HEADERS, params={"fixture": fid}, timeout=10)
                        for team_stat in rs.json().get("response", []):
                            if team_stat["team"]["id"] == equipo_id:
                                for s in team_stat["statistics"]:
                                    if s["type"] == "Corner Kicks" and s["value"]:
                                        total_corners += s["value"]
                                        corners_count+=1
                                        corners_partidos+=1
                    except:
                        continue

                n=len(fixtures)
                prom_corners = round(total_corners/corners_count,1) if corners_count>0 else 0

                return {
                    "prom": round(goles/n,2),
                    "o15": int(o15/n*100),
                    "o25": int(o25/n*100),
                    "btts": int(btts/n*100),
                    "corners_avg": prom_corners,
                    "corners_count": corners_count,
                    "fixtures_total": n
                }
            except:
                continue
    return None

def analizar(texto):
    if "vs" not in texto.lower(): return "Escribe: West ham vs Wolves"
    try:
        e1, e2 = [x.strip() for x in texto.lower().split("vs",1)]
        id1, name1 = buscar_equipo(e1)
        id2, name2 = buscar_equipo(e2)
        if not id1 or not id2: return "No encontre equipo"

        s1 = get_stats_con_corners(id1)
        s2 = get_stats_con_corners(id2)
        if not s1 or not s2: return "Sin datos"

        o15 = int((s1["o15"]+s2["o15"])/2)
        o25 = int((s1["o25"]+s2["o25"])/2)
        btts = int((s1["btts"]+s2["btts"])/2)

        corners_partido = round(s1["corners_avg"] + s2["corners_avg"],1)
        over85 = "OVER 8.5" if corners_partido > 8.5 else "UNDER 8.5"
        over95 = "OVER 9.5" if corners_partido > 9.5 else "UNDER 9.5"

        corners_txt = f"{corners_partido} corners"
        if s1["corners_avg"]==0 and s2["corners_avg"]==0:
            corners_txt = "No disponible (API no dio corners en ultimos 3)"

        return (f"ANALISIS REAL: {name1} vs {name2}\n"
                f"Prom gol ult 10: {s1['prom']} vs {s2['prom']}\n"
                f"OVER 1.5: {o15}% | {s1['o15']}% - {s2['o15']}%\n"
                f"OVER 2.5: {o25}% | {s1['o25']}% - {s2['o25']}%\n"
                f"BTTS SI: {btts}% | {s1['btts']}% - {s2['btts']}%\n\n"
                f"CORNERS REAL (ult 3):\n"
                f"{name1}: {s1['corners_avg']} avg\n"
                f"{name2}: {s2['corners_avg']} avg\n"
                f"TOTAL PARTIDO: {corners_txt}\n"
                f"8.5: {over85} | 9.5: {over95}")

    except Exception as e:
        return f"Error: {e}"

@bot.message_handler(func=lambda m: True)
def handle(m):
    bot.reply_to(m, analizar(m.text))

bot.infinity_polling()
