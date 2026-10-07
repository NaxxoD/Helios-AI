"""
Test du SOUS-AGENT MEMOIRE d'Helios sur une vraie session.

Principe : sur une session reelle (multi-tours), on prend le DEBUT (le "vieil
historique" qui serait reinjecte a chaque tour) et on le remplace par un RESUME
STRUCTURE. On mesure :
  (a) tokens economises  = 1 - (taille resume / taille brut)
  (b) fidelite (grille)  = le resume perd-il une info referencable ? (juge Opus)
  (c) effet du modele redacteur : Haiku vs Sonnet vs Opus (la question d'AD)
  (d) LATENCE du resumeur SEUL = combien de secondes le sous-agent ajoute par tour
      de compaction (mediane de N_TIMING appels, juge EXCLU)

Lancer : python analysis/qm/test_memoire_session.py
"""
import json, os, re, sys, time
import httpx
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

SESSION = "A:/ClaudeMemory/EIAT_Migrate/Session interface.md"
KEEP_RECENT = 6          # nb de segments recents gardes VERBATIM (non resumes)
N_TIMING = 3             # nb d'appels resumeur pour une latence MEDIANE (le juge ne tourne qu'1 fois)
PRICE = {"claude-haiku-4-5": (1.0, 5.0), "claude-sonnet-4-6": (3.0, 15.0), "claude-opus-4-8": (5.0, 25.0)}

SUMM_SYS = (
    "Tu es un sous-agent memoire. On te donne le DEBUT d'une conversation (plusieurs tours). "
    "Produis un RESUME STRUCTURE compact qui permettra au modele principal de CONTINUER la "
    "conversation sans relire le brut. Preserve IMPERATIVEMENT : decisions et faits actes, "
    "entites / chiffres / noms / fichiers cites, le fil et l'objectif courant, les questions ouvertes. "
    "Jette : politesses, re-explications, tangentes abandonnees, verbosite. "
    "Sections claires. Aussi court que possible SANS perdre une info referencable."
)
JUDGE_SYS = (
    "Tu es un evaluateur STRICT de fidelite de resume. On te donne un HISTORIQUE BRUT et un RESUME "
    "cense le remplacer dans la suite de la conversation. Question : le resume perd-il une information "
    "IMPORTANTE (decision, fait, entite, chiffre, question ouverte) presente dans le brut, qui "
    "empecherait de continuer correctement ? IGNORE le style et la longueur (un resume plus court qui "
    "garde le fond est PARFAIT). Reponds UNIQUEMENT en JSON : "
    "{\"verdict\": \"fidele\"|\"perte_mineure\"|\"perte_grave\", \"manque\": \"...\"}"
)

def _post(url, headers, body, retries=4, timeout=180.0):
    last=None
    for a in range(retries):
        try:
            r=httpx.post(url,headers=headers,json=body,timeout=timeout)
            if r.status_code in (429,500,502,503,504) and a<retries-1: time.sleep(3*(a+1)); continue
            return r
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last=e
            if a<retries-1: time.sleep(3*(a+1)); continue
            raise
    raise last

def call(system, user, model, api_key, max_tokens=1500):
    body={"model":model,"max_tokens":max_tokens,"system":[{"type":"text","text":system}],
          "messages":[{"role":"user","content":user}]}
    h={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"}
    r=_post("https://api.anthropic.com/v1/messages",h,body); r.raise_for_status()
    d=r.json(); txt=next((b["text"] for b in d["content"] if b["type"]=="text"),"")
    u=d.get("usage",{}); return txt,u.get("input_tokens",0),u.get("output_tokens",0)

def main():
    api_key=os.environ.get("ANTHROPIC_API_KEY")
    if not api_key: sys.exit("ANTHROPIC_API_KEY absente")
    txt=open(SESSION,encoding="utf-8",errors="replace").read()
    seg=[p.strip() for p in re.split(r'(?m)^\s*\d{1,2}:\d{2}\s*$', txt) if p.strip()]
    n=len(seg)
    old="\n\n".join(seg[:n-KEEP_RECENT])      # le bloc a resumer
    print(f"Session : {n} segments | on resume les {n-KEEP_RECENT} premiers, on garde {KEEP_RECENT} verbatim")
    print(f"Bloc brut a resumer : ~{len(old)//4} tokens (approx)\n")

    results={}
    for model in ["claude-haiku-4-5","claude-sonnet-4-6","claude-opus-4-8"]:
        # LATENCE DU RESUMEUR SEUL : N_TIMING appels chronometres (perf_counter), juge EXCLU.
        # On garde le 1er resume pour la fidelite/le cout ; les reps ne servent qu'a la mediane.
        durs=[]; summ=None; in_tok=out_tok=0
        for k in range(N_TIMING):
            t=time.perf_counter()
            s, itk, otk = call(SUMM_SYS, old, model, api_key, max_tokens=2000)
            durs.append(time.perf_counter()-t)
            if k==0: summ, in_tok, out_tok = s, itk, otk
        durs.sort()
        dur_summ = durs[len(durs)//2]                       # latence MEDIANE du resumeur seul
        tok_s = out_tok/dur_summ if dur_summ else 0          # debit (plus stable que la latence brute)
        # juge la fidelite avec Opus (constant), brut vs resume — UNE seule fois, hors chrono
        juser=f"=== HISTORIQUE BRUT ===\n{old}\n\n=== RESUME (a evaluer) ===\n{summ}\n\nEvalue la fidelite."
        jtxt, jin, jout = call(JUDGE_SYS, juser, "claude-opus-4-8", api_key, max_tokens=600)
        m=re.search(r"\{.*\}", jtxt, re.DOTALL);
        try: verdict=json.loads(m.group(0)) if m else {"verdict":"?","manque":jtxt[:80]}
        except Exception: verdict={"verdict":"?","manque":jtxt[:80]}
        pin,pout=PRICE[model]
        cost_summ = in_tok*pin/1e6 + out_tok*pout/1e6        # cout d'UN resume (per-tour), pas des reps
        cost_judge = jin*5.0/1e6 + jout*25.0/1e6
        ratio = out_tok/in_tok if in_tok else 0
        results[model]=dict(brut=in_tok,resume=out_tok,ratio=ratio,verdict=verdict.get("verdict"),
                            manque=verdict.get("manque","")[:120],cost=cost_summ+cost_judge,
                            dur=dur_summ,tok_s=tok_s)
        print(f"[{model}]  brut~{in_tok}tk -> resume {out_tok}tk  (={100*ratio:.0f}% du brut, coupe {100*(1-ratio):.0f}%)")
        print(f"          fidelite (juge Opus) : {verdict.get('verdict')}  | manque: {verdict.get('manque','')[:90]}")
        print(f"          cout {results[model]['cost']:.3f}$  | latence resumeur SEUL {dur_summ:.1f}s (mediane/{N_TIMING}, {tok_s:.0f} tok/s)\n")

    print("=== SYNTHESE ===")
    print(f"{'redacteur':22}{'coupe':>8}{'fidelite':>16}{'cout':>9}{'latence':>10}")
    for model,r in results.items():
        print(f"{model:22}{100*(1-r['ratio']):>7.0f}%{r['verdict']:>16}{r['cost']:>8.3f}${r['dur']:>8.1f}s")
    # cout REELLEMENT depense = N_TIMING resumes + 1 juge par modele (le 'cost' stocke = 1 resume + 1 juge, per-tour)
    tot=sum(r['cost'] + (N_TIMING-1)*r['resume']*PRICE[m][1]/1e6 + (N_TIMING-1)*r['brut']*PRICE[m][0]/1e6
            for m,r in results.items())
    print(f"\ncout total test (incl. {N_TIMING} appels resumeur/modele pour le chrono) : {tot:.3f}$")
    # projection economie INPUT session : si on remplace le brut (B tk) par le resume (S tk)
    # a chaque tour apres compaction, on reinjecte S au lieu de B
    avg_ratio=sum(r['ratio'] for r in results.values())/len(results)
    print(f"\nProjection : apres compaction, on reinjecte ~{100*avg_ratio:.0f}% du vieil historique a chaque tour")
    print(f"-> economie input sur la partie compactee : ~{100*(1-avg_ratio):.0f}% (a qualite verifiee par la grille)")

if __name__=="__main__":
    main()
