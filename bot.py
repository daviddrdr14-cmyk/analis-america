import os, time, pandas as pd, re, requests
from flask import Flask
from threading import Thread
import telebot

app = Flask(__name__)
@app.route('/')
def home(): return "OK V28 FUSION AMERICA+EUROPA"
Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()

TOKEN=os.getenv("BOT_TOKEN")
print(f"TOKEN CHECK: {bool(TOKEN)}", flush=True)
bot=telebot.TeleBot(TOKEN, threaded=False)
try:
    bot.remove_webhook()
    time.sleep(1)
except: pass

def clean(t):
 t=t.lower()
 t=t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')
 return t.strip()

# --- MAPEO DE EQUIPOS PARA ESPN ---
ALIAS = {
    "america":"club america", "ame":"club america",
    "chivas":"guadalajara", "guadalajara":"guadalajara", "rebaño":"guadalajara",
    "cruz azul":"cruz azul", "azul":"cruz azul", "maquina":"cruz azul",
    "pumas":"pumas", "unam":"pumas",
    "tigres":"tigres uanl", "uanl":"tigres",
    "monterrey":"monterrey", "rayados":"monterrey"
}

LIGAS = {
    "mex.1": "Liga MX",
    "usa.1": "MLS",
    "esp.1": "La Liga",
    "eng.1": "Premier League",
    "ita.1": "Serie A",
    "ger.1": "Bundesliga"
}

KEYS_LIGA = {
    "mex.1": ["america","chivas","guadalajara","cruz azul","pumas","unam","tigres","monterrey","toluca","santos","atlas","leon","pachuca","necaxa","juarez","queretaro","tijuana","mazatlan","puebla","san luis"],
    "usa.1": ["inter miami","lafc","galaxy","messi"],
    "esp.1": ["osasuna","getafe","villarreal","real madrid","barcelona","atletico madrid","sevilla","betis"],
    "ita.1": ["lecce","roma","inter","milan","juventus","napoli"],
    "eng.1": ["arsenal","city","united","liverpool","chelsea"],
    "ger.1": ["bayern","dortmund","leverkusen"]
}

def detect_liga(t):
 t=clean(t)
 for code, equipos in KEYS_LIGA.items():
  for eq in equipos:
   if eq in t: return code
 return "mex.1"

def get_stats_espn(team, liga_code):
 try:
  original = team
  tc=clean(team)
  # aplicar alias
  for k,v in ALIAS.items():
   if k==tc or k in tc:
    tc=v
    break

  # 1. buscar equipo
  r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/teams", timeout=15).json()
  teams = r.get('sports',[{}])[0].get('leagues',[{}])[0].get('teams',[])
  team_id=None
  team_name_real=original
  for t in teams:
   name=clean(t['team']['displayName'])
   if tc in name or name in tc or tc[:4] in name:
    team_id=t['team']['id']
    team_name_real=t['team']['displayName']
    break

  print(f"Buscando {original}({tc}) -> {team_name_real} ID:{team_id} liga:{liga_code}", flush=True)

  if not team_id:
   return None

  # 2. traer schedule (ultimos 10)
  data = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/teams/{team_id}/schedule", timeout=15).json()
  events = data.get('events', []) or data.get('team',{}).get('events',[]) or []

  # si no hay, usa scoreboard general de la liga para sacar ultimos 10
  if len(events)<3:
   data2 = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/scoreboard", timeout=15).json()
   events = data2.get('events', [])[:20]

  ht=[]; goles=[]; btts=0; total=0
  for ev in events[:10]:
   try:
    comp=ev['competitions'][0]
    fth=int(comp['competitors'][0]['score'])
    fta=int(comp['competitors'][1]['score'])
    total+=1
    goles.append(fth+fta)
    if fth>0 and fta>0: btts+=1
    if fth+fta>0: ht.append(1)
    else: ht.append(0)
   except: continue

  if total==0: # fallback si ESPN no trae score
   print(f"Sin juegos para {team_name_real}, usando promedio liga", flush=True)
   return {"name":team_name_real.title(),"ht":62,"o15":75,"o25":55,"btts":58,"corn":9.2,"corn_ht":4.1}

  return {
   "name": team_name_real.title(),
   "ht": int(sum(ht)/len(ht)*100) if ht else 60,
   "o15": int(sum([1 for g in goles if g>1.5])/len(goles)*100),
   "o25": int(sum([1 for g in goles if g>2.5])/len(goles)*100),
   "btts": int(btts/total*100),
   "corn": 9.2, "corn_ht": 4.1
  }
 except Exception as e:
  print("error espn",e, flush=True)
  return None

def get_stats_csv(team,liga):
 try:
  tc=clean(team)
  df=pd.read_csv(f"https://www.football-data.co.uk/mmz4281/2526/{liga}.csv")
  df['hc']=df['HomeTeam'].apply(lambda x: clean(str(x)))
  df['ac']=df['AwayTeam'].apply(lambda x: clean(str(x)))
  m=df['hc'].str.contains(tc,na=False)|df['ac'].str.contains(tc,na=False)
  d=df[m].tail(5)
  if d.empty: d=df.tail(5)
  ht=int(((d["HTHG"]+d["HTAG"])>0).mean()*100)
  o15=int(((d["FTHG"]+d["FTAG"])>1.5).mean()*100)
  o25=int(((d["FTHG"]+d["FTAG"])>2.5).mean()*100)
  btts=int(((d["FTHG"]>0)&(d["FTAG"]>0)).mean()*100)
  corn=round((d["HC"]+d["AC"]).mean(),1)
  corn_ht=round(corn*0.45,1)
  return {"name":team.title(),"ht":ht,"o15":o15,"o25":o25,"btts":btts,"corn":corn,"corn_ht":corn_ht}
 except: return None

def get_stats(team,liga):
  # intenta primero ESPN (America y Europa nueva)
  s=get_stats_espn(team,liga)
  if s: return s
  # si falla, usa CSV solo para SP1, I1 etc
  liga_csv = "SP1" if liga=="esp.1" else "I1" if liga=="ita.1" else "E0" if liga=="eng.1" else None
  if liga_csv:
   return get_stats_csv(team, liga_csv)
  return None

def armar(s1,s2, liga_code):
 liga_nombre = LIGAS.get(liga_code, liga_code)
 avg_ht=int((s1['ht']+s2['ht'])/2)
 avg_o15=int((s1['o15']+s2['o15'])/2)
 avg_o25=int((s1['o25']+s2['o25'])/2)
 avg_btts=int((s1['btts']+s2['btts'])/2)
 rec=""
 if avg_ht>=60: rec+=f"GOL 1T SI {avg_ht}%\n"
 else: rec+=f"GOL 1T NO {100-avg_ht}%\n"
 if avg_o15>=70: rec+=f"OVER 1.5 {avg_o15}%\n"
 if avg_o25>=60: rec+=f"OVER 2.5 {avg_o25}%\n"
 if avg_btts>=60: rec+=f"BTTS SI {avg_btts}%\n"
 else: rec+=f"BTTS NO {100-avg_btts}%\n"
 rec+=f"CORNERS { (s1['corn']+s2['corn'])/2:.1f} / 1T { (s1['corn_ht']+s2['corn_ht'])/2:.1f}\n"
 return f"🏆 {liga_nombre}\n{s1['name']} vs {s2['name']}\nHT {s1['ht']}%/{s2['ht']}% -> {avg_ht}%\nO1.5 {s1['o15']}%/{s2['o15']}% O2.5 {s1['o25']}%/{s2['o25']}%\nBTTS {s1['btts']}%/{s2['btts']}%\n\nRECOM:\n{rec}"

@bot.message_handler(commands=['start'])
def start_cmd(m):
 bot.reply_to(m, "🦅 Bot América V28 listo!\nEscribe: America vs Chivas\nO: Osasuna vs Getafe")

@bot.message_handler(content_types=['photo'])
def handle_photo(m):
 bot.reply_to(m,"Mándamelo escrito: Ej. America vs Chivas")

@bot.message_handler(func=lambda m: True)
def handle(m):
 try:
  txt=m.text or ""
  if "vs" not in txt.lower():
   if txt.startswith("/"): return
   bot.reply_to(m,"Escribe: Equipo vs Equipo\nEj: America vs Chivas"); return
  p=re.split(r'\s+vs\s+',txt, flags=re.IGNORECASE)
  if len(p)<2: return
  l=p[0].strip(); v=p[1].strip()
  if len(l)<3 or len(v)<3: return
  liga=detect_liga(l+" "+v)
  s1=get_stats(l,liga); s2=get_stats(v,liga)
  if not s1 or not s2:
   bot.reply_to(m,f"No encontre {l} o {v} en {liga} - intenta: {l.title()} vs {v.title()}"); return
  bot.reply_to(m, armar(s1,s2, liga))
 except Exception as e:
  print(e, flush=True)

print("BOT V28 FUSION LISTO",flush=True)
bot.infinity_polling(timeout=90,long_polling_timeout=90,skip_pending=True)
