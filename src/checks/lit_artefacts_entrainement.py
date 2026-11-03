"""Lit r_scale, les configurations enregistrées et les λ finaux dans les artefacts d'ENTRAÎNEMENT de l'étape E12.

Lecture seule. Fichiers lus : results/e12/train_summary.json et results/e12/checkpoints/*.pt (écrits par `--train`, qui ne charge jamais
le split test ; `meta.test_split_read` est vérifié ci-dessous). Ne lit ni results/e12/test_results.json, ni data/, ni tests/.
Aucun entraînement, aucune évaluation, aucun calcul nouveau : les valeurs sont recopiées telles quelles.

Sortie : docs/e12_artefacts_entrainement.md
"""
from __future__ import annotations

import json
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
E12 = ROOT / "results" / "e12"
SUMMARY = E12 / "train_summary.json"          # seul fichier JSON lu ; test_results.json n'est jamais ouvert
CKPT = E12 / "checkpoints"
OUT = ROOT / "docs" / "e12_artefacts_entrainement.md"
SAFE = ("safe_cql_a0.1", "safe_cql_a0.5", "safe_cql_a0.1_g0")


def main() -> int:
    summ = json.loads(SUMMARY.read_text(encoding="utf-8"))
    meta = summ["meta"]
    assert meta["test_split_read"] is False, "le résumé d'entraînement annonce une lecture du test"
    runs = {}
    for r in summ["runs"]:
        runs.setdefault(r["config"], {})[r["seed"]] = r
    cks = {}
    for name in runs:
        for seed in sorted(runs[name]):
            cks[(name, seed)] = torch.load(CKPT / f"{name}_seed{seed}.pt", weights_only=False)
    r_scales = sorted({ck["r_scale"] for ck in cks.values()})

    L = ["# Artefacts d'entraînement E12 : r_scale, configurations enregistrées, λ finaux", "",
         "Produit par `src/checks/lit_artefacts_entrainement.py` (lecture seule ; valeurs recopiées, aucun calcul ; ni `data/`, ni `tests/`, "
         "ni `results/e12/test_results.json` lus). Sources : `results/e12/train_summary.json` et `results/e12/checkpoints/*.pt`.", "",
         "## Provenance", "",
         f"- Commit de l'entraînement : `{meta['git_commit']}` (arbre propre : {not meta['git_dirty']}).",
         f"- Empreinte gelée : `{meta['fingerprint']}`.",
         f"- Version du dataset : `{meta['dataset_version']}`.",
         f"- Époques : {meta['epochs']} ; seeds : {meta['seeds']}.",
         f"- `test_split_read` : {meta['test_split_read']}.", "",
         "## r_scale", "",
         f"Valeurs distinctes sur les {len(cks)} checkpoints : {', '.join(repr(v) for v in r_scales)}.",
         "C'est l'écart-type du reward d'entraînement (`train_cql`, `train_iql`), le même pour tous les agents.", "",
         "## Configurations enregistrées dans les checkpoints (seed 0)", "",
         "| nom | cfg enregistrée |", "|---|---|"]
    for name in runs:
        L.append(f"| {name} | {cks[(name, 0)]['cfg']} |")
    L += ["", "## Safe-CQL : λ et coût greedy d'entraînement", "",
          "`λ fin` = `final_lambda` de `train_summary.json` (valeur après la dernière mise à jour, époque 99). "
          "`coût greedy` = `greedy_cost_train` de la dernière époque (table de coût d'entraînement, fenêtres d'entraînement). "
          "`λ[79]` et `λ[99]` = `lambda_history` du checkpoint (valeur après la mise à jour des époques 79 et 99).", "",
          "| config | seed | λ fin | coût greedy | λ[79] | λ[99] |", "|---|---|---|---|---|---|"]
    for name in SAFE:
        for seed in sorted(runs[name]):
            r, h = runs[name][seed], cks[(name, seed)]["lambda_history"]
            L.append(f"| {name} | {seed} | {r['final_lambda']:.4f} | {r['last_epoch']['greedy_cost_train']:.4f} | "
                     f"{h[79]['lambda']:.4f} | {h[99]['lambda']:.4f} |")
    L += ["", "## Agents sans multiplicateur : coût greedy d'entraînement à la dernière époque", "",
          "| config | seed | coût greedy |", "|---|---|---|"]
    for name in runs:
        if name in SAFE:
            continue
        for seed in sorted(runs[name]):
            L.append(f"| {name} | {seed} | {runs[name][seed]['last_epoch']['greedy_cost_train']:.4f} |")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"écrit {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
