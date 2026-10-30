"""D7: scheduler effect, time coverage and execution order on the 3 scripts that cover all 8 actions.

Read-only. Reads ONLY derived files (results/dataset_canonical.parquet and results/d6_reservations.csv written by
D6); the raw dataset tree is not opened. Deterministic except the permutation test of step 4 (seed 0).

For every script that has usable windows for all 8 actions (expected: a908e4cc, a53521b2, c40f2fe7):
  1. coverage   : script-time segment [first window start, last window end] of each reservation, and whether all
                  reservations of the script cover (nearly) the same segment;
  2. scheduler  : PF - RR difference of reward and cost at fixed slicing, per script, on the script bins present
                  on both sides; sign / order-of-magnitude coherence across the scripts;
  3. order      : reservation ids (supposed chronological, [H]) -> does the sign of PF - RR change when the
                  early/late half of each scheduler's reservations is used? Also the time drift of a single action;
  4. exogeneity : at fixed script and script bin, do nof_ue, the URLLC received packet rate and the eMBB rate
                  depend on the action? (script-bin centring, reservation-level F and permutation test);
  5. repetitions: number of reservations per (slicing, scheduler).

Conventions (choices, not results): script time and bins come from src/checks/d6_shared_scripts.py (reservations
whose origin is not ACCEPTED there are excluded from 1-4 and counted); PF = sched 1, RR = sched 0 (build_dataset
SCHED_BIN: raw policy 2 -> 1, raw policy 0 -> 0); cost = urllc_frac_viol of the window (raw); reward =
reward_embb_Mbps; URLLC received rate = n_pkts / WINDOW_S (packets with a valid latency in mgen.csv, all 4 URLLC UEs).
"""
import argparse
import hashlib
import json
import os

import numpy as np
import pandas as pd

from src.build_dataset import WINDOW_S
from src.checks import d6_shared_scripts as D6

N_ACTIONS = 8
SCHED_NAME = {0: "RR", 1: "PF"}
METRICS = (("reward", "reward_embb_Mbps"), ("cost", "urllc_frac_viol"))
SAME_SEGMENT_MIN_OVERLAP = 0.9  # intersection / union of the reservations' script-time spans
SAME_ORDER_MAX_RATIO = 10.0     # |effect| ratio across scripts below which the order of magnitude is "the same"
N_PERM = 2000                  # permutations of the action labels in action_dependence
SEED = 0
CORE_START_TOL_S = 10.0         # a reservation is in the "core" if its start / end are within these of the script median
CORE_END_TOL_S = 60.0
SE_Z = 2.0                      # |diff| > SE_Z * se is called distinguishable from 0 (naive SE, see [H])


def res_id(name):
    """Numeric part of 'RESERVATION-142703'."""
    return int(str(name).split("-")[-1])


# ---------------------------------------------------------------- selection
def target_scripts(usable_windows):
    """md5 of scripts that have usable windows for all N_ACTIONS actions."""
    n = usable_windows.groupby("md5")["action"].nunique()
    return sorted(n[n == N_ACTIONS].index.tolist())


# ---------------------------------------------------------------- 1. coverage
def reservation_coverage(w):
    """One row per reservation: script-time span of its windows (`ws_s` from D6.add_script_bins)."""
    g = w.groupby("reservation")
    cov = g.agg(md5=("md5", "first"), slicing=("slicing", "first"), sched=("sched", "first"),
                start_s=("ws_s", "min"), last_ws_s=("ws_s", "max"), n_win=("win", "size")).reset_index()
    cov["end_s"] = cov["last_ws_s"] + WINDOW_S
    cov["fill"] = cov["n_win"] * WINDOW_S / (cov["end_s"] - cov["start_s"])  # < 1 when windows are missing inside the span
    return cov.drop(columns="last_ws_s")


def _q5(x):
    return dict(zip(["min", "p25", "p50", "p75", "max"], np.percentile(np.asarray(x, float), [0, 25, 50, 75, 100]).round(1).tolist()))


def segment_report(cov, min_overlap=SAME_SEGMENT_MIN_OVERLAP):
    """Per script: do all reservations cover the same script-time segment?
    overlap_ratio = |intersection of all spans| / |union of all spans|; same_segment = overlap_ratio >= min_overlap.
    A few truncated / late-starting reservations make this strict criterion fail, so `n_outside_core` counts the
    reservations whose start is > CORE_START_TOL_S or end > CORE_END_TOL_S from the script median, and
    `core_overlap_ratio` is the same ratio on the others.
    Also the same ratio restricted to each scheduler and between the two schedulers' median spans."""
    out = {}
    for h, g in cov.groupby("md5"):
        inter = max(0.0, g.end_s.min() - g.start_s.max())
        union = g.end_s.max() - g.start_s.min()
        med_s, med_e = g.start_s.median(), g.end_s.median()
        core = g[((g.start_s - med_s).abs() <= CORE_START_TOL_S) & ((g.end_s - med_e).abs() <= CORE_END_TOL_S)]
        c_inter = max(0.0, core.end_s.min() - core.start_s.max()) if len(core) else 0.0
        c_union = core.end_s.max() - core.start_s.min() if len(core) else np.nan
        r = {"n_res": len(g), "n_outside_core": int(len(g) - len(core)), "core_overlap_ratio": round(float(c_inter / c_union), 3) if len(core) else None,
             "start_s": _q5(g.start_s), "end_s": _q5(g.end_s), "intersection_s": round(float(inter), 1),
             "union_s": round(float(union), 1), "overlap_ratio": round(float(inter / union), 3),
             "same_segment": bool(inter / union >= min_overlap), "median_fill": round(float(g.fill.median()), 3)}
        for s, gs in g.groupby("sched"):
            i_s = max(0.0, gs.end_s.min() - gs.start_s.max())
            r[f"overlap_ratio_{SCHED_NAME[s]}"] = round(float(i_s / (gs.end_s.max() - gs.start_s.min())), 3)
            r[f"median_start_s_{SCHED_NAME[s]}"] = round(float(gs.start_s.median()), 1)
            r[f"median_end_s_{SCHED_NAME[s]}"] = round(float(gs.end_s.median()), 1)
        out[h] = r
    return out


# ---------------------------------------------------------------- 2. pairwise effect on common script bins
def pair_effect(ga, gb):
    """b - a over the script bins present on both sides (per-bin mean over repetitions, then mean over bins).
    se = sqrt(var_a/n_a + var_b/n_b) of the per-reservation means over those bins. NaN if a side has 1 repetition. [H]
    The SE treats reservations as independent, which ignores the script-level dependence (see docs)."""
    common = set(ga["sbin"]) & set(gb["sbin"])
    out = {"n_rep_a": ga["reservation"].nunique(), "n_rep_b": gb["reservation"].nunique(), "n_bins": len(common)}
    for tag, col in METRICS:
        if not common:
            out[f"diff_{tag}"] = out[f"se_{tag}"] = np.nan
            continue
        xa, xb = ga[ga["sbin"].isin(common)], gb[gb["sbin"].isin(common)]
        out[f"diff_{tag}"] = float(xb.groupby("sbin")[col].mean().mean() - xa.groupby("sbin")[col].mean().mean())
        va, vb = xa.groupby("reservation")[col].mean(), xb.groupby("reservation")[col].mean()
        out[f"se_{tag}"] = float(np.sqrt(va.var(ddof=1) / len(va) + vb.var(ddof=1) / len(vb))) if len(va) > 1 and len(vb) > 1 else np.nan
    return out


def scheduler_effects(w):
    """PF - RR per (script, slicing)."""
    rows = []
    for (h, sl), g in w.groupby(["md5", "slicing"]):
        rr, pf = g[g.sched == 0], g[g.sched == 1]
        if rr.empty or pf.empty:
            continue
        rows.append({"md5": h, "slicing": sl, "prb_embb": int(g.prb_embb.iloc[0]), **pair_effect(rr, pf)})
    return pd.DataFrame(rows)


def _sign(x):
    return int(np.sign(x)) if np.isfinite(x) else 0


def consistency(eff, max_ratio=SAME_ORDER_MAX_RATIO):
    """Across scripts, for each slicing (and the unweighted mean over slicings, slicing = 'mean'), per metric:
    same_sign (all scripts the same non-zero sign), n_distinguishable (|diff| > SE_Z*se), ratio = max|diff|/min|diff|,
    same_order (ratio < max_ratio), coherent = same_sign & same_order."""
    rows = []
    pooled = eff.groupby("md5")[[f"diff_{t}" for t, _ in METRICS] + [f"se_{t}" for t, _ in METRICS]].mean().reset_index().assign(slicing="mean")
    for sl, g in list(eff.groupby("slicing")) + list(pooled.groupby("slicing")):
        for tag, _ in METRICS:
            d, se = g[f"diff_{tag}"].to_numpy(float), g[f"se_{tag}"].to_numpy(float)
            signs = {_sign(x) for x in d}
            ad = np.abs(d)
            ratio = float(ad.max() / ad.min()) if len(ad) and ad.min() > 0 else np.inf
            rows.append({"slicing": sl, "metric": tag, "n_scripts": len(d), "diffs": [round(float(x), 4) for x in d],
                         "same_sign": len(signs) == 1 and 0 not in signs,
                         "n_distinguishable": int((ad > SE_Z * np.nan_to_num(se, nan=np.inf)).sum()),
                         "ratio": ratio, "same_order": bool(ratio < max_ratio),
                         "coherent": bool(len(signs) == 1 and 0 not in signs and ratio < max_ratio)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 3. confusion with execution order
def _halves(g):
    """(early, late) frames: reservations of g sorted by numeric id and split in two (None if < 2 reservations)."""
    ids = sorted(g["reservation"].unique(), key=res_id)
    if len(ids) < 2:
        return None
    parts = np.array_split(np.array(ids, dtype=object), 2)
    return [g[g["reservation"].isin(set(p))] for p in parts], [float(np.median([res_id(x) for x in p])) for p in parts]


def order_confusion(w):
    """Per (script, slicing):
      * ranges : id range of each scheduler, number of RR<->PF switches in the id-sorted sequence (1 = two blocks);
      * combos : PF - RR for each (RR half, PF half) in {early, late}^2, plus the median-id gap of the pair;
      * drift  : late - early half of ONE action (same scheduler, same slicing): pure time effect, no scheduler change."""
    ranges, combos, drift = [], [], []
    for (h, sl), g in w.groupby(["md5", "slicing"]):
        ids = g.drop_duplicates("reservation").assign(rid=lambda d: d["reservation"].map(res_id)).sort_values("rid")
        seq = ids["sched"].to_numpy()
        r = {"md5": h, "slicing": sl, "n_switches": int((seq[1:] != seq[:-1]).sum())}
        for s in (0, 1):
            x = ids.loc[ids.sched == s, "rid"]
            r[f"id_min_{SCHED_NAME[s]}"], r[f"id_max_{SCHED_NAME[s]}"], r[f"n_{SCHED_NAME[s]}"] = (int(x.min()), int(x.max()), len(x)) if len(x) else (None, None, 0)
        both = r["n_RR"] > 0 and r["n_PF"] > 0
        r["id_ranges_overlap"] = bool(both and max(r["id_min_RR"], r["id_min_PF"]) <= min(r["id_max_RR"], r["id_max_PF"]))
        ranges.append(r)
        hv = {s: _halves(g[g.sched == s]) for s in (0, 1)}
        for s in (0, 1):
            if hv[s] is not None:
                (e, l), _ = hv[s]
                drift.append({"md5": h, "slicing": sl, "sched": SCHED_NAME[s], **pair_effect(e, l)})
        if hv[0] is None or hv[1] is None:
            continue
        (rr_h, rr_m), (pf_h, pf_m) = hv[0], hv[1]
        for i, ni in enumerate(("early", "late")):
            for j, nj in enumerate(("early", "late")):
                combos.append({"md5": h, "slicing": sl, "rr_half": ni, "pf_half": nj, "id_gap": abs(pf_m[j] - rr_m[i]), **pair_effect(rr_h[i], pf_h[j])})
    return pd.DataFrame(ranges), pd.DataFrame(combos), pd.DataFrame(drift)


def order_verdict(combos):
    """Per (script, slicing, metric): can the sign of PF - RR be reversed by choosing which halves are compared?
    sign_depends_on_order = both a positive and a negative PF - RR among the evaluable combinations."""
    rows = []
    for (h, sl), g in combos.groupby(["md5", "slicing"]):
        for tag, _ in METRICS:
            d = g[f"diff_{tag}"].to_numpy(float)
            d = d[np.isfinite(d)]
            rows.append({"md5": h, "slicing": sl, "metric": tag, "n_combos": len(d), "n_pos": int((d > 0).sum()), "n_neg": int((d < 0).sum()),
                         "sign_depends_on_order": bool(len(d) >= 2 and (d > 0).any() and (d < 0).any())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 4. dependence of nof_ue / received rate on the action
def action_dependence(g, col, n_perm=N_PERM, seed=SEED):
    """One script, one variable. The action is constant within a reservation, so the unit is the reservation:
      1. y is centred within each script bin (mean over all rows of that bin, on bins covered by >= 2 actions), which
         removes the common load shape over script time;
      2. each reservation is summarised by the mean of its centred values;
      3. one-way test of the action on these reservation values: F statistic (eta2 = between / total sum of squares)
         and a permutation p-value obtained by shuffling the action labels across reservations (seeded). It
         assumes the labels are exchangeable under the null, i.e. it ignores execution-order blocks [H].
    A window-level cluster-robust Wald test was tried and rejected: it over-rejects under the null with ~30
    reservations (checked by simulation), hence the permutation test."""
    x = g[["sbin", "action", "reservation", col]].dropna()
    k = x.groupby("sbin")["action"].transform("nunique")
    x = x[k >= 2].copy()
    x["yc"] = x[col] - x.groupby("sbin")[col].transform("mean")
    r = x.groupby("reservation").agg(action=("action", "first"), yc=("yc", "mean"))
    if r["action"].nunique() < 2 or len(r) < 3:
        return None
    v, lab = r["yc"].to_numpy(float), r["action"].to_numpy()

    def f_eta(labels):
        gm = v.mean()
        ss_t = float(((v - gm) ** 2).sum())
        groups = [v[labels == a] for a in np.unique(labels)]
        ss_b = float(sum(len(z) * (z.mean() - gm) ** 2 for z in groups))
        df_b, df_w = len(groups) - 1, len(v) - len(groups)
        ss_w = ss_t - ss_b
        f = (ss_b / df_b) / (ss_w / df_w) if df_w > 0 and ss_w > 0 else np.nan
        return f, (ss_b / ss_t if ss_t > 0 else np.nan)

    f_obs, eta2 = f_eta(lab)
    rng = np.random.default_rng(seed)
    perm = np.array([f_eta(rng.permutation(lab))[0] for _ in range(n_perm)])
    p = float((1 + np.sum(perm >= f_obs)) / (n_perm + 1)) if np.isfinite(f_obs) else np.nan
    ybar = float(x[col].mean())
    dev = r.groupby("action")["yc"].mean()
    return {"n_res": len(r), "n_bins": int(x["sbin"].nunique()), "mean": ybar, "eta2": eta2, "F": f_obs, "p_perm": p,
            "n_perm": n_perm, "seed": seed, "dev_by_action": {int(a_): round(float(d_), 4) for a_, d_ in dev.items()},
            "max_abs_dev_rel": float(dev.abs().max() / abs(ybar)) if ybar else np.nan}


def exogeneity(w):
    """nof_ue, URLLC received packet rate (n_pkts / WINDOW_S) and, as a POSITIVE CONTROL (it depends on the PRB split
    by construction), the eMBB rate: dependence on the action at fixed script bin, per script.
    `subset` = all 8 actions, or only the RR (resp. PF) reservations, i.e. the 4 slicings within one scheduler: since
    each scheduler ran as one block of ids, a dependence that persists inside one block cannot come from the
    scheduler / block change."""
    d = w.assign(urllc_rx_pps=w["n_pkts"] / WINDOW_S)
    rows = []
    for h, g in d.groupby("md5"):
        for subset, gs in (("all", g), ("RR only", g[g.sched == 0]), ("PF only", g[g.sched == 1])):
            for name, col in (("nof_ue", "nof_ue"), ("urllc_rx_pps", "urllc_rx_pps"), ("embb_rate_Mbps (control)", "reward_embb_Mbps")):
                r = action_dependence(gs, col)
                if r is not None:
                    rows.append({"md5": h, "subset": subset, "variable": name, **r})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 5. repetitions
def repetitions(usable, accepted):
    """Reservations per (script, slicing, scheduler): among usable reservations and among those with an accepted
    script origin (the ones used in 1-4)."""
    a = usable.drop_duplicates("reservation").groupby(["md5", "slicing", "sched"]).size().rename("n_usable")
    b = accepted.drop_duplicates("reservation").groupby(["md5", "slicing", "sched"]).size().rename("n_origin_ok")
    return pd.concat([a, b], axis=1).fillna(0).astype(int).reset_index()


# ---------------------------------------------------------------- main
def _md5_file(p):
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", default="results/dataset_canonical.parquet")
    ap.add_argument("--d6-reservations", default="results/d6_reservations.csv")
    ap.add_argument("--out", default="results/d7")
    a = ap.parse_args()

    canon = pd.read_parquet(a.canonical)
    with open(a.canonical.replace(".parquet", ".meta.json")) as f:
        meta = json.load(f)
    info = pd.read_csv(a.d6_reservations)
    usable = canon.assign(md5=canon["reservation"].map(info.set_index("res")["md5"]))
    targets = target_scripts(usable.dropna(subset=["md5"]))
    w, dropped = D6.attach_bins(canon, info)
    w = w[w["md5"].isin(targets)].reset_index(drop=True)
    usable = usable[usable["md5"].isin(targets)]

    cov = reservation_coverage(w)
    seg = segment_report(cov)
    eff = scheduler_effects(w)
    cons = consistency(eff)
    ranges, combos, drift = order_confusion(w)
    verdict = order_verdict(combos)
    exo = exogeneity(w)
    reps = repetitions(usable, w)

    summary = {
        "canonical_dataset_version": meta.get("dataset_version"), "d6_reservations_md5": _md5_file(a.d6_reservations),
        "raw_data_read": False, "seed": SEED, "n_perm": N_PERM, "target_scripts": targets,
        "n_usable_res_target_scripts": int(usable["reservation"].nunique()), "n_res_origin_ok_target_scripts": int(w["reservation"].nunique()),
        "segment": seg,
        "scheduler_consistency": cons.to_dict(orient="records"),
        "order_blocks": ranges.to_dict(orient="records"),
        "order_sign_depends": verdict.to_dict(orient="records"),
        "exogeneity": exo.to_dict(orient="records"),
        "repetitions": reps.to_dict(orient="records"),
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    cov.to_csv(a.out + "_coverage.csv", index=False)
    eff.to_csv(a.out + "_scheduler_effects.csv", index=False)
    cons.to_csv(a.out + "_consistency.csv", index=False)
    ranges.to_csv(a.out + "_order_ranges.csv", index=False)
    combos.to_csv(a.out + "_order_combos.csv", index=False)
    drift.to_csv(a.out + "_order_drift.csv", index=False)
    verdict.to_csv(a.out + "_order_verdict.csv", index=False)
    exo.to_csv(a.out + "_exogeneity.csv", index=False)
    reps.to_csv(a.out + "_repetitions.csv", index=False)
    with open(a.out + "_summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=_json_default)
    print(json.dumps(summary, indent=1, default=_json_default))


if __name__ == "__main__":
    main()
