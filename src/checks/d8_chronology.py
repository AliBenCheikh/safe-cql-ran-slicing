"""D8: absolute chronology of the reservations, order of the ids, PF/RR separation in time, nearest-in-time PF/RR
pairs and breaks of the cost drift.

Read-only. Raw files opened: ONLY bs/enb_metrics.csv (columns `time`, `nof_ue`) of the usable reservations, to get the
absolute start. Everything else comes from derived files (results/dataset_canonical.parquet, results/d6_reservations.csv).

  1. times     : for each usable reservation, absolute start (epoch ms -> UTC) read from the DATA files (not from the
                 ids): `t0_ms` = first eNB row with nof_ue > 0 (the anchor of window 0 in build_dataset), `enb_first_ms`,
                 `enb_last_ms`. Cross-checked against the t0_ms stored by D6.
  2. order     : does the numeric id order match the chronological order (Spearman / Kendall, adjacent inversions)?
  3. separation: per (script, slicing) with both schedulers: are the PF and RR reservations separated by hours, days or
                 weeks, or interleaved? (time-sorted sequence of schedulers: 1 switch = two blocks.)
  4. nearest   : PF - RR recomputed on the PF/RR pairs closest in time (greedy global-nearest one-to-one matching on the
                 start times, same slicing, same script), keeping the closest 100 % / 50 % / 25 % of the pairs; compared
                 with the D7 estimate (sign, order of magnitude) and across scripts.
  5. drift     : breaks of the time drift of the cost (and reward) per script: consecutive-day jumps and the best
                 single-split (max |t|, permutation p, compared with a linear trend), on values averaged over the bins
                 covered by almost all reservations of the script.

Conventions (choices, not results): PF = sched 1, RR = sched 0; cost = urllc_frac_viol; the gap classes are
hours (< 24 h), days (< 7 d), weeks (>= 7 d); "same order of magnitude" = ratio < D7.SAME_ORDER_MAX_RATIO;
distinguishable from 0 = |diff| > D7.SE_Z * se; days are UTC calendar days.
"""
import argparse
import hashlib
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy import stats

from src.checks import common as C
from src.checks import d6_shared_scripts as D6
from src.checks import d7_scheduler_order as D7

SCHED_NAME = D7.SCHED_NAME
METRICS = D7.METRICS
H = 3600.0
DAY_S = 86400.0
FRACS = (1.0, 0.5, 0.25)        # share of the closest PF/RR pairs kept
MIN_PAIRS = 3                    # a closest-pairs estimate needs at least this many pairs
MIN_BIN_COV = 0.8                # drift: a script bin is kept if covered by this share of the script's reservations
MIN_RES_COV = 0.9                # drift: a reservation is kept if it covers this share of the kept bins
MIN_SEG = 5                      # drift: minimum reservations on each side of a split
DAY_JUMP_Z = 3.0                 # drift: |z| above which a consecutive-day jump is flagged
SPLIT_P = 0.01                   # drift: permutation p below which the best split is flagged
N_PERM = 1000
SEED = 0
PLAUSIBLE_MS = (1.5e12, 1.9e12)  # epoch ms between 2017 and 2030: sanity check on the units of `time`


# ---------------------------------------------------------------- 1. absolute times (raw eNB files, 2 columns)
def reservation_times(res):
    """Start / end of one reservation from bs/enb_metrics.csv (epoch ms). None fields when unreadable or never active."""
    out = {**C.path_cfg(res), "enb_first_ms": None, "enb_last_ms": None, "t0_ms": None, "enb_rows": 0, "problem": None}
    problems = []
    enb = C.safe_read_csv(os.path.join(res, "bs", "enb_metrics.csv"), problems, usecols=["time", "nof_ue"])
    if enb is None:
        out["problem"] = "; ".join(problems) or "unreadable"
        return out
    enb = enb.assign(time=pd.to_numeric(enb["time"], errors="coerce")).dropna(subset=["time"])
    if not len(enb):
        out["problem"] = "no numeric time"
        return out
    out.update(enb_first_ms=float(enb["time"].min()), enb_last_ms=float(enb["time"].max()), enb_rows=int(len(enb)))
    act = enb.loc[enb["nof_ue"] > 0, "time"]
    if len(act):
        out["t0_ms"] = float(act.iloc[0])  # same definition as build_dataset._enb_stream
    else:
        out["problem"] = "nof_ue never > 0"
    return out


def read_times(resv, workers=6):
    if workers and workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            rows = list(ex.map(reservation_times, resv, chunksize=8))
    else:
        rows = [reservation_times(r) for r in resv]
    return pd.DataFrame(rows).rename(columns={"sched": "sched_raw_dir", "slicing": "slicing_dir", "cluster": "cluster_dir"})


def add_utc(df, col="t0_ms"):
    """Adds `start_utc` (tz-aware UTC timestamp), `date_utc` (YYYY-MM-DD) and `hour_utc` (decimal hour) from epoch ms."""
    ts = pd.to_datetime(df[col], unit="ms", utc=True)
    return df.assign(start_utc=ts, date_utc=ts.dt.strftime("%Y-%m-%d"), hour_utc=ts.dt.hour + ts.dt.minute / 60.0)


def build_table(canon, info, times):
    """One row per usable reservation: cfg (canonical), md5 and D6 t0 (info), absolute times (raw eNB files)."""
    c = canon.drop_duplicates("reservation")[["reservation", "cluster", "slicing", "sched", "prb_embb", "split"]]
    c = c.merge(info[["res", "md5", "t0_ms"]].rename(columns={"res": "reservation", "t0_ms": "t0_ms_d6"}), on="reservation", how="left")
    c = c.merge(times[["res", "enb_first_ms", "enb_last_ms", "t0_ms", "enb_rows", "problem"]].rename(columns={"res": "reservation"}),
                on="reservation", how="left")
    c["rid"] = c["reservation"].map(D7.res_id)
    return add_utc(c).sort_values("rid").reset_index(drop=True)


# ---------------------------------------------------------------- 2. id order vs chronological order
def _order_stats(g):
    g = g.sort_values("rid")
    t = g["t0_ms"].to_numpy(float)
    d = np.diff(t)
    r = {"n": len(g)}
    if len(g) >= 3:
        r["spearman"] = float(stats.spearmanr(g["rid"], t)[0])
        r["kendall"] = float(stats.kendalltau(g["rid"], t)[0])
    else:
        r["spearman"] = r["kendall"] = np.nan
    r["n_adjacent_inversions"] = int((d < 0).sum())
    r["max_backward_jump_h"] = float(-d.min() / H / 1000) if len(d) and d.min() < 0 else 0.0
    r["monotone"] = bool(len(d) == 0 or (d >= 0).all())
    return r


def order_check(tab):
    """Id order vs start-time order: overall, per cluster, per script. Also the list of adjacent inversions
    (reservation k has a larger id than k-1 in the same group but starts earlier)."""
    t = tab.dropna(subset=["t0_ms"])
    rows = [{"level": "all", "key": "all", **_order_stats(t)}]
    for k, g in t.groupby("cluster"):
        rows.append({"level": "cluster", "key": str(k), **_order_stats(g)})
    for k, g in t.groupby("md5"):
        rows.append({"level": "script", "key": k, **_order_stats(g)})
    inv = []
    for level, groups in (("all", [("all", t)]), ("cluster", [(str(k), g) for k, g in t.groupby("cluster")])):
        for key, g in groups:
            g = g.sort_values("rid").reset_index(drop=True)
            for i in range(1, len(g)):
                if g.at[i, "t0_ms"] < g.at[i - 1, "t0_ms"]:
                    inv.append({"level": level, "key": key, "res_prev": g.at[i - 1, "reservation"], "res": g.at[i, "reservation"],
                                "backward_h": float((g.at[i - 1, "t0_ms"] - g.at[i, "t0_ms"]) / H / 1000)})
    return pd.DataFrame(rows), pd.DataFrame(inv, columns=["level", "key", "res_prev", "res", "backward_h"])


# ---------------------------------------------------------------- 3. separation PF / RR in time
def classify_gap(gap_s):
    """hours (< 24 h) / days (< 7 d) / weeks (>= 7 d); NaN gap -> None."""
    if gap_s is None or not np.isfinite(gap_s):
        return None
    if gap_s < DAY_S:
        return "heures"
    if gap_s < 7 * DAY_S:
        return "jours"
    return "semaines"


def separation(tab):
    """Per (script, slicing) with both schedulers: time-sorted scheduler sequence.
    n_switches = 1 -> two blocks, class of the gap between the end of the first block and the start of the second
    (boundary reservations); n_switches >= 2 -> 'entrelacées'. `min_misplaced` = fewest reservations to move to
    make two clean blocks (0 when n_switches <= 1): a few strays are visible there."""
    rows = []
    t = tab.dropna(subset=["t0_ms", "enb_last_ms", "md5"])
    for (h, sl), g in t.groupby(["md5", "slicing"]):
        g = g.sort_values("t0_ms").reset_index(drop=True)
        seq = g["sched"].to_numpy()
        if len(set(seq)) < 2:
            continue
        nsw = int((seq[1:] != seq[:-1]).sum())
        n = len(seq)
        pf_cum = np.concatenate([[0], np.cumsum(seq == 1)])
        rr_cum = np.concatenate([[0], np.cumsum(seq == 0)])
        mis = min(min(pf_cum[k] + (rr_cum[n] - rr_cum[k]), rr_cum[k] + (pf_cum[n] - pf_cum[k])) for k in range(n + 1))
        r = {"md5": h, "slicing": int(sl), "cluster": int(g["cluster"].iloc[0]), "n_res": n, "n_switches": nsw, "min_misplaced": int(mis)}
        for s in (0, 1):
            x = g[g["sched"] == s]
            r[f"n_{SCHED_NAME[s]}"] = len(x)
            r[f"start_{SCHED_NAME[s]}_utc"] = x["start_utc"].min()
            r[f"end_{SCHED_NAME[s]}_utc"] = pd.to_datetime(x["enb_last_ms"].max(), unit="ms", utc=True)
            r[f"span_{SCHED_NAME[s]}_h"] = float((x["enb_last_ms"].max() - x["t0_ms"].min()) / H / 1000)
        if nsw == 1:
            k = int(np.argmax(seq != seq[0]))  # first reservation of the second block
            gap = max(0.0, (g.at[k, "t0_ms"] - g.loc[:k - 1, "enb_last_ms"].max()) / 1000.0)
            r.update(first_block=SCHED_NAME[int(seq[0])], gap_h=gap / H, gap_class=classify_gap(gap))
        else:
            r.update(first_block=None, gap_h=np.nan, gap_class="entrelacées")
        rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 4. nearest-in-time PF / RR pairs
def greedy_pairs(a, b):
    """One-to-one pairs between times a and b, taken by increasing |a_i - b_j| (global nearest first, stable ties).
    Returns [(i, j, gap)] sorted by gap."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not len(a) or not len(b):
        return []
    gaps = np.abs(a[:, None] - b[None, :])
    used_i, used_j, out = set(), set(), []
    for flat in np.argsort(gaps, axis=None, kind="stable"):
        i, j = divmod(int(flat), len(b))
        if i in used_i or j in used_j:
            continue
        used_i.add(i); used_j.add(j)
        out.append((i, j, float(gaps[i, j])))
        if len(out) == min(len(a), len(b)):
            break
    return out


def _pair_diff(x_rr, x_pf, col):
    """PF - RR for one pair, over the script bins present in both reservations (mean of per-bin values)."""
    common = set(x_rr["sbin"]) & set(x_pf["sbin"])
    if not common:
        return np.nan
    return float(x_pf[x_pf["sbin"].isin(common)].groupby("sbin")[col].mean().mean()
                 - x_rr[x_rr["sbin"].isin(common)].groupby("sbin")[col].mean().mean())


def nearest_pair_effects(w, tab, fracs=FRACS, min_pairs=MIN_PAIRS):
    """PF - RR per (script, slicing, share of closest pairs kept). `w` = windows with script bins (D6.attach_bins),
    `tab` = build_table output (absolute start times). The SE is the paired one: sd(pair differences)/sqrt(n_pairs),
    which treats the pairs as independent [H]."""
    t0 = tab.set_index("reservation")["t0_ms"]
    rows = []
    for (h, sl), g in w.groupby(["md5", "slicing"]):
        frames = {r: x for r, x in g.groupby("reservation")}
        rr = sorted(g.loc[g.sched == 0, "reservation"].unique())
        pf = sorted(g.loc[g.sched == 1, "reservation"].unique())
        pairs = greedy_pairs(t0.reindex(pf).to_numpy(), t0.reindex(rr).to_numpy())  # (i in pf, j in rr, gap_ms)
        if len(pairs) < min_pairs:
            continue
        for frac in fracs:
            k = int(round(frac * len(pairs)))
            if k < min_pairs:
                continue
            kept = pairs[:k]
            gaps_h = np.array([p[2] for p in kept]) / 1000.0 / H
            row = {"md5": h, "slicing": int(sl), "frac": frac, "n_pairs_total": len(pairs), "n_pairs": k,
                   "gap_median_h": float(np.median(gaps_h)), "gap_max_h": float(gaps_h.max()), "gap_class_max": classify_gap(gaps_h.max() * H)}
            for tag, col in METRICS:
                d = np.array([_pair_diff(frames[rr[j]], frames[pf[i]], col) for i, j, _ in kept], float)
                d = d[np.isfinite(d)]
                row[f"diff_{tag}"] = float(d.mean()) if len(d) else np.nan
                row[f"se_{tag}"] = float(d.std(ddof=1) / math.sqrt(len(d))) if len(d) > 1 else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def compare_with_reference(near, ref, max_ratio=D7.SAME_ORDER_MAX_RATIO):
    """Adds, per metric, the D7 all-reservations estimate (`ref_*`), `same_sign`, `ratio` = |near|/|ref|, `same_order`
    (1/max_ratio < ratio < max_ratio) and `distinguishable` (|diff| > SE_Z * se)."""
    cols = ["md5", "slicing"] + [f"diff_{t}" for t, _ in METRICS]
    r = ref[cols].rename(columns={f"diff_{t}": f"ref_{t}" for t, _ in METRICS})
    out = near.merge(r, on=["md5", "slicing"], how="left")
    for tag, _ in METRICS:
        d, f, se = out[f"diff_{tag}"].to_numpy(float), out[f"ref_{tag}"].to_numpy(float), out[f"se_{tag}"].to_numpy(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.abs(d) / np.abs(f)
        out[f"same_sign_{tag}"] = (np.sign(d) == np.sign(f)) & (np.sign(f) != 0)
        out[f"ratio_{tag}"] = ratio
        out[f"same_order_{tag}"] = (ratio > 1 / max_ratio) & (ratio < max_ratio)
        out[f"distinguishable_{tag}"] = np.abs(d) > D7.SE_Z * np.nan_to_num(se, nan=np.inf)
    return out


def nearest_summary(cmp_, near):
    """Per share kept and metric: cells evaluable, cells with the D7 sign, with sign and order of magnitude, positive
    cells, distinguishable cells, and the cross-script coherence (D7.consistency) of the closest-pairs estimate."""
    rows = []
    for frac, g in cmp_.groupby("frac"):
        cons = D7.consistency(near[near["frac"] == frac]) if len(g) else pd.DataFrame()
        for tag, _ in METRICS:
            c = cons[(cons["metric"] == tag)] if len(cons) else pd.DataFrame()
            rows.append({"frac": frac, "metric": tag, "n_cells": len(g), "n_same_sign_as_D7": int(g[f"same_sign_{tag}"].sum()),
                         "n_same_sign_and_order": int((g[f"same_sign_{tag}"] & g[f"same_order_{tag}"]).sum()),
                         "n_positive": int((g[f"diff_{tag}"] > 0).sum()), "n_distinguishable": int(g[f"distinguishable_{tag}"].sum()),
                         "gap_median_h": float(g["gap_median_h"].median()), "gap_max_h": float(g["gap_max_h"].max()),
                         "n_slicings_coherent_across_scripts": int(c.loc[c["slicing"] != "mean", "coherent"].sum()) if len(c) else 0,
                         "n_slicings_evaluated": int((c["slicing"] != "mean").sum()) if len(c) else 0})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 5. time drift of the cost: breaks
def common_segment_values(w, col, min_bin_cov=MIN_BIN_COV, min_res_cov=MIN_RES_COV):
    """Per script: mean of `col` per reservation over the script bins covered by >= min_bin_cov of its reservations,
    for the reservations covering >= min_res_cov of those bins (so every value averages the same stretch of the
    script, which removes the script-time shape from the drift)."""
    rows = []
    for h, g in w.groupby("md5"):
        nres = g["reservation"].nunique()
        cov = g.groupby("sbin")["reservation"].nunique()
        keep = cov[cov >= min_bin_cov * nres].index
        if not len(keep):
            continue
        per = g[g["sbin"].isin(keep)].groupby("reservation").agg(value=(col, "mean"), n_bins=("sbin", "nunique"))
        per = per[per["n_bins"] >= min_res_cov * len(keep)]
        rows.append(per.reset_index().assign(md5=h, n_bins_segment=len(keep)))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["reservation", "value", "n_bins", "md5", "n_bins_segment"])


def add_residuals(v):
    """resid_slicing = value - mean(script, slicing): keeps a scheduler / block step; resid_cell = value - mean(script,
    slicing, scheduler): within-block drift only (a step between blocks is absorbed)."""
    v = v.copy()
    v["resid_slicing"] = v["value"] - v.groupby(["md5", "slicing"])["value"].transform("mean")
    v["resid_cell"] = v["value"] - v.groupby(["md5", "slicing", "sched"])["value"].transform("mean")
    return v


def _split_stats(y, min_seg):
    """t statistic (pooled variance) of every split of y with >= min_seg points on each side. Returns (ks, t, step)."""
    n = len(y)
    ks = np.arange(min_seg, n - min_seg + 1)
    if not len(ks) or n < 2 * min_seg:
        return ks, np.array([]), np.array([])
    cs, css = np.cumsum(y), np.cumsum(y * y)
    m1 = cs[ks - 1] / ks
    m2 = (cs[-1] - cs[ks - 1]) / (n - ks)
    ss1 = css[ks - 1] - ks * m1 ** 2
    ss2 = (css[-1] - css[ks - 1]) - (n - ks) * m2 ** 2
    var = (ss1 + ss2) / (n - 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (m2 - m1) / np.sqrt(var * (1 / ks + 1 / (n - ks)))
    return ks, np.nan_to_num(t, nan=0.0), m2 - m1


def best_split(y, min_seg=MIN_SEG, n_perm=N_PERM, seed=SEED):
    """Best single split of the time-ordered series y: index k (first point of the right segment), t, step, and a
    permutation p-value of max|t| (shuffling y, seeded). The permutation ignores autocorrelation: a smooth drift also
    produces a small p, so `sse_ratio` = SSE(linear trend) / SSE(best step) tells which fits better (> 1: the step).
    None if the series is too short."""
    y = np.asarray(y, float)
    ks, t, step = _split_stats(y, min_seg)
    if not len(ks):
        return None
    j = int(np.argmax(np.abs(t)))
    k = int(ks[j])
    rng = np.random.default_rng(seed)
    obs = abs(t[j])
    perm = np.array([np.abs(_split_stats(rng.permutation(y), min_seg)[1]).max() for _ in range(n_perm)])
    x = np.arange(len(y), dtype=float)
    lin = np.polyfit(x, y, 1)
    sse_lin = float(((y - np.polyval(lin, x)) ** 2).sum())
    sse_step = float(((y[:k] - y[:k].mean()) ** 2).sum() + ((y[k:] - y[k:].mean()) ** 2).sum())
    return {"k": k, "n": len(y), "t": float(t[j]), "step": float(step[j]), "p_perm": float((1 + np.sum(perm >= obs)) / (n_perm + 1)),
            "sse_ratio": sse_lin / sse_step if sse_step > 0 else np.inf, "slope_per_res": float(lin[0])}


def drift_breaks(v, kinds=("resid_slicing", "resid_cell"), min_seg=MIN_SEG, n_perm=N_PERM, seed=SEED):
    """Per script and residual kind: best split of the series sorted by start time (see best_split), with its context:
    time of the split, pause between the two adjacent reservations, PF share on each side, and flag
    `step_is_sched_switch` (PF share differs by > 0.5 across the split)."""
    rows = []
    for h, g in v.groupby("md5"):
        g = g.sort_values("t0_ms").reset_index(drop=True)
        for kind in kinds:
            r = best_split(g[kind].to_numpy(), min_seg, n_perm, seed)
            if r is None:
                continue
            k = r["k"]
            pf_l, pf_r = float((g["sched"][:k] == 1).mean()), float((g["sched"][k:] == 1).mean())
            pause = float((g.at[k, "t0_ms"] - g.at[k - 1, "t0_ms"]) / 1000.0 / H)
            rows.append({"md5": h, "kind": kind, **r, "split_utc": g.at[k, "start_utc"], "pause_h": pause, "pf_share_left": pf_l, "pf_share_right": pf_r,
                         "step_is_sched_switch": bool(abs(pf_l - pf_r) > 0.5),
                         "flag_split": bool(r["p_perm"] < SPLIT_P and r["sse_ratio"] > 1)})
    return pd.DataFrame(rows)


def daily_series(v, kinds=("resid_slicing", "resid_cell")):
    """Per script and UTC day: n reservations, PF share, mean raw value and mean residuals."""
    g = v.groupby(["md5", "date_utc"])
    out = g.agg(n=("reservation", "size"), pf_share=("sched", "mean"), mean_value=("value", "mean"),
                **{f"mean_{k}": (k, "mean") for k in kinds}).reset_index()
    return out


def daily_jumps(v, kind="resid_slicing", z_thr=DAY_JUMP_Z, min_n=3):
    """Jump of the mean residual between consecutive UTC days present for a script (both with >= min_n reservations);
    z = jump / sqrt(s1^2/n1 + s2^2/n2) (Welch: each day keeps its own spread, so a noisy PF day is not judged against
    the small spread of a quiet RR day). `calendar_gap_days` > 1 when days are missing in between.
    Flag when |z| > z_thr (choice); treats reservations as independent [H]."""
    rows = []
    for h, g in v.groupby("md5"):
        days = sorted(g["date_utc"].unique())
        grp = {d: g.loc[g["date_utc"] == d, kind].to_numpy(float) for d in days}
        sched = {d: g.loc[g["date_utc"] == d, "sched"].to_numpy() for d in days}
        for d1, d2 in zip(days[:-1], days[1:]):
            x1, x2 = grp[d1], grp[d2]
            if len(x1) < min_n or len(x2) < min_n:
                continue
            jump = float(x2.mean() - x1.mean())
            se = math.sqrt(x1.var(ddof=1) / len(x1) + x2.var(ddof=1) / len(x2))
            z = jump / se if se > 0 else np.nan
            rows.append({"md5": h, "kind": kind, "day_from": d1, "day_to": d2,
                         "calendar_gap_days": int((pd.Timestamp(d2) - pd.Timestamp(d1)).days), "n_from": len(x1), "n_to": len(x2),
                         "pf_share_from": float((sched[d1] == 1).mean()), "pf_share_to": float((sched[d2] == 1).mean()),
                         "jump": jump, "z": z, "flag": bool(np.isfinite(z) and abs(z) > z_thr)})
    return pd.DataFrame(rows, columns=["md5", "kind", "day_from", "day_to", "calendar_gap_days", "n_from", "n_to", "pf_share_from",
                                       "pf_share_to", "jump", "z", "flag"])


# ---------------------------------------------------------------- main
def _md5_file(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return str(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=C.DATA)
    ap.add_argument("--canonical", default="results/dataset_canonical.parquet")
    ap.add_argument("--d6-reservations", default="results/d6_reservations.csv")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="results/d8")
    a = ap.parse_args()

    canon = pd.read_parquet(a.canonical)
    with open(a.canonical.replace(".parquet", ".meta.json")) as f:
        meta = json.load(f)
    info = pd.read_csv(a.d6_reservations)
    usable = set(canon["reservation"].unique())
    resv = [r for r in C.list_reservations(a.data) if C.path_cfg(r)["res"] in usable]
    times = read_times(resv, a.workers)
    tab = build_table(canon, info, times)

    plausible = tab["t0_ms"].between(*PLAUSIBLE_MS)
    both = tab.dropna(subset=["t0_ms", "t0_ms_d6"])
    order, inversions = order_check(tab)
    sep = separation(tab)

    targets = D7.target_scripts(canon.assign(md5=canon["reservation"].map(info.set_index("res")["md5"])).dropna(subset=["md5"]))
    w, _ = D6.attach_bins(canon, info)
    w = w[w["md5"].isin(targets)].reset_index(drop=True)
    eff = D7.scheduler_effects(w)
    near = nearest_pair_effects(w, tab)
    cmp_ = compare_with_reference(near, eff)
    nsum = nearest_summary(cmp_, near)

    vals = []
    for tag, col in METRICS:
        v = common_segment_values(w, col)
        v = v.merge(tab[["reservation", "slicing", "sched", "t0_ms", "start_utc", "date_utc"]], on="reservation", how="left")
        vals.append(add_residuals(v).assign(metric=tag))
    breaks, jumps, daily = [], [], []
    for v in vals:
        tag = v["metric"].iloc[0]
        breaks.append(drift_breaks(v).assign(metric=tag))
        jumps.append(pd.concat([daily_jumps(v, k) for k in ("resid_slicing", "resid_cell")]).assign(metric=tag))
        daily.append(daily_series(v).assign(metric=tag))
    breaks, jumps, daily = pd.concat(breaks), pd.concat(jumps), pd.concat(daily)

    summary = {
        "canonical_dataset_version": meta.get("dataset_version"), "d6_reservations_md5": _md5_file(a.d6_reservations),
        "raw_files_read": "bs/enb_metrics.csv (time, nof_ue) of the usable reservations only", "seed": SEED, "n_perm": N_PERM,
        "n_usable": len(usable), "n_dirs_read": len(resv), "n_with_t0": int(tab["t0_ms"].notna().sum()), "n_plausible_epoch_ms": int(plausible.sum()),
        "n_t0_equal_to_d6": int((both["t0_ms"] == both["t0_ms_d6"]).sum()), "n_t0_compared_to_d6": len(both),
        "problems": tab.loc[tab["problem"].notna(), ["reservation", "problem"]].to_dict(orient="records"),
        "first_start_utc": tab["start_utc"].min(), "last_start_utc": tab["start_utc"].max(),
        "per_cluster_span_utc": {str(k): [g["start_utc"].min(), g["start_utc"].max()] for k, g in tab.groupby("cluster")},
        "order": order.to_dict(orient="records"), "n_inversions": int(len(inversions)),
        "separation": sep.to_dict(orient="records"),
        "target_scripts": targets, "nearest_summary": nsum.to_dict(orient="records"),
        "drift_breaks": breaks.to_dict(orient="records"),
        "daily_jumps_flagged": jumps[jumps["flag"]].to_dict(orient="records"),
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    tab.to_csv(a.out + "_times.csv", index=False)
    order.to_csv(a.out + "_order.csv", index=False)
    inversions.to_csv(a.out + "_inversions.csv", index=False)
    sep.to_csv(a.out + "_separation.csv", index=False)
    cmp_.to_csv(a.out + "_nearest_pairs.csv", index=False)
    nsum.to_csv(a.out + "_nearest_summary.csv", index=False)
    pd.concat(vals).to_csv(a.out + "_drift_values.csv", index=False)
    daily.to_csv(a.out + "_daily.csv", index=False)
    jumps.to_csv(a.out + "_daily_jumps.csv", index=False)
    breaks.to_csv(a.out + "_drift_breaks.csv", index=False)
    with open(a.out + "_summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=_json_default)
    print(json.dumps({k: summary[k] for k in ("n_usable", "n_with_t0", "n_plausible_epoch_ms", "n_t0_equal_to_d6", "n_t0_compared_to_d6",
                                               "first_start_utc", "last_start_utc", "per_cluster_span_utc", "n_inversions")}, indent=1, default=_json_default))


if __name__ == "__main__":
    main()
