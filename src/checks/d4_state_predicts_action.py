"""D4: how well does the state predict the (constant-per-reservation) action?

Trivial classifiers on window tables written by D3 (results/windows/*.parquet). CPU only, no RL.
Split mirrors the notebook: train = clusters 2-3, test = cluster 1. Accuracy CIs: reservation-level bootstrap.
Feature sets (columns as in notebook cell 22):
  lag_nb      : reward/urllc_p50 lag1, lag2, built exactly as in the notebook (shift on rows, bfill, median fill)
  lag_clean   : same lags, but first 2 windows of each reservation dropped (no bfill: no look-ahead)
  load_only   : nof_ue (current window)
  cur_nolabel : current-window radio+load (nof_ue, rsrp, dl_snr, dl_mcs, dl_bler, ul_buff), no reward/latency
  cur_all     : current-window 8 columns incl. reward_embb_Mbps and urllc_p50
  full12      : notebook state (cur_all + lags)
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

CUR_RADIO = ["nof_ue", "rsrp", "dl_snr", "dl_mcs", "dl_bler", "ul_buff"]
CUR_LAB = ["reward_embb_Mbps", "urllc_p50"]
LAGS = ["reward_embb_Mbps_lag1", "reward_embb_Mbps_lag2", "urllc_p50_lag1", "urllc_p50_lag2"]


def load(dirpath, sample=None, seed=0):
    files = sorted(glob.glob(os.path.join(dirpath, "*.parquet")))
    if sample:
        files = list(np.random.default_rng(seed).permutation(files)[:sample])
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.sort_values(["reservation", "win"]).reset_index(drop=True)
    g = df.groupby("reservation")
    for col in ["urllc_p50", "reward_embb_Mbps"]:
        for lag in (1, 2):
            df[f"{col}_lag{lag}"] = g[col].shift(lag)
    df["pos"] = g.cumcount()
    df["lag_clean_ok"] = df["pos"] >= 2
    raw = df[LAGS].copy()
    df[LAGS] = df.groupby("reservation")[LAGS].bfill()
    df[LAGS] = df[LAGS].fillna(df[LAGS].median())
    df.attrs["raw_lags"] = raw
    df["split"] = np.where(df["cluster"] == 1, "test", "train")
    df["prb_idx"] = df["action"] // 2
    return df


FEATSETS = {"lag_nb": LAGS, "lag_clean": LAGS, "load_only": ["nof_ue"], "cur_nolabel": CUR_RADIO,
            "cur_all": CUR_RADIO + CUR_LAB, "full12": CUR_RADIO + CUR_LAB + LAGS}


def boot_ci(test, correct, B, rng):
    g = pd.DataFrame({"r": test["reservation"].to_numpy(), "c": correct.astype(float)}).groupby("r")["c"].agg(["sum", "count"])
    s, n = g["sum"].to_numpy(), g["count"].to_numpy()
    idx = rng.integers(0, len(s), (B, len(s)))
    acc = s[idx].sum(1) / n[idx].sum(1)
    return float(np.percentile(acc, 2.5)), float(np.percentile(acc, 97.5))


def fit_eval(name, cols, target, df, model, B, seed):
    d = df[df["lag_clean_ok"]] if name == "lag_clean" else df
    tr, te = d[d["split"] == "train"], d[d["split"] == "test"]
    sc = StandardScaler().fit(tr[cols])
    Xtr, Xte = sc.transform(tr[cols]), sc.transform(te[cols])
    if model == "logreg":
        clf = LogisticRegression(max_iter=1000, C=1.0)
    else:
        clf = HistGradientBoostingClassifier(max_iter=100, random_state=seed)
    clf.fit(Xtr, tr[target])
    proba = clf.predict_proba(Xte)
    pred = clf.classes_[proba.argmax(1)]
    correct = pred == te[target].to_numpy()
    # reservation-level vote: average probabilities over the reservation's windows
    pr = pd.DataFrame(proba, index=te["reservation"].to_numpy()).groupby(level=0).mean()
    truth = te.groupby("reservation")[target].first()
    res_acc = float((clf.classes_[pr.to_numpy().argmax(1)] == truth.loc[pr.index].to_numpy()).mean())
    rng = np.random.default_rng(seed)
    lo, hi = boot_ci(te, correct, B, rng)
    maj = tr[target].mode().iloc[0]
    return {"featset": name, "target": target, "model": model, "n_train": len(tr), "n_test": len(te),
            "acc_test": float(correct.mean()), "ci95": [lo, hi],
            "acc_reservation_vote": res_acc, "n_test_res": int(truth.size),
            "baseline_majority_train": float((te[target] == maj).mean()),
            "baseline_uniform": 1.0 / tr[target].nunique()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", default="results/windows")
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--models", default="logreg,hgb")
    ap.add_argument("--out", default="results/d4.json")
    a = ap.parse_args()
    df = load(a.windows, a.sample, a.seed)
    rows = []
    for model in a.models.split(","):
        for target in ["action", "prb_idx", "sched"]:
            for name, cols in FEATSETS.items():
                r = fit_eval(name, cols, target, df, model, a.boot, a.seed)
                rows.append(r)
                print(f"{model:6s} {target:8s} {name:12s} acc={r['acc_test']:.3f} CI[{r['ci95'][0]:.3f},{r['ci95'][1]:.3f}] res-vote={r['acc_reservation_vote']:.3f} maj={r['baseline_majority_train']:.3f}", flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump({"seed": a.seed, "sample": a.sample, "n_rows": len(df), "n_res": int(df.reservation.nunique()), "results": rows}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
