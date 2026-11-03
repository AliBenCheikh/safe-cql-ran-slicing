"""E12: final evaluation on the TEST split (cluster 1) - the SECOND reading of the test (the first was phase 2).

Everything below the line "FROZEN" is fixed by the freeze commit; `frozen_fingerprint()` hashes the constants and the
source of every function that trains a model, reads the test, estimates or checks an expectation (plus the agent,
baseline and table code they call). `tests/test_e12.py` and `PINNED_SHA256` pin its value. The pre-registered
expectations are in docs/e12_attente_pre_test.md (committed before this code).

Two separate phases, one command each; there is no option to choose policies, scripts, seeds, epochs or metrics:
  --train      trains the 6 configurations x seeds 0-4 on the TRAIN split (`load_train` filters split == 'train'); the
               test split is never loaded here. Writes checkpoints + train_summary.json.
  --evaluate   guarded (clean tree, fingerprint = pin, pre-registration committed, trained under the same fingerprint,
               no lock). Creates the lock, reads the test ONCE (`load_test`, the only place the split name appears),
               computes every policy x script x estimator in one pass, persists test_results.json, and only then prints.
               A rerun is allowed only after a crash BEFORE test_results.json was written (nothing was shown).

Estimators (all are ESTIMATES; the configuration is constant per reservation):
  dm_*       direct method with the train tables: reward R[a, load_bin], cost C[a, load_bin]. Says what the train tables
             predict for the policy's actions on the test load bins. It does not measure the system and assumes the
             tables transfer across scripts.
  matched_*  observed reward / cost on the windows where the chosen action equals the logged action. Unbiased by the
             tables but covers only part of the windows (matched_coverage), says nothing about never-logged actions, and
             is confounded with the execution block (PF ran, then RR, in the test script, D8).
Intervals: reservation bootstrap (B = 2000, seed 0) INSIDE each script, label "conditional on this script"; train
tables and the trained models are held fixed. For agents the interval is on the seed-averaged value; the spread between
seeds (seed_sd) is reported separately. They ignore the variability between scripts (the independent unit is the script).
"""
import argparse
import hashlib
import inspect
import json
import os
import subprocess
import time
import warnings
from multiprocessing import Pool

import numpy as np
import pandas as pd

from src import baselines as BL
from src.agents import cql, iql, safe_cql
from src.common import BUDGET, GAMMA, PARQUET, N_ACTIONS, cost_table_array, fit_zscore, make_arrays, reward_table, set_seed, split_val, state_tensor

# ===================================================== FROZEN (constants) ==========================================
SEEDS = (0, 1, 2, 3, 4)
EPOCHS = 100
B_BOOT = 2000
BOOT_SEED = 0
DATASET_VERSION = "268d524c117eb6de"
CONFIGS = {
    "safe_cql_a0.1": ("safe_cql", {"alpha": 0.1}),
    "cql_a0.1": ("cql", {"alpha": 0.1}),
    "safe_cql_a0.5": ("safe_cql", {"alpha": 0.5}),
    "cql_a0.5": ("cql", {"alpha": 0.5}),
    "safe_cql_a0.1_g0": ("safe_cql", {"alpha": 0.1, "gamma": 0.0}),
    "iql": ("iql", {}),
}
BASELINES = ("always_rr", "always_pf", "best_fixed", "table_greedy")
PRIMARY = "safe_cql_a0.1"
MAIN_SCRIPT = "c40f2fe7"
MIN_RES_FLAG = 10          # a script with fewer test reservations is flagged `low_n` (interval not interpretable)
PROCHE_REL = 0.10          # expectation (a): agents "close" if max - min DM reward <= 10 % of their mean
PARTIAL_COV = 0.5          # expectation (c): matched coverage "partial" if < 50 % for every agent
NET_SD = 2.0               # expectation (d): "net" improvement = more than 2 seed sd
D6_CSV = "results/d6_reservations.csv"
COST_TABLE_PATH = "results/cost_table.csv"
PRE_REG_DOC = "docs/e12_attente_pre_test.md"
LOCK_NAME, RESULTS_NAME, SUMMARY_NAME = "test_read_final.lock", "test_results.json", "train_summary.json"
CKPT_SUB = "checkpoints"
PINNED_SHA256 = "c88c288ea41dd1cb05b9a66b1574e4180bf6a2d562e37c9bb42198d74536d854"    # set in the freeze commit (outside the hashed source)
CI_LABEL = ("conditionnel à ce script : réservations rééchantillonnées dans le script, tables d'entraînement et modèles "
            "fixes ; hors variabilité entre scripts")


# ===================================================== FROZEN (functions) ==========================================
def _sh(*cmd):
    return subprocess.run(["git", *cmd], capture_output=True, text=True).stdout.strip()


def git_state():
    return {"git_commit": _sh("rev-parse", "HEAD"), "git_dirty": bool(_sh("status", "--porcelain", "src", "tests", PRE_REG_DOC))}


def _check_version(parquet):
    with open(parquet.replace(".parquet", ".meta.json")) as f:
        v = json.load(f)["dataset_version"]
    assert v == DATASET_VERSION, f"dataset version {v} != frozen {DATASET_VERSION}"
    return v


def load_train(parquet=PARQUET):
    """TRAIN rows only (filter pushed to the reader)."""
    _check_version(parquet)
    df = pd.read_parquet(parquet, filters=[("split", "==", "train")])
    assert len(df) > 0 and set(df["split"]) == {"train"}
    return df


def load_test(parquet=PARQUET):
    """The ONLY place where the test split is read. Called only from `evaluate_once`, after the lock is taken."""
    df = pd.read_parquet(parquet, filters=[("split", "==", "test")])
    assert len(df) > 0 and set(df["split"]) == {"test"}
    return df.reset_index(drop=True)


def _train_one(train, agent, seed, overrides, cost_tbl):
    """Train one model on the train frame. Returns (model, zs, r_scale, cfg_full, extra, hist)."""
    cfg = dict(overrides)
    if agent == "cql":
        model, zs, rs, hist = cql.train_cql(train, seed, cfg, cost_tbl=cost_tbl)
        return model, zs, rs, {**cql.CFG, **cfg}, {}, hist
    if agent == "safe_cql":
        model, zs, rs, hist, lam = safe_cql.train_safe_cql(train, seed, cfg, cost_tbl=cost_tbl)
        return model, zs, rs, {**safe_cql.SAFE_CFG, **cfg}, {"lambda_history": lam}, hist
    model, zs, rs, hist = iql.train_iql(train, seed, cfg, cost_tbl=cost_tbl)
    return model, zs, rs, {**iql.IQL_CFG, **cfg}, {}, hist


def train_job(job):
    name, seed, epochs, parquet, out, cost_path, extra_cfg = job
    import torch
    torch.set_num_threads(1)
    agent, over = CONFIGS[name]
    train = load_train(parquet)
    t0 = time.time()
    model, zs, rs, cfg, extra, hist = _train_one(train, agent, seed, {**over, "epochs": epochs, **(extra_cfg or {})},
                                                 cost_table_array(cost_path))
    path = os.path.join(out, CKPT_SUB, f"{name}_seed{seed}.pt")
    (iql if agent == "iql" else cql).save_checkpoint(path, model, zs, rs, cfg, seed, history=hist, **extra)
    last = {k: v for k, v in hist[-1].items() if isinstance(v, (int, float))}
    return {"config": name, "seed": seed, "seconds": time.time() - t0, "epochs": len(hist), "last_epoch": last,
            "final_lambda": extra["lambda_history"][-1]["lambda"] if extra else None}


def train_phase(out, parquet=PARQUET, workers=6, epochs=EPOCHS, cost_path=COST_TABLE_PATH, extra_cfg=None):
    """No test access: only `load_train` is called (in the workers)."""
    jobs = [(n, s, epochs, parquet, out, cost_path, extra_cfg) for n in CONFIGS for s in SEEDS]
    if workers == 1:
        rows = [train_job(j) for j in jobs]
    else:
        with Pool(workers) as pool:
            rows = list(pool.imap_unordered(train_job, jobs, chunksize=1))
    rows.sort(key=lambda r: (r["config"], r["seed"]))
    summ = {"meta": {**git_state(), "fingerprint": frozen_fingerprint(), "dataset_version": DATASET_VERSION,
                     "epochs": epochs, "seeds": SEEDS, "configs": CONFIGS, "test_split_read": False}, "runs": rows}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, SUMMARY_NAME), "w") as f:
        json.dump(summ, f, indent=1, default=float)
    return summ


def script_of(res_ids, d6_csv=D6_CSV):
    """script id (first 8 hex of the traffic-script md5) of each reservation id."""
    m = pd.read_csv(d6_csv, usecols=["res", "md5"])
    mp = dict(zip(m["res"], m["md5"].str[:8]))
    out = [mp[r] for r in res_ids]
    return np.array(out)


def predict(name, seed, frame, out):
    agent = CONFIGS[name][0]
    path = os.path.join(out, CKPT_SUB, f"{name}_seed{seed}.pt")
    if agent == "iql":
        nets, ck = iql.load_iql(path)
        return iql.greedy_actions(nets, frame, ck["zscore"])
    net, ck = cql.load_q_net(path)
    return cql.greedy_actions(net, frame, ck["zscore"])


def _res_sums(frame, actions, codes, k, r_tbl, c_tbl, d):
    """Per-reservation numerators / denominators of every metric, for one action vector."""
    a = np.asarray(actions, dtype=int)
    lb = frame["load_bin"].to_numpy(int)
    m = (a == frame["action"].to_numpy(int)).astype(float)
    bc = lambda v: np.bincount(codes, weights=v, minlength=k)
    n, nm = bc(np.ones(len(a))), bc(m)
    dc = bc(c_tbl[a, lb])
    mc = bc(frame["urllc_frac_viol"].to_numpy() * m)
    has = nm > 0
    dm_safe = (dc / n <= d).astype(float)
    m_safe = ((mc / np.where(has, nm, 1.0)) <= d) & has
    one = np.ones(k)
    return {"dm_reward": (bc(r_tbl[a, lb]), n), "dm_cost": (dc, n), "dm_pct_safe": (dm_safe, one),
            "matched_reward": (bc(frame["reward_embb_Mbps"].to_numpy() * m), nm), "matched_cost": (mc, nm),
            "matched_pct_safe": (m_safe.astype(float), has.astype(float)), "matched_coverage": (nm, n)}


def _ratio(num, den, idx=None):
    if idx is not None:
        num, den = num[idx].sum(1), den[idx].sum(1)
    else:
        num, den = num.sum(), den.sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def boot_stats(parts, idx):
    """parts: one `_res_sums` dict per seed (a baseline has one). Per metric: seed-mean point estimate, seed sd (ddof 1),
    95 % bootstrap interval of the seed-averaged value, share of bootstrap samples where it is undefined."""
    out = {}
    warnings.simplefilter("ignore", RuntimeWarning)       # undefined matched ratios on low-n scripts are reported, not hidden
    for key in parts[0]:
        pts = np.array([float(_ratio(*p[key])) for p in parts])
        boots = np.nanmean(np.stack([_ratio(*p[key], idx) for p in parts]), axis=0) if len(parts) > 1 else _ratio(*parts[0][key], idx)
        ok = ~np.isnan(boots)
        lo, hi = np.percentile(boots[ok], [2.5, 97.5]) if ok.any() else (np.nan, np.nan)
        out[key] = {"mean": float(np.nanmean(pts)) if (~np.isnan(pts)).any() else float("nan"),
                    "seed_sd": float(np.nanstd(pts, ddof=1)) if len(pts) > 1 else float("nan"),
                    "ci_lo": float(lo), "ci_hi": float(hi), "undefined_frac": float(1 - ok.mean())}
    return out


def demonstrated_safe(stats, d=BUDGET):
    """Upper bound of the 95 % interval <= d for BOTH the DM and the matched cost (undefined -> False)."""
    return bool(stats["dm_cost"]["ci_hi"] <= d and stats["matched_cost"]["ci_hi"] <= d)


def check_expectations(res, d=BUDGET):
    """Mechanical check of the pre-registered expectations (a)-(e), on the main script and on the pooled test."""
    out = {}
    agents = ("safe_cql_a0.1", "cql_a0.1", "iql")
    for g in (MAIN_SCRIPT, "pooled"):
        grp = res["groups"].get(g)
        if grp is None:
            continue
        P = grp["policies"]
        v = lambda p, k, f="mean": P[p][k][f]
        rew = [v(p, "dm_reward") for p in agents]
        a = {"table_greedy_above_all_agents": all(v("table_greedy", "dm_reward") > v(p, "dm_reward") for p in CONFIGS),
             "agents_close": bool(max(rew) - min(rew) <= PROCHE_REL * float(np.mean(rew)))}
        pairs = (("safe_cql_a0.1", "cql_a0.1"), ("safe_cql_a0.5", "cql_a0.5"))
        b = {"safe_below_cql_and_iql": all(v(s, "dm_cost") < v(c, "dm_cost") and v(s, "dm_cost") < v("iql", "dm_cost") for s, c in pairs),
             "safe_ci_hi_not_below_d": all(v(s, "dm_cost", "ci_hi") >= d for s, _ in pairs)}
        c = {"matched_same_order": all(v(s, "matched_cost") < v(c_, "matched_cost") and v(s, "matched_cost") < v("iql", "matched_cost")
                                       for s, c_ in pairs),
             "coverage_partial": all(v(p, "matched_coverage") < PARTIAL_COV for p in CONFIGS)}
        sdc = max(v("safe_cql_a0.1", "dm_cost", "seed_sd"), v("safe_cql_a0.1_g0", "dm_cost", "seed_sd"))
        sdr = max(v("safe_cql_a0.1", "dm_reward", "seed_sd"), v("safe_cql_a0.1_g0", "dm_reward", "seed_sd"))
        c0, c7 = v("safe_cql_a0.1_g0", "dm_cost"), v("safe_cql_a0.1", "dm_cost")
        r0, r7 = v("safe_cql_a0.1_g0", "dm_reward"), v("safe_cql_a0.1", "dm_reward")
        net = bool(c0 < c7 - NET_SD * sdc or (r0 > r7 + NET_SD * sdr and c0 <= c7))
        dd = {"net_improvement": net, "cost_g0_minus_g07": c0 - c7, "reward_g0_minus_g07": r0 - r7}
        safe = {p: demonstrated_safe(P[p], d) for p in (*CONFIGS, *BASELINES)}
        out[g] = {"a": {**a, "holds": all(a.values())}, "b": {**b, "holds": all(b.values())},
                  "c": {**c, "holds": all(c.values())}, "d": {**dd, "holds": not net},
                  "e": {"demonstrated_safe": safe, "holds": not any(safe.values())}}
    return out


def guard():
    """Refuses to read the test unless the tree is clean, the code is the frozen one and the pre-registration is committed."""
    st = git_state()
    assert not st["git_dirty"], "uncommitted changes in src/, tests/ or the pre-registration"
    fp = frozen_fingerprint()
    assert PINNED_SHA256 != "UNSET" and fp == PINNED_SHA256, "frozen code differs from the pinned fingerprint"
    assert _sh("ls-files", PRE_REG_DOC) == PRE_REG_DOC, "pre-registration document is not committed"
    return {**st, "fingerprint": fp}


def acquire_lock(out, info):
    """O_EXCL lock. If it exists: allowed only when status == 'started' and no results file (crash before anything was
    persisted or shown); the attempt counter is incremented. Otherwise refuse."""
    path, res = os.path.join(out, LOCK_NAME), os.path.join(out, RESULTS_NAME)
    os.makedirs(out, exist_ok=True)
    if os.path.exists(path):
        cur = json.load(open(path))
        if cur.get("status") != "started" or os.path.exists(res):
            raise RuntimeError(f"the final test reading was already done: {cur}")
        cur["attempts"] = cur.get("attempts", 1) + 1
        json.dump(cur, open(path, "w"))
        return cur
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    cur = {"status": "started", "attempts": 1, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **info}
    with os.fdopen(fd, "w") as f:
        json.dump(cur, f)
    return cur


def evaluate_once(out, parquet=PARQUET, d6_csv=D6_CSV, cost_path=COST_TABLE_PATH, guard_fn=guard):
    """Final reading of the test. Nothing is printed before test_results.json is written."""
    info = guard_fn()
    summ = json.load(open(os.path.join(out, SUMMARY_NAME)))
    assert summ["meta"]["fingerprint"] == info["fingerprint"] and summ["meta"]["epochs"] == EPOCHS, "trained under other code"
    for n in CONFIGS:
        for s in SEEDS:
            assert os.path.exists(os.path.join(out, CKPT_SUB, f"{n}_seed{s}.pt")), f"missing checkpoint {n} {s}"
    train = load_train(parquet)
    r_tbl, c_tbl = reward_table(train), cost_table_array(cost_path)
    _, val = split_val(train, 0.2, 0)
    bf_action, bf_info = BL.best_fixed(val, BUDGET)
    tg_map, tg_feas = BL.table_greedy_map(r_tbl, c_tbl, BUDGET)
    lock = acquire_lock(out, info)
    test = load_test(parquet)
    scripts = script_of(test["reservation"].to_numpy(), d6_csv)
    logged = test["action"].to_numpy(int)
    acts = {"always_rr": [BL.always_rr(logged)], "always_pf": [BL.always_pf(logged)],
            "best_fixed": [np.full(len(test), bf_action)],
            "table_greedy": [BL.table_greedy(test["load_bin"], r_tbl, c_tbl, BUDGET)]}
    for n in CONFIGS:
        acts[n] = [predict(n, s, test, out) for s in SEEDS]
    order = [s for s, _ in sorted(((s, (scripts == s).sum()) for s in set(scripts)), key=lambda t: -t[1])]
    groups = {}
    for g in (*order, "pooled"):
        sel = np.ones(len(test), bool) if g == "pooled" else scripts == g
        sub = test[sel].reset_index(drop=True)
        uniq, codes = np.unique(sub["reservation"].to_numpy(), return_inverse=True)
        k = len(uniq)
        idx = np.random.default_rng(BOOT_SEED).integers(0, k, size=(B_BOOT, k))
        pol = {}
        for name, per_seed in acts.items():
            parts = [_res_sums(sub, a[sel], codes, k, r_tbl, c_tbl, BUDGET) for a in per_seed]
            st = boot_stats(parts, idx)
            st["action_hist_mean"] = np.mean([np.bincount(a[sel], minlength=N_ACTIONS) for a in per_seed], axis=0).tolist()
            pol[name] = st
        groups[g] = {"n_reservations": int(k), "n_windows": int(len(sub)), "low_n": bool(k < MIN_RES_FLAG),
                     "ci_label": CI_LABEL, "policies": pol}
    res = {"meta": {**info, "dataset_version": DATASET_VERSION, "reading": "final (second reading of the test)",
                    "budget": BUDGET, "seeds": SEEDS, "epochs": EPOCHS, "bootstrap": {"B": B_BOOT, "seed": BOOT_SEED},
                    "lock": lock, "n_test_windows": int(len(test)),
                    "best_fixed": {"action": int(bf_action), **bf_info},
                    "table_greedy": {"action_per_load_bin": tg_map.tolist(), "bin_feasible": tg_feas.tolist()},
                    "estimate_note": "dm_* use train tables (not measured returns); matched_* cover only windows where "
                                     "the chosen action equals the logged action"},
           "groups": groups}
    res["expectations"] = check_expectations(res)
    tmp = os.path.join(out, RESULTS_NAME + ".tmp")
    with open(tmp, "w") as f:
        json.dump(res, f, indent=1, default=float)
    os.replace(tmp, os.path.join(out, RESULTS_NAME))
    lock["status"] = "completed"
    json.dump(lock, open(os.path.join(out, LOCK_NAME), "w"))
    return res


FROZEN = (_check_version, load_train, load_test, _train_one, train_job, train_phase, script_of, predict, _res_sums,
          _ratio, boot_stats, demonstrated_safe, check_expectations, guard, acquire_lock, evaluate_once, git_state,
          BL.always_rr, BL.always_pf, BL.best_fixed, BL.table_greedy_map, BL.table_greedy,
          cql.train_cql, cql.cql_loss, cql.mlp, cql.soft_update, cql.epoch_stats, cql.greedy_actions, cql.save_checkpoint,
          cql.load_q_net, safe_cql.train_safe_cql, safe_cql.update_lambda,
          iql.train_iql, iql.iql_losses, iql.expectile_loss, iql.greedy_actions, iql.save_checkpoint, iql.load_iql,
          fit_zscore, make_arrays, reward_table, cost_table_array, set_seed, split_val, state_tensor)


def frozen_fingerprint():
    """sha256 of the constants and of the source of every frozen function; pinned in PINNED_SHA256 and tests/test_e12.py."""
    consts = repr((SEEDS, EPOCHS, B_BOOT, BOOT_SEED, DATASET_VERSION, CONFIGS, BASELINES, PRIMARY, MAIN_SCRIPT, MIN_RES_FLAG,
                   PROCHE_REL, PARTIAL_COV, NET_SD, D6_CSV, COST_TABLE_PATH, PRE_REG_DOC, LOCK_NAME, RESULTS_NAME, SUMMARY_NAME,
                   CKPT_SUB, CI_LABEL, BUDGET, GAMMA, PARQUET, cql.CFG, safe_cql.SAFE_CFG, iql.IQL_CFG))
    return hashlib.sha256((consts + "".join(inspect.getsource(f) for f in FROZEN) + inspect.getsource(frozen_fingerprint)).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/e12")
    ap.add_argument("--workers", type=int, default=6)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--train", action="store_true")
    mode.add_argument("--evaluate", action="store_true")
    a = ap.parse_args()
    if a.train:
        assert not git_state()["git_dirty"], "uncommitted changes: commit first"
        s = train_phase(a.out, workers=a.workers)
        print(f"[e12] trained {len(s['runs'])} models, fingerprint {s['meta']['fingerprint'][:16]}, test not read")
        return
    res = evaluate_once(a.out)
    print("[e12] test_results.json written; policy / script / dm_reward / dm_cost / matched_cost / coverage")
    for g, grp in res["groups"].items():
        for p, st in grp["policies"].items():
            print(f"{g:9s} {p:18s} {st['dm_reward']['mean']:7.3f} {st['dm_cost']['mean']:.4f} "
                  f"[{st['dm_cost']['ci_lo']:.4f},{st['dm_cost']['ci_hi']:.4f}] {st['matched_cost']['mean']:.4f} "
                  f"cov {100 * st['matched_coverage']['mean']:.1f}%")
    print(json.dumps(res["expectations"], indent=1))


if __name__ == "__main__":
    main()
