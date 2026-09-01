import os, time, pandas as pd, re, requests
from flask import Flask
from threading import Thread
import telebot

app = Flask(__name__)
@app.route('/')
def home(): return "OK V29 FUSION FINAL"
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

ALIAS = {
    "america":"club america", "ame":"club america", "aguilas":"club america",
    "chivas":"guadalajara", "guadalajara":"guadalajara",
    "cruz azul":"cruz azul", "azul":"cruz azul", "maquina":"cruz azul",
    "pumas":"pumas", "unam":"pumas",
    "tigres":"tigres", "uanl":"tigres",
    "monterrey":"monterrey", "rayados":"monterrey",
    "osasuna":"osasuna", "getafe":"getafe", "villarreal":"villarreal",
    "real madrid":"real madrid", "madrid":"real madrid", "barcelona":"barcelona", "barca":"barcelona",
    "inter miami":"inter miami", "miami":"inter miami", "messi":"inter miami"
}

LIGAS = {
    "mex.1": "Liga MX", "usa.1": "MLS",
    "esp.1": "La Liga", "eng.1": "Premier League",
    "ita.1": "Serie A", "ger.1": "Bundesliga"
}

KEYS_LIGA = {
    "mex.1": ["america","chivas","guadalajara","cruz azul","pumas","unam","tigres","monterrey","toluca","santos","atlas","leon","pachuca","necaxa","juarez","queretaro","tijuana","mazatlan","puebla","san luis"],
    "usa.1": ["inter miami","lafc","galaxy","messi","seattle"],
    "esp.1": ["osasuna","getafe","villarreal","real madrid","barcelona","atletico","sevilla","betis","valencia","athletic"],
    "ita.1": ["lecce","roma","inter","milan","juventus","napoli","atalanta"],
    "eng.1": ["arsenal","city","united","liverpool","chelsea","tottenham"],
    "ger.1": ["bayern","dortmund","leverkusen"]
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
 except Exception as e:
  print(f"csv fail {team} {e}", flush=True)
  return None

def get_stats_espn(team, liga_code):
 try:
  original=team
  tc=clean(team)
  for k,v in ALIAS.items():
   if k==tc or k in tc:
    tc=v; break

  r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/teams", timeout=15).json()
  teams = r.get('sports',[{}])[0].get('leagues',[{}])[0].get('teams',[])
  team_id=None; team_name_real=original
  for t in teams:
   name=clean(t['team']['displayName'])
   if tc in name or name in tc or tc[:5] in name:
    team_id=t['team']['id']; team_name_real=t['team']['displayName']; break

  print(f"ES
