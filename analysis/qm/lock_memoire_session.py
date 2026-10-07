"""
(b2) VERROUILLER le levier sous-agent memoire : on rejoue le test sur PLUSIEURS
sessions x PLUSIEURS points de compaction x DEUX juges premium.

Pour chaque (session, point) :
  - resume le vieil historique avec Haiku (le redacteur prod, valide en (b))
  - mesure la compression (resume / brut)
  - juge la FIDELITE avec Opus ET Sonnet (le resume perd-il une info referencable ?)

Agrege : taux de fidelite par juge, kappa Opus<->Sonnet (fiabilite du verdict),
compression moyenne, projection economie input par session.

Lancer : python analysis/qm/lock_memoire_session.py
"""
import json, os, re, sys, time
import httpx
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

SESSIONS = [
    ("MAX",  "A:/ClaudeMemory/EIAT_Migrate/Session interface.md"),
    ("FREE", "A:/ClaudeMemory/EIAT_Migrate/Contexte Free-Interface Claude.md"),
]
FRACS = [0.4, 0.6, 0.8]     # on resume les X% premiers segments
KEEP = 6                     # fenetre verbatim (pour la projection)
SUMMARIZER = "claude-haiku-4-5"
JUDGES = ["claude-opus-4-8", "claude-sonnet-4-6"]

SUMM_SYS = (
    "Tu es un sous-agent memoire. On te donne le DEBUT d'une conversation. Produis un RESUME "
    "STRUCTURE compact qui permettra de CONTINUER sans relire le brut. Preserve IMPERATIVEMENT : "
    "decisions/faits actes, entites/chiffres/noms/fichiers, le fil et l'objectif, les questions "
    "ouvertes. Jette : politesses, re-explications, tangentes mortes, verbosite. Sections claires, "
    "aussi court que possible SANS perdre une info referencable."
)
JUDGE_SYS = (
    "Evaluateur STRICT de fidelite de resume. On te donne un HISTORIQUE BRUT et un RESUME cense le "
    "remplacer. Le resume perd-il une info IMPORTANTE (decision, fait, entite, chiffre, question "
    "ouverte) presente dans le brut, qui empecherait de continuer ? IGNORE style et longueur. "
    "Reponds UNIQUEMENT en JSON : {\"verdict\": \"fidele\"|\"perte_mineure\"|\"perte_grave\"}"
)

def _post(url, h, b, retries=4, timeout=180.0):
    last=None
    for a in range(retries):
        try:
            r=httpx.post(url,headers=h,json=b,timeout=timeout)
            if r.status_code in (429,500,502,503,504) and a<retries-1: time.sleep(3*(a+1)); continue
            return r
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last=e
            if a<retries-1: time.sleep(3*(a+1)); continue
            raise
    raise last

def call(system, user, model, key, max_tokens=3000):
    body={"model":model,"max_tokens":max_tokens,"system":[{"type":"text","text":system}],
          "messages":[{"role":"user","content":user}]}
    h={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"}
    r=_post("https://api.anthropic.com/v1/messages",h,body); r.raise_for_status()
    d=r.json(); txt=next((b["text"] for b in d["content"] if b["type"]=="text"),"")
    u=d.get("usage",{}); return txt,u.get("input_tokens",0),u.get("output_tokens",0)

def verdict_of(raw):
    m=re.search(r"\{.*\}", raw, re.DOTALL)
    try: return json.loads(m.group(0)).get("verdict","?") if m else "?"
    except Exception: return "?"

def main():
    key=os.environ.get("ANTHROPIC_API_KEY")
    if not key: sys.exit("ANTHROPIC_API_KEY absente")
    rows=[]
    for sname,path in SESSIONS:
        txt=open(path,encoding="utf-8",errors="replace").read()
        seg=[p.strip() for p in re.split(r'(?m)^\s*\d{1,2}:\d{2}\s*$', txt) if p.strip()]
        N=len(seg)
        for frac in FRACS:
            M=max(4,int(frac*N))
            if M>=N: continue
            old="\n\n".join(seg[:M])
            summ,bin_,bout = call(SUMM_SYS, old, SUMMARIZER, key, max_tokens=3000)
            juser=f"=== HISTORIQUE BRUT ===\n{old}\n\n=== RESUME ===\n{summ}\n\nEvalue."
            verds={}
            for j in JUDGES:
                jt,_,_=call(JUDGE_SYS, juser, j, key, max_tokens=400)
                verds[j]=verdict_of(jt)
            ratio=bout/bin_ if bin_ else 0
            rows.append(dict(session=sname,M=M,N=N,brut=bin_,resume=bout,ratio=ratio,
                             opus=verds[JUDGES[0]],sonnet=verds[JUDGES[1]]))
            print(f"[{sname} {M}/{N} seg]  brut~{bin_}tk -> resume {bout}tk ({100*ratio:.0f}%, coupe {100*(1-ratio):.0f}%)  "
                  f"Opus={verds[JUDGES[0]]}  Sonnet={verds[JUDGES[1]]}", flush=True)

    # --- agregation ---
    def acc(v): return v in ("fidele","perte_mineure")
    n=len(rows)
    opus_ok=sum(acc(r["opus"]) for r in rows)
    son_ok =sum(acc(r["sonnet"]) for r in rows)
    agree=sum(acc(r["opus"])==acc(r["sonnet"]) for r in rows)
    # kappa Cohen sur le binaire acceptable/non
    po=agree/n
    a1=sum(acc(r["opus"]) for r in rows)/n; a2=sum(acc(r["sonnet"]) for r in rows)/n
    pe=a1*a2+(1-a1)*(1-a2)
    kappa=(po-pe)/(1-pe) if (1-pe) else 1.0
    mean_ratio=sum(r["ratio"] for r in rows)/n
    print(f"\n=== AGREGE ({n} points : {len(SESSIONS)} sessions x {len(FRACS)} compactions) ===")
    print(f"  compression moyenne : resume = {100*mean_ratio:.0f}% du brut (coupe {100*(1-mean_ratio):.0f}%)")
    print(f"  FIDELE/tolerable    : Opus {opus_ok}/{n} ({100*opus_ok/n:.0f}%)  |  Sonnet {son_ok}/{n} ({100*son_ok/n:.0f}%)")
    print(f"  accord Opus<->Sonnet : {agree}/{n} ({100*po:.0f}%)  |  kappa Cohen = {kappa:.3f}")
    graves=[r for r in rows if r["opus"]=="perte_grave" or r["sonnet"]=="perte_grave"]
    print(f"  pertes graves (au moins 1 juge) : {len(graves)}  {[(r['session'],r['M']) for r in graves]}")

    # --- projection economie input par session (ratio mesure de la session) ---
    print("\n=== PROJECTION economie input session (ratio mesure) ===")
    for sname,path in SESSIONS:
        seg=[max(1,len(p.strip())//4) for p in re.split(r'(?m)^\s*\d{1,2}:\d{2}\s*$', open(path,encoding='utf-8',errors='replace').read()) if p.strip()]
        N=len(seg)
        rr=[r["ratio"] for r in rows if r["session"]==sname]
        R=sum(rr)/len(rr) if rr else 0.1
        def cum(compact):
            tot=0
            for t in range(1,N+1):
                hist=seg[:t-1]
                if compact and len(hist)>KEEP:
                    inp=int(sum(hist[:-KEEP])*R)+sum(hist[-KEEP:])
                else: inp=sum(hist)
                tot+=inp+seg[t-1]
            return tot
        s0,s1=cum(False),cum(True)
        print(f"  {sname:5} ({N} tours, ratio {100*R:.0f}%) : {s0} -> {s1} tk  = -{100*(s0-s1)/s0:.0f}% input")

if __name__=="__main__":
    main()
