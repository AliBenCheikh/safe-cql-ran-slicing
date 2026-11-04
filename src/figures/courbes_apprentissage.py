"""Courbes d'apprentissage de Safe-CQL (E12) : λ et coût greedy d'entraînement par epoch.

Lecture seule, données d'entraînement uniquement. Source : `lambda_history` des 15 checkpoints Safe-CQL de results/e12/checkpoints
(3 configurations x seeds 0-4, 100 epochs ; clés `epoch`, `lambda` = λ après mise à jour, `greedy_cost` = coût greedy de fin d'epoch lu dans la
table de coût d'entraînement sur les fenêtres d'entraînement). Ne lit ni data/, ni results/e12/test_results.json. Aucun entraînement.
Tracé : moyenne sur les seeds et bande min-max. Sortie : paper/figures/courbes_apprentissage.pdf (vectoriel).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CKPT = ROOT / "results" / "e12" / "checkpoints"
SUMMARY = ROOT / "results" / "e12" / "train_summary.json"
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


def main() -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    meta = json.loads(SUMMARY.read_text(encoding="utf-8"))["meta"]
    assert meta["test_split_read"] is False, "le résumé d'entraînement annonce une lecture du test"
    seeds = meta["seeds"]
    plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
    fig, (ax_l, ax_c) = plt.subplots(2, 1, figsize=(3.5, 4.0), sharex=True)
    for name, label, color, ls in CONFIGS:
        lam, cost = load_curves(name, seeds)
        ep = np.arange(lam.shape[1])
        for ax, y in ((ax_l, lam), (ax_c, cost)):
            ax.fill_between(ep, y.min(0), y.max(0), color=color, alpha=0.18, linewidth=0)
            ax.plot(ep, y.mean(0), color=color, linestyle=ls, linewidth=1.5, label=label)
    ax_c.axhline(BUDGET, color="black", linewidth=0.8, label=r"budget $d=0.03$")
    ax_c.legend(frameon=False, loc="upper right", fontsize=7)
    ax_l.set_ylabel(r"multiplier $\lambda$")
    ax_c.set_ylabel("training greedy cost")
    ax_c.set_xlabel("epoch")
    for ax in (ax_l, ax_c):
        ax.grid(axis="y", color="#dddddd", linewidth=0.5)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, metadata={"CreationDate": None})
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
