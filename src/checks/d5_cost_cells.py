"""D5: per (action, load-bin) cost cell: sample counts and reservation-level bootstrap CIs.

Cost = urllc_frac_viol per 5 s window (notebook definition, mean over windows). Load = window nof_ue.
Bin edges are the two tables used in the notebook (3 bins: cell 27 / 4 bins: cells 29-30).
Bootstrap resamples RESERVATIONS inside a cell (windows of one reservation are strongly dependent).
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

EDGES = {"3bin": [0, 3.5, 5.5, 8.1], "4bin": [0, 2.5, 4.5, 6.5, 8.1]}
SLOTS = {"3bin": ["low", "mid", "high"], "4bin": ["low", "med-", "med+", "high"]}


def load(d):
    return pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(d, "*.parquet")))], ignore_index=True)


def res_boot(x, res, B, rng):
    g = pd.DataFrame({"r": res, "x": x}).groupby("r")["x"].agg(["sum", "count"])
    s, n = g["sum"].to_numpy(), g["count"].to_numpy()
    if len(s) < 2:
        return (np.nan, np.nan)
    idx = rng.integers(0, len(s), (B, len(s)))
    m = s[idx].sum(1) / n[idx].sum(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def cells(df, scheme, B, seed):
    rng = np.random.default_rng(seed)
    df = df.assign(bin=pd.cut(df["nof_ue"], EDGES[scheme], labels=SLOTS[scheme], include_lowest=True))
    rows = []
    for (a, b), g in df.groupby(["action", "bin"], observed=False):
        n = len(g)
        r = {"scheme": scheme, "action": int(a), "bin": str(b), "n_windows": n, "n_reservations": int(g.reservation.nunique()),
             "n_clusters": int(g.cluster.nunique())}
        if n:
            x = g["urllc_frac_viol"].to_numpy()
            lo, hi = res_boot(x, g.reservation.to_numpy(), B, rng)
            se = x.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
            r.update(mean_cost=float(x.mean()), ci_res_lo=lo, ci_res_hi=hi, ci_naive_lo=float(x.mean() - 1.96 * se),
                     ci_naive_hi=float(x.mean() + 1.96 * se), frac_windows_viol_gt0=float((x > 0).mean()),
                     mean_p99_ms=float(g["urllc_p99"].mean()), median_p99_ms=float(g["urllc_p99"].median()))
        r["flag_n_lt20"], r["flag_n_lt50"], r["flag_res_lt5"] = n < 20, n < 50, r["n_reservations"] < 5
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", default="results/windows")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/d5")
    a = ap.parse_args()
    df = load(a.windows)
    summ = {"seed": a.seed, "boot": a.boot, "n_rows": len(df), "n_res": int(df.reservation.nunique())}
    all_cells = []
    for subset, d in [("train_cl2_3", df[df.cluster != 1]), ("test_cl1", df[df.cluster == 1]), ("all", df)]:
        for scheme in EDGES:
            c = cells(d, scheme, a.boot, a.seed)
            c.insert(0, "subset", subset)
            all_cells.append(c)
            ne = c[c.n_windows > 0]
            summ[f"{subset}/{scheme}"] = {
                "n_cells": len(c), "n_empty": int((c.n_windows == 0).sum()), "n_lt20": int(c.flag_n_lt20.sum()),
                "n_lt50": int(c.flag_n_lt50.sum()), "n_res_lt5": int(c.flag_res_lt5.sum()),
                "n_ci_excl_budget003": int(((ne.ci_res_lo > 0.03) | (ne.ci_res_hi < 0.03)).sum()),
                "median_ci_width_res": float((ne.ci_res_hi - ne.ci_res_lo).median()),
                "median_ci_width_naive": float((ne.ci_naive_hi - ne.ci_naive_lo).median()),
                "median_n_windows": float(ne.n_windows.median()), "median_n_res": float(ne.n_reservations.median()),
            }
    out = pd.concat(all_cells, ignore_index=True)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    out.to_csv(a.out + "_cells.csv", index=False)
    json.dump(summ, open(a.out + "_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))
    pd.set_option("display.width", 250)
    t = out[(out.subset == "train_cl2_3") & (out.scheme == "3bin")]
    print(t[["action", "bin", "n_windows", "n_reservations", "mean_cost", "ci_res_lo", "ci_res_hi", "ci_naive_lo", "ci_naive_hi"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
