import os, requests, telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"x-apisports-key": API_KEY}

def get_team_id(name):
    try:
        url = f"https://v3.football.api-sports.io/teams?search={name}"
        r = requests.get(url, headers=HEADERS, timeout=15).json()
        if r.get('results',0) > 0:
            team = r['response'][0]['team']
            return team['id'], team['name']
    except Exception as e:
        print(f"Error get_team_id {name}: {e}")
    return None, None

def get_stats_real(team_name):
    team_id, real_name = get_team_id(team_name)
    if not team_id:
        return None
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=10"
        resp = requests.get(url, headers=HEADERS, timeout=15).json()
        data = resp.get('response',[])
        if not data:
            return None

        ht=o15=o25=btts=0
        total=len(data)
        for f in data:
            try:
                gh = f['goals']['halftime']['home'] or 0
                ga = f['goals']['halftime']['away'] or 0
                if gh+ga>0: ht+=1

                home = f['goals']['home'] or 0
                away = f['goals']['away'] or 0
                gf = home+away
                if gf>=2: o15+=1
                if gf>=3: o25+=1
                if home>0 and away>0: btts+=1
            except: continue

        return {
            "name":real_name,
            "ht":int(ht/total*100) if total>0 else 0,
            "o15":int(o15/total*100) if total>0 else 0,
            "o25":int(o25/total*100) if total>0 else 0,
            "btts":int(btts/total*100) if total>0 else 0,
            "total":total
        }
    except Exception as e:
        print(f"Error get_stats {team_name}: {e}")
        return None

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Bot V34 API-FOOTBALL listo.\nEscribe: America vs Chivas\nO: Getafe vs Osasuna")

@bot.message_handler(func=lambda m: 'vs' in m.text.lower())
def vs_handler(m):
    try:
        parts = m.text.lower().split('vs')
        if len(parts)!=2: return
        t1, t2 = parts[0].strip(), parts[1].strip()
        if not t1 or not t2: return
