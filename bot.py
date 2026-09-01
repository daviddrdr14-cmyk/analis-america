import os, time, pandas as pd, re, requests
from flask import Flask
from threading import Thread
import telebot

app = Flask(__name__)
@app.route('/')
def home(): return "OK V27 AMERICA AUTO"
Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))), daemon=True).start()

TOKEN=os.getenv("BOT_TOKEN")
bot=telebot.TeleBot(TOKEN)
bot.remove_webhook()
time.sleep(2)

def clean(t):
 t=t.lower()
 t=t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n')
 return t.strip()

# === LIGAS DE AMERICA DONDE VA A LEER AUTOMATICO ===
LIGAS_AMERICA = {
    "mex.1": "Liga MX",
    "usa.1": "MLS",
    "bra.1": "Brasileirao",
    "arg.1": "Liga Argentina",
    "col.1": "Liga Colombia",
    "chi.1": "Liga Chile",
    "ecu.1": "Liga Ecuador",
    "peru.1": "Liga Peru"
}

# Palabras clave para detectar de que liga es
KEYS_LIGA = {
    "mex.1": ["america","chivas","cruz azul","pumas","tigres","monterrey","toluca","santos","atlas","leon","pachuca","necaxa","juarez","queretaro","tijuana","mazatlan","puebla","san luis"],
    "usa.1": ["inter miami","lafc","galaxy","seattle","atlanta","columbus","cincinnati","messi","austin","dallas","houston","portland","nycfc","red bulls"],
    "bra.1": ["flamengo","palmeiras","corinthians","sao paulo","santos","gremio","botafogo","fluminense","atletico mineiro","cruzeiro","vasco"],
    "arg.1": ["river","boca","racing","independiente","san lorenzo","velez","estudiantes","rosario","newells","talleres","lanus"],
    "col.1": ["nacional","millonarios","america de cali","junior","santa fe","medellin","cali","tolima"],
    "chi.1": ["colo colo","u de chile","catolica","audax"],
    "ecu.1": ["barcelona sc","emelec","ldu","independiente del valle"],
    "peru.1": ["alianza lima","universitario","cristal"]
}

def detect_liga(t):
 t=clean(t)
 # 1. Busca primero en América
 for code, equipos in KEYS_LIGA.items():
  for eq in equipos:
   if eq in t:
    return code
 # 2. Si es europeo, usa tu logica vieja
 if "osasuna" in t or "getafe" in t or "villarreal" in t: return "SP1"
 if "lecce" in t or "roma" in t: return "I1"
 if "braga" in t or "benfica" in t: return "P1"
 return "mex.1" # por defecto Liga MX

def get_stats_america(team, liga_code):
 try:
  # Busca el ID del equipo en ESPN
  tc=clean(team)
  r = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/teams", timeout=10).json()
  team_id = None
  team_name_real = team
  for t in r.get('sports',[{}])[0].get('leagues',[{}])[0].get('teams',[]):
   name = t['team']['displayName']
   if tc in clean(name) or clean(name) in tc or tc[:4] in clean(name):
    team_id = t['team']['id']
    team_name_real = name
    break

  # Trae ultimos 10 juegos de ese equipo
  if team_id:
   url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/teams/{team_id}/schedule"
  else:
   # Si no encuentra ID, usa scoreboard general de la liga
   url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga_code}/scoreboard"

  data = requests.get(url, timeout=10).json()
  games = data.get('events', [])[:10]

  ht=goles=[]; btts=0; total=0; corners=[]
  for ev in games:
   comp = ev['competitions'][0]
   # HT y FT si existen
   try:
    fth = int(comp['competitors'][0]['score']); fta = int(comp['competitors'][1]['score'])
    total+=1
    goles.append(fth+fta)
    if fth>0 and fta>0: btts+=1
    # ESPN a veces trae estadistica de HT
    ht.append(1 if fth+fta>0 else 0)
   except: pass

  if total==0: return None

  return {
   "name": team_name_real.title(),
   "ht": int(sum(ht)/len(ht)*100) if ht else 50,
   "o15": int(sum([1 for g in goles if g>1.5])/len(goles)*100),
   "o25": int(sum([1 for g in goles if g>2.5])/len(goles)*100),
   "btts": int(btts/total*100),
   "corn": 9.2, # ESPN no da corners gratis, dejamos promedio liga
   "corn_ht": 4.1
  }
 except Exception as e:
  print("error america",e)
  return None

def get_stats(team,liga):
 # Si es liga americana, lee de ESPN AUTO
 if liga in LIGAS_AMERICA:
  return get_stats_america(team, liga)
 # Si es europea, usa tu metodo viejo de CSV (football-data)
 try:
  tc=clean(team)
  df=pd.read_csv(f"https://www.football-data.co.uk/mmz4281/2526/{liga}.csv")
  df['hc']=df['HomeTeam'].apply(lambda x: clean(str(x)))
  df['ac']=df['AwayTeam'].apply(lambda x: clean(str(x)))
  m=df['hc'].str.contains(tc,na=False)|df['ac'].str.contains(tc,na=False)
  d=df[m].tail(5)
  if d.empty:
   d=df[df['hc'].str.contains(tc[:4],na=False)|df['ac'].str.contains(tc[:4],na=False)].tail(5)
  if d.empty: d=df.tail(5)
  ht=int(((d["HTHG"]+d["HTAG"])>0).mean()*100)
  o15=int(((d["FTHG"]+d["FTAG"])>1.5).mean()*100)
  o25=int(((d["FTHG"]+d["FTAG"])>2.5).mean()*100)
  btts=int(((d["FTHG"]>0)&(d["FTAG"]>0)).mean()*100)
  corn=round((d["HC"]+d["AC"]).mean(),1)
  corn_ht=round(corn*0.45,1)
  return {"name":team.title(),"ht":ht,"o15":o15,"o25":o25,"btts":btts,"corn":corn,"corn_ht":corn_ht}
 except: return None

def armar(s1,s2, liga_code):
 liga_nombre = LIGAS_AMERICA.get(liga_code, liga_code)
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

@bot.message_handler(content_types=['photo'])
def handle_photo(m):
 bot.reply_to(m,"Mándamelo escrito porfa: Ej. America vs Chivas")

@bot.message_handler(func=lambda m: True)
def handle(m):
 try:
  txt=m.text
  if not txt or "vs" not in txt.lower(): return
  p=re.split(r'\s+vs\s+',txt, flags=re.IGNORECASE)
  if len(p)<2: return
  l=p[0].strip(); v=p[1].strip()
  if len(l)<3 or len(v)<3: return
  liga=detect_liga(l+" "+v)
  s1=get_stats(l,liga); s2=get_stats(v,liga)
  if not s1 or not s2:
   bot.reply_to(m,f"No encontre {l} o {v} en {liga}"); return
  bot.reply_to(m, armar(s1,s2, liga))
 except Exception as e:
  print(e)

print("BOT V27 AMERICA LISTO",flush=True)
bot.infinity_polling(timeout=90,long_polling_timeout=90,skip_pending=True)
