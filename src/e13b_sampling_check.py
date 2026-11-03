"""E13b: real sampling step of the raw files (reviewer point R2-W1). READ-ONLY on the dataset, TIMESTAMP COLUMNS ONLY.

Reads, for 12 TRAIN reservations (cluster 2/3 x scheduler, 3 each = first / middle / last by chronological rank inside the
cell, from D8's start dates; list in results/e13b_sample.csv): `bs/enb_metrics.csv` (time), `bs/<IMSI>_metrics.csv`
(Timestamp), `ue_*/ue_metrics.csv` (time), `ue_*/mgen.csv` (Sent Time, Received Time). Nothing else is loaded (`usecols`),
no latency, no KPM value. No window-sensitivity analysis is run here.

Pre-declared criteria (fixed before the first read):
  - KPM streams (enb, bs per-UE, ue_metrics): window w is "possible" for a reservation iff >= 99 % of the windows between the
    first and last sample hold >= 3 samples (enough for a mean).
  - mgen (URLLC packets, pooled over the UE files of the reservation): "possible" iff >= 99 % of windows hold >= 34 packets
    (1/34 < d = 0.03: below that a violation fraction cannot even take a value under d).
  - candidate windows: 0.1, 0.25, 0.5, 1, 2, 2.5, 5, 10 s. Result = number of reservations (of 12) meeting each criterion.
Time units are ASSUMED: enb `time`, BS `Timestamp`, ue_metrics `time` in ms; mgen times in s (as src/build_dataset.py does).
The ue_metrics unit is checked by the ratio of its duration to the enb duration (reported, not corrected).

    python -m src.e13b_sampling_check --sample results/e13b_sample.csv --out results/e13b_sampling
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

ROOT = "/home/AliBen/data/safe-cql/dataset-kpm"
WINDOWS = (0.1, 0.25, 0.5, 1.0, 2.0, 2.5, 5.0, 10.0)
MIN_KPM, MIN_PKT, SHARE = 3, 34, 0.99
SCHED_DIR = {0: 0, 1: 2}      # canonical sched bin -> scheduling_<policy> directory


def step_stats(t_s):
    """Sorted timestamps in seconds -> distribution of successive steps (s) and regularity."""
    t = np.sort(np.asarray(t_s, float))
    t = t[np.isfinite(t)]
    if len(t) < 3:
        return {"n": int(len(t))}
    dt = np.diff(t)
    med = float(np.median(dt))
    q = np.quantile(dt, [0.01, 0.05, 0.5, 0.95, 0.99])
    return {"n": int(len(t)), "duration_s": float(t[-1] - t[0]), "step_min": float(dt.min()), "step_p01": float(q[0]),
            "step_p05": float(q[1]), "step_median": med, "step_p95": float(q[3]), "step_p99": float(q[4]),
            "step_max": float(dt.max()), "share_dup": float((dt == 0).mean()),
            "share_within_10pct_median": float((np.abs(dt - med) <= 0.1 * med).mean()) if med > 0 else None,
            "share_gt_2x_median": float((dt > 2 * med).mean()) if med > 0 else None}


def window_counts(t_s, w):
    """Samples per window of width w between the first and the last sample (windows with no sample included)."""
    t = np.sort(np.asarray(t_s, float))
    t = t[np.isfinite(t)]
    if len(t) < 2:
        return np.zeros(0, int)
    k = int(np.floor((t[-1] - t[0]) / w)) + 1
    return np.bincount(np.floor((t - t[0]) / w).astype(int), minlength=k)


def window_report(t_s, w, min_n):
    c = window_counts(t_s, w)
    if not len(c):
        return {"n_windows": 0, "possible": False}
    return {"n_windows": int(len(c)), "median_per_window": float(np.median(c)), "p05_per_window": float(np.quantile(c, 0.05)),
            "share_empty": float((c == 0).mean()), "share_ge_min": float((c >= min_n).mean()),
            "possible": bool((c >= min_n).mean() >= SHARE)}


def _col(path, col, sep):
    return pd.read_csv(path, sep=sep, usecols=[col])[col].apply(pd.to_numeric, errors="coerce").to_numpy(float)


def read_reservation(res_dir):
    """Timestamps (seconds) per stream of one reservation; timestamp columns only."""
    out = {"enb": [], "bs_ue": [], "ue_metrics": [], "mgen_sent": [], "mgen_recv": []}
    errs = []
    p = os.path.join(res_dir, "bs", "enb_metrics.csv")
    try:
        out["enb"].append(_col(p, "time", ",") / 1000.0)
    except Exception as e:
        errs.append(f"enb: {e!r}")
    for p in sorted(glob.glob(os.path.join(res_dir, "bs", "*_metrics.csv"))):
        if os.path.basename(p) == "enb_metrics.csv":
            continue
        try:
            out["bs_ue"].append(_col(p, "Timestamp", ",") / 1000.0)
        except Exception as e:
            errs.append(f"{os.path.basename(p)}: {e!r}")
    for d in sorted(glob.glob(os.path.join(res_dir, "ue_*"))):
        for key, fn, col, sep, div in (("ue_metrics", "ue_metrics.csv", "time", ";", 1000.0),
                                       ("mgen_sent", "mgen.csv", "Sent Time", ",", 1.0),
                                       ("mgen_recv", "mgen.csv", "Received Time", ",", 1.0)):
            try:
                out[key].append(_col(os.path.join(d, fn), col, sep) / div)
            except Exception as e:
                errs.append(f"{os.path.basename(d)}/{fn}:{col}: {e!r}")
    return out, errs


def analyse_reservation(res_dir):
    streams, errs = read_reservation(res_dir)
    rep = {"errors": errs, "streams": {}}
    for key, files in streams.items():
        if not files:
            continue
        per_file = [step_stats(f) for f in files]
        meds = [s["step_median"] for s in per_file if "step_median" in s]
        agg = {"n_files": len(files), "per_file_step_median_min_med_max": [float(min(meds)), float(np.median(meds)), float(max(meds))] if meds else None,
               "per_file": per_file}
        if key.startswith("mgen"):
            pooled = np.concatenate(files)
            agg["pooled"] = step_stats(pooled)
            agg["windows"] = {str(w): window_report(pooled, w, MIN_PKT) for w in WINDOWS}
        else:
            agg["windows"] = {str(w): {"min_over_files_share_ge_min": float(min(window_report(f, w, MIN_KPM).get("share_ge_min", 0) for f in files)),
                                       "possible": bool(all(window_report(f, w, MIN_KPM)["possible"] for f in files))} for w in WINDOWS}
        rep["streams"][key] = agg
    if "enb" in streams and streams["enb"] and streams.get("ue_metrics"):
        d_enb = np.ptp(streams["enb"][0][np.isfinite(streams["enb"][0])])
        d_ue = [np.ptp(f[np.isfinite(f)]) for f in streams["ue_metrics"] if np.isfinite(f).sum() > 1]
        rep["ue_over_enb_duration_ratio_median"] = float(np.median(d_ue) / d_enb) if d_ue and d_enb > 0 else None
    return rep


def res_path(row, root=ROOT):
    return os.path.join(root, f"cluster_{row.cluster}", f"slicing_{row.slicing}", f"scheduling_{SCHED_DIR[int(row.sched)]}", row.reservation)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="results/e13b_sample.csv")
    ap.add_argument("--out", default="results/e13b_sampling")
    a = ap.parse_args()
    sample = pd.read_csv(a.sample)
    assert len(sample) == 12 and sample["cluster"].isin([2, 3]).all(), "train clusters only"
    reps = []
    for row in sample.itertuples():
        r = analyse_reservation(res_path(row))
        r.update(reservation=row.reservation, cluster=int(row.cluster), sched=int(row.sched), position=row.position, slicing=int(row.slicing))
        reps.append(r)
        st = r["streams"]
        print(f"[e13b] {row.reservation} c{row.cluster} s{row.sched} {row.position}: " +
              " ".join(f"{k}={v['per_file_step_median_min_med_max']}" for k, v in st.items()) + f" errs={len(r['errors'])}", flush=True)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out + ".json", "w") as f:
        json.dump({"meta": {"read_only": True, "columns": "timestamps only", "windows": WINDOWS, "min_kpm": MIN_KPM, "min_pkt": MIN_PKT,
                            "share": SHARE, "test_split_read": False, "root": ROOT}, "reservations": reps}, f, indent=1, default=float)


if __name__ == "__main__":
    main()
