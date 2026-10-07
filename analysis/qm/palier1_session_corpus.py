"""
Palier 1 (GRATUIT) — thèse structurelle sur le corpus REEL.

Sur les conversations FR multi-tours de comparia (docs/conversations.parquet),
on simule la reinjection sans-etat (le LLM relit tout l'historique a chaque tour)
et on mesure, sans aucun appel LLM :
  - input cumule vs output cumule  -> l'input domine-t-il sur une session ?
  - part de la Couche B (relecture) dans l'input
  - projection memoire : compresser le vieil historique a 12% (garde KEEP verbatim)

Token estimes depuis le contenu (chars/4), coherent avec le reste du projet.
Lancer : python analysis/qm/palier1_session_corpus.py
"""
import sys, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
import pyarrow.parquet as pq

PATH = "docs/conversations.parquet"
KEEP = 6        # tours recents gardes verbatim
RATIO = 0.12    # resume = 12% du vieil historique (mesure b2)

def toks(s): return max(1, len(s)//4) if s else 0

def main():
    pf = pq.ParquetFile(PATH)
    tot_in = tot_out = tot_B = tot_in_mem = 0
    n_conv = 0
    bucket = collections.defaultdict(lambda: [0, 0, 0, 0])  # b -> [in, out, in_mem, count]
    seen = 0
    for batch in pf.iter_batches(batch_size=8000, columns=["conv_turns", "languages", "conversation_a"]):
        d = batch.to_pydict()
        seen += len(d["conv_turns"])
        for i in range(len(d["conv_turns"])):
            ct = d["conv_turns"][i]
            if ct is None or ct < 3:
                continue
            langs = d["languages"][i] or []
            if "fr" not in langs:
                continue
            conv = d["conversation_a"][i]
            if not conv:
                continue
            turns = [toks(t.get("content")) for t in conv]
            ci = co = cb = cim = 0
            for pos, t in enumerate(conv):
                if (t.get("role") or "") != "assistant":
                    continue
                hist = turns[:pos]
                if not hist:
                    continue
                ci  += sum(hist)              # input reinjecte (tout le passe)
                co  += turns[pos]             # output (la reponse)
                cb  += sum(hist[:-1])         # Couche B = passe SANS le dernier message user
                cim += (int(sum(hist[:-KEEP])*RATIO) + sum(hist[-KEEP:])) if len(hist) > KEEP else sum(hist)
            if co == 0:
                continue
            tot_in += ci; tot_out += co; tot_B += cb; tot_in_mem += cim
            n_conv += 1
            b = "3-4" if ct <= 4 else "5-9" if ct <= 9 else "10+"
            bk = bucket[b]; bk[0] += ci; bk[1] += co; bk[2] += cim; bk[3] += 1
        print(f"  ...{seen:,} lignes scannées, {n_conv:,} convs FR multi-tours traitées", flush=True)

    print(f"\n=== PALIER 1 — {n_conv:,} conversations FR multi-tours réelles ===\n")
    print("L'input domine-t-il sur une session ?")
    print(f"  input cumulé (relecture)  : {tot_in:,} tk")
    print(f"  output cumulé (réponses)  : {tot_out:,} tk")
    print(f"  -> ratio input/output     : {tot_in/tot_out:.1f}x  (l'input écrase l'output sur session)")
    print(f"  -> part Couche B (relecture redondante) dans l'input : {100*tot_B/tot_in:.0f}%")
    print()
    print("Par nombre de tours (le ratio input/output grossit avec la session) :")
    print(f"  {'tours':7}{'convs':>9}{'in/out':>9}{'éco input mémoire':>20}")
    for b in ["3-4", "5-9", "10+"]:
        s = bucket[b]
        if s[3]:
            print(f"  {b:7}{s[3]:>9,}{s[0]/s[1]:>8.1f}x{100*(s[0]-s[2])/s[0]:>18.0f}%")
    print()
    print("Projection sous-agent mémoire (compresser la Couche B à 12%, garde 6 tours) :")
    print(f"  input SANS mémoire : {tot_in:,} tk")
    print(f"  input AVEC mémoire : {tot_in_mem:,} tk")
    print(f"  -> économie INPUT (brut) sur le corpus réel : -{100*(tot_in-tot_in_mem)/tot_in:.0f}%")
    print("\n(quali à vérifier en Palier 2 ; ici = thèse structurelle + magnitude, n=corpus réel)")

if __name__ == "__main__":
    main()
