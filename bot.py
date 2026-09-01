import os, time, pandas as pd, re, requests, random
from flask import Flask
from threading import Thread
import telebot

app = Flask(__name__)
@app.route('/')
def home(): return "OK V32 APERTURA 2025 J5"

def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
Thread(target=run_web, daemon=True).start()

def keep_alive():
    while True:
        time.sleep(600)
        try:
            url=os.getenv("RENDER_EXTERNAL_URL")
            if url: requests.get(url, timeout=10)
        except: pass
Thread(target=keep_alive, daemon=True).start()

TOKEN=os.getenv("BOT_TOKEN")
bot=telebot.TeleBot(TOKEN, threaded=False)
try: bot.remove_webhook(); time.sleep(1)
except: pass

def clean(t):
 t=t.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')
 return t.strip()

ALIAS = {"america":"club america","ame":"club america","chivas":"guadalajara","guadalajara":"guadalajara","cruz azul":"cruz azul","pumas":"pumas","unam":"pumas","tigres":"tigres","monterrey":"monterrey","osasuna":"osasuna","getafe":"getafe"}

def detect_liga(t):
 t=clean(t)
 if any(x in t for x in ["osasuna","getafe","villarreal","real madrid","barcelona"]): return "esp.1"
 if any(x in t for x in ["inter miami","lafc","messi"]): return "usa.1"
 return "mex.1"

def get_stats_espn(team, liga):
 try:
  tc=clean(team)
  for k,v in ALIAS.items():
   if k in tc: tc=v; break

  # 1. Buscar ID del equipo
  r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/teams", timeout=15).json()
  teams = r.get('sports',[{}])[0].get('leagues',[{}])[0].get('teams',[])
  team_id=None; team_name=team.title()
  for t in teams:
   if tc in clean(t['team']['displayName']) or clean(t['team']['displayName']) in tc:
    team_id=t['team']['id']; team_name=t['team']['displayName']; break
  if not team_id: return None

  # 2. JALAR TEMPORADA 2025 (Apertura actual) y 2024 si falla
  goles=[]; btts=0; total=0
  for season in [2025, 2024]:
   try:
    url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/teams/{team_id}/schedule?season={season}"
    data=requests.get(url, timeout=15).json()
    events=data.get('events',[])[:15]
    for ev in events:
     try:
      comp=ev['competitions'][0]
      if comp['status']['type']['completed']==False: continue # solo finalizados
      c1=comp['competitors'][0]; c2=comp['competitors'][1]
      if 'score' not in c1: continue
      s1=int(float(c1['score'])); s2=int(float(c2['score']))
      total+=1; goles.append(s1+s2)
      if s1>0 and s2>0: btts+=1
     except: continue
    if total>=5: break
   except: continue

  print(f"STATS {team_name} {liga} 2025 -> {total} partidos {goles}", flush=True)
  if total>=2:
   return {
    "name":team_name.title(),
    "ht": 68 if sum(goles)/len(goles)>1.2 else 55,
    "o15": int(sum(1 for g in goles if g>1.5)/len(goles)*100),
    "o25": int(sum(1 for g in goles if g>2.5)/len(goles)*100),
    "btts": int(btts/total*100),
    "corn": 9.4, "corn_ht": 4.2
   }
  return None
 except Exception as e:
  print(f"espn error {e}", flush=True); return None

def get_stats_csv(team, liga_csv):
 try:
  if not liga_csv: return None
  tc=clean(team)
  df=pd.read_csv(f"https://www.football-data.co.uk/mmz4281/2526/{liga_csv}.csv")
  df['hc']=df['HomeTeam'].apply(lambda x: clean(str(x))); df['ac']=df['AwayTeam'].apply(lambda x: clean(str(x)))
  m=df['hc'].str.contains(tc,na=False)|df['ac'].str.contains(tc,na=False); d=df[m].tail(10)
  if len(d)<3: return None
  return {"name":team.title(),"ht":int(((d["HTHG"]+d["HTAG"])>0).mean()*100),"o15":int(((d["FTHG"]+d["FTAG"])>1.5).mean()*100),"o25":int(((d["FTHG"]+d["FTAG"])>2.5).mean()*100),"btts":int(((d["FTHG"]>0)&(d["FTAG"]>0)).mean()*100),"corn":round((d["HC"]+d["AC"]).mean(),1) if "HC" in d else 9.1,"corn_ht":4.1}
 except: return None

def get_stats(team, liga):
 s=get_stats_espn(team, liga)
 if s: return s
 # fallback europa
 mapa={"esp.1":"SP1","eng.1":"E0","ita.1":"I1"}
 s2=get_stats_csv(team, mapa.get(liga))
 if s2: return s2
 return {"name":team.title(),"ht":60,"o15":72,"o25":52,"btts":50,"corn":9.0,"corn_ht":4.0}

def armar(s1,s2, liga):
 avg_ht=int((s1['ht']+s2['ht'])/2); avg_o15=int((s1['o15']+s2['o15'])/2); avg_o25=int((s1['o25']+s2['o25'])/2); avg_btts=int((s1['btts']+s2['btts'])/2)
 rec=f"{'GOL 1T SI' if avg_ht>=60 else 'GOL 1T NO'} {avg_ht}%\nOVER 1.5 {avg_o15}%\nOVER 2.5 {avg_o25}%\nBTTS {'SI' if avg_btts>=55 else 'NO'} {avg_btts}%\nCORNERS {(s1['corn']+s2['corn'])/2:.1f}\n"
 return f"🏆 {liga}\n{s1['name']} vs {s2['name']}\nHT {s1['ht']}%/{s2['ht']}% -> {avg_ht}%\nO1.5 {s1['o15']}%/{s2['o15']}% O2.5 {s1['o25']}%/{s2['o25']}%\nBTTS {s1['btts']}%/{s2['btts']}%\n\nRECOM:\n{rec}"

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m,"🦅 V32 J5 listo! America vs Chivas")

@bot.message_handler(func=lambda m: True)
def handle(m):
 try:
  txt=(m.text or "").strip()
  if "vs" not in txt.lower(): return
  l,v=re.split(r'\s+vs\s+',txt, flags=re.IGNORECASE)
  liga=detect_liga(l+" "+v)
  s1=get_stats(l.strip(),liga); s2=get_stats(v.strip(),liga)
  bot.reply_to(m, armar(s1,s2,liga))
 except Exception as e: print(e, flush=True)

print("V32 APERTURA 2025 LISTO",flush=True)
bot.infinity_polling(timeout=90,long_polling_timeout=90,skip_pending=True)
