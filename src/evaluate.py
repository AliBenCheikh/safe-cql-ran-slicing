"""Evaluation of baselines and offline-RL agents on the TEST split.

All values are ESTIMATES (the configuration is constant per reservation, so the reward of an
action other than the logged one is not observed):
  dm_*      direct method with the train tables: reward = R[a, load_bin], cost = cost_hat[a, load_bin]
  matched_* observed reward/cost on the windows where the chosen action equals the logged action
Reservation-level bootstrap (B=2000, seed 0) for the 95% CI; pct_safe = share of test reservations
whose mean cost <= 0.03. RL agents: seeds 0..4, mean +- std (ddof=1).

    python -m src.evaluate --seeds 0 1 2 3 4
"""
import argparse
import json
import multiprocessing as mp
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from src import baselines as BL
from src.build_dataset import git_hash
from src.common import BUDGET, N_ACTIONS, cost_table_array, load_canonical, reward_table, split_val

B_BOOT = 2000
BOOT_SEED = 0
AGENTS = ("cql", "safe_cql", "iql")


# ----------------------------------------------------------------------------- metrics

def _per_res(values, codes, k):
    return np.bincount(codes, weights=values, minlength=k)


def evaluate_policy(test, actions, r_tbl, c_tbl, budget=BUDGET, boot_idx=None):
    """Flat dict of floats (JSON-ready). `test` is the test frame, `actions` one action per row."""
    actions = np.asarray(actions, dtype=int)
    lb = test["load_bin"].to_numpy(int)
    uniq, codes = np.unique(test["reservation"].to_numpy(), return_inverse=True)
    k = len(uniq)
    if boot_idx is None:
        boot_idx = np.random.default_rng(BOOT_SEED).integers(0, k, size=(B_BOOT, k))

    dm_r, dm_c = r_tbl[actions, lb], c_tbl[actions, lb]
    m = actions == test["action"].to_numpy(int)
    obs_r, obs_c = test["reward_embb_Mbps"].to_numpy(), test["urllc_frac_viol"].to_numpy()

    n = _per_res(np.ones(len(test)), codes, k)
    nm = _per_res(m.astype(float), codes, k)
    out = {"n_windows": int(len(test)), "n_reservations": int(k)}

    def block(prefix, vals, num, den):
        s = _per_res(vals * (num if num is not None else 1.0), codes, k)
        mean = s.sum() / den.sum()
        b = s[boot_idx].sum(1) / den[boot_idx].sum(1)
        lo, hi = np.nanpercentile(b, [2.5, 97.5])
        out[f"{prefix}_mean"], out[f"{prefix}_ci_lo"], out[f"{prefix}_ci_hi"] = float(mean), float(lo), float(hi)
        return s / np.where(den > 0, den, np.nan)

    block("dm_reward", dm_r, None, n)
    c_res = block("dm_cost", dm_c, None, n)
    out["dm_pct_safe"] = float(np.mean(c_res <= budget))

    mf = m.astype(float)
    block("matched_reward", obs_r, mf, nm)
    mc_res = block("matched_cost", obs_c, mf, nm)
    has = nm > 0
    out["matched_coverage"] = float(m.mean())
    out["matched_n_reservations"] = int(has.sum())
    out["matched_pct_safe"] = float(np.mean(mc_res[has] <= budget)) if has.any() else float("nan")
    out["action_hist"] = np.bincount(actions, minlength=N_ACTIONS).tolist()
    return out


def aggregate_seeds(per_seed):
    """mean +- std (ddof=1) over seeds for every scalar metric."""
    keys = [k for k, v in next(iter(per_seed.values())).items() if isinstance(v, float)]
    agg = {}
    for key in keys:
        x = np.array([m[key] for m in per_seed.values()], dtype=float)
        agg[key] = {"mean": float(np.nanmean(x)), "std": float(np.nanstd(x, ddof=1)) if len(x) > 1 else float("nan")}
    hist = np.array([m["action_hist"] for m in per_seed.values()], dtype=float)
    agg["action_hist_mean"] = hist.mean(0).tolist()
    return agg


# ----------------------------------------------------------------------------- RL jobs

def _job(args):
    """Train one agent for one seed on the TRAIN split, predict on the test windows."""
    agent, seed, epochs, ckpt_dir = args
    import torch
    torch.set_num_threads(1)
    from src.agents import cql, iql, safe_cql

    df, _ = load_canonical()
    train, test = df[df["split"] == "train"], df[df["split"] == "test"]
    cfg = {"epochs": epochs} if epochs else None
    t = time.time()
    if agent == "iql":
        model, zs, extra = iql.run(train, seed, cfg, ckpt_dir)
        acts = iql.greedy_actions(model, test, zs)
    else:
        model, zs, extra = (cql if agent == "cql" else safe_cql).run(train, seed, cfg, ckpt_dir)
        acts = cql.greedy_actions(model, test, zs)
    extra["train_seconds"] = time.time() - t
    return agent, seed, acts, extra


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--epochs", type=int, default=None, help="override (smoke tests only)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--ckpt-dir", default="results/checkpoints")
    ap.add_argument("--out", default="results/evaluation_results.json")
    ap.add_argument("--agents", nargs="+", default=list(AGENTS))
    a = ap.parse_args()

    df, meta = load_canonical()
    train, test = df[df["split"] == "train"], df[df["split"] == "test"].reset_index(drop=True)
    r_tbl, c_tbl = reward_table(train), cost_table_array()
    sub, val = split_val(train, 0.2, 0)
    k = test["reservation"].nunique()
    boot_idx = np.random.default_rng(BOOT_SEED).integers(0, k, size=(B_BOOT, k))
    ev = lambda acts: evaluate_policy(test, acts, r_tbl, c_tbl, BUDGET, boot_idx)

    logged = test["action"].to_numpy(int)
    bf_action, bf_info = BL.best_fixed(val, BUDGET)
    tg_map, tg_feas = BL.table_greedy_map(r_tbl, c_tbl, BUDGET)
    base = {
        "always_rr": (BL.always_rr(logged), {}),
        "always_pf": (BL.always_pf(logged), {}),
        "best_fixed": (np.full(len(test), bf_action), {"action": bf_action, **bf_info}),
        "table_greedy": (BL.table_greedy(test["load_bin"], r_tbl, c_tbl, BUDGET),
                         {"action_per_load_bin": tg_map.tolist(), "bin_feasible": tg_feas.tolist()}),
        "logged_policy": (logged, {"note": "behaviour policy, reference only"}),
    }
    results = {"baselines": {n: {**ev(acts), **info} for n, (acts, info) in base.items()}, "rl": {}}

    jobs = [(ag, s, a.epochs, a.ckpt_dir) for ag in a.agents for s in a.seeds]
    with ProcessPoolExecutor(a.workers, mp_context=mp.get_context("spawn")) as ex:
        outs = list(ex.map(_job, jobs))
    for ag in a.agents:
        per_seed, extras = {}, {}
        for agent, seed, acts, extra in outs:
            if agent == ag:
                per_seed[seed], extras[seed] = ev(acts), extra
        results["rl"][ag] = {"per_seed": per_seed, "extras": extras, "mean_std": aggregate_seeds(per_seed)}

    results["meta"] = {
        "script": "src/evaluate.py", "git_commit": git_hash(), "dataset_version": meta["dataset_version"],
        "seeds": a.seeds, "epochs_override": a.epochs, "bootstrap": {"B": B_BOOT, "seed": BOOT_SEED, "unit": "reservation"},
        "budget": BUDGET, "split": "test (cluster 1)", "n_train_windows": int(len(train)),
        "n_test_windows": int(len(test)), "n_test_reservations": int(k),
        "n_val_reservations_best_fixed": int(val["reservation"].nunique()),
        "estimate_note": "dm_* use train tables (not measured returns); matched_* only cover windows where "
                         "the chosen action equals the logged action (see matched_coverage).",
        "seed_ci_note": "for RL agents mean_std holds mean and std over seeds of every metric, including "
                        "the per-seed CI bounds",
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(results, f, indent=1)

    print(f"{'method':14s} {'dm_reward':>10s} {'dm_cost':>9s} {'safe%':>6s} | {'m_reward':>9s} {'m_cost':>8s} {'cov%':>6s}")
    for n, m in results["baselines"].items():
        print(f"{n:14s} {m['dm_reward_mean']:10.3f} {m['dm_cost_mean']:9.4f} {100*m['dm_pct_safe']:6.1f} | "
              f"{m['matched_reward_mean']:9.3f} {m['matched_cost_mean']:8.4f} {100*m['matched_coverage']:6.1f}")
    for n, r in results["rl"].items():
        g = r["mean_std"]
        print(f"{n:14s} {g['dm_reward_mean']['mean']:10.3f} {g['dm_cost_mean']['mean']:9.4f} "
              f"{100*g['dm_pct_safe']['mean']:6.1f} | {g['matched_reward_mean']['mean']:9.3f} "
              f"{g['matched_cost_mean']['mean']:8.4f} {100*g['matched_coverage']['mean']:6.1f}")


if __name__ == "__main__":
    main()
