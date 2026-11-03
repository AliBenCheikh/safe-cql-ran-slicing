"""Applique le critère de convergence d'E2 (`convergence` de src/e2_safe_cql_diagnostic.py, importé tel quel) aux 15 runs Safe-CQL d'E12.

Lecture seule. Fichiers lus : results/e12/train_summary.json (méta uniquement) et results/e12/checkpoints/*.pt (`lambda_history` : λ après mise à jour
et coût greedy de fin d'époque sur la table d'entraînement, mêmes quantités qu'en E2). Ne lit ni results/e12/test_results.json, ni data/, ni tests/.
Aucun entraînement, aucune évaluation. Le critère et ses seuils sont ceux d'E2 (fixés avant les runs d'E2), sans modification.

Sortie : docs/e12_convergence.md
"""
from __future__ import annotations

import json
from pathlib import Path

import torch

from src.e2_safe_cql_diagnostic import COST_LOW, LAM_SPREAD_MAX, WINDOW, convergence
from src.common import BUDGET

ROOT = Path(__file__).resolve().parents[2]
E12 = ROOT / "results" / "e12"
SUMMARY = E12 / "train_summary.json"
CKPT = E12 / "checkpoints"
OUT = ROOT / "docs" / "e12_convergence.md"
SAFE = ("safe_cql_a0.1", "safe_cql_a0.5", "safe_cql_a0.1_g0")


def main() -> int:
    meta = json.loads(SUMMARY.read_text(encoding="utf-8"))["meta"]
    assert meta["test_split_read"] is False, "le résumé d'entraînement annonce une lecture du test"
    rows = []
    for name in SAFE:
        for seed in meta["seeds"]:
            h = torch.load(CKPT / f"{name}_seed{seed}.pt", weights_only=False)["lambda_history"]
            lam, cost = [e["lambda"] for e in h], [e["greedy_cost"] for e in h]
            rows.append((name, seed, len(h), lam[-1], cost[-1], convergence(lam, cost, BUDGET)))
    n_ok = sum(r[5]["converged"] for r in rows)
    L = ["# Convergence de λ dans les 15 runs Safe-CQL d'E12 (critère d'E2)", "",
         "Produit par `src/checks/convergence_e12.py` (lecture seule ; ni `data/`, ni `tests/`, ni `results/e12/test_results.json` lus). "
         "Sources : `results/e12/checkpoints/*.pt` (`lambda_history`) et la méta de `results/e12/train_summary.json`.", "",
         f"Critère : celui d'E2 (`convergence`, importé sans modification) sur les {WINDOW} dernières époques : (1) étendue de λ < {LAM_SPREAD_MAX} ; "
         f"(2) λ > 0 et {COST_LOW} d ≤ coût greedy ≤ d partout, ou λ = 0 et coût ≤ d ; (3) l'IC à 95 % de la pente de λ contient 0. d = {BUDGET}.",
         "Le coût greedy est lu sur la table de coût d'entraînement et les fenêtres d'entraînement : c'est une quantité dans l'échantillon.", "",
         f"Commit d'entraînement : `{meta['git_commit']}` ; empreinte `{meta['fingerprint']}` ; époques {meta['epochs']}.", "",
         f"**Résultat : {n_ok} run(s) convergé(s) sur {len(rows)}.**", "",
         "| config | seed | époques | λ fin | coût greedy fin | étendue de λ | (1) | (2) | (3) | converge |", "|---|---|---|---|---|---|---|---|---|---|"]
    for name, seed, n, lf, cf, c in rows:
        L.append(f"| {name} | {seed} | {n} | {lf:.4f} | {cf:.4f} | {c['lambda_spread']:.4f} | {c['c1_lambda_spread']} | {c['c2_cost_band']} | "
                 f"{c['c3_slope_ci_has_0']} | {c['converged']} |")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"écrit {OUT} : {n_ok}/{len(rows)} convergés")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
