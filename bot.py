import os
import requests
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"x-apisports-key": API_KEY}

def get_team_id(name):
    try:
        url = f"https://v3.football.api-sports.io/teams?search={name}"
        r = requests.get(url, headers=HEADERS, timeout=15).json()
        if r.get("results", 0) > 0:
            team = r["response"][0]["team"]
            return team["id"], team["name"]
    except:
        pass
    return None, None

def get_stats_real(team_name):
    team_id, real_name = get_team_id(team_name)
    if not team_id:
        return None
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=10"
        data = requests.get(url, headers=HEADERS, timeout=15).json().get("response", [])
        if not data:
            return None
        ht = 0
        o15 = 0
        o25 = 0
        btts = 0
        total = len(data)
        for f in data:
            gh = f["goals"]["halftime"]["home"] or 0
            ga = f["goals"]["halftime"]["away"] or 0
            if gh + ga > 0:
                ht += 1
            home = f["goals"]["home"] or 0
            away = f["goals"]["away"] or 0
            if home + away >= 2:
                o15 += 1
            if home + away >= 3:
                o25 += 1
            if home > 0 and away > 0:
                btts += 1
        return {
            "name": real_name,
            "ht": int(ht/total*100),
            "o15": int(o15/total*100),
            "o25": int(o25/total*100),
            "btts": int(btts/total*100),
            "total": total
        }
    except:
        return None

@bot.message_handler(commands=["start"])
def start_cmd(m):
    bot.reply_to(m, "Bot V34 listo. Escribe: America vs Chivas")

@bot.message_handler(func=lambda m: "vs" in m.text.lower())
def vs_handler(m):
    txt = m.text.lower()
    if "vs" not in txt:
        return
    parts = txt.split("vs")
    if len(parts)!= 2:
        return
    t1 = parts[0].strip()
    t2 = parts[1].strip()
    if t1 == "" or t2 == "":
        return
    try:
        bot.send_message(m.chat.id, f"Buscando REALES: {t1} vs {t2}...")
        s1 = get_stats_real(t1)
        s2 = get_stats_real(t2)
        if s1 is None or s2 is None:
            bot.send_message(m.chat.id, "No encontre un equipo. Prueba: America vs Guadalajara")
            return
        ph = (s1["ht"] + s2["ht"]) // 2
        po15 = (s1["o15"] + s2["o15"]) // 2
        po25 = (s1["o25"] + s2["o25"]) // 2
        pb = (s1["btts"] + s2["btts"]) // 2
        msg = f"⚽ {s1['name']} vs {s2['name']} - REAL API\n{s1['name']} ({s1['total']}j): HT:{s1['ht']}% O1.5:{s1['o15']}% O2.5:{s1['o25']}% BTTS:{s1['btts']}%\n{s2['name']} ({s2['total']}j): HT:{s2['ht']}% O1.5:{s2['o15']}% O2.5:{s2['o25']}% BTTS:{s2['btts']}%\n🔥 COMBINADO: HT:{ph}% O1.5:{po15}% O2.5:{po25}% BTTS:{pb}%"
        bot.send_message(m.chat.id, msg)
    except Exception as e:
        bot.send_message(m.chat.id, f"Error: {e}")

print("Bot V34 iniciado")
bot.delete_webhook()
bot.infinity_polling(skip_pending=True)
