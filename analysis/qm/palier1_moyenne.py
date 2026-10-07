"""Palier 1 bis — distribution de l'economie PAR conversation (n=39k).
Contraste : economie ponderee-tokens (la facture corpus) vs moyenne/mediane par conv."""
import sys, statistics as st
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
import pyarrow.parquet as pq

KEEP=6; RATIO=0.12
def toks(s): return max(1,len(s)//4) if s else 0

pf=pq.ParquetFile("docs/conversations.parquet")
savings=[]            # economie % par conversation (non ponderee)
tot_in=tot_in_mem=0   # pour la version ponderee-tokens
by={}                 # bucket -> list de savings
for batch in pf.iter_batches(batch_size=8000, columns=["conv_turns","languages","conversation_a"]):
    d=batch.to_pydict()
    for i in range(len(d["conv_turns"])):
        ct=d["conv_turns"][i]
        if ct is None or ct<3: continue
        if "fr" not in (d["languages"][i] or []): continue
        conv=d["conversation_a"][i]
        if not conv: continue
        turns=[toks(t.get("content")) for t in conv]
        ci=cim=co=0
        for pos,t in enumerate(conv):
            if (t.get("role") or "")!="assistant": continue
            h=turns[:pos]
            if not h: continue
            ci+=sum(h); co+=turns[pos]
            cim+=(int(sum(h[:-KEEP])*RATIO)+sum(h[-KEEP:])) if len(h)>KEEP else sum(h)
        if co==0 or ci==0: continue
        s=100*(ci-cim)/ci
        savings.append(s)
        tot_in+=ci; tot_in_mem+=cim
        b="3-4" if ct<=4 else "5-9" if ct<=9 else "10+"
        by.setdefault(b,[]).append(s)

n=len(savings)
print(f"=== Economie input par conversation (n={n:,}) ===\n")
print(f"  ponderee-tokens (la FACTURE corpus) : -{100*(tot_in-tot_in_mem)/tot_in:.0f}%   <- tiree par les sessions longues")
print(f"  MOYENNE par conversation            : -{st.mean(savings):.0f}%")
print(f"  MEDIANE par conversation            : -{st.median(savings):.0f}%   <- la conversation TYPIQUE")
q=st.quantiles(savings,n=4)
print(f"  p25 / p75                           : -{q[0]:.0f}% / -{q[2]:.0f}%")
print()
print("  moyenne par bucket de tours :")
for b in ["3-4","5-9","10+"]:
    if b in by: print(f"    {b:5} (n={len(by[b]):>6,}) : moyenne -{st.mean(by[b]):.0f}%  | mediane -{st.median(by[b]):.0f}%")
