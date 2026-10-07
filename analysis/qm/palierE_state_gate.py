"""Palier État — mesure HORS-LIGNE du gate de cohérence d'état (retour du co-auteur).

Question (inconnue n°1 d'co-auteur) : un juge ABORDABLE (Haiku) attrape-t-il les contradictions
d'état d'un résumé, et à quel taux de faux positifs / coût ? On répond AVANT tout câblage
sur le chemin de requête (prod) — pur offline sur l'API, en crédits.

Méthode (labels CONTRÔLÉS) : sur des conversations comparia longues contenant un changement
d'état (un problème puis sa RÉSOLUTION), pour chacune :
  - résumé FIDÈLE   (Haiku, prompt MEMORY_SYS du code)         → label attendu : PAS de contradiction
  - résumé CORROMPU (Sonnet fige l'état au moment du blocage)  → label attendu : CONTRADICTION
On fait juger les deux par le state judge (Haiku, STATE_GATE_SYS du code) et on mesure :
  - rappel        = % des corrompus correctement détectés (contradiction=true)
  - faux positifs = % des fidèles wrongly flaggés (contradiction=true)
  - coût total.

⚠️ La corruption est SYNTHÉTIQUE (proxy d'une vraie péremption d'état) — borne, pas vérité
terrain. n petit → IC large. Reproduit la discipline « mesurer avant de lancer ».

Lancer : python analysis/qm/palierE_state_gate.py [N]   (défaut N=30 ; smoke : 4)
"""
import sys, os, json, re, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from services.memory_service import STATE_GATE_SYS, MEMORY_SYS, render_history  # cohérence live
import pyarrow.parquet as pq

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
DEBUG = os.environ.get("PALIERE_DEBUG") == "1"   # capture textes (résumés + verdicts) pour diagnostic
KEEP = 4
TMIN, TMAX = 8, 20
STRIDE = 5
PARQUET = os.path.join(ROOT, "docs", "conversations.parquet")
OUT = os.path.join(ROOT, "analysis", "qm", "palierE_verdicts.json")

SUMM_MODEL = "claude-haiku-4-5"      # rédacteur (comme apply_memory)
CORRUPT_MODEL = "claude-sonnet-4-6"  # corrupteur (génère la péremption d'état contrôlée)
JUDGE_MODEL = "claude-haiku-4-5"     # le GATE sous test (= le juge abordable)
PREMIUM_JUDGE = "claude-sonnet-4-6"  # bonus : juge premium sur les MÊMES positifs (cheap vs premium)

# Marqueurs de résolution → la conv contient probablement un changement d'état
MARKERS = ["résolu", "resolu", "corrigé", "corrige", "réglé", "regle", "ça marche", "ca marche",
           "fonctionne maintenant", "finalement", "c'est bon", "réparé", "repare", "ça y est",
           "ca y est", "problème est réglé", "marche enfin"]

CORRUPT_SYS = (
    "On te donne un RÉSUMÉ fidèle d'une conversation. Si la conversation contient un problème / "
    "blocage qui a FINI par être RÉSOLU, réécris le résumé en FIGEANT l'état au moment du blocage : "
    "présente le problème comme ENCORE non résolu / toujours bloqué, en retirant toute mention de la "
    "résolution finale, et en gardant TOUT le reste identique (entités, chiffres, décisions). Renvoie "
    "UNIQUEMENT ce résumé réécrit.\n"
    "Si la conversation ne contient AUCUN problème résolu à figer, réponds EXACTEMENT : NO_STATE_CHANGE"
)


def _post(url, h, b, retries=4, timeout=180.0):
    last = None
    for a in range(retries):
        try:
            r = httpx.post(url, headers=h, json=b, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504) and a < retries - 1:
                time.sleep(3 * (a + 1)); continue
            return r
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last = e
            if a < retries - 1: time.sleep(3 * (a + 1)); continue
            raise
    raise last


PRICE = {"claude-haiku-4-5": (1.0, 5.0), "claude-sonnet-4-6": (3.0, 15.0)}


def call(system, user, model, key, max_tokens=1200):
    h = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    r = _post("https://api.anthropic.com/v1/messages", h,
              {"model": model, "max_tokens": max_tokens,
               "system": [{"type": "text", "text": system}],
               "messages": [{"role": "user", "content": user}]})
    r.raise_for_status(); d = r.json()
    txt = next((b["text"] for b in d["content"] if b["type"] == "text"), "")
    u = d.get("usage", {})
    pin, pout = PRICE[model]
    cost = (u.get("input_tokens", 0) * pin + u.get("output_tokens", 0) * pout) / 1e6
    return txt, cost


def contradiction(t):
    # Lit le booléen directement (robuste à un JSON tronqué par max_tokens : le champ
    # "detail" verbeux vient APRÈS et n'empêche pas la lecture du verdict).
    m = re.search(r'"contradiction"\s*:\s*(true|false)', t or "", re.IGNORECASE)
    return (m.group(1).lower() == "true") if m else None


def main():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: sys.exit("ANTHROPIC_API_KEY absente")

    pf = pq.ParquetFile(PARQUET)
    sample = []; matched = 0
    for batch in pf.iter_batches(batch_size=8000,
                                 columns=["id", "conv_turns", "languages", "conversation_a"]):
        d = batch.to_pydict()
        for i in range(len(d["conv_turns"])):
            ct = d["conv_turns"][i]
            if not ct or not (TMIN <= ct <= TMAX): continue
            if "fr" not in (d["languages"][i] or []): continue
            conv = d["conversation_a"][i]
            if not conv or len(conv) <= KEEP + 2: continue
            fold = conv[:len(conv) - KEEP]
            old = render_history([{"role": t.get("role") or "?", "content": t.get("content") or ""}
                                  for t in fold])
            if not any(mk in old.lower() for mk in MARKERS): continue   # changement d'état probable
            matched += 1
            if matched % STRIDE != 1: continue
            sample.append({"id": int(d["id"][i]), "turns": ct, "old": old})
            if len(sample) >= N: break
        if len(sample) >= N: break
    print(f"Échantillon : {len(sample)} convs FR {TMIN}-{TMAX}t avec marqueur de résolution "
          f"(sur {matched} candidates)\n", flush=True)

    cost = {"v": 0.0}; lock = threading.Lock(); rows = []

    def work(s):
        faithful, c1 = call(MEMORY_SYS, s["old"], SUMM_MODEL, key)
        corrupted, c2 = call(CORRUPT_SYS, faithful, CORRUPT_MODEL, key)
        state_changed = not corrupted.strip().upper().startswith("NO_STATE_CHANGE")
        jf = f"=== BRUT ===\n{s['old']}\n\n=== RÉSUMÉ ===\n{faithful}\n\nVérifie."
        vf, c3 = call(STATE_GATE_SYS, jf, JUDGE_MODEL, key, 250)
        caught, caught_premium, vc, vcp, c4, c5 = None, None, "", "", 0.0, 0.0
        if state_changed:   # contradiction réellement injectée → cas de rappel valide
            jc = f"=== BRUT ===\n{s['old']}\n\n=== RÉSUMÉ ===\n{corrupted}\n\nVérifie."
            vc, c4 = call(STATE_GATE_SYS, jc, JUDGE_MODEL, key, 250)
            caught = contradiction(vc)
            vcp, c5 = call(STATE_GATE_SYS, jc, PREMIUM_JUDGE, key, 250)  # même cas, juge premium
            caught_premium = contradiction(vcp)
        rec = {"id": s["id"], "turns": s["turns"], "state_changed": state_changed,
               "faithful_flagged": contradiction(vf),   # attendu False
               "corrupt_caught": caught,                 # Haiku (attendu True si state_changed)
               "corrupt_caught_premium": caught_premium,  # Sonnet, mêmes cas
               "cost": c1 + c2 + c3 + c4 + c5}
        if DEBUG:
            rec["_old_tail"] = s["old"][-600:]
            rec["_faithful"] = faithful
            rec["_corrupted"] = corrupted
            rec["_vf_raw"] = vf
            rec["_vc_raw"] = vc
        return rec

    done = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(work, s): s for s in sample}
        for f in as_completed(futs):
            try: rec = f.result()
            except Exception as e: rec = {"id": futs[f]["id"], "error": str(e)}
            done += 1
            with lock:
                rows.append(rec); cost["v"] += rec.get("cost", 0)
                json.dump({"verdicts": rows}, open(OUT + ".tmp", "w", encoding="utf-8"),
                          ensure_ascii=False, indent=2)
                os.replace(OUT + ".tmp", OUT)
            print(f"  {done}/{len(sample)} [{rec.get('turns','?')}t] "
                  f"fidèle_flaggé={rec.get('faithful_flagged')} "
                  f"corrompu_attrapé={rec.get('corrupt_caught')} coût=${cost['v']:.3f}", flush=True)

    done_rows = [r for r in rows if "state_changed" in r]
    valids = [r for r in done_rows if r["state_changed"] and r["corrupt_caught"] is not None]
    faithfuls = [r for r in done_rows if r["faithful_flagged"] is not None]
    print(f"\n=== PALIER ÉTAT — gate {JUDGE_MODEL} (labels contrôlés) ===")
    print(f"  contradictions réellement injectées : {len(valids)} / {len(done_rows)} "
          f"(reste = NO_STATE_CHANGE, exclu du rappel)")
    if valids:
        c = sum(1 for r in valids if r["corrupt_caught"])
        print(f"  RAPPEL Haiku (gate abordable)  : {100*c/len(valids):.0f}%  ({c}/{len(valids)})")
        cp = sum(1 for r in valids if r.get("corrupt_caught_premium"))
        print(f"  RAPPEL Sonnet (premium, m. cas) : {100*cp/len(valids):.0f}%  ({cp}/{len(valids)})")
    if faithfuls:
        f_ = sum(1 for r in faithfuls if r["faithful_flagged"])
        print(f"  FAUX POSITIFS (fidèles flaggés) : {100*f_/len(faithfuls):.0f}%  ({f_}/{len(faithfuls)})")
    print(f"  COÛT TOTAL : ${cost['v']:.3f}  | verdicts → {OUT}")
    print("  ⚠️ corruption synthétique (proxy) ; n petit → IC large.")


if __name__ == "__main__":
    main()
