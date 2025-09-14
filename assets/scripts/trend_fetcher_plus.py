#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, re, csv, math
from datetime import datetime, timezone
from urllib.request import urlopen, Request

DAILY_URL = "https://trends.google.com/trends/api/dailytrends?hl=de-DE&tz=120&geo=DE"
TIKTOK_CSV = "data/tiktok_keywords.csv"
SALES_JSON = "data/sales_feedback.json"

NICHES = {
    "Kleidung":["jacke","lederjacke","hose","jeans","shirt","t-shirt","sneaker","pullover","hoodie","trikot","kleid","vintage","mode","fashion","stiefel","schuhe","cap","mütze","mantel","gürtel"],
    "Elektronik":["iphone","samsung","xiaomi","huawei","smartphone","konsole","ps5","playstation","xbox","nintendo","switch","kopfhörer","airpods","tablet","laptop","grafikkarte","rtx","ssd","ram","fernseher","tv","monitor","kamera","drohne","router"],
    "Motorrad":["motorrad","helm","lederkombi","handschuh","auspuff","kettenkit","reifen","bmw gs","r nine t","ducati","yamaha","ktm","honda","suzuki","kawasaki","harley","harley-davidson","touring","enduro","topcase","navihalter"]
}
WEIGHTS={"traffic":0.55,"media":0.15,"keywords":0.20,"news_penalty":0.10,"tiktok":0.30,"personal":0.25}
NEWS_TERMS=r'\b(bundestag|wahl|kanzler|minister|bundesliga|em|wm|spiel|tor|transfer)\b'

def log2p1(x): 
    import math; return math.log2(max(1.0,x)+1.0)
def normalized_number(s):
    if not s: return 0.0
    s=s.replace('\u202f','').replace('.','').replace(',','')
    m=re.search(r'(\d+)',s)
    return float(m.group(1)) if m else 0.0
def niche_for(title):
    t=(title or "").lower()
    best,hits=None,0
    for n,kws in NICHES.items():
        h=sum(1 for kw in kws if kw in t)
        if h>hits: best,hits=n,h
    return best or "Sonstiges"

def apply_personal_boost(score,title,sales):
    if not sales: return score
    t=(title or "").lower()
    for ent in sales.get("boost_terms",[]):
        term=(ent.get("term") or "").lower().strip()
        w=float(ent.get("weight",1.0))
        if term and term in t: score+=100*WEIGHTS["personal"]*min(1.0,(w-0.8))
    return score

def fetch_google_daily():
    req=Request(DAILY_URL,headers={"User-Agent":"Mozilla/5.0"})
    with urlopen(req,timeout=25) as resp:
        raw=resp.read().decode("utf-8")
    if raw.startswith(")]}',"): raw=raw[5:]
    data=json.loads(raw)
    items=[]
    for day in data.get("default",{}).get("trendingSearchesDays",[]):
        for tr in day.get("trendingSearches",[]):
            title=tr.get("title",{}).get("query","")
            traffic=normalized_number(tr.get("formattedTraffic",""))
            media=len(tr.get("articles",[]))
            penalty=1.0 if re.search(NEWS_TERMS,title.lower()) else 0.0
            niche=niche_for(title)
            kw=sum(1 for kw in NICHES.get(niche,[]) if kw in title.lower())
            score=100.0*(WEIGHTS["traffic"]*(log2p1(traffic)/16.0)+WEIGHTS["media"]*min(1.0,media/10.0)+WEIGHTS["keywords"]*min(1.0,kw/4.0)-WEIGHTS["news_penalty"]*penalty)
            items.append({
                "title":title,"niche":niche,"score":max(0,min(100,score)),"sources":["GoogleTrends"],
                "formattedTraffic":tr.get("formattedTraffic",""),
                "articles":[{"title":a.get("title",""),"url":a.get("url","")} for a in tr.get("articles",[])],
                "shareUrl":tr.get("shareUrl","")
            })
    dedup={}
    for it in items:
        k=(it["title"] or "").lower()
        if k not in dedup or it["score"]>dedup[k]["score"]: dedup[k]=it
    return list(dedup.values())

def parse_tiktok_csv():
    if not os.path.exists(TIKTOK_CSV): return []
    items=[]
    with open(TIKTOK_CSV,encoding="utf-8") as f:
        for row in csv.DictReader(f):
            title=row.get("keyword") or row.get("hashtag") or row.get("term") or ""
            if not title: continue
            v=float(re.sub(r"[^\d]","",row.get("views","") or "0") or 0)
            g=float(re.sub(r"[^\d\.\-]","",row.get("growthRate","") or "0") or 0)
            niche=niche_for(title)
            score=100.0*WEIGHTS["tiktok"]*min(1.0,(log2p1(v)/30.0+(g/100.0)))
            items.append({"title":title,"niche":niche,"score":max(0,min(100,score)),"sources":["TikTokCSV"],"tiktokViews":v,"tiktokGrowth":g})
    dedup={}
    for it in items:
        k=(it["title"] or "").lower()
        if k not in dedup or it["score"]>dedup[k]["score"]: dedup[k]=it
    return list(dedup.values())

def load_sales():
    if not os.path.exists(SALES_JSON): return {}
    try: return json.load(open(SALES_JSON,encoding="utf-8"))
    except: return {}

def merge(*lists,sales=None):
    out={}
    for lst in lists:
        for it in lst:
            k=(it.get("title") or "").lower()
            if not k: continue
            if k not in out: out[k]={**it}
            else:
                out[k]["score"]=min(100,(out[k]["score"]+it["score"]))
                out[k]["sources"]=sorted(set(out[k]["sources"]+it["sources"]))
    for it in out.values():
        it["score"]=max(0,min(100,apply_personal_boost(it["score"],it["title"],sales)))
    return sorted(out.values(),key=lambda x:x["score"],reverse=True)

def main():
    g=fetch_google_daily()
    t=parse_tiktok_csv()
    s=load_sales()
    items=merge(g,t,sales=s)
    payload={"source":{"google":True,"tiktok_csv":bool(t)},"fetched_at":datetime.now(timezone.utc).isoformat(),"items":items}
    with open("trends.json","w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)
    print("Schreibe trends.json –",len(items),"Einträge")
if __name__=="__main__": main()
