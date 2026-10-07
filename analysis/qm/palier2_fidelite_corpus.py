"""
Palier 2 — fidélité du sous-agent mémoire sur le CORPUS REEL (pas les 2 sessions perso).

Échantillon de vraies conversations comparia LONGUES (8-20 tours, FR) — là où le
levier s'active. Pour chacune : on résume le vieil historique (Haiku), et on juge
la fidélité du résumé avec Opus ET Sonnet. Mesure compression + fidélité + κ inter-juges.

Lancer : python analysis/qm/palier2_fidelite_corpus.py
"""
import sys, json, os, re, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
import pyarrow.parquet as pq

N_SAMPLE = 60
KEEP = 4            # derniers tours gardés verbatim
STRIDE = 80         # 1 conv prise toutes les STRIDE candidates (étale l'échantillon)
TMIN, TMAX = 8, 20  # conversations longues
OUT = "analysis/qm/palier2_verdicts.json"
PRICE = {"claude-haiku-4-5": (1.0, 5.0), "claude-opus-4-8": (5.0, 25.0), "claude-sonnet-4-6": (3.0, 15.0)}

SUMM_SYS = ("Tu es un sous-agent memoire. On te donne le DEBUT d'une conversation. Produis un RESUME "
    "STRUCTURE compact pour CONTINUER sans relire le brut. Preserve IMPERATIVEMENT : decisions/faits, "
    "entites/chiffres/noms, le fil et l'objectif, les questions ouvertes. Jette politesses, redites, "
    "verbosite. Sections claires, aussi court que possible SANS perdre une info referencable.")
JUDGE_SYS = ("Evaluateur STRICT de fidelite de resume. HISTORIQUE BRUT + RESUME cense le remplacer. "
    "Le resume perd-il une info IMPORTANTE (decision, fait, entite, chiffre, question ouverte) du brut, "
    "qui empecherait de continuer ? IGNORE style et longueur. JSON SEUL : "
    "{\"verdict\":\"fidele\"|\"perte_mineure\"|\"perte_grave\"}")

def _post(url,h,b,retries=4,timeout=180.0):
    last=None
    for a in range(retries):
        try:
            r=httpx.post(url,headers=h,json=b,timeout=timeout)
            if r.status_code in (429,500,502,503,504) and a<retries-1: time.sleep(3*(a+1)); continue
            return r
        except (httpx.TimeoutException,httpx.TransportError) as e:
            last=e
            if a<retries-1: time.sleep(3*(a+1)); continue
            raise
    raise last

def call(system,user,model,key,max_tokens=2500):
    h={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"}
    r=_post("https://api.anthropic.com/v1/messages",h,
            {"model":model,"max_tokens":max_tokens,"system":[{"type":"text","text":system}],
             "messages":[{"role":"user","content":user}]})
    r.raise_for_status(); d=r.json()
    txt=next((b["text"] for b in d["content"] if b["type"]=="text"),"")
    u=d.get("usage",{}); return txt,u.get("input_tokens",0),u.get("output_tokens",0)

def verdict_of(t):
    m=re.search(r"\{.*\}",t,re.DOTALL)
    try: return json.loads(m.group(0)).get("verdict","?") if m else "?"
    except Exception: return "?"

def main():
    key=os.environ.get("ANTHROPIC_API_KEY")
    if not key: sys.exit("ANTHROPIC_API_KEY absente")
    # --- collecte echantillon ---
    pf=pq.ParquetFile("docs/conversations.parquet")
    sample=[]; matched=0
    for batch in pf.iter_batches(batch_size=8000, columns=["id","conv_turns","languages","conversation_a"]):
        d=batch.to_pydict()
        for i in range(len(d["conv_turns"])):
            ct=d["conv_turns"][i]
            if ct is None or not (TMIN<=ct<=TMAX): continue
            if "fr" not in (d["languages"][i] or []): continue
            conv=d["conversation_a"][i]
            if not conv or len(conv)<=KEEP+2: continue
            matched+=1
            if matched % STRIDE != 1: continue
            old="\n\n".join(f"[{(t.get('role') or '?')}] {t.get('content') or ''}" for t in conv[:len(conv)-KEEP])
            sample.append({"id":int(d["id"][i]),"turns":ct,"old":old})
            if len(sample)>=N_SAMPLE: break
        if len(sample)>=N_SAMPLE: break
    print(f"Echantillon : {len(sample)} conversations FR de {TMIN}-{TMAX} tours (sur {matched} candidates)\n",flush=True)

    cost={"v":0.0}; lock=threading.Lock(); rows=[]
    def work(s):
        summ,sin,sout=call(SUMM_SYS,s["old"],"claude-haiku-4-5",key)
        ju=f"=== BRUT ===\n{s['old']}\n\n=== RESUME ===\n{summ}\n\nEvalue."
        vo,oin,oout=call(JUDGE_SYS,ju,"claude-opus-4-8",key,max_tokens=300)
        vs,nin,nout=call(JUDGE_SYS,ju,"claude-sonnet-4-6",key,max_tokens=300)
        c=(sin*1+sout*5 + oin*5+oout*25 + nin*3+nout*15)/1e6
        bin_=len(s["old"])//4
        return {"id":s["id"],"turns":s["turns"],"brut~":bin_,"resume":sout,
                "ratio":sout/max(sin,1),"opus":verdict_of(vo),"sonnet":verdict_of(vs),"cost":c}
    done=0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs={ex.submit(work,s):s for s in sample}
        for f in as_completed(futs):
            try: rec=f.result()
            except Exception as e: rec={"id":futs[f]["id"],"error":str(e)}
            done+=1
            with lock:
                rows.append(rec); cost["v"]+=rec.get("cost",0)
                json.dump({"verdicts":rows},open(OUT+".tmp","w",encoding="utf-8"),ensure_ascii=False,indent=2)
                os.replace(OUT+".tmp",OUT)
            print(f"  {done}/{len(sample)}  [{rec.get('turns','?')}t] coupe {100*(1-rec.get('ratio',0)):.0f}%  "
                  f"Opus={rec.get('opus','?')} Sonnet={rec.get('sonnet','?')}  cout=${cost['v']:.2f}",flush=True)

    ok=[r for r in rows if "opus" in r]
    def acc(v): return v in ("fidele","perte_mineure")
    import statistics as st
    n=len(ok)
    opus_ok=sum(acc(r["opus"]) for r in ok); son_ok=sum(acc(r["sonnet"]) for r in ok)
    agree=sum(acc(r["opus"])==acc(r["sonnet"]) for r in ok)
    a1=opus_ok/n if n else 0; a2=son_ok/n if n else 0; po=agree/n if n else 0
    pe=a1*a2+(1-a1)*(1-a2); kappa=(po-pe)/(1-pe) if (1-pe) else 1.0
    print(f"\n=== PALIER 2 — fidélité sur {n} vraies conversations comparia ===")
    print(f"  compression moyenne : coupe {100*(1-st.mean([r['ratio'] for r in ok])):.0f}%")
    print(f"  FIDELE/tolerable    : Opus {opus_ok}/{n} ({100*opus_ok/n:.0f}%)  |  Sonnet {son_ok}/{n} ({100*son_ok/n:.0f}%)")
    print(f"  accord Opus<->Sonnet: {agree}/{n} ({100*po:.0f}%)  |  kappa = {kappa:.3f}")
    graves=[(r['id'],r['turns']) for r in ok if r['opus']=='perte_grave' or r['sonnet']=='perte_grave']
    print(f"  pertes graves (>=1 juge) : {len(graves)} {graves[:8]}")
    print(f"  COUT TOTAL : ${cost['v']:.2f}  | verdicts -> {OUT}")

if __name__=="__main__":
    main()
