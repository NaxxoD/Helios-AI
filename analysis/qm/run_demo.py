"""
Script de démo soutenance — replay automatique d'une vraie conversation
avec le sous-agent mémoire.

Usage :
    python run_demo.py [--dry-run] [--speed 1.0]

--dry-run  : affiche le replay sans appels API (utilise les vrais contenus du parquet)
--speed    : facteur de vitesse d'affichage (1.0 = normal, 0.5 = lent, 0 = instantané)

La démo :
1. Charge la conversation #1 depuis demo_economics.json
2. Rejoue les tours un par un en simulant :
   - l'accumulation de la Couche B (sans sous-agent) → barre de coût qui monte
   - la compaction automatique (avec sous-agent) → la Couche B se réinitialise
3. Affiche un résumé final avec les chiffres clés
"""
import sys, os, json, time, argparse
sys.stdout.reconfigure(encoding="utf-8")

ECON_FILE = os.path.join(os.path.dirname(__file__), "demo_economics.json")

def bar(n, total, width=40, fill="█", empty="░"):
    filled = int(width * n / max(total, 1))
    return fill * filled + empty * (width - filled)

def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)

def fmt_cost(c):
    if c < 0.001:
        return f"${c*1000:.3f}m"   # millièmes
    return f"${c:.4f}"

def clear_line():
    print("\r" + " " * 80 + "\r", end="", flush=True)

def demo(dry_run=True, speed=1.0):
    with open(ECON_FILE, encoding="utf-8") as f:
        data = json.load(f)

    meta     = data["meta"]
    totals   = data["totals"]
    no_agent = data["turns_no_agent"]
    with_ag  = data["turns_with_agent"]
    contents = data["turns_content"]

    n_turns     = meta["n_turns"]
    max_input   = max(t["input"] for t in no_agent)
    PRICE_IN    = 3.0 / 1_000_000  # Sonnet 4.6

    print("\n" + "=" * 70)
    print("  HELIOS — Démo sous-agent mémoire")
    print("  Conversation réelle — comparia dataset (FR)")
    print("=" * 70)
    print(f"\n  Sujet : {meta['first_message'][:65]}...")
    print(f"  Durée : {n_turns} tours | Compression cible : {int(meta['COMPRESS']*100)}%")
    print(f"  Fenêtre verbatim : KEEP = {meta['KEEP']} derniers tours")
    print()

    if speed > 0:
        time.sleep(0.5 * speed)

    print("─" * 70)
    print(f"  {'Tour':<5} {'Input sans':>11}  {'Input avec':>11}  {'Économie':>9}  Couche B")
    print("─" * 70)

    cumul_cost_no  = 0.0
    cumul_cost_yes = 0.0

    for i in range(n_turns):
        na = no_agent[i]
        wa = with_ag[i]
        ct = contents[i]

        saving_t = max(0, na["input"] - wa["input"])
        pct_t    = saving_t / max(na["input"], 1) * 100

        cumul_cost_no  += na["input"]  * PRICE_IN
        cumul_cost_yes += wa["input"]  * PRICE_IN

        b_bar   = bar(na["couche_b"], max_input, width=20)
        compacted = wa.get("summary_tokens", 0) > 0 and i > 0

        compaction_marker = " ← compaction" if (
            i > 0 and
            with_ag[i]["summary_tokens"] > with_ag[i-1]["summary_tokens"]
        ) else ""

        print(
            f"  T{na['t']:<4} {fmt_tokens(na['input']):>11}  {fmt_tokens(wa['input']):>11}"
            f"  {pct_t:>7.1f}%  {b_bar}{compaction_marker}"
        )

        if speed > 0:
            delay = 0.15 * speed
            if compaction_marker:
                delay = 0.4 * speed
            time.sleep(delay)

    print("─" * 70)
    print()
    print("  RÉSULTAT FINAL")
    print(f"  Input total sans sous-agent : {fmt_tokens(totals['input_no_agent'])}")
    print(f"  Input total avec sous-agent : {fmt_tokens(totals['input_with_agent'])}")
    print(f"  Réduction input             : {totals['saving_input_pct']:.1f}%")
    print(f"  Économie nette (incl. coût sous-agent) : {totals['saving_net_pct']:.1f}%")
    print()
    print(f"  Coût session SANS : {fmt_cost(totals['cost_no_agent'])}")
    print(f"  Coût session AVEC : {fmt_cost(totals['cost_net'])}")
    print(f"  Économie          : {fmt_cost(totals['cost_no_agent'] - totals['cost_net'])}")
    print()
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Vitesse d'affichage (0=instantané, 1=normal, 2=lent)")
    args = parser.parse_args()
    demo(dry_run=args.dry_run, speed=args.speed)
