import os, requests, telebot, time
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

if not BOT_TOKEN or not API_KEY:
    print("FALTA TOKEN O API KEY EN ENVIRONMENT", flush=True)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
HEADERS = {"x-apisports-key": API_KEY}

def get_team_id(name):
    try:
        url = f"https://v3.football.api-sports.io/teams?search={name}"
        r = requests.get(url, headers=HEADERS, timeout=10).json()
        if r.get('results',0) > 0:
            return r['response'][0]['team']['id'], r['response'][0]['team']['name']
    except Exception as e:
        print(f"Error team_id {name}: {e}", flush=True)
    return None, None

def get_stats_real(team_name):
    team_id, real_name = get_team_id(team_name)
    if not team_id:
        return None
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=10&status=FT"
        data = requests.get(url, headers=HEADERS, timeout=15).json().get('response',[])
        if not data:
            return None
        ht_count=0; o15=0; o25=0; btts=0
        total=len(data)
        for f in data:
            ht_h = f['goals']['halftime']['home']
            ht_a = f['goals']['halftime']['away']
            if ht_h is None: ht_h=0
            if ht_a is None: ht_a=0
            if ht_h+ht_a > 0: ht_count+=1

            g_h = f['goals']['home'] or 0
            g_a = f['goals']['away'] or 0
            gf = g_h+g_a
            if gf >= 2: o15+=1
            if gf >= 3: o25+=1
            if g_h>0 and g_a>0: btts+=1

        return {
            "name": real_name,
            "id": team_id,
            "ht": int(ht_count/total*100),
            "o15": int(o15/total*100),
            "o25": int(o25/total*100),
            "btts": int(btts/total*100),
            "total": total
        }
    except Exception as e:
        print(f"Error stats {team_name}: {e}", flush=True)
        return None

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Bot V34 API-FOOTBALL LISTO ✅\nEscribe: America vs Chivas\nO: Getafe vs Osasuna\nTodo jalado REAL de los ultimos 10 partidos.")

@bot.message_handler(func=lambda m: 'vs' in m.text.lower())
def vs_handler(m):
    try:
        parts = m.text.lower().split('vs')
        if len(parts)!=2: return
        t1, t2 = parts[0].strip(), parts[1].strip()

        bot.send_message
