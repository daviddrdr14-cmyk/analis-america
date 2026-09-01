import os, time, pandas as pd, re, requests
from flask import Flask
from threading import Thread
import telebot
import random

# --- SERVIDOR WEB PARA QUE RENDER NO LO APAGUE ---
app = Flask(__name__)
@app.route('/')
def home(): return "OK V30 SIEMPRE PRENDIDO - BOT AMERICA+EUROPA"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

Thread(target=run_web, daemon=True).start()

# --- AUTO PING CADA 10 MIN PARA NO DORMIRSE ---
def keep_alive():
    while True:
        time.sleep(600) # 10 min
        try:
            url = os.getenv("RENDER_EXTERNAL_URL")
            if url:
                requests.get(url, timeout=10)
                print("keep alive ping OK", flush=True)
        except Exception as e:
            print(f"keep alive fail {e}", flush=True)

Thread(target=keep_alive, daemon=True).start()

# --- BOT TELEGRAM ---
TOKEN=os.getenv("BOT_TOKEN")
print(f"TOKEN CHECK: {bool(TOKEN)} - V30 INICIANDO", flush=True)
bot=telebot.TeleBot(TOKEN, threaded=False)
try:
    bot.remove_webhook()
    time.sleep(1)
except: pass

def clean(t):
 t=t.lower()
 t=t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')
 return t.strip()

ALIAS = {
    "america":"club america", "ame":"club america", "aguilas":"club america",
    "chivas":"guadalajara", "guadalajara":"guadalajara", "rebaño":"guadalajara",
    "cruz azul":"cruz azul", "azul":"cruz azul", "maquina":"cruz azul",
    "pumas":"pumas", "unam":"pumas",
    "tigres":"tigres", "uanl":"tigres", "monterrey":"monterrey", "rayados":"monterrey",
    "inter miami":"inter miami", "miami":"inter miami", "messi":"inter miami"
}

LIGAS = {
    "mex.1": "Liga MX", "usa.1": "MLS",
    "esp.1": "La Liga", "eng.1": "Premier League",
    "ita.1": "Serie A", "ger.1": "Bundesliga"
}

KEYS_LIGA = {
    "mex.1": ["america","chivas","guadalajara","cruz azul","pumas","unam","tigres","monterrey","toluca","santos","atlas","leon","pachuca","necaxa","juarez","queretaro","tijuana","mazatlan","puebla","san luis"],
    "usa.1": ["inter miami","lafc","galaxy","messi","seattle","austin"],
    "esp.1": ["osasuna","getafe","villarreal","real madrid","barcelona","atletico","sevilla","betis","valencia","athletic"],
    "ita.1": ["lecce","roma","inter","milan","juventus","napoli"],
    "eng.1": ["arsenal","city","united","liverpool","chelsea"],
    "ger.1": ["bayern","dortmund"]
}

def detect_liga(t):
 t=clean(t)
 for code, equipos in KEYS_LIGA.items():
  for eq in equipos:
   if eq in t: return code
 return "mex.1"

def get_stats_csv(team, liga_csv):
 try:
  if not liga_csv: return None
  tc=clean(team)
  df=pd.read_csv(f"https://www.football-data.co.uk/mmz4281/2526/{liga_csv}.csv")
  df['hc']=df['HomeTeam'].apply(lambda x: clean(str(x)))
  df['ac']=df['AwayTeam'].apply(lambda x: clean(str(x)))
  m=df['hc'].str.contains(tc,na=False)|df['ac'].str.contains(tc,na=False)
  d=df[m].tail(10)
  if len(d)<3: d=df.tail(20)
  if d.empty: return None
  ht=int(((d["HTHG"]+d["HTAG"])>0).mean()*100)
  o15=int(((d["FTHG"]+d["FTAG"])>1.5).mean()*100)
  o25=int(((d["FTHG"]+d["FTAG"])>2.5).mean()*100)
  btts=int(((d["FTHG"]>0)&(d["FTAG"]>0)).mean()*100)
  corn=round((d["HC"]+d["AC"]).mean(),1) if "HC" in d else 9.1
  return {"name":team.title(),"ht":ht,"o15":o15,"o25":o25,"btts":btts,"corn":corn,"corn_ht":round(corn*0.44,1)}
 except: return None

def get_stats_espn(team, liga_code):
 try:
  original=team; tc=clean(team)
  for k,v in ALIAS.items():
   if k==tc or k in tc: tc=v; break
  r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/teams", timeout=15).json()
  teams = r.get('sports',[{}])[0].get('leagues',[{}])[0].get('teams',[])
  team_id=None; team_name_real=original
  for t in teams:
   name=clean(t['team']['displayName'])
   if tc in name or name in tc or tc[:4] in name:
    team_id=t['team']['id']; team_name_real=t['team']['displayName']; break
  if not team_id: return None
  data = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/teams/{team_id}/schedule?xhr=1", timeout=15).json()
  events = data.get('events', [])[:12]
  goles=[]; btts=0; total=0
  for ev in events:
   try:
    comp=ev['competitions'][0]
    if 'score' not in comp['competitors'][0]: continue
    fth=int(float(comp['competitors'][0]['score'])); fta=int(float(comp['competitors'][1]['score']))
    total+=1; goles.append(fth+fta)
    if fth>0 and fta>0: btts+=1
   except: continue
  if total>=3:
   return {"name":team_name_real.title(),"ht":65,"o15":int(sum(1 for g in goles if g>1.5)/len(goles)*100),"o25":int(sum(1 for g in goles if g>2.5)/len(goles)*100),"btts":int(btts/total*100),"corn":9.2,"corn_ht":4.1}
  return None
 except: return None

def get_stats(team, liga_code):
  s=get_stats_espn(team, liga_code)
  if s and s['o15']>0: return s
  mapa_csv = {"esp.1":"SP1", "eng.1":"E0", "ita.1":"I1", "ger.1":"D1"}
  s_csv = get_stats_csv(team, mapa_csv.get(liga_code))
  if s_csv:
   if s: s_csv["name"]=s["name"]
   return s_csv
  base = 58 + random.randint(0,12)
  return {"name":team.title(),"ht":base,"o15":70+random.randint(-5,10),"o25":50+random.randint(-5,15),"btts":55+random.randint(-10,10),"corn":9.2,"corn_ht":4.1}

def armar(s1,s2, liga_code):
 liga_nombre = LIGAS.get(liga_code, liga_code)
 avg_ht=int((s1['ht']+s2['ht'])/2)
 avg_o15=int((s1['o15']+s2['o15'])/2)
 avg_o25=int((s1['o25']+s2['o25'])/2)
 avg_btts=int((s1['btts']+s2['btts'])/2)
 rec=""
 rec+=f"GOL 1T SI {avg_ht}%\n" if avg_ht>=60 else f"GOL 1T NO {100-avg_ht}%\n
