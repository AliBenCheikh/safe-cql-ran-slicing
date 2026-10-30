"""E11: finer alpha grid for Safe-CQL with validation BY SCRIPT, a revised convergence criterion, and comparison with
table-greedy / randomised LP references.

DIAGNOSTIC, NOT A PERFORMANCE. Every cost / reward is a DM value read in (action x load-bin) tables, which are noisy
(E1: some cells rest on 2-6 reservations), and there are only 2 scripts. The test split is never loaded
(`load_folds` filters split == 'train').

Folds A = a908e4cc, B = a53521b2 (as E1/E2). Direction "A->B": Q-net trained on A, VALIDATED on B (B's windows
as states, B's tables as costs/rewards, z-score learned on A). "B->A" the other way. Everything not listed below is
`SAFE_CFG` as in E2 (hidden 256, batch 1024, lr 3e-4, tau 0.005, eta 0.1), gamma = 0.7, 100 epochs, seeds 0-4.

==================================== FROZEN BEFORE THE GRID (do not edit after the freeze commit) ====================
The alpha values were CHOSEN AFTER SEEING E2 (where alpha in {0, 0.1, 0.5} were run): E2 showed alpha 0.1 leaving the
greedy cost near d on both folds and alpha 0 giving an unstable cost, so the grid refines [0, 0.2] and keeps 0.5
(the current SAFE_CFG value). They are not tuned blind, and they are not a hyperparameter search of the final method.
gamma = 0 is NOT in this grid: it is an ablation at the retained alpha, in step 12. No further grid without approval.

REVISED CONVERGENCE CRITERION ("revised after the 0/60 finding of E2" - the E2 criterion `e2.convergence` is still
computed on every run and reported next to it, unchanged). Over the last WINDOW = 20 epochs (post-update lambda,
end-of-epoch greedy train cost), ALL of:
  R1  the 95 % CI (t, 18 df) of the OLS slope of lambda on epoch contains 0 (lambda constant: slope = 0)
  R2  if lambda > 0 in some epoch of the window: |mean greedy cost over the window - d| <= BAND_TOL ;
      if lambda = 0 on all 20 epochs: mean greedy cost over the window <= d
  R3  the 95 % CI of the OLS slope of the greedy cost on epoch contains 0
Differences with E2: no absolute lambda spread (meaningless across lambda scales 0.05 .. 6); the cost level is read on
the window MEAN with a two-sided tolerance instead of on every epoch in [0.9 d, d]; a cost drift condition is added.
BAND_TOL = 0.0025 is CALIBRATED ON ALREADY-OBSERVED RUNS: it is the 90th percentile (0.00243, rounded up) of the
within-window standard deviation of the greedy cost over the 60 E2 runs (median 0.00033, max 0.0054). It is therefore
not independent of the data it will be applied to.

ALPHA SELECTION RULE (`select_alpha`), on the VALIDATION cost/reward of each direction, averaged over the 5 seeds:
  feasible alpha := mean validation cost <= d in BOTH directions.
  If at least one feasible alpha: keep the one with the highest mean (over the two directions) validation reward;
      alphas within TIE_REWARD (0.01 Mbps) of that maximum are tied -> the smallest alpha.
  If none: keep the alpha with the lowest mean (over the two directions) validation cost (exact tie -> smaller alpha)
      and flag status = "infeasible: no configuration is feasible" - this MUST be said in the report.
Both cases also report the cost and reward (mean +- sd over seeds) of EVERY alpha in each direction, and in the
infeasible case the reward gap to table-greedy on the same validation tables.

REFERENCES (per tables T in {A, B}), all values read in T's tables with T's bin shares:
  table-greedy(T): argmax of the Lagrangian score r/r_scale - lam (c/d - 1) per bin, at the smallest lam on the grid
      arange(0, 200, 0.005) whose cost on T is <= d (the largest lam if none), i.e. the E1 argmax curve;
  LP(T): the randomised one-step LP of E1 (`lp_report`).
  PRINCIPAL comparison: Q-net validated on T's states/tables vs table-greedy(T) / LP(T) evaluated on T (T = the
      validation fold). These references are oracles on the validation tables (they use them to choose).
  SECONDARY: same on the TRAINING tables - a CIRCULAR diagnostic (the Q-net saw these tables' costs in its target).
  ALSO reported: table-greedy built on the training tables and evaluated on the validation tables ("transfer").

    python -m src.e11_alpha_grid --out results/e11            # full grid (6 alphas x 2 folds x 5 seeds = 60 runs)
    python -m src.e11_alpha_grid --summarize results/e11
=====================================================================================================================
"""
import argparse
import hashlib
import inspect
import json
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy import stats

from src.e2_safe_cql_diagnostic import analyse, convergence as convergence_e2, git_state, load_folds, train_variant
from src.common import BUDGET, N_BINS, PARQUET
from src.lp_diagnostic import argmax_curve, lp_report

ALPHAS = (0.0, 0.02, 0.05, 0.1, 0.2, 0.5)
SEEDS = (0, 1, 2, 3, 4)
EPOCHS = 100
WINDOW = 20
BAND_TOL = 0.0025
TIE_REWARD = 0.01
OTHER = {"A": "B", "B": "A"}
LAM_GRID = np.arange(0.0, 200.0 + 0.005, 0.005)


# ----------------------------------------------------------------------------- frozen block
def _slope_ci_has_zero(y):
    y = np.asarray(y, float)
    if np.ptp(y) == 0:
        return True
    r = stats.linregress(np.arange(len(y)), y)
    return bool(abs(r.slope) <= stats.t.ppf(0.975, len(y) - 2) * r.stderr)


def convergence_r(lam, cost, d=BUDGET):
    """Revised criterion R1 & R2 & R3 (see module docstring)."""
    if len(lam) < WINDOW:
        return {"converged": False, "reason": f"{len(lam)} epochs < window {WINDOW}"}
    lw, cw = np.asarray(lam[-WINDOW:], float), np.asarray(cost[-WINDOW:], float)
    r1 = _slope_ci_has_zero(lw)
    m = float(cw.mean())
    r2 = bool(m <= d) if np.all(lw <= 1e-12) else bool(abs(m - d) <= BAND_TOL)
    r3 = _slope_ci_has_zero(cw)
    return {"converged": r1 and r2 and r3, "r1_lambda_slope_ci_has_0": r1, "r2_cost_level": r2,
            "r3_cost_slope_ci_has_0": r3, "window_mean_cost": m, "window_mean_cost_le_d": bool(m <= d)}


def select_alpha(summary, d=BUDGET):
    """summary: DataFrame with columns alpha, direction ('A->B','B->A'), val_cost_mean, val_reward_mean (over seeds).
    Returns {'alpha', 'status', 'feasible_alphas'}."""
    cost = summary.pivot(index="alpha", columns="direction", values="val_cost_mean")
    rew = summary.pivot(index="alpha", columns="direction", values="val_reward_mean")
    feas = [a for a in cost.index if (cost.loc[a] <= d).all()]
    if feas:
        mr = rew.loc[feas].mean(axis=1)
        best = mr.max()
        tied = [a for a in feas if mr[a] >= best - TIE_REWARD]
        return {"alpha": float(min(tied)), "status": "feasible", "feasible_alphas": [float(a) for a in feas]}
    mc = cost.mean(axis=1)
    return {"alpha": float(min(mc.index[mc == mc.min()])), "status": "infeasible: no configuration is feasible",
            "feasible_alphas": []}


FROZEN = (convergence_r, _slope_ci_has_zero, select_alpha)


def frozen_fingerprint():
    """sha256 of the constants and the source of the frozen functions; `tests/test_e11.py` pins its value."""
    consts = repr((ALPHAS, SEEDS, EPOCHS, WINDOW, BAND_TOL, TIE_REWARD, OTHER, BUDGET))
    return hashlib.sha256((consts + "".join(inspect.getsource(f) for f in FROZEN)).encode()).hexdigest()


# ----------------------------------------------------------------------------- references
def table_greedy(tab, d=BUDGET):
    """Per-bin action of the E1 argmax curve at the smallest lambda of the grid with cost on `tab` <= d."""
    rew, cost, a = argmax_curve(tab["R"], tab["C"], tab["p"], d, tab["r_scale"], LAM_GRID)
    ok = np.flatnonzero(cost <= d)
    i = int(ok[0]) if len(ok) else len(LAM_GRID) - 1
    return a[i], float(LAM_GRID[i]), bool(len(ok))


def references(folds, d=BUDGET):
    """For each tables fold T: table-greedy(T) and LP(T) evaluated on T, and table-greedy(T) evaluated on the other fold."""
    out = {}
    b = np.arange(N_BINS)
    for name, (_, tab) in folds.items():
        other = folds[OTHER[name]][1]
        pol, lam, feasible = table_greedy(tab, d)
        lp, _ = lp_report(tab["R"], tab["C"], tab["p"], d, tab["r_scale"])
        out[name] = {"table_greedy_policy": pol.tolist(), "table_greedy_lambda": lam, "table_greedy_reached_d": feasible,
                     "table_greedy_on_own": dict(zip(("reward", "cost"), (float((tab["p"] * tab["R"][pol, b]).sum()),
                                                                          float((tab["p"] * tab["C"][pol, b]).sum())))),
                     "table_greedy_on_other": dict(zip(("reward", "cost"), (float((other["p"] * other["R"][pol, b]).sum()),
                                                                            float((other["p"] * other["C"][pol, b]).sum())))),
                     "lp_on_own": {k: lp.get(k) for k in ("feasible", "reward", "cost")}}
    return out


# ----------------------------------------------------------------------------- one run
def run_one(job):
    import torch
    fold, alpha, seed, epochs = job
    torch.set_num_threads(1)
    folds = load_folds()
    (own_df, own), (oth_df, oth) = folds[fold], folds[OTHER[fold]]
    t0 = time.time()
    q_net, zs, r_scale, hist, lam_hist = train_variant(own_df, seed, own["C"], {"alpha": alpha, "epochs": epochs})
    assert abs(r_scale - own["r_scale"]) < 1e-9
    lam = [e["lambda"] for e in lam_hist]
    cost = [e["greedy_cost"] for e in lam_hist]
    an = analyse(q_net, zs, lam[-1], own_df, own, oth_df, oth)
    return {"fold": fold, "direction": f"{fold}->{OTHER[fold]}", "alpha": alpha, "seed": seed, "epochs": len(lam),
            "seconds": time.time() - t0, "lambda_final": lam[-1], "greedy_cost_final": cost[-1],
            "lambda_hist": lam, "greedy_cost_hist": cost,
            "convergence_e2": convergence_e2(lam, cost), "convergence_r": convergence_r(lam, cost),
            "train_cost": an["own_states_own_tables"]["cost"], "train_reward": an["own_states_own_tables"]["reward"],
            "val_cost": an["other_states_other_tables"]["cost"], "val_reward": an["other_states_other_tables"]["reward"],
            "own_states_other_tables": an["own_states_other_tables"]}


# ----------------------------------------------------------------------------- summary
def _ms(x):
    return float(np.mean(x)), float(np.std(x, ddof=1))


def summarize(path):
    blob = json.load(open(path + "_runs.json"))
    runs, refs = blob["runs"], blob["meta"]["references"]
    df = pd.DataFrame([{"alpha": r["alpha"], "direction": r["direction"], "fold": r["fold"], "seed": r["seed"],
                        "lambda_final": r["lambda_final"], "train_cost": r["train_cost"], "train_reward": r["train_reward"],
                        "val_cost": r["val_cost"], "val_reward": r["val_reward"],
                        "conv_e2": r["convergence_e2"]["converged"], "conv_r": r["convergence_r"]["converged"],
                        "r1": r["convergence_r"].get("r1_lambda_slope_ci_has_0"), "r2": r["convergence_r"].get("r2_cost_level"),
                        "r3": r["convergence_r"].get("r3_cost_slope_ci_has_0"),
                        "window_mean_cost": r["convergence_r"].get("window_mean_cost")} for r in runs])
    df.to_csv(path + "_runs.csv", index=False)
    rows = []
    for (a, dr), g in df.groupby(["alpha", "direction"]):
        f, v = dr.split("->")                                    # trained on f, validated on v
        ref = refs[v]                                            # references on the validation tables
        row = {"alpha": a, "direction": dr, "n": len(g), "n_conv_r": int(g.conv_r.sum()), "n_conv_e2": int(g.conv_e2.sum()),
               "n_r1": int(g.r1.sum()), "n_r2": int(g.r2.sum()), "n_r3": int(g.r3.sum())}
        for c in ("lambda_final", "train_cost", "train_reward", "val_cost", "val_reward"):
            row[f"{c}_mean"], row[f"{c}_sd"] = _ms(g[c])
        row["tg_val_reward"], row["tg_val_cost"] = ref["table_greedy_on_own"]["reward"], ref["table_greedy_on_own"]["cost"]
        row["lp_val_reward"], row["lp_val_cost"] = ref["lp_on_own"]["reward"], ref["lp_on_own"]["cost"]
        row["tg_transfer_reward"], row["tg_transfer_cost"] = refs[f]["table_greedy_on_other"]["reward"], refs[f]["table_greedy_on_other"]["cost"]
        row["gap_reward_to_tg_val"] = row["val_reward_mean"] - row["tg_val_reward"]
        row["gap_reward_to_lp_val"] = row["val_reward_mean"] - row["lp_val_reward"]
        row["tg_train_reward"], row["tg_train_cost"] = refs[f]["table_greedy_on_own"]["reward"], refs[f]["table_greedy_on_own"]["cost"]
        row["gap_reward_to_tg_train_circular"] = row["train_reward_mean"] - row["tg_train_reward"]
        rows.append(row)
    s = pd.DataFrame(rows)
    s.to_csv(path + "_summary.csv", index=False)
    sel = select_alpha(s)
    sel["fingerprint"] = frozen_fingerprint()
    json.dump(sel, open(path + "_selection.json", "w"), indent=1)
    pd.set_option("display.width", 250, "display.max_columns", 50)
    print(s[["alpha", "direction", "n_conv_r", "n_conv_e2", "lambda_final_mean", "val_cost_mean", "val_cost_sd",
             "val_reward_mean", "val_reward_sd", "tg_val_reward", "gap_reward_to_tg_val"]].round(4).to_string(index=False))
    print(sel)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/e11")
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--allow-dirty", action="store_true", help="smoke tests only")
    ap.add_argument("--summarize", default=None)
    a = ap.parse_args()
    if a.summarize:
        return summarize(a.summarize)
    git = git_state()
    assert a.allow_dirty or not git["git_dirty_src_tests"], "uncommitted changes in src/ or tests/: commit first"
    folds = load_folds()
    jobs = [(f, al, s, a.epochs) for al in ALPHAS for f in ("A", "B") for s in SEEDS]
    t0 = time.time()
    print(f"[e11] {git} fingerprint={frozen_fingerprint()[:16]} | {len(jobs)} runs, {a.workers} workers", flush=True)
    runs = []
    with Pool(a.workers) as pool:
        for r in pool.imap_unordered(run_one, jobs, chunksize=1):
            runs.append(r)
            print(f"[e11] {len(runs)}/{len(jobs)} {r['direction']} alpha={r['alpha']} seed{r['seed']} {r['seconds']:.0f}s "
                  f"lam={r['lambda_final']:.3f} train_cost={r['greedy_cost_final']:.4f} val_cost={r['val_cost']:.4f} "
                  f"val_reward={r['val_reward']:.2f} conv_R={r['convergence_r']['converged']} elapsed {time.time() - t0:.0f}s", flush=True)
    runs.sort(key=lambda r: (r["alpha"], r["fold"], r["seed"]))
    with open(PARQUET.replace(".parquet", ".meta.json")) as f:
        version = json.load(f)["dataset_version"]
    meta = {"dataset_version": version, **git, "fingerprint": frozen_fingerprint(), "script": "src/e11_alpha_grid.py",
            "budget": BUDGET, "alphas": ALPHAS, "seeds": SEEDS, "epochs": a.epochs, "band_tol": BAND_TOL, "window": WINDOW,
            "references": references(folds), "diagnostic_only": True, "test_split_read": False, "wall_seconds": time.time() - t0}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out + "_runs.json", "w") as f:
        json.dump({"meta": meta, "runs": runs}, f, default=float)
    summarize(a.out)


if __name__ == "__main__":
    main()
