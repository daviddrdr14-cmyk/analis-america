from flask import Flask
import threading, os, telebot, requests

app = Flask(__name__)
@app.route('/')
def home(): return "Bot corners corregido!"

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

def get_stats_corregido(equipo_id):
    ligas = [39, 140] # 39=Premier, 140=LaLiga
    for liga in ligas:
        for temp in [2024, 2023]:
            try:
                r = requests.get("https://v3.football.api-sports.io/fixtures", headers=HEADERS, params={"team": equipo_id, "league": liga, "season": temp}, timeout=15)
                fixtures = r.json().get("response", [])
                if len(fixtures) < 5: continue
                fixtures_10 = fixtures[-10:]
                fixtures_5_corners = fixtures[-5:] # 5 para corners mas exacto

                goles=0; o15=0; o25=0; btts=0
                for f in fixtures_10:
                    gh = f["goals"]["home"] or 0
                    ga = f["goals"]["away"] or 0
                    total=gh+ga
                    goles+=total
                    if total>1.5: o15+=1
                    if total>2.5: o25+=1
                    if gh>0 and ga>0: btts+=1

                # CORNERS CORREGIDO - TOTAL DEL PARTIDO
                lista_totales = []
                lista_equipo = []
                for f in fixtures_5_corners:
                    fid = f["fixture"]["id"]
                    try:
                        rs = requests.get("https://v3.football.api-sports.io/fixtures/statistics", headers=HEADERS, params={"fixture": fid}, timeout=10)
                        data = rs.json().get("response", [])
                        if not data or len(data) < 2:
                            continue
                        # data[0] = local, data[1] = visitante
                        c_local = 0
                        c_visit = 0
                        for team_stat in data:
                            for s in team_stat["statistics"]:
                                if s["type"] == "Corner Kicks":
                                    val = s["value"] or 0
                                    if team_stat["team"]["id"] == equipo_id:
                                        c_equipo = val
                                        lista_equipo.append(c_equipo)
                                    if team_stat["team"]["id"] == data[0]["team"]["id"]:
                                        c_local = val
                                    else:
                                        c_visit = val
                        total_partido = (c_local or 0) + (c_visit or 0)
                        if total_partido > 0:
                            lista_totales.append(total_partido)
                    except:
                        continue

                n=len(fixtures_10)
                avg_equipo = round(sum(lista_equipo)/len(lista_equipo),1) if lista_equipo else 0
                avg_total = round(sum(lista_totales)/len(lista_totales),1) if lista_totales else 0

                print(f"Equipo {equipo_id} corners equipo {lista_equipo} totales {lista_totales}")

                return {
                    "prom": round(goles/n,2),
                    "o15": int(o15/n*100), "o25": int(o25/n*100), "btts": int(btts/n*100),
                    "corners_equipo": avg_equipo,
                    "corners_total": avg_total,
                    "muestras": len(lista_totales),
                    "detalle_totales": lista_totales
                }
            except Exception as e:
                print(e)
                continue
    return None

def analizar(texto):
    if "vs" not in texto.lower(): return "Escribe: West ham vs Wolves"
    try:
        e1, e2 = [x.strip() for x in texto.lower().split("vs",1)]
        id1, name1 = buscar_equipo(e1)
        id2, name2 = buscar_equipo(e2)
        if not id1 or not id2: return "No encontre equipo"

        s1 = get_stats_corregido(id1)
        s2 = get_stats_corregido(id2)
        if not s1 or not s2: return "Sin datos"

        o15 = int((s1["o15"]+s2["o15"])/2)
        o25 = int((s1["o25"]+s2["o25"])/2)
        btts = int((s1["btts"]+s2["btts"])/2)

        # Promedio de corners del partido = promedio de los totales
        if s1["corners_total"] and s2["corners_total"]:
            total_estimado = round((s1["corners_total"] + s2["corners_total"])/2,1)
            detalle = f"{s1['detalle_totales']} vs {s2['detalle_totales']}"
        else:
            total_estimado = 0
            detalle = "API no devolvio corners en esos 5 partidos"

        if total_estimado == 0:
            corners_msg = f"N/D - No hay datos de corners en plan gratis para esos fixtures ({s1['muestras']} muestras)"
        else:
            over85 = "OVER 8.5 ✅" if total_estimado > 8.5 else "UNDER 8.5"
            over95 = "OVER 9.5 ✅" if total_estimado > 9.5 else "UNDER 9.5"
            corners_msg = (f"Prom total por partido: {total_estimado}\n"
                           f"{name1}: {s1['corners_equipo']} propios (total partido {s1['corners_total']} en {s1['muestras']} juegos)\n"
                           f"{name2}: {s2['corners_equipo']} propios (total partido {s2['corners_total']})\n"
                           f"Historial: {detalle}\n"
                           f"8.5: {over85} | 9.5: {over95}")

        return (f"ANALISIS REAL: {name1} vs {name2}\n"
                f"Prom gol: {s1['prom']} vs {s2['prom']}\n"
                f"OVER 1.5: {o15}% | OVER 2.5: {o25}%\n"
                f"BTTS: {btts}%\n\n"
                f"CORNERS REAL:\n{corners_msg}")

    except Exception as e:
        return f"Error: {e}"

@bot.message_handler(func=lambda m: True)
def handle(m):
    bot.reply_to(m, analizar(m.text))

bot.infinity_polling()
