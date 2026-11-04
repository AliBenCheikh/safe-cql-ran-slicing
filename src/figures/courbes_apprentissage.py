"""Courbes d'apprentissage de Safe-CQL (E12) : λ et coût greedy d'entraînement par epoch.

Lecture seule, données d'entraînement uniquement. Source : `lambda_history` des 15 checkpoints Safe-CQL de results/e12/checkpoints
(3 configurations x seeds 0-4, 100 epochs ; clés `epoch`, `lambda` = λ après mise à jour, `greedy_cost` = coût greedy de fin d'epoch lu dans la
table de coût d'entraînement sur les fenêtres d'entraînement). Ne lit ni data/, ni results/e12/test_results.json. Aucun entraînement.
Troisième panneau : λ des 10 runs `current_300ep` (α = 0,5 ; γ = 0,7 ; 300 epochs ; plis A et B) de results/e2_runs.json (`lambda_hist`, clé `fold`),
données d'entraînement du pli uniquement. Tracé : moyenne sur les seeds et bande min-max. Sortie : paper/figures/courbes_apprentissage.pdf (vectoriel).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CKPT = ROOT / "results" / "e12" / "checkpoints"
SUMMARY = ROOT / "results" / "e12" / "train_summary.json"
E2_RUNS = ROOT / "results" / "e2_runs.json"
E2_VARIANT = "current_300ep"
FOLDS = (("A", "script A (a908e4cc)", "#2a6fb0", "-"), ("B", "script B (a53521b2)", "#d9822b", "--"))
OUT = ROOT / "paper" / "figures" / "courbes_apprentissage.pdf"
BUDGET = 0.03
CONFIGS = (  # (nom, libellé, couleur, style de trait)
    ("safe_cql_a0.1", r"$\alpha=0.1,\ \gamma=0.7$", "#2a6fb0", "-"),
    ("safe_cql_a0.5", r"$\alpha=0.5,\ \gamma=0.7$", "#d9822b", "--"),
    ("safe_cql_a0.1_g0", r"$\alpha=0.1,\ \gamma=0$", "#5b5b5b", ":"),
)


def load_curves(name: str, seeds) -> tuple[np.ndarray, np.ndarray]:
    """Renvoie (λ, coût greedy), chacun de forme (seeds, epochs)."""
    import torch

    lam, cost = [], []
    for s in seeds:
        h = torch.load(CKPT / f"{name}_seed{s}.pt", map_location="cpu", weights_only=False)["lambda_history"]
        lam.append([e["lambda"] for e in h])
        cost.append([e["greedy_cost"] for e in h])
    return np.array(lam), np.array(cost)


def load_e2_lambda(fold: str) -> np.ndarray:
    """λ après mise à jour par epoch des runs `current_300ep` d'un pli, forme (seeds, 300)."""
    runs = json.loads(E2_RUNS.read_text(encoding="utf-8"))["runs"]
    return np.array([r["lambda_hist"] for r in runs if r["variant"] == E2_VARIANT and r["fold"] == fold])


def main() -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    e2_meta = json.loads(E2_RUNS.read_text(encoding="utf-8"))["meta"]
    assert e2_meta["test_split_read"] is False, "E2 annonce une lecture du test"
    meta = json.loads(SUMMARY.read_text(encoding="utf-8"))["meta"]
    assert meta["test_split_read"] is False, "le résumé d'entraînement annonce une lecture du test"
    seeds = meta["seeds"]
    plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
    fig, (ax_l, ax_c, ax_e) = plt.subplots(3, 1, figsize=(3.5, 5.6))
    for name, label, color, ls in CONFIGS:
        lam, cost = load_curves(name, seeds)
        ep = np.arange(lam.shape[1])
        for ax, y in ((ax_l, lam), (ax_c, cost)):
            ax.fill_between(ep, y.min(0), y.max(0), color=color, alpha=0.18, linewidth=0)
            ax.plot(ep, y.mean(0), color=color, linestyle=ls, linewidth=1.5, label=label)
    for fold, label, color, ls in FOLDS:
        y = load_e2_lambda(fold)
        assert y.shape == (len(seeds), 300), y.shape
        ep2 = np.arange(y.shape[1])
        ax_e.fill_between(ep2, y.min(0), y.max(0), color=color, alpha=0.18, linewidth=0)
        ax_e.plot(ep2, y.mean(0), color=color, linestyle=ls, linewidth=1.5, label=label)
    ax_e.set_ylabel(r"$\lambda$, 300 epochs")
    ax_e.set_xlabel("epoch")
    ax_c.set_xlabel("epoch")
    ax_e.legend(frameon=False, loc="upper left", fontsize=7)
    ax_c.axhline(BUDGET, color="black", linewidth=0.8, label=r"budget $d=0.03$")
    ax_c.legend(frameon=False, loc="upper right", fontsize=7)
    ax_l.set_xlim(0, 99); ax_c.set_xlim(0, 99)
    ax_l.set_ylabel(r"multiplier $\lambda$")
    ax_c.set_ylabel("training greedy cost")
    for ax in (ax_l, ax_c, ax_e):
        ax.grid(axis="y", color="#dddddd", linewidth=0.5)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, metadata={"CreationDate": None})
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
