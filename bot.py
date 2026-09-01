import os, requests, telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"x-apisports-key": API_KEY}

def get_team_id(name):
    try:
        url = f"https://v3.football.api-sports.io/teams?search={name}"
        r = requests.get(url, headers=HEADERS, timeout=10).json()
        if r.get('results',0) > 0:
            return r['response'][0]['team']['id'], r['response'][0]['team']['name']
    except: pass
    return None, None

def get_stats_real(team_name):
    team_id, real_name = get_team_id(team_name)
    if not team_id: return None
    try:
        url = f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=10"
        data = requests.get(url, headers=HEADERS, timeout=10).json().get('response',[])
        if not data: return None
        ht=o15=o25=btts=0
        total=len(data)
        for f in data:
            gh = f['goals']['halftime']['home'] or 0
            ga = f['goals']['halftime']['away'] or 0
            if gh+ga>0: ht+=1
            gf = (f['goals']['home'] or 0)+(f['goals']['away'] or 0)
            if gf>=2: o15+=1
            if gf>=3: o25+=1
            if (f['goals']['home'] or 0)>0 and (f['goals']['away'] or 0)>0: btts+=1
        return {"name":real_name,"ht":int(ht/total*100),"o15":int(o15/total*100),"o25":int(o25/total*100),"btts":int(btts/total*100),"total":total}
    except Exception as e:
        print(e)
        return None

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "Bot V34 API-FOOTBALL listo. Escribe: America vs Chivas")

@bot.message_handler(func=lambda m: 'vs' in m.text.lower())
def vs_handler(m):
    try:
        parts = m.text.lower().split('vs')
        if len(parts)!=2: return
        t1, t2 = parts[0].strip(), parts[1].strip()
        bot.send_message(m.chat.id, f"⏳ Buscando {t1} vs {t2} en API-FOOTBALL...")
        s1 = get_stats_real(t1)
        s2 = get_stats_real(t2)
        if not s1 or not s2:
            bot.send_message(m.chat.id, "❌ No encontré un equipo. Prueba: Club America vs Guadalajara")
            return
        ph = (s1['ht']+s2['ht'])//2
        po15 = (s1['o15']+s2['o15'])//2
        po25 = (s1['o25']+s2['o25'])//2
        pb = (s1['btts']+s2['btts'])//2
        msg = f"⚽ {s1['name']} vs {s2['name']} - REAL API\n\n{s1['name']} ({s1['total']}j):\nHT:{s1['ht']}% O1.5:{s1['o15']}% O2.5:{s1['o25']}% BTTS:{s1['btts']}%\n\n{s2['name']} ({s2['total']}j):\nHT:{s2['ht']}% O1.5:{s2['o15']}% O2.5:{s2['o25']}% BTTS:{s2['btts']}%\n\n🔥 COMBINADO:\n1er Tiempo Gol: {ph}%\nOver 1.5: {po15}%\nOver 2.5: {po25}%\nBTTS: {pb}%"
        bot.send_message(m.chat.id, msg)
    except Exception as e:
        print(f"Error handler: {e}")
        bot.send_message(m.chat.id, f"Error: {e}")

print("Bot V34 iniciado")
bot.infinity_polling()
