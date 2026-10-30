"""E1: LP diagnostic of the one-step CMDP on the (action x load-bin) tables.

DIAGNOSTIC, NOT A PERFORMANCE. The LP uses the same tables (reward R[a, b], cost C[a, b]) and the same
bin shares p_b as the direct-method (DM) estimator of `src.evaluate.evaluate_policy`. Its optimum is an
upper bound of what any policy that only sees the load bin can reach *according to these tables*.

    max_x  sum_b p_b sum_a x[a,b] R[a,b]    s.t.  sum_b p_b sum_a x[a,b] C[a,b] <= d,  sum_a x[a,b] = 1,  x >= 0

Folds (validation BY SCRIPT, never by random reservations): script A = a908e4cc, script B = a53521b2,
both read from the TRAIN split only. The test split is never loaded (`load_fold` filters split == 'train').
For each fold: tables fitted on that script alone, bin shares from that script's windows.

Outputs (results/e1_*): summary.json, cells.csv, det_policies.csv, lagrangian_curve.csv, boot.csv.
Read-only on the dataset; deterministic given --seed. No training.

    python -m src.lp_diagnostic
"""
import argparse
import itertools
import json
import os

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from src.build_dataset import MIN_CELL_N
from src.common import BUDGET, N_ACTIONS, N_BINS, PARQUET

SCRIPTS = {"A": "a908e4cc", "B": "a53521b2"}   # md5 prefixes, both in train (clusters 2 and 3)
FOLDS = {**SCRIPTS, "TRAIN": None}              # TRAIN = whole train split: the table the notebook agents see
TAUS = (0.05, 0.1, 0.2)                          # softmax temperatures (scaled-reward units): a choice, not tuned
LAM_MAX, LAM_STEP = 200.0, 0.005


# ----------------------------------------------------------------------------- data
def load_fold(parquet, d6_csv, md5_prefix):
    """Windows of one traffic script, TRAIN split only (the test rows are filtered out at read time)."""
    cols = ["reservation", "split", "action", "load_bin", "reward_embb_Mbps", "urllc_frac_viol"]
    df = pd.read_parquet(parquet, columns=cols, filters=[("split", "==", "train")])
    if md5_prefix is not None:                    # None: the whole train split (all clusters 2-3 scripts)
        res = pd.read_csv(d6_csv, usecols=["res", "md5"])
        res = res[res["md5"].str.startswith(md5_prefix)]
        df = df[df["reservation"].isin(res["res"])]
    assert len(df) and (df["split"] == "train").all()
    return df.reset_index(drop=True)


def cell_sums(df):
    """Per-reservation sums on the (action, bin) grid: Sc, Sr, N with shape [n_res, A, B].
    Each reservation has one action, so most of its cells are empty."""
    codes, uniq = pd.factorize(df["reservation"])
    k = len(uniq)
    idx = (codes, df["action"].to_numpy(int), df["load_bin"].to_numpy(int))
    shape = (k, N_ACTIONS, N_BINS)
    Sc, Sr, N = np.zeros(shape), np.zeros(shape), np.zeros(shape)
    np.add.at(Sc, idx, df["urllc_frac_viol"].to_numpy())
    np.add.at(Sr, idx, df["reward_embb_Mbps"].to_numpy())
    np.add.at(N, idx, 1.0)
    return Sc, Sr, N


def tables_from_sums(Sc, Sr, N, min_n=MIN_CELL_N):
    """Same tables as the pipeline (`fit_cost_table`: cost falls back to the per-action mean when the cell has
    < min_n windows; `reward_table`: reward falls back to the per-action mean when the cell is empty).
    Inputs: sums over reservations, shape [A, B]. Returns (R, C, p, n_cell); NaN if an action has no window."""
    with np.errstate(invalid="ignore", divide="ignore"):
        c_act = Sc.sum(1) / N.sum(1)
        r_act = Sr.sum(1) / N.sum(1)
        C = np.where(N >= min_n, Sc / N, c_act[:, None])
        R = np.where(N > 0, Sr / N, r_act[:, None])
    p = N.sum(0) / N.sum()
    return R, C, p, N


# ----------------------------------------------------------------------------- LP
def solve_lp(R, C, p, d):
    """Returns dict(feasible, cost_min, reward, cost, x, mu_marginal). `x` is [A, B] (columns sum to 1).
    mu_marginal: dual of the budget constraint in reward units per unit of cost (>= 0)."""
    A, B = R.shape
    cost_min = float((p * C.min(0)).sum())
    out = {"cost_min": cost_min, "feasible": cost_min <= d}
    if not out["feasible"]:
        return out
    c = -(p[None, :] * R).ravel()
    A_ub = (p[None, :] * C).ravel()[None, :]
    A_eq = np.zeros((B, A * B))
    for b in range(B):
        A_eq[b, b::B] = 1.0
    res = linprog(c, A_ub=A_ub, b_ub=[d], A_eq=A_eq, b_eq=np.ones(B), bounds=(0, None), method="highs")
    assert res.status == 0, res.message
    x = res.x.reshape(A, B)
    out.update(reward=float(-res.fun), cost=float((p * (x * C).sum(0)).sum()), x=x,
               mu_marginal=float(max(0.0, -res.ineqlin.marginals[0])))
    return out


def value_slopes(R, C, p, d, h=1e-6):
    """Left/right derivative of the value function V(d) (concave, piecewise linear): the dual is an interval
    when d sits on a kink. In reward units per unit cost; NaN where V is undefined (infeasible side)."""
    f = lambda dd: solve_lp(R, C, p, dd).get("reward", np.nan)
    v0, vm, vp = f(d), f(d - h), f(d + h)
    return (v0 - vm) / h, (vp - v0) / h


# ----------------------------------------------------------------------------- deterministic policies
def enumerate_det(R, C, p):
    """All A**B deterministic per-bin policies. Returns a frame (policy, reward, cost)."""
    rows = []
    b = np.arange(R.shape[1])
    for pol in itertools.product(range(R.shape[0]), repeat=R.shape[1]):
        rows.append({"policy": "-".join(map(str, pol)), "reward": float((p * R[list(pol), b]).sum()),
                     "cost": float((p * C[list(pol), b]).sum())})
    return pd.DataFrame(rows)


def best_det(det, d):
    ok = det[det["cost"] <= d]
    if ok.empty:
        return None
    return ok.loc[ok["reward"].idxmax()].to_dict()


def eval_policy(x, R, C, p):
    """DM reward and cost of a randomised per-bin policy x [A, B] under tables (R, C) and shares p."""
    return float((p * (x * R).sum(0)).sum()), float((p * (x * C).sum(0)).sum())


def det_to_x(pol, n_actions=N_ACTIONS):
    pol = [int(v) for v in pol.split("-")]
    x = np.zeros((n_actions, len(pol)))
    x[pol, np.arange(len(pol))] = 1.0
    return x


# ----------------------------------------------------------------------------- Lagrangian-greedy curves
def lagrangian_scores(R, C, lam, d, r_scale):
    """Per-bin score of each action in the units of the agent's target: r/r_scale - lam * (c/d - 1).
    lam: array [L]. Returns [L, A, B]."""
    return R[None] / r_scale - lam[:, None, None] * (C[None] / d - 1.0)


def argmax_curve(R, C, p, d, r_scale, lam):
    """Reward, cost and policy of the argmax (deterministic, ties -> lowest index) policy as a function of lambda."""
    a = lagrangian_scores(R, C, lam, d, r_scale).argmax(1)       # [L, B]
    b = np.arange(R.shape[1])[None]
    return (p * R[a, b]).sum(1), (p * C[a, b]).sum(1), a


def softmax_cost(R, C, p, d, r_scale, lam, tau):
    S = lagrangian_scores(R, C, np.atleast_1d(lam), d, r_scale) / tau
    S = S - S.max(1, keepdims=True)
    pi = np.exp(S)
    pi /= pi.sum(1, keepdims=True)                               # [L, A, B]
    return (p * (pi * R[None]).sum(1)).sum(1), (p * (pi * C[None]).sum(1)).sum(1), pi


def softmax_lambda(R, C, p, d, r_scale, tau, hi=LAM_MAX):
    """Smallest lambda >= 0 with softmax-policy cost <= d (cost decreases with lambda); None if even `hi` fails."""
    cost = lambda l: softmax_cost(R, C, p, d, r_scale, l, tau)[1][0]
    if cost(0.0) <= d:
        return 0.0
    if cost(hi) > d:
        return None
    lo_, hi_ = 0.0, hi
    for _ in range(80):
        mid = 0.5 * (lo_ + hi_)
        lo_, hi_ = (mid, hi_) if cost(mid) > d else (lo_, mid)
    return hi_


def curve_steps(R, C, p, d, r_scale):
    """Distinct segments of the argmax curve: (lam_from, lam_to, cost, reward, policy)."""
    lam = np.arange(0.0, LAM_MAX + LAM_STEP, LAM_STEP)
    rew, cost, a = argmax_curve(R, C, p, d, r_scale, lam)
    rows, start = [], 0
    for i in range(1, len(lam) + 1):
        if i == len(lam) or not np.array_equal(a[i], a[start]):
            rows.append({"lam_from": lam[start], "lam_to": lam[i - 1], "cost": float(cost[start]),
                         "reward": float(rew[start]), "policy": "-".join(map(str, a[start]))})
            start = i
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- one fold
def lp_report(R, C, p, d, r_scale):
    """Everything computed from a (R, C, p) triple."""
    lp = solve_lp(R, C, p, d)
    rep = {"cost_min": lp["cost_min"], "feasible": bool(lp["feasible"]),
           "reward_unconstrained": float((p * R.max(0)).sum())}
    if not lp["feasible"]:
        # Decision: report as is with the minimal reachable cost; the budget is not changed.
        x = np.zeros_like(R)
        x[C.argmin(0), np.arange(R.shape[1])] = 1.0
        rep.update(reward_at_min_cost=eval_policy(x, R, C, p)[0], x_min_cost=x.tolist())
        return rep, lp
    ml, mr = value_slopes(R, C, p, d)
    x = lp["x"]
    n_rand = int(((x > 1e-9) & (x < 1 - 1e-9)).any(0).sum())
    rep.update(reward=lp["reward"], cost=lp["cost"], x=x.tolist(), n_randomised_bins=n_rand,
               budget_active=bool(lp["cost"] >= d - 1e-9), mu_marginal=lp["mu_marginal"], mu_left=ml, mu_right=mr,
               lam_star=lp["mu_marginal"] * d / r_scale, lam_star_left=ml * d / r_scale, lam_star_right=mr * d / r_scale)
    return rep, lp


def run_fold(df, d, boot, seed):
    Sc, Sr, N = cell_sums(df)
    R, C, p, _ = tables_from_sums(Sc.sum(0), Sr.sum(0), N.sum(0))
    r_scale = float(df["reward_embb_Mbps"].std())
    rep, lp = lp_report(R, C, p, d, r_scale)
    det = enumerate_det(R, C, p)
    bd = best_det(det, d)
    # behaviour policy = the logged actions: DM reward/cost with the same tables (reference, not a candidate)
    Nab = N.sum(0)
    x_beh = Nab / Nab.sum(0, keepdims=True)
    rep["behaviour"] = dict(zip(("reward", "cost"), eval_policy(x_beh, R, C, p)))
    rep.update(n_windows=int(len(df)), n_reservations=int(df["reservation"].nunique()), p=p.tolist(),
               r_scale=r_scale, R=R.tolist(), C=C.tolist(),
               n_cell_windows=N.sum(0).tolist(), n_cell_reservations=(N > 0).sum(0).tolist(),
               cells_cost_fallback=int((N.sum(0) < MIN_CELL_N).sum()),
               cost_det_min=float(det["cost"].min()), n_det_feasible=int((det["cost"] <= d).sum()), best_det=bd)
    if bd is not None and rep["feasible"]:
        rep["det_gap_reward"] = rep["reward"] - bd["reward"]
        rep["det_gap_reward_rel"] = rep["det_gap_reward"] / rep["reward"]
    # deterministic costs just below / above d: the granularity argmax cannot cross
    below, above = det[det["cost"] <= d]["cost"], det[det["cost"] > d]["cost"]
    rep["det_cost_below_d"] = float(below.max()) if len(below) else None
    rep["det_cost_above_d"] = float(above.min()) if len(above) else None
    steps = curve_steps(R, C, p, d, r_scale)
    cross = steps[steps["cost"] <= d]
    rep["argmax_curve"] = {"n_segments": int(len(steps)),
                           "lam_first_cost_le_d": float(cross["lam_from"].iloc[0]) if len(cross) else None,
                           "cost_at_that_segment": float(cross["cost"].iloc[0]) if len(cross) else None,
                           "reward_at_that_segment": float(cross["reward"].iloc[0]) if len(cross) else None,
                           "reaches_cost_exactly_d": bool(np.any(np.abs(steps["cost"] - d) < 1e-4))}
    sm = {}
    for tau in TAUS:
        lam = softmax_lambda(R, C, p, d, r_scale, tau)
        if lam is None:
            sm[str(tau)] = None
            continue
        rw, ct, pi = softmax_cost(R, C, p, d, r_scale, lam, tau)
        sm[str(tau)] = {"lam": lam, "reward": float(rw[0]), "cost": float(ct[0]),
                        "max_prob_mean": float((p * pi[0].max(0)).sum())}
    rep["softmax_variant"] = sm
    # bootstrap of reservations INSIDE this script (conditional on the script; reservations treated as exchangeable [H])
    rng = np.random.default_rng(seed)
    k = Sc.shape[0]
    rows = []
    for i in range(boot):
        idx = rng.integers(0, k, k)
        Rb, Cb, pb, _ = tables_from_sums(Sc[idx].sum(0), Sr[idx].sum(0), N[idx].sum(0))
        if np.isnan(Rb).any() or np.isnan(Cb).any():
            rows.append({"b": i, "valid": False})
            continue
        rb, _ = lp_report(Rb, Cb, pb, d, r_scale)
        rows.append({"b": i, "valid": True, "feasible": rb["feasible"], "cost_min": rb["cost_min"],
                     "reward": rb.get("reward", np.nan), "lam_star": rb.get("lam_star", np.nan),
                     "budget_active": rb.get("budget_active", np.nan)})
    return rep, steps, det, pd.DataFrame(rows), (R, C, p, r_scale, lp)


def cross_eval(src, dst, d):
    """Policies derived from tables of `src`, evaluated with the tables and bin shares of `dst`. Still DM."""
    R1, C1, p1, _, lp1 = src
    R2, C2, p2, _, lp2 = dst
    out = {"d": d}
    if lp1["feasible"]:
        out["lp_policy"] = dict(zip(("reward", "cost"), eval_policy(lp1["x"], R2, C2, p2)))
    b1 = best_det(enumerate_det(R1, C1, p1), d)
    if b1 is not None:
        out["best_det_policy"] = {**dict(zip(("reward", "cost"), eval_policy(det_to_x(b1["policy"], R1.shape[0]), R2, C2, p2))),
                                  "policy": b1["policy"]}
    if lp2["feasible"]:
        out["oracle_lp_dst"] = {"reward": lp2["reward"], "cost": lp2["cost"]}
    out["cost_min_dst"] = lp2["cost_min"]
    return out


def boot_summary(boot):
    v = boot[boot["valid"]]
    f = v[v["feasible"].astype(bool)]
    q = lambda s: [float(s.quantile(0.025)), float(s.quantile(0.5)), float(s.quantile(0.975))] if len(s) else None
    return {"B": int(len(boot)), "n_valid": int(len(v)), "share_feasible": float(v["feasible"].astype(bool).mean()),
            "cost_min_q025_q50_q975": q(v["cost_min"]), "reward_q025_q50_q975": q(f["reward"]),
            "lam_star_q025_q50_q975": q(f["lam_star"]),
            "share_budget_active": float(f["budget_active"].astype(bool).mean()) if len(f) else None}


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default=PARQUET)
    ap.add_argument("--d6", default="results/d6_reservations.csv")
    ap.add_argument("--meta", default=PARQUET.replace(".parquet", ".meta.json"))
    ap.add_argument("--budget", type=float, default=BUDGET)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/e1")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.meta) as f:
        version = json.load(f)["dataset_version"]
    summ = {"meta": {"dataset_version": version, "budget": a.budget, "seed": a.seed, "boot": a.boot, "taus": list(TAUS),
                     "scripts": SCRIPTS, "folds": list(FOLDS), "diagnostic_only": True, "test_split_read": False}, "folds": {}}
    packs, steps_all, det_all, boot_all = {}, [], [], []
    for name, md5 in FOLDS.items():
        df = load_fold(a.parquet, a.d6, md5)
        rep, steps, det, boot, pack = run_fold(df, a.budget, a.boot, a.seed)
        rep["boot"] = boot_summary(boot)
        summ["folds"][name] = rep
        packs[name] = pack
        steps_all.append(steps.assign(fold=name))
        det_all.append(det.assign(fold=name))
        boot_all.append(boot.assign(fold=name))
    summ["cross"] = {"A_to_B": cross_eval(packs["A"], packs["B"], a.budget),
                     "B_to_A": cross_eval(packs["B"], packs["A"], a.budget)}
    pd.concat(steps_all).to_csv(a.out + "_lagrangian_curve.csv", index=False)
    pd.concat(det_all).to_csv(a.out + "_det_policies.csv", index=False)
    pd.concat(boot_all).to_csv(a.out + "_boot.csv", index=False)
    cells = [{"fold": n, "action": ai, "bin": b, "R": rep["R"][ai][b], "C": rep["C"][ai][b],
              "n_windows": rep["n_cell_windows"][ai][b], "n_reservations": rep["n_cell_reservations"][ai][b]}
             for n, rep in summ["folds"].items() for ai in range(N_ACTIONS) for b in range(N_BINS)]
    pd.DataFrame(cells).to_csv(a.out + "_cells.csv", index=False)
    with open(a.out + "_summary.json", "w") as f:
        json.dump(summ, f, indent=1, default=float)
    for n, rep in summ["folds"].items():
        print(n, {k: rep[k] for k in ("feasible", "cost_min", "cost_det_min", "reward", "cost", "lam_star") if k in rep})


if __name__ == "__main__":
    main()
