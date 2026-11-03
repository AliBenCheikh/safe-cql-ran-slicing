"""E13a: sensitivity of the table-greedy diagnostic to the NUMBER OF LOAD LEVELS (2, 3, 4, 5), reviewer point R1-W2.

DESCRIPTIVE, NOT A SELECTION. All k are reported; no k is chosen, ranked or recommended. TRAIN split only (the test split
is never read: the loader filters split == 'train' and asserts it). The frozen paper configuration (3 load bins, 5 s
windows) is unchanged. This does not motivate a third read of the test split.

Folds as E1/E11: A = a908e4cc, B = a53521b2. Direction "A->B": edges, tables and table-greedy come from A (source);
the policy is evaluated on B's tables with B's bin shares (validation); B's windows are binned with A's edges.

Edges: interior k-quantiles (probabilities i/k, i = 1..k-1) of `nof_ue` over the SOURCE script's windows, right-closed bins
(a value equal to an edge goes to the lower bin), open ends (equivalent to the clipping of `load_bin`). Duplicate edges
(ties) are merged: the realised number of levels is reported, nothing is substituted. Reference row `edges3_current`
uses the pipeline's LOAD_EDGES (interior 3.5, 5.5).

Tables: `tables_from_sums` (cost falls back to the per-action mean below MIN_CELL_N windows). Table-greedy: the E11 one
(`e11_alpha_grid.table_greedy`). Cell CI: percentile bootstrap over the reservations of the cell (B = 2000), raw cell mean
sum(c)/sum(n); cells with < 2 reservations have no CI. Transferred-cost bootstrap: reservations resampled inside the
source script and inside the validation script (independently), edges and r_scale fixed at the original source values;
conditional on the script, it does not measure between-script variability.

REPRODUCTION GUARD (run first, the run aborts if it fails): with the current edges the transferred table-greedy must give
0.0520 / 0.0303 (cost, A->B / B->A) and reward 10.352 / 11.370, and the oracle 10.765 / 0.0286 (on B) and 11.703 / 0.0215
(on A), as written in docs/e11_alpha_grid.md.

    python -m src.e13_load_levels --guard          # guard only
    python -m src.e13_load_levels --out results/e13a
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

from src.build_dataset import LOAD_EDGES, MIN_CELL_N
from src.common import BUDGET, N_ACTIONS, PARQUET
from src.e11_alpha_grid import table_greedy
from src.e2_safe_cql_diagnostic import git_state
from src.lp_diagnostic import SCRIPTS, tables_from_sums

KS = (2, 3, 4, 5)
REF = "edges3_current"
D6_CSV = "results/d6_reservations.csv"
BOOT_B = 2000
SEED = 0
DIRECTIONS = (("A", "B"), ("B", "A"))   # (source, validation)

# E11 numbers (docs/e11_alpha_grid.md, "Références"): (reward, cost) rounded as printed there.
GUARD = {"transferred": {("A", "B"): (10.352, 0.0520), ("B", "A"): (11.370, 0.0303)},
         "oracle_on": {"B": (10.765, 0.0286), "A": (11.703, 0.0215)}}
GUARD_TOL_REWARD, GUARD_TOL_COST = 5e-4, 5e-5


# ----------------------------------------------------------------------------- pure functions
def quantile_edges(nof, k):
    """Interior edges (sorted, unique) of the k-quantile split of `nof`. Fewer than k-1 if there are ties."""
    q = np.quantile(np.asarray(nof, float), [i / k for i in range(1, k)])
    return np.unique(q)


def assign_bins(nof, interior):
    """Right-closed bins 0..len(interior), open ends: x <= interior[0] -> 0, x > interior[-1] -> last."""
    return np.searchsorted(np.asarray(interior, float), np.asarray(nof, float), side="left").astype(int)


def edge_sets(src_nof):
    """name -> interior edges, for every k and the current-edges reference."""
    out = {f"k{k}": quantile_edges(src_nof, k) for k in KS}
    out[REF] = np.asarray(LOAD_EDGES[1:-1], float)
    return out


def res_sums(df, n_bins):
    """Per-reservation sums of cost, reward and window count on the (action, bin) grid: arrays [n_res, A, B]."""
    codes, uniq = pd.factorize(df["reservation"])
    idx = (codes, df["action"].to_numpy(int), df["bin"].to_numpy(int))
    shape = (len(uniq), N_ACTIONS, n_bins)
    Sc, Sr, N = np.zeros(shape), np.zeros(shape), np.zeros(shape)
    np.add.at(Sc, idx, df["urllc_frac_viol"].to_numpy())
    np.add.at(Sr, idx, df["reward_embb_Mbps"].to_numpy())
    np.add.at(N, idx, 1.0)
    return Sc, Sr, N


def tables(Sc, Sr, N, r_scale):
    R, C, p, _ = tables_from_sums(Sc.sum(0), Sr.sum(0), N.sum(0))
    return {"R": R, "C": C, "p": p, "r_scale": r_scale}


def evaluate(pol, tab):
    b = np.arange(len(pol))
    return float((tab["p"] * tab["R"][pol, b]).sum()), float((tab["p"] * tab["C"][pol, b]).sum())


def cell_stats(Sc, N, rng, boot=BOOT_B, d=BUDGET):
    """Per (action, bin) cell: reservations, windows, raw mean cost, bootstrap CI over reservations (None if < 2)."""
    rows = []
    for a in range(N_ACTIONS):
        for b in range(N.shape[2]):
            m = N[:, a, b] > 0
            n_res, n_win = int(m.sum()), int(N[:, a, b].sum())
            row = {"action": a, "bin": b, "n_res": n_res, "n_win": n_win, "fallback": bool(n_win < MIN_CELL_N),
                   "cost_mean": float(Sc[:, a, b].sum() / n_win) if n_win else np.nan, "ci_lo": np.nan, "ci_hi": np.nan,
                   "ci_has_d": None}
            if n_res >= 2:
                sc, n = Sc[m, a, b], N[m, a, b]
                idx = rng.integers(0, n_res, (boot, n_res))
                est = sc[idx].sum(1) / n[idx].sum(1)
                lo, hi = np.quantile(est, [0.025, 0.975])
                row.update(ci_lo=float(lo), ci_hi=float(hi), ci_has_d=bool(lo <= d <= hi))
            rows.append(row)
    return pd.DataFrame(rows)


def side_summary(cells):
    """Counts of the pre-declared report for one side (source or validation) of one (k, direction)."""
    nr = cells["n_res"]
    with_ci = cells[cells["n_res"] >= 2]
    nres_pos = nr[nr > 0]
    return {"n_cells": int(len(cells)), "n_empty": int((nr == 0).sum()), "n_res_le2": int((nr <= 2).sum()),
            "n_res_le5": int((nr <= 5).sum()), "n_fallback_lt_min_n": int(cells["fallback"].sum()),
            "n_res_min": int(nr.min()), "n_res_median": float(np.median(nr)), "n_res_max": int(nr.max()),
            "n_res_median_nonempty": float(np.median(nres_pos)) if len(nres_pos) else None,
            "n_cells_without_ci": int((nr < 2).sum()), "n_cells_with_ci": int(len(with_ci)),
            "n_ci_contains_d": int(with_ci["ci_has_d"].sum()),
            "share_ci_contains_d": float(with_ci["ci_has_d"].mean()) if len(with_ci) else None}


def transferred_boot(src_sums, val_sums, src_r_scale, val_r_scale, rng, boot=BOOT_B, d=BUDGET):
    """Reservations resampled inside each script; edges and r_scale fixed. Replicates with an action absent from a
    resampled table are invalid and counted."""
    ks, kv = src_sums[0].shape[0], val_sums[0].shape[0]
    cost, rew, invalid = [], [], 0
    for _ in range(boot):
        i, j = rng.integers(0, ks, ks), rng.integers(0, kv, kv)
        ts = tables(*(s[i] for s in src_sums), src_r_scale)
        tv = tables(*(s[j] for s in val_sums), val_r_scale)
        if any(np.isnan(t[x]).any() for t in (ts, tv) for x in ("R", "C")):
            invalid += 1
            continue
        pol, _, _ = table_greedy(ts, d)
        r, c = evaluate(pol, tv)
        rew.append(r)
        cost.append(c)
    cost, rew = np.asarray(cost), np.asarray(rew)
    q = lambda x: [float(v) for v in np.quantile(x, [0.025, 0.5, 0.975])] if len(x) else None
    return {"B": boot, "n_invalid": invalid, "cost_q025_q50_q975": q(cost), "reward_q025_q50_q975": q(rew),
            "share_cost_le_d": float((cost <= d).mean()) if len(cost) else None}


# ----------------------------------------------------------------------------- data
def load_scripts(parquet=PARQUET, d6_csv=D6_CSV):
    """name -> window frame of that script, TRAIN split only."""
    cols = ["reservation", "split", "action", "nof_ue", "load_bin", "reward_embb_Mbps", "urllc_frac_viol"]
    df = pd.read_parquet(parquet, columns=cols, filters=[("split", "==", "train")])
    assert len(df) and (df["split"] == "train").all(), "test split must never be read"
    res = pd.read_csv(d6_csv, usecols=["res", "md5"])
    out = {}
    for name, md5 in SCRIPTS.items():
        out[name] = df[df["reservation"].isin(set(res.loc[res["md5"].str.startswith(md5), "res"]))].reset_index(drop=True)
        assert len(out[name]) and out[name]["nof_ue"].notna().all()
    return out


def analyse_direction(src_name, val_name, scripts, edges_by_name, rng_seed, boot=BOOT_B, do_boot=True):
    """All pre-declared quantities for one direction and every edge set."""
    src, val = scripts[src_name], scripts[val_name]
    r_scale_s, r_scale_v = float(src["reward_embb_Mbps"].std()), float(val["reward_embb_Mbps"].std())
    out = []
    for ei, (name, interior) in enumerate(edges_by_name.items()):
        k = len(interior) + 1
        s, v = src.assign(bin=assign_bins(src["nof_ue"], interior)), val.assign(bin=assign_bins(val["nof_ue"], interior))
        ss, vs = res_sums(s, k), res_sums(v, k)
        ts, tv = tables(*ss, r_scale_s), tables(*vs, r_scale_v)
        assert not any(np.isnan(t[x]).any() for t in (ts, tv) for x in ("R", "C")), "an action is absent from a fold"
        pol, lam, reached = table_greedy(ts, BUDGET)
        tr_r, tr_c = evaluate(pol, tv)
        own_r, own_c = evaluate(pol, ts)
        rng = np.random.default_rng([SEED, rng_seed, ei])
        cs, cv = cell_stats(ss[0], ss[2], rng, boot), cell_stats(vs[0], vs[2], rng, boot)
        rec = {"edge_set": name, "k_requested": int(name[1:]) if name.startswith("k") else 3, "k_realised": k,
               "direction": f"{src_name}->{val_name}", "interior_edges": [float(x) for x in interior],
               "share_windows_source": [float(x) for x in ts["p"]], "share_windows_validation": [float(x) for x in tv["p"]],
               "source": side_summary(cs), "validation": side_summary(cv),
               "table_greedy_policy_by_level": [int(x) for x in pol], "table_greedy_lambda": lam, "table_greedy_reached_d": reached,
               "transferred": {"reward": tr_r, "cost": tr_c}, "on_source_tables": {"reward": own_r, "cost": own_c}}
        if do_boot:
            rec["transferred_boot"] = transferred_boot(ss, vs, r_scale_s, r_scale_v, rng, boot)
        out.append((rec, cs.assign(edge_set=name, direction=rec["direction"], side="source"),
                    cv.assign(edge_set=name, direction=rec["direction"], side="validation")))
    return out


# ----------------------------------------------------------------------------- guard
def reproduction_guard(scripts):
    """Current edges -> E11's printed references. Returns (ok, details). Never skipped by the main run."""
    edges = {REF: np.asarray(LOAD_EDGES[1:-1], float)}
    det, ok = {}, True
    for si, (a, b) in enumerate(DIRECTIONS):
        # the rebinning must equal the pipeline's own load_bin
        for nm in (a, b):
            same = np.array_equal(assign_bins(scripts[nm]["nof_ue"], edges[REF]), scripts[nm]["load_bin"].to_numpy(int))
            det[f"rebin_equals_load_bin_{nm}"] = bool(same)
            ok &= same
        (rec, _, _), = analyse_direction(a, b, scripts, edges, si, do_boot=False)
        er, ec = GUARD["transferred"][(a, b)]
        det[f"transferred_{a}->{b}"] = {"got": [rec["transferred"]["reward"], rec["transferred"]["cost"]], "expected": [er, ec]}
        ok &= abs(rec["transferred"]["reward"] - er) <= GUARD_TOL_REWARD and abs(rec["transferred"]["cost"] - ec) <= GUARD_TOL_COST
        # oracle on b = table-greedy(b) on b's own tables = source b, direction b->a gives it as "on_source_tables"
        (rec_b, _, _), = analyse_direction(b, a, scripts, edges, si, do_boot=False)
        orr, oc = GUARD["oracle_on"][b]
        det[f"oracle_on_{b}"] = {"got": [rec_b["on_source_tables"]["reward"], rec_b["on_source_tables"]["cost"]], "expected": [orr, oc]}
        ok &= abs(rec_b["on_source_tables"]["reward"] - orr) <= GUARD_TOL_REWARD and abs(rec_b["on_source_tables"]["cost"] - oc) <= GUARD_TOL_COST
    return bool(ok), det


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/e13a")
    ap.add_argument("--guard", action="store_true", help="reproduction guard only")
    ap.add_argument("--boot", type=int, default=BOOT_B)
    ap.add_argument("--allow-dirty", action="store_true")
    a = ap.parse_args()
    git = git_state()
    assert a.allow_dirty or a.guard or not git["git_dirty_src_tests"], "uncommitted changes in src/ or tests/: commit first"
    scripts = load_scripts()
    ok, det = reproduction_guard(scripts)
    print(f"[e13a] reproduction guard: {'PASS' if ok else 'FAIL'}\n{json.dumps(det, indent=1, default=float)}", flush=True)
    if not ok:
        sys.exit("[e13a] GUARD FAILED: stopping, nothing else computed")
    if a.guard:
        return
    recs, cells = [], []
    for si, (s, v) in enumerate(DIRECTIONS):
        for rec, cs, cv in analyse_direction(s, v, scripts, edge_sets(scripts[s]["nof_ue"]), si, a.boot):
            recs.append(rec)
            cells += [cs, cv]
            t = rec["transferred"]
            print(f"[e13a] {rec['direction']} {rec['edge_set']:>14} k={rec['k_realised']} edges={np.round(rec['interior_edges'], 3).tolist()} "
                  f"transferred reward={t['reward']:.3f} cost={t['cost']:.4f} "
                  f"CI={np.round(rec['transferred_boot']['cost_q025_q50_q975'], 4).tolist()}", flush=True)
    with open(PARQUET.replace(".parquet", ".meta.json")) as f:
        version = json.load(f)["dataset_version"]
    meta = {"dataset_version": version, **git, "script": "src/e13_load_levels.py", "budget": BUDGET, "seed": SEED, "boot": a.boot,
            "ks": KS, "folds": SCRIPTS, "guard": det, "diagnostic_only": True, "test_split_read": False}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out + "_summary.json", "w") as f:
        json.dump({"meta": meta, "rows": recs}, f, indent=1, default=float)
    pd.concat(cells, ignore_index=True).to_csv(a.out + "_cells.csv", index=False)


if __name__ == "__main__":
    main()
