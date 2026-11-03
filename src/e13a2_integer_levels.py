"""E13a2: tie-tolerant load levels (integer edges) for the R1-W2 sensitivity. Follow-up of E13a, whose quantile edges
collapsed because 98 % of the windows have an integer `nof_ue`. TRAIN only, descriptive, ONE run, no other variant.
Same machinery as E13a (`src.e13_load_levels`): same tables, folds, table-greedy, cell CIs, transferred-cost bootstrap,
same reproduction guard (run first, abort on failure).

Edge sets (all derived from the SOURCE script's `nof_ue` alone; bins are right-closed on the raw value: x <= e):
  int_k{2,3,4,5}  for each target probability i/k (i = 1..k-1), the INTEGER e in 1..8 whose cumulative share
                  mean(nof_ue <= e) is closest to i/k (ties -> smaller e). Duplicate integers are merged: the realised
                  number of levels is reported, nothing is substituted.
  int_each        one level per integer value: edges 1..7 (levels <=1, (1,2], ..., (7, inf)). A level holding < 1 % of the
                  source windows is merged into its neighbour with the smaller share (ties -> lower), repeatedly.
  edges3_current  reference (pipeline edges 3.5 / 5.5).
Small cells: unchanged `tables_from_sums` rule (cost of a cell with < MIN_CELL_N = 20 windows falls back to the
per-action mean; reward falls back only if the cell is empty); the number of fallback cells is reported.

    python -m src.e13a2_integer_levels --edges      # print the edges only (no table, no cost)
    python -m src.e13a2_integer_levels --out results/e13a2
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from src import e13_load_levels as L
from src.common import BUDGET, PARQUET
from src.e2_safe_cql_diagnostic import git_state

TARGET_KS = (2, 3, 4, 5)
INT_RANGE = np.arange(1, 9)
MIN_LEVEL_SHARE = 0.01


def integer_edges_closest(nof, k):
    nof = np.asarray(nof, float)
    cum = np.array([(nof <= e).mean() for e in INT_RANGE])
    picks = [int(INT_RANGE[int(np.argmin(np.abs(cum - i / k)))]) for i in range(1, k)]   # argmin: first = smaller e on ties
    return np.unique(picks).astype(float)


def per_integer_edges(nof, min_share=MIN_LEVEL_SHARE):
    nof = np.asarray(nof, float)
    edges = list(range(1, 8))
    while len(edges) > 0:
        b = np.searchsorted(np.asarray(edges, float), nof, side="left")
        sh = np.bincount(b, minlength=len(edges) + 1) / len(nof)
        i = int(np.argmin(sh))
        if sh[i] >= min_share:
            break
        if i == 0:
            j = 0                                   # merge into the upper neighbour: drop edge 0
        elif i == len(sh) - 1:
            j = len(edges) - 1                      # merge into the lower neighbour: drop the last edge
        else:
            j = i - 1 if sh[i - 1] <= sh[i + 1] else i      # neighbour with the smaller share (ties -> lower)
        edges.pop(j)
    return np.asarray(edges, float)


def edge_sets(src_nof):
    out = {f"int_k{k}": integer_edges_closest(src_nof, k) for k in TARGET_KS}
    out["int_each"] = per_integer_edges(src_nof)
    out[L.REF] = np.asarray(L.LOAD_EDGES[1:-1], float)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/e13a2")
    ap.add_argument("--edges", action="store_true")
    ap.add_argument("--boot", type=int, default=L.BOOT_B)
    a = ap.parse_args()
    scripts = L.load_scripts()
    if a.edges:
        for s, _ in L.DIRECTIONS:
            nof = scripts[s]["nof_ue"].to_numpy()
            for nm, e in edge_sets(nof).items():
                sh = np.bincount(np.searchsorted(e, nof, side="left"), minlength=len(e) + 1) / len(nof)
                print(f"source {s} {nm:>14} edges={e.tolist()} levels={len(e) + 1} source shares={np.round(sh, 4).tolist()}")
        return
    git = git_state()
    assert not git["git_dirty_src_tests"], "uncommitted changes in src/ or tests/: commit first"
    ok, det = L.reproduction_guard(scripts)
    print(f"[e13a2] reproduction guard: {'PASS' if ok else 'FAIL'}", flush=True)
    if not ok:
        sys.exit("[e13a2] GUARD FAILED: stopping")
    recs, cells = [], []
    for si, (s, v) in enumerate(L.DIRECTIONS):
        for rec, cs, cv in L.analyse_direction(s, v, scripts, edge_sets(scripts[s]["nof_ue"].to_numpy()), si, a.boot):
            recs.append(rec)
            cells += [cs, cv]
            t = rec["transferred"]
            print(f"[e13a2] {rec['direction']} {rec['edge_set']:>14} k={rec['k_realised']} edges={rec['interior_edges']} "
                  f"reward={t['reward']:.3f} cost={t['cost']:.4f}", flush=True)
    with open(PARQUET.replace(".parquet", ".meta.json")) as f:
        version = json.load(f)["dataset_version"]
    meta = {"dataset_version": version, **git, "script": "src/e13a2_integer_levels.py", "budget": BUDGET, "seed": L.SEED,
            "boot": a.boot, "guard": det, "diagnostic_only": True, "test_split_read": False}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out + "_summary.json", "w") as f:
        json.dump({"meta": meta, "rows": recs}, f, indent=1, default=float)
    pd.concat(cells, ignore_index=True).to_csv(a.out + "_cells.csv", index=False)


if __name__ == "__main__":
    main()
