"""E13d: effect of the latency filter of `build_dataset._urllc_stream` on the URLLC cost. Protocol:
docs/e13d_protocole_filtre_latence.md (committed before any read). TRAIN split only (510 usable reservations); the test
split and its saved results are never opened; nothing is trained (checkpoints are only used for inference).

Per window, packets are split into kept (0 <= lat < 20000 ms, the pipeline's own filter), dropped-negative (lat < 0),
dropped-big (lat >= 20000) and non-finite lat (counted, not assigned). Bounds on the window cost:
  lo_w = v_w / (k_w + e_w)         dropped counted as non-violations
  hi_w = (v_w + e_w) / (k_w + e_w) dropped counted as violations      (e_w = dropped-neg + dropped-big of that window)

    python -m src.e13d_latency_filter --out results/e13d
"""
import argparse
import json
import os
import sys
from multiprocessing import Pool
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.build_dataset import (SLA_MS, URLLC_IMSI, _enb_stream, _imsi_full, _read, fit_cost_table, window_index)
from src.checks import common as C
from src.common import BUDGET, N_ACTIONS, N_BINS, PARQUET, COST_TABLE, cost_table_array
from src.e13b_sampling_check import res_path
from src.e2_safe_cql_diagnostic import git_state

D = BUDGET
TRIPLES = {"alpha0.1": ("safe_cql_a0.1", "cql_a0.1", "iql"), "alpha0.5": ("safe_cql_a0.5", "cql_a0.5", "iql")}
SEEDS = (0, 1, 2, 3, 4)
SCRIPT_MD5 = {"A": "a908e4cc", "B": "a53521b2"}
BIG_MS = 20000.0


# ----------------------------------------------------------------------------- pure functions
def classify(lat):
    """Boolean masks (kept, neg, big, nan) of a latency vector in ms. kept is the pipeline's filter, verbatim."""
    lat = np.asarray(lat, float)
    kept = (lat >= 0) & (lat < 20000)
    return kept, lat < 0, lat >= BIG_MS, ~np.isfinite(lat)


def bounds(k, v, e):
    """Per-window cost: pipeline (kept only), lo (dropped = non-violations), hi (dropped = violations)."""
    k, v, e = (np.asarray(x, float) for x in (k, v, e))
    return v / k, v / (k + e), (v + e) / (k + e)


def reservation_windows(res_dir):
    """(per-window DataFrame, counts dict) for one reservation, or (None, counts) if the pipeline would skip it."""
    ue = sorted(d for d in __import__("glob").glob(os.path.join(res_dir, "ue_*")) if os.path.isdir(d))
    t0, _ = _enb_stream(res_dir)
    frames = []
    for d in ue:
        imsi = _imsi_full(d)
        if imsi is None or imsi[-3:] not in URLLC_IMSI:
            continue
        m = _read(os.path.join(d, "mgen.csv"), ",", usecols=["Received Time", "Sent Time"])
        if m is None:
            continue
        m["lat"] = (m["Received Time"] - m["Sent Time"]) * 1000.0
        if len(m):                                  # header-only files have object dtype and would contaminate the concat
            frames.append(m)
    counts = {"n_packets": 0, "n_kept": 0, "n_neg": 0, "n_big": 0, "n_nan": 0, "n_nan_time_dropped": 0}
    if t0 is None or not frames:
        return None, counts
    u = pd.concat(frames, ignore_index=True)
    kept, neg, big, nan = classify(u["lat"].to_numpy())
    counts.update(n_packets=int(len(u)), n_kept=int(kept.sum()), n_neg=int(neg.sum()), n_big=int(big.sum()), n_nan=int(nan.sum()))
    if not kept.any():
        return None, counts
    # same time transform as the pipeline: day0 / tz_h from the minimum Received Time of the KEPT packets
    day0 = pd.Timestamp(t0, unit="ms", tz="UTC").normalize().timestamp()
    tz_h = int(round((day0 + u.loc[kept, "Received Time"].min() - t0 / 1000.0) / 3600.0))

    def win(rt):
        t_abs = day0 + np.asarray(rt, float) - 3600.0 * tz_h
        t_abs = np.where(t_abs < t0 / 1000.0 - 43200.0, t_abs + 86400.0, t_abs)
        return window_index(t_abs * 1000.0, t0)

    uk = u[kept]
    wk = win(uk["Received Time"].to_numpy())
    kdf = pd.DataFrame({"win": wk, "viol": (uk["lat"].to_numpy() > SLA_MS)})
    kdf = kdf[kdf["win"] >= 0].groupby("win").agg(k=("viol", "size"), v=("viol", "sum"))
    dropped = u[neg | big]
    finite = np.isfinite(dropped["Received Time"].to_numpy())
    counts["n_nan_time_dropped"] = int((~finite).sum())
    dr = dropped[finite]
    wd = win(dr["Received Time"].to_numpy())
    ddf = pd.DataFrame({"win": wd, "neg": (dr["lat"].to_numpy() < 0), "big": (dr["lat"].to_numpy() >= BIG_MS)})
    n_dropped_win_lt0 = int((ddf["win"] < 0).sum())
    ddf = ddf[ddf["win"] >= 0].groupby("win").agg(e_neg=("neg", "sum"), e_big=("big", "sum"))
    w = kdf.join(ddf, how="outer").fillna(0)
    w["e"] = w["e_neg"] + w["e_big"]
    counts["n_dropped_win_lt0"] = n_dropped_win_lt0
    return w.reset_index(), counts


def cost_array(df, col):
    """[8, 3] table of `col` with the pipeline's own rule (cost falls back to the per-action mean below MIN_CELL_N)."""
    t = fit_cost_table(df.assign(urllc_frac_viol=df[col]))
    out = np.full((N_ACTIONS, N_BINS), np.nan)
    out[t["action"].to_numpy(int), t["load_bin"].to_numpy(int)] = t["cost_hat"].to_numpy()
    return out


def dm_cost(actions, load_bin, tbl):
    return float(tbl[np.asarray(actions, int), np.asarray(load_bin, int)].mean())


def order_holds(c_safe, c_cql, c_iql):
    return bool(c_safe < c_cql < c_iql)


# ----------------------------------------------------------------------------- run
def _one(rec):
    row = SimpleNamespace(**rec)
    w, counts = reservation_windows(res_path(row))
    if w is not None:
        w.insert(0, "reservation", row.reservation)
    return row.reservation, w, counts


def summarize_reservations(win, counts, canon):
    """Per-reservation table. `win`: per-window k, v, e restricted to canonical windows; counts: per-reservation counters."""
    rows = []
    for res, g in win.groupby("reservation"):
        c = counts[res]
        pipe, lo, hi = bounds(g["k"], g["v"], g["e"])
        allw = canon[res]["w"]
        rows.append({"reservation": res, **c, "share_neg": c["n_neg"] / c["n_packets"], "share_big": c["n_big"] / c["n_packets"],
                     "share_dropped": (c["n_neg"] + c["n_big"] + c["n_nan"]) / c["n_packets"],
                     "share_viol_kept": float(g["v"].sum() / g["k"].sum()), "n_canon_windows": int(len(g)),
                     "cost_pipeline": float(pipe.mean()), "cost_lo": float(lo.mean()), "cost_hi": float(hi.mean()),
                     "gap_lo": float(lo.mean() - D), "gap_hi": float(hi.mean() - D),
                     "n_dropped_outside_canon": canon[res]["dropped_outside"], "n_windows_lost": canon[res]["lost"]})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/e13d")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--e12", default="results/e12")
    a = ap.parse_args()
    git = git_state()
    assert not git["git_dirty_src_tests"], "uncommitted changes in src/ or tests/: commit first"
    from src.e12_final import load_train, predict, script_of     # inference only; evaluate_once (the test read) is never called
    train = load_train()
    assert set(train["split"]) == {"train"} and train["reservation"].nunique() == 510
    t = pd.read_csv("results/d8_times.csv")
    t = t[t["reservation"].isin(set(train["reservation"])) & t["cluster"].isin([2, 3])]
    assert len(t) == 510 and (t["split"] == "train").all()
    with Pool(a.workers) as p:
        out = list(p.imap_unordered(_one, t.to_dict("records"), chunksize=4))
    counts = {r: c for r, _, c in out}
    # --- restrict to canonical windows, G1
    canon_w = train[["reservation", "win", "urllc_frac_viol"]]
    wins = pd.concat([w for _, w, _ in out if w is not None], ignore_index=True)
    m = canon_w.merge(wins, on=["reservation", "win"], how="left")
    assert m["k"].notna().all(), "G1 failed: canonical windows missing from the recomputation"
    err = float(np.abs(m["v"] / m["k"] - m["urllc_frac_viol"]).max())
    print(f"[e13d] G1 max |recomputed - parquet| = {err:.3e}", flush=True)
    if err > 1e-9:
        sys.exit("[e13d] G1 FAILED: stopping")
    train = train.merge(m[["reservation", "win", "k", "v", "e_neg", "e_big", "e"]], on=["reservation", "win"])
    _, train["cost_lo"], train["cost_hi"] = bounds(train["k"], train["v"], train["e"])
    train["cost_pipe"] = train["urllc_frac_viol"]
    tbl = {n: cost_array(train, c) for n, c in (("orig", "cost_pipe"), ("lo", "cost_lo"), ("hi", "cost_hi"))}
    g2 = float(np.abs(tbl["orig"] - cost_table_array(COST_TABLE)).max())
    print(f"[e13d] G2 max |refit table - results/cost_table.csv| = {g2:.3e}", flush=True)
    if g2 > 1e-9:
        sys.exit("[e13d] G2 FAILED: stopping")
    # --- per-reservation report
    canon = {}
    for res, w in wins.groupby("reservation"):
        cw = set(train.loc[train["reservation"] == res, "win"])
        isc = w["win"].isin(cw)
        canon[res] = {"w": cw, "lost": int(((w["k"] == 0) & (w["e"] > 0)).sum()), "dropped_outside": int(w.loc[~isc, "e"].sum())}
    per = summarize_reservations(train, counts, canon)
    tot = {k: int(per[k].sum()) for k in ("n_packets", "n_kept", "n_neg", "n_big", "n_nan", "n_nan_time_dropped", "n_windows_lost", "n_dropped_outside_canon")}
    tot["n_dropped_win_lt0"] = int(sum(c.get("n_dropped_win_lt0", 0) for c in counts.values()))
    pooled = {"cost_pipeline": float(train["cost_pipe"].mean()), "cost_lo": float(train["cost_lo"].mean()), "cost_hi": float(train["cost_hi"].mean())}
    pooled.update({"gap_lo": pooled["cost_lo"] - D, "gap_hi": pooled["cost_hi"] - D, "gap_pipeline": pooled["cost_pipeline"] - D})
    q = lambda s: [float(x) for x in s.quantile([0, .25, .5, .75, 1])]
    dist = {c: q(per[c]) for c in ("share_neg", "share_big", "share_dropped", "share_viol_kept", "cost_pipeline", "cost_lo", "cost_hi", "gap_lo", "gap_hi")}
    cnt = {"n_res": int(len(per)), "hi_le_d": int((per["cost_hi"] <= D).sum()), "lo_gt_d": int((per["cost_lo"] > D).sum()),
           "pipeline_le_d": int((per["cost_pipeline"] <= D).sum()), "no_dropped": int((per["share_dropped"] == 0).sum())}
    # --- order Safe-CQL < CQL < IQL (inference only)
    sub = {"all_train": np.ones(len(train), bool)}
    scr = script_of(train["reservation"].to_numpy())
    for nm, md5 in SCRIPT_MD5.items():
        sub[nm] = scr == md5
    order, lb = {}, train["load_bin"].to_numpy(int)
    acts = {}
    for cfg in {c for tr in TRIPLES.values() for c in tr}:
        acts[cfg] = [np.asarray(predict(cfg, s, train, a.e12), int) for s in SEEDS]
    for tname, trip in TRIPLES.items():
        for sn, mask in sub.items():
            for tb, T in tbl.items():
                cost = {c: np.array([dm_cost(a_[mask], lb[mask], T) for a_ in acts[c]]) for c in trip}
                mean = {c: float(v.mean()) for c, v in cost.items()}
                order[f"{tname}|{sn}|{tb}"] = {"mean": mean, "sd": {c: float(v.std(ddof=1)) for c, v in cost.items()},
                                               "gap_to_d": {c: mean[c] - D for c in trip}, "order_holds": order_holds(*(mean[c] for c in trip))}
    meta = {**git, "dataset_version": json.load(open(PARQUET.replace(".parquet", ".meta.json")))["dataset_version"], "G1_max_abs_err": err,
            "G2_max_abs_err": g2, "budget": D, "sla_ms": SLA_MS, "test_split_read": False, "trained_anything": False}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    per.to_csv(a.out + "_reservations.csv", index=False)
    json.dump({"meta": meta, "totals": tot, "pooled_train_windows": pooled, "per_reservation_quantiles_min_q1_med_q3_max": dist,
               "per_reservation_counts": cnt, "tables": {k: v.tolist() for k, v in tbl.items()}, "order": order},
              open(a.out + "_summary.json", "w"), indent=1, default=float)
    print(json.dumps({"totals": tot, "pooled": pooled, "counts": cnt}, indent=1, default=float))


if __name__ == "__main__":
    main()
