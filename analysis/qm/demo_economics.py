"""
Calcule l'économie réelle tour par tour sur la conversation de démo (#1 du classement).
Produit :
  - tableau token input cumulé par tour (avec Couche B)
  - simulation sous-agent mémoire (compaction tous les KEEP tours)
  - coût avant/après en $ (Sonnet 4.6 $3/1M input)
  - export JSON pour le script de démo
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
import pyarrow.parquet as pq
from utils.routing import suggest_routing

# tier de routing → modèle (matrice Helios : simple=cheap, complex=premium)
_TIER_MODEL = {"simple": "Haiku", "medium": "Sonnet", "complex": "Opus"}

def route_of(user_text):
    r = suggest_routing(user_text or "")
    return {"model": _TIER_MODEL.get(r["model_tier"], "Sonnet"),
            "tier": r["model_tier"], "effort": r["effort"], "task": r["task"]}

PARQUET  = os.path.join(os.path.dirname(__file__), "../../docs/conversations.parquet")
CANDS    = os.path.join(os.path.dirname(__file__), "demo_candidates.json")
KEEP     = 4       # tours verbatim conservés
COMPRESS = 0.88    # Couche B compressée à 88% (borne haute mesurée)
PRICE_IN = 3.0     # $/1M tokens input (Sonnet 4.6)
PRICE_OUT= 15.0    # $/1M tokens output

with open(CANDS, encoding="utf-8") as f:
    cands = json.load(f)
best = cands[0]  # rang #1
print(f"Conversation : idx={best['idx']} | {best['n_turns']} tours | modèle : {best.get('model_a','?')}")
print(f"Premier message : {best['first_message'][:80]}...\n")

# Charger UNIQUEMENT la conversation cible (pyarrow, basse mémoire — pas de pandas/full load)
target = best["idx"]
conv = None
seen = 0
for batch in pq.ParquetFile(PARQUET).iter_batches(batch_size=2000, columns=["conversation_a"]):
    if seen + batch.num_rows > target:
        conv = list(batch.column("conversation_a")[target - seen].as_py())
        break
    seen += batch.num_rows
if conv is None:
    sys.exit(f"index {target} hors limites du parquet")

# --- Extraire les paires (user, assistant) ---
turns = []  # liste de dicts {user_content, assistant_content, output_tokens}
i = 0
while i < len(conv):
    item = conv[i]
    if not isinstance(item, dict):
        i += 1
        continue
    if item.get("role") == "user":
        user_content = str(item.get("content", ""))
        # chercher l'assistant suivant
        if i + 1 < len(conv) and isinstance(conv[i+1], dict) and conv[i+1].get("role") == "assistant":
            asst = conv[i + 1]
            meta = asst.get("metadata") or {}
            ot = (meta.get("output_tokens") if isinstance(meta, dict) else None) or 0
            turns.append({
                "t": len(turns) + 1,
                "user": user_content,
                "assistant": str(asst.get("content", "")),
                "output_tokens": int(ot),
            })
            i += 2
            continue
    i += 1

print(f"Tours extraits : {len(turns)}")

# Estimer output_tokens si manquants (≈ chars/4)
for t in turns:
    if t["output_tokens"] == 0:
        t["output_tokens"] = max(1, len(t["assistant"]) // 4)

# --- Simulation SANS sous-agent ---
# Input au tour t = user_t + Σ(output_{1..t-1}) [Couche B]
base_user_tokens = 50   # prompt système minimal (estimation)
no_agent = []
cumulative_b = 0
total_input_no_agent  = 0
total_output_no_agent = 0
for t in turns:
    user_tok = max(1, len(t["user"]) // 4) + base_user_tokens
    input_tok = user_tok + cumulative_b
    output_tok = t["output_tokens"]
    no_agent.append({
        "t": t["t"],
        "input": input_tok,
        "output": output_tok,
        "couche_b": cumulative_b,
    })
    total_input_no_agent  += input_tok
    total_output_no_agent += output_tok
    cumulative_b += output_tok

# --- Simulation AVEC sous-agent mémoire ---
# - Garde les KEEP derniers tours en verbatim
# - Compacte le reste à COMPRESS (88% de réduction)
# - Compaction déclenchée quand historique > KEEP tours
with_agent = []
total_input_with_agent  = 0
total_output_with_agent = 0
total_compaction_cost   = 0   # coût du sous-agent lui-même
summary_tokens  = 0   # tokens du résumé actif
verbatim_window = []  # liste de output_tokens des KEEP derniers tours
full_history    = []  # output_tokens de TOUS les tours passés

for t in turns:
    user_tok = max(1, len(t["user"]) // 4) + base_user_tokens

    # Construire le contexte injecté : résumé + verbatim
    verbatim_tokens = sum(verbatim_window)
    context_tokens  = summary_tokens + verbatim_tokens
    input_tok = user_tok + context_tokens

    output_tok = t["output_tokens"]
    with_agent.append({
        "t": t["t"],
        "input": input_tok,
        "output": output_tok,
        "summary_tokens": summary_tokens,
        "verbatim_tokens": verbatim_tokens,
    })
    total_input_with_agent  += input_tok
    total_output_with_agent += output_tok

    # Mettre à jour la fenêtre
    full_history.append(output_tok)
    verbatim_window.append(output_tok)

    # Compaction si fenêtre verbatim > KEEP
    if len(verbatim_window) > KEEP:
        # Tout ce qui déborde de la fenêtre verbatim va dans le résumé
        to_compact_tokens = verbatim_window[0]  # le plus ancien déborde
        verbatim_window   = verbatim_window[1:]

        # Coût du sous-agent : lit les tokens à compacter + le résumé existant
        compaction_input  = to_compact_tokens + summary_tokens
        compaction_output = int(to_compact_tokens * (1 - COMPRESS))  # ~12% de ce qu'il compacte
        total_compaction_cost += compaction_input + compaction_output

        # Le résumé grandit légèrement
        summary_tokens += compaction_output

# --- Résultats ---
cost_no_agent   = (total_input_no_agent   * PRICE_IN  + total_output_no_agent  * PRICE_OUT) / 1_000_000
cost_with_agent = (total_input_with_agent * PRICE_IN  + total_output_with_agent * PRICE_OUT) / 1_000_000
cost_compaction = (total_compaction_cost  * PRICE_IN) / 1_000_000  # modèle cheap (Haiku), on approxime
cost_net        = cost_with_agent + cost_compaction

saving_pct = (1 - (total_input_with_agent / max(total_input_no_agent, 1))) * 100
net_saving  = (1 - ((cost_net) / max(cost_no_agent, 1e-9))) * 100  # epsilon, PAS 1$ (clampait le %)

print("=" * 60)
print("SANS sous-agent")
print(f"  Input total  : {total_input_no_agent:>10,} tokens")
print(f"  Output total : {total_output_no_agent:>10,} tokens")
print(f"  Coût estimé  : ${cost_no_agent:.4f}")

print("\nAVEC sous-agent mémoire (KEEP={}, compression={}%)".format(KEEP, int(COMPRESS*100)))
print(f"  Input total  : {total_input_with_agent:>10,} tokens")
print(f"  Output total : {total_output_with_agent:>10,} tokens")
print(f"  Coût agent   : ${cost_with_agent:.4f}")
print(f"  Coût compaction (sous-agent) : ${cost_compaction:.4f}")
print(f"  Coût NET     : ${cost_net:.4f}")

print("\nÉCONOMIE")
print(f"  Réduction input  : {saving_pct:.1f}%")
print(f"  Économie nette   : {net_saving:.1f}%")
print(f"  $ économisés     : ${cost_no_agent - cost_net:.4f}")
print("=" * 60)

# --- Table tour par tour (afficher les 10 premiers et derniers) ---
print("\nDétail par tour (extrait) :")
print(f"{'Tour':<5} {'Input_sans':>11} {'Input_avec':>11} {'CoucheB':>9} {'Résumé':>8} {'Verbatim':>9}")
print("-" * 60)
indices = list(range(min(5, len(turns)))) + ["..."] + list(range(max(5, len(turns)-5), len(turns)))
for i in indices:
    if i == "...":
        print("  ...")
        continue
    na = no_agent[i]
    wa = with_agent[i]
    print(f"{na['t']:<5} {na['input']:>11,} {wa['input']:>11,} {na['couche_b']:>9,} {wa['summary_tokens']:>8,} {wa['verbatim_tokens']:>9,}")

# --- Export JSON pour script de démo ---
export = {
    "meta": {
        "idx": best["idx"],
        "n_turns": len(turns),
        "model": best.get("model_a", ""),
        "first_message": best["first_message"],
        "KEEP": KEEP,
        "COMPRESS": COMPRESS,
    },
    "totals": {
        "input_no_agent":   total_input_no_agent,
        "input_with_agent": total_input_with_agent,
        "output_total":     total_output_no_agent,
        "cost_no_agent":    round(cost_no_agent, 6),
        "cost_net":         round(cost_net, 6),
        # décomposition du NET (pour la popup) : input réduit + sortie (inchangée) + sous-agent
        "cost_input_no":    round(total_input_no_agent  * PRICE_IN  / 1e6, 6),
        "cost_input_with":  round(total_input_with_agent * PRICE_IN / 1e6, 6),
        "cost_output":      round(total_output_no_agent * PRICE_OUT / 1e6, 6),
        "cost_subagent":    round(cost_compaction, 6),
        "saving_input_pct": round(saving_pct, 2),
        "saving_net_pct":   round(net_saving, 2),
    },
    "turns_no_agent":   no_agent,
    "turns_with_agent": with_agent,
    "turns_content":    [{"t": t["t"], "user": t["user"][:2500], "assistant": t["assistant"][:2500],
                           "route": route_of(t["user"])} for t in turns],
}
out = os.path.join(os.path.dirname(__file__), "demo_economics.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(export, f, ensure_ascii=False, indent=2)
print(f"\nExporté : {out}")
