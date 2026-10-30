"""E2: why does Safe-CQL's lambda run away although the one-step LP says d is feasible with small lambda*?

DIAGNOSTIC, NOT A PERFORMANCE. Trains the Q-net of Safe-CQL on ONE traffic script (fold) of the TRAIN split and
compares it with the tables of that script. Folds: A = a908e4cc, B = a53521b2 (same as E1). A->B means: trained on A,
evaluated (DM, B's tables) on B's windows. The test split is never loaded.

Fold hygiene: `cost_hat` (the `c` of the Bellman target), the cost table used for the greedy cost and the dual update,
`r_scale` and the z-score are all recomputed from the training fold alone (`prepare_fold`, `train_cql`).

Variants (all other settings = SAFE_CFG: hidden 256, batch 1024, lr 3e-4, tau 0.005, eta 0.1):
  current        gamma 0.7, alpha 0.5, 100 epochs
  gamma0         gamma 0
  alpha0.1       alpha 0.1 (diagnostic value, not tuned)
  alpha0         alpha 0
  guard10        VARIANT: lambda frozen (no increase) when the greedy cost is not lower than it was GUARD_N = 10 epochs ago
  current_300ep  as `current`, 300 epochs (test of "train longer")

CONVERGENCE CRITERION, fixed before the runs and NOT to be changed after seeing results. Over the last 20 epochs
(post-update lambda, end-of-epoch greedy train cost), ALL of:
  (1) max(lambda) - min(lambda) < 0.02
  (2) lambda > 0 on all 20 epochs and 0.9 d <= greedy cost <= d on all 20; OR lambda = 0 on all 20 and cost <= d
  (3) the 95 % CI (t, 18 df) of the OLS slope of lambda on epoch contains 0 (constant lambda: slope = 0)
Otherwise "non converge" (also when fewer than 20 epochs were run).

    python -m src.e2_safe_cql_diagnostic --out results/e2          # full grid
    python -m src.e2_safe_cql_diagnostic --summarize results/e2
"""
import argparse
import json
import os
import subprocess
import time
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
import pandas as pd
import torch
from scipy import stats

from src.agents.cql import train_cql
from src.agents.safe_cql import SAFE_CFG, update_lambda
from src.common import BUDGET, N_ACTIONS, N_BINS, PARQUET, state_tensor
from src.lp_diagnostic import SCRIPTS, cell_sums, lagrangian_scores, lp_report, tables_from_sums

SEEDS = (0, 1, 2, 3, 4)
GUARD_N = 10
WINDOW, LAM_SPREAD_MAX, COST_LOW = 20, 0.02, 0.9
D6_CSV = "results/d6_reservations.csv"
VARIANTS = {
    "current": {},
    "gamma0": {"gamma": 0.0},
    "alpha0.1": {"alpha": 0.1},
    "alpha0": {"alpha": 0.0},
    "guard10": {"guard_n": GUARD_N},
    "current_300ep": {"epochs": 300},
}


# ----------------------------------------------------------------------------- fold preparation
def prepare_fold(train_df, res_ids):
    """Rows of the reservations `res_ids` only, with `cost_hat` recomputed from THEIR tables (same tables as the
    LP of E1: `tables_from_sums`). Returns (fold_df, tab) with tab = R, C [A, B], p [B], r_scale."""
    fold = train_df[train_df["reservation"].isin(set(res_ids))].reset_index(drop=True)
    assert len(fold) and (fold["split"] == "train").all()
    Sc, Sr, N = cell_sums(fold)
    R, C, p, _ = tables_from_sums(Sc.sum(0), Sr.sum(0), N.sum(0))
    assert not (np.isnan(R).any() or np.isnan(C).any()), "an action never appears in this fold"
    fold = fold.assign(cost_hat=C[fold["action"].to_numpy(int), fold["load_bin"].to_numpy(int)])
    return fold, {"R": R, "C": C, "p": p, "r_scale": float(fold["reward_embb_Mbps"].std())}


@lru_cache(maxsize=1)
def load_folds(parquet=PARQUET, d6_csv=D6_CSV):
    df = pd.read_parquet(parquet, filters=[("split", "==", "train")])
    res = pd.read_csv(d6_csv, usecols=["res", "md5"])
    return {name: prepare_fold(df, res.loc[res["md5"].str.startswith(md5), "res"]) for name, md5 in SCRIPTS.items()}


# ----------------------------------------------------------------------------- training
def train_variant(fold_df, seed, C, cfg=None, guard_n=None):
    """Safe-CQL as in `src.agents.safe_cql.train_safe_cql`, with the cost table `C` [A, B] given explicitly and an
    optional freeze of lambda's increase (`guard_n`). guard_n=None gives exactly train_safe_cql.
    Returns (q_net, zs, r_scale, hist, lam_hist)."""
    cfg = {**SAFE_CFG, **(cfg or {})}
    d, eta = cfg["budget"], cfg["eta"]
    state, lam_hist, costs = {"lam": 0.0}, [], []
    lb = torch.as_tensor(fold_df["load_bin"].to_numpy().copy(), dtype=torch.int64)
    tbl = torch.as_tensor(C, dtype=torch.float32)

    def reward_fn(batch):
        return batch["r"] - state["lam"] * (batch["c"] / d - 1.0)

    def on_epoch_end(q_net, ep, data):
        with torch.no_grad():
            mean_cost = tbl[q_net(data["s"]).argmax(1), lb].mean().item()
        new = update_lambda(state["lam"], mean_cost, d, eta)
        frozen = bool(guard_n is not None and new > state["lam"] and len(costs) >= guard_n
                      and mean_cost >= costs[-guard_n])
        costs.append(mean_cost)
        state["lam"] = state["lam"] if frozen else new
        lam_hist.append({"epoch": ep, "greedy_cost": mean_cost, "lambda": state["lam"], "frozen": frozen})

    def log_lambda(q_net, ep, zs):
        return {"lambda": state["lam"]}

    q_net, zs, r_scale, hist = train_cql(fold_df, seed, cfg, reward_fn, on_epoch_end, True,
                                         cost_tbl=C, monitor=log_lambda)
    return q_net, zs, r_scale, hist, lam_hist


# ----------------------------------------------------------------------------- criterion
def convergence(lam, cost, d=BUDGET):
    """Pre-registered criterion (see module docstring). lam, cost: per-epoch lists."""
    if len(lam) < WINDOW:
        return {"converged": False, "reason": f"{len(lam)} epochs < window {WINDOW}"}
    lw, cw = np.asarray(lam[-WINDOW:], float), np.asarray(cost[-WINDOW:], float)
    c1 = bool(lw.max() - lw.min() < LAM_SPREAD_MAX)
    if np.all(lw <= 1e-12):
        c2 = bool(np.all(cw <= d))
    else:
        c2 = bool(np.all(lw > 1e-12) and np.all((cw >= COST_LOW * d) & (cw <= d)))
    if np.ptp(lw) == 0:
        c3 = True
    else:
        r = stats.linregress(np.arange(WINDOW), lw)
        c3 = bool(abs(r.slope) <= stats.t.ppf(0.975, WINDOW - 2) * r.stderr)
    return {"converged": c1 and c2 and c3, "c1_lambda_spread": c1, "c2_cost_band": c2, "c3_slope_ci_has_0": c3,
            "lambda_spread": float(lw.max() - lw.min())}


# ----------------------------------------------------------------------------- analysis of a trained Q-net
@torch.no_grad()
def analyse(q_net, zs, lam, own_df, own, oth_df, oth, d=BUDGET):
    """Q-net vs table argmax at the same lambda (per bin), and the Q-net policy under both scripts' tables."""
    act = lambda df: q_net(state_tensor(df, zs)).argmax(1).numpy()
    a_q, lb = act(own_df), own_df["load_bin"].to_numpy(int)
    a_log = own_df["action"].to_numpy(int)
    a_tab = lagrangian_scores(own["R"], own["C"], np.array([lam]), d, own["r_scale"])[0].argmax(0)   # [B]
    per_bin = []
    for b in range(N_BINS):
        m = lb == b
        per_bin.append({"bin": b, "n": int(m.sum()), "table_argmax_action": int(a_tab[b]),
                        "qnet_agrees_with_table": float((a_q[m] == a_tab[b]).mean()),
                        "qnet_equals_logged": float((a_q[m] == a_log[m]).mean()),
                        "logged_equals_table": float((a_log[m] == a_tab[b]).mean()),
                        "qnet_action_counts": np.bincount(a_q[m], minlength=N_ACTIONS).tolist()})
    a_o, lb_o = act(oth_df), oth_df["load_bin"].to_numpy(int)
    b_ = np.arange(N_BINS)
    return {"lambda_used": lam, "per_bin": per_bin,
            "table_argmax_cost_own": float((own["p"] * own["C"][a_tab, b_]).sum()),
            "own_states_own_tables": {"cost": float(own["C"][a_q, lb].mean()), "reward": float(own["R"][a_q, lb].mean())},
            "own_states_other_tables": {"cost": float(oth["C"][a_q, lb].mean()), "reward": float(oth["R"][a_q, lb].mean())},
            "other_states_other_tables": {"cost": float(oth["C"][a_o, lb_o].mean()), "reward": float(oth["R"][a_o, lb_o].mean())}}


def run_one(job):
    fold, variant, seed, epochs = job
    torch.set_num_threads(1)
    folds = load_folds()
    other = "B" if fold == "A" else "A"
    (own_df, own), (oth_df, oth) = folds[fold], folds[other]
    spec = dict(VARIANTS[variant])
    guard_n = spec.pop("guard_n", None)
    cfg = {**spec, **({"epochs": epochs} if epochs else {})}
    t0 = time.time()
    q_net, zs, r_scale, hist, lam_hist = train_variant(own_df, seed, own["C"], cfg, guard_n)
    assert abs(r_scale - own["r_scale"]) < 1e-9
    lam = [e["lambda"] for e in lam_hist]
    cost = [e["greedy_cost"] for e in lam_hist]
    res = {"fold": fold, "variant": variant, "seed": seed, "epochs": len(lam_hist), "seconds": time.time() - t0,
           "lambda_final": lam[-1], "greedy_cost_final": cost[-1], "lambda_hist": lam, "greedy_cost_hist": cost,
           "n_frozen_epochs": int(sum(e["frozen"] for e in lam_hist)),
           "convergence": convergence(lam, cost), "analysis": analyse(q_net, zs, hist[-1]["lambda"], own_df, own, oth_df, oth)}
    return res


def lp_reference(folds):
    out = {}
    for name, (df, tab) in folds.items():
        rep, _ = lp_report(tab["R"], tab["C"], tab["p"], BUDGET, tab["r_scale"])
        out[name] = {k: rep.get(k) for k in ("feasible", "cost_min", "reward", "cost", "lam_star", "budget_active")}
    return out


# ----------------------------------------------------------------------------- summary
def summarize(path):
    runs = json.load(open(path + "_runs.json"))["runs"]
    rows = []
    for r in runs:
        a = r["analysis"]
        w = np.array([b["n"] for b in a["per_bin"]], float)
        rows.append({"fold": r["fold"], "variant": r["variant"], "seed": r["seed"], "epochs": r["epochs"],
                     "lambda_final": r["lambda_final"], "greedy_cost": r["greedy_cost_final"],
                     "converged": r["convergence"]["converged"],
                     "c1_lambda_stable": r["convergence"].get("c1_lambda_spread"), "c2_cost_band": r["convergence"].get("c2_cost_band"),
                     "c3_slope_ci_has_0": r["convergence"].get("c3_slope_ci_has_0"), "lambda_spread": r["convergence"].get("lambda_spread"), "n_frozen": r["n_frozen_epochs"],
                     "agree_table": float(np.dot([b["qnet_agrees_with_table"] for b in a["per_bin"]], w) / w.sum()),
                     "agree_bin0": a["per_bin"][0]["qnet_agrees_with_table"], "agree_bin1": a["per_bin"][1]["qnet_agrees_with_table"],
                     "agree_bin2": a["per_bin"][2]["qnet_agrees_with_table"],
                     "equals_logged": float(np.dot([b["qnet_equals_logged"] for b in a["per_bin"]], w) / w.sum()),
                     "table_argmax_cost": a["table_argmax_cost_own"], "cost_own_tables": a["own_states_own_tables"]["cost"],
                     "cost_own_states_oth_tables": a["own_states_other_tables"]["cost"],
                     "cost_oth_states_oth_tables": a["other_states_other_tables"]["cost"]})
    df = pd.DataFrame(rows)
    df.to_csv(path + "_runs.csv", index=False)
    agg = df.groupby(["fold", "variant"]).agg(
        n=("seed", "size"), n_conv=("converged", "sum"), n_c1=("c1_lambda_stable", "sum"), n_c2=("c2_cost_band", "sum"), n_c3=("c3_slope_ci_has_0", "sum"),
        **{f"{c}_{s}": (c, f) for c in ("lambda_final", "greedy_cost", "agree_table", "equals_logged", "table_argmax_cost",
                                        "cost_own_states_oth_tables", "cost_oth_states_oth_tables")
           for s, f in (("mean", "mean"), ("sd", lambda x: x.std(ddof=1)))}).reset_index()
    agg.to_csv(path + "_summary.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 50)
    print(agg.round(4).to_string(index=False))


# ----------------------------------------------------------------------------- main
def git_state():
    """Commit hash of the code that produced the runs, and whether the working tree had uncommitted changes."""
    sh = lambda *c: subprocess.run(["git", *c], capture_output=True, text=True).stdout.strip()
    return {"git_commit": sh("rev-parse", "HEAD"), "git_dirty_src_tests": bool(sh("status", "--porcelain", "src", "tests"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/e2")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    ap.add_argument("--epochs", type=int, default=None, help="override the epochs of every variant (smoke test)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--summarize", default=None)
    a = ap.parse_args()
    if a.summarize:
        return summarize(a.summarize)
    folds = load_folds()
    seeds = [int(s) for s in a.seeds.split(",")]
    jobs = [(f, v, s, a.epochs) for v in a.variants.split(",") for f in ("A", "B") for s in seeds]
    t0 = time.time()
    git = git_state()
    print(f"[e2] {git} | {len(jobs)} runs, {a.workers} workers", flush=True)
    runs = []
    with Pool(a.workers) as pool:
        for r in pool.imap_unordered(run_one, jobs, chunksize=1):
            runs.append(r)
            c = r["convergence"]
            print(f"[e2] {len(runs)}/{len(jobs)} {r['fold']} {r['variant']} seed{r['seed']} {r['epochs']}ep {r['seconds']:.0f}s "
                  f"lam={r['lambda_final']:.3f} cost={r['greedy_cost_final']:.4f} converged={c['converged']} "
                  f"[lam_stable={c.get('c1_lambda_spread')} band={c.get('c2_cost_band')} slope0={c.get('c3_slope_ci_has_0')}] "
                  f"elapsed {time.time() - t0:.0f}s", flush=True)
    runs.sort(key=lambda r: (r["variant"], r["fold"], r["seed"]))
    with open(PARQUET.replace(".parquet", ".meta.json")) as f:
        version = json.load(f)["dataset_version"]
    meta = {"dataset_version": version, **git, "script": "src/e2_safe_cql_diagnostic.py", "budget": BUDGET, "seeds": seeds, "epochs_override": a.epochs,
            "guard_n": GUARD_N, "variants": {v: VARIANTS[v] for v in a.variants.split(",")}, "folds": SCRIPTS,
            "n_rows": {n: len(f[0]) for n, f in folds.items()}, "lp_reference": lp_reference(folds),
            "diagnostic_only": True, "test_split_read": False, "wall_seconds": time.time() - t0}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out + "_runs.json", "w") as f:
        json.dump({"meta": meta, "runs": runs}, f, default=float)
    summarize(a.out)


if __name__ == "__main__":
    main()
