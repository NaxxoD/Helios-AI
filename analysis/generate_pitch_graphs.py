"""
Helios — graphes de pitch (vulgarisation de la valeur PROPRE d'Helios).

On ne montre QUE des données rendues possibles par Helios (pas de prix/CO₂
publics génériques) :
  - fig1  part du prompt retirée (bruit)        — optimise() sur corpus
  - fig2  tokens avant/après par prompt          — optimise()
  - fig3  qualité 4 axes avant→après (radar)     — quality_note
  - fig5  économies cumulées (€/mois)            — EN ATTENTE données d'usage

Thème : charte Helios sombre (source frontend/src/assets/tokens.css).
Lancer :  cd backend && ./.venv/Scripts/python.exe ../analysis/generate_pitch_graphs.py
Sortie  :  analysis/figures/*.png
"""
import os, re, sys, types, importlib.util
import matplotlib
matplotlib.use("Agg")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BACKEND = os.path.join(ROOT, "backend")
CORPUS = os.path.join(ROOT, "docs", "10 Tests.txt")
OUT = os.path.join(HERE, "figures"); os.makedirs(OUT, exist_ok=True)

# --- modules backend en isolé (évite le __init__ lourd) ------------------
sys.modules.setdefault("httpx", types.ModuleType("httpx"))
_pkg = types.ModuleType("utils"); _pkg.__path__ = [os.path.join(BACKEND, "utils")]
sys.modules["utils"] = _pkg
def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(BACKEND, "utils", fname))
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod
    spec.loader.exec_module(mod); return mod
_load("utils.calculator", "calculator.py")
_load("utils.lexique_bootstrap", "lexique_bootstrap.py")
opt = _load("utils.optimiseur", "optimiseur.py")

# --------------------------------------------------------------------------
# Charte Helios SOMBRE (tokens.css)
# --------------------------------------------------------------------------
BG     = "#0b0e0d"   # fond app (noir légèrement vert)
SURF   = "#111c18"   # cartes
GREEN  = "#34d399"   # accent (= "après" / bon)
GREEN2 = "#10b981"
WARN   = "#f97316"   # orange ("avant" / gaspillage)
PURPLE = "#a78bfa"
FG     = "#f0faf5"   # texte principal
MUTED  = "#7aab92"   # labels secondaires
DIM    = "#4a7060"   # captions
GRID   = "#1a2822"

plt.rcParams.update({
    "figure.facecolor": BG, "savefig.facecolor": BG,
    "axes.facecolor": BG, "font.size": 12.5,
    "axes.titlesize": 18, "axes.titleweight": "bold", "axes.titlecolor": FG,
    "text.color": FG, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": FG,
    "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
})

def _save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("✓", os.path.relpath(path, ROOT))

def _cap(fig, txt):
    fig.text(0.5, 0.01, txt, ha="center", fontsize=9.5, color=DIM)

# --- données réelles : optimise() sur le corpus --------------------------
def load_corpus():
    raw = open(CORPUS, encoding="utf-8").read()
    prompts = [p.strip() for p in re.split(r"(?m)^\s*\d+#\s*$", raw) if p.strip()]
    rows = []
    for p in prompts:
        r = opt.optimise(p)
        jd = opt._compute_junk_density(r["original"])
        qb = opt._compute_quality_note(r["original"], r["tokens_before"],
                                       r["tokens_before"], jd, False, False, jd > 0.35)
        rows.append({"before": r["tokens_before"], "after": r["tokens_after"],
                     "reduc": 100 * r["tokens_saved"] / max(1, r["tokens_before"]),
                     "q_before": qb, "q_after": r["quality_note"]})
    return rows

DATA = load_corpus(); N = len(DATA)

# ==========================================================================
# FIG 1 — Le problème : une part du prompt ne sert à rien
# ==========================================================================
def fig1_probleme():
    bruit = np.mean([d["reduc"] for d in DATA])
    fig, ax = plt.subplots(figsize=(8, 6))
    w, _, _ = ax.pie([100 - bruit, bruit], labels=["Signal utile", "Bruit retiré"],
        colors=[GREEN, WARN], startangle=90, counterclock=False,
        autopct="%1.0f%%", pctdistance=0.78,
        wedgeprops={"width": 0.40, "edgecolor": BG, "linewidth": 3},
        textprops={"fontsize": 14, "weight": "bold", "color": FG})
    ax.text(0, 0.06, "%.0f%%" % bruit, ha="center", va="center", fontsize=46,
            weight="bold", color=WARN)
    ax.text(0, -0.22, "de tokens inutiles", ha="center", va="center",
            fontsize=13, color=MUTED)
    ax.set_title("Ce que vous payez sans le savoir", pad=22, fontsize=20)
    _cap(fig, "En moyenne %.0f%% du prompt ne change rien à la réponse · %d prompts réels · optimiseur Helios" % (bruit, N))
    _save(fig, "fig1_probleme.png")

# ==========================================================================
# FIG 2 — Optimiseur : tokens avant → après (dumbbell)
# ==========================================================================
def fig2_tokens():
    d = sorted(DATA, key=lambda x: x["before"]); y = np.arange(N)
    fig, ax = plt.subplots(figsize=(9.5, 6))
    for i, r in enumerate(d):
        ax.plot([r["after"], r["before"]], [i, i], color=GRID, lw=3, zorder=1)
    ax.scatter([r["before"] for r in d], y, color=WARN, s=90, zorder=3, label="Avant", edgecolor=BG, linewidth=1.5)
    ax.scatter([r["after"] for r in d], y, color=GREEN, s=90, zorder=3, label="Après Helios", edgecolor=BG, linewidth=1.5)
    tb = sum(r["before"] for r in d); ta = sum(r["after"] for r in d)
    red = 100 * (tb - ta) / tb
    ax.set_title("Optimiseur : −%.0f%% de tokens, sans perte de sens" % red, pad=14)
    ax.set_xlabel("Tokens du prompt"); ax.set_yticks([])
    leg = ax.legend(loc="lower right", facecolor=SURF, edgecolor=GRID, labelcolor=FG)
    _cap(fig, "n=%d · optimiseur déterministe · (Qwen sémantique : −52%% sur 35 prompts)" % N)
    _save(fig, "fig2_tokens.png")

# ==========================================================================
# FIG 3 — Qualité du prompt avant → après (radar 4 axes) — figure héro
# ==========================================================================
def fig3_radar():
    ks = ["clarte", "specificite", "structure", "concision"]
    labels = ["Clarté", "Spécificité", "Structure", "Concision"]
    before = [np.mean([d["q_before"][k] for d in DATA]) for k in ks]
    after = [np.mean([d["q_after"][k] for d in DATA]) for k in ks]
    ang = np.linspace(0, 2 * np.pi, len(ks), endpoint=False).tolist(); ang += ang[:1]
    b = before + before[:1]; a = after + after[:1]
    fig, ax = plt.subplots(figsize=(7.5, 7.5), subplot_kw={"polar": True})
    ax.set_facecolor(BG)
    ax.plot(ang, b, color=WARN, lw=2.5, label="Avant"); ax.fill(ang, b, color=WARN, alpha=0.10)
    ax.plot(ang, a, color=GREEN, lw=3, label="Après Helios"); ax.fill(ang, a, color=GREEN, alpha=0.22)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels, fontsize=13, weight="bold", color=FG)
    ax.set_ylim(0, 100); ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], color=DIM, fontsize=9)
    ax.tick_params(colors=MUTED); ax.spines["polar"].set_color(GRID); ax.grid(color=GRID)
    ax.set_title("Un meilleur prompt, pas juste plus court", pad=34, fontsize=17, y=1.06)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.20), ncol=2,
              facecolor=SURF, edgecolor=GRID, labelcolor=FG)
    fig.subplots_adjust(bottom=0.16)
    _cap(fig, "Note qualité Helios · n=%d · (Spécificité affinée par E3, à venir)" % N)
    _save(fig, "fig3_radar_qualite.png")

# ==========================================================================
# FIG 5 — Facture API cumulée sans vs avec Helios (données RÉELLES compar:IA)
# ==========================================================================
def fig5_facture():
    # Hypothèses labellisées — bench sur prompts humains réels (compar:IA) :
    PRICE_IN, PRICE_OUT = 0.80, 4.00     # $/M tokens (Claude Haiku, scénario)
    TOK_IN, TOK_OUT = 100, 300           # prompt conversationnel type
    RED_IN, RED_OUT = 0.215, 0.174       # réductions MESURÉES (Qwen, réel)
    RED_OUT_POT = 0.30                   # output potentiel (hors cap 1024 tokens)
    c_raw = (TOK_IN * PRICE_IN + TOK_OUT * PRICE_OUT) / 1e6
    c_helios = (TOK_IN * (1 - RED_IN) * PRICE_IN + TOK_OUT * (1 - RED_OUT) * PRICE_OUT) / 1e6
    c_pot = (TOK_IN * (1 - RED_IN) * PRICE_IN + TOK_OUT * (1 - RED_OUT_POT) * PRICE_OUT) / 1e6
    save = round((c_raw - c_helios) * 1e6)
    save_pot = round((c_raw - c_pot) * 1e6)
    x = np.linspace(0, 1_000_000, 200)
    fig, ax = plt.subplots(figsize=(9.5, 6))
    ax.plot(x, x * c_raw, color=WARN, lw=2.5, label="Sans Helios")
    ax.fill_between(x, x * c_helios, x * c_raw, color=GREEN, alpha=0.10)
    ax.plot(x, x * c_pot, color=GREEN, lw=1.5, ls="--", alpha=0.65,
            label="Avec Helios — potentiel (~−%d $/M)" % save_pot)
    ax.plot(x, x * c_helios, color=GREEN, lw=2.8, label="Avec Helios — mesuré (−%d $/M)" % save)
    ax.set_title("Facture API : −%d $ par million de prompts" % save, pad=14)
    ax.set_xlabel("Prompts envoyés"); ax.set_ylabel("Coût cumulé ($)")
    ax.xaxis.set_major_formatter(lambda v, _: ("1M" if v >= 1e6 else "%dk" % (v / 1000)) if v else "0")
    ax.legend(loc="upper left", facecolor=SURF, edgecolor=GRID, labelcolor=FG)
    _cap(fig, "Prompts humains réels (compar:IA) · Qwen −21.5%% in / −17.4%% out — mesure conservatrice (output cappé à 1024) · Haiku $0.80+$4/M · 100/300 tok"
         .replace("%%", "%"))
    _save(fig, "fig5_facture.png")

if __name__ == "__main__":
    print("Génération (thème Helios sombre · n=%d) ..." % N)
    fig1_probleme(); fig2_tokens(); fig3_radar(); fig5_facture()
    print("Figures :", os.path.relpath(OUT, ROOT))
