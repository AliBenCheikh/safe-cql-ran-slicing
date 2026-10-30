"""D6: traffic scripts shared between reservations (md5 of bs/mgen-script-scope.mg*).

Read-only on the dataset. For every distinct script (md5):
  1. cluster(s), configurations (slicing x scheduler) covered, number of reservations per configuration;
  2. noise: variance, across repetitions of the same (script, cluster, action), of the per-reservation mean
     reward and cost;
  3. mean reward / cost difference between actions for the same script, aligned on SCRIPT time;
  4. number of distinct scripts and reservations per script in train (clusters 2-3) and test (cluster 1).

Alignment on script time (hypotheses [H], none is proven by the data):
  * The script clock starts at 0 when MGEN starts. The first ON line of a URLLC flow (6 or 7) is at script time
    t_on. MGEN numbers packets from 1 and sends PERIODIC at `rate` pkt/s, so the flow started at
        start_abs = Sent Time(first logged packet) - (Sequence No. - 1) / rate.
    Hence  origin_abs = start_abs - t_on  is the absolute time of script time 0 (median over flows 6 and 7;
    their disagreement is reported as `origin_flow_gap_s`). The estimate is ACCEPTED only if both flows are
    observed and agree within ORIGIN_TOL_S (a flow whose first logged packet is not from its first ON segment
    gives a wrong origin: seen as gaps of 60 s / 1021 s). Single-flow origins cannot be cross-checked and are
    rejected unless --allow-single-flow. Rejected reservations are excluded from the script-aligned
    statistics and counted.
  * Sent Time is seconds of day on the sender host; it is mapped to UTC epoch with the same whole-hour rule as
    src/build_dataset.py (reference t0 = first eNB row with nof_ue > 0). A clock offset between hosts is
    NOT corrected.
  * A canonical window `win` starts at t0 + win*WINDOW_S, i.e. at script time
        ws = t0 + win*WINDOW_S - origin_abs.
    It is assigned to the script bin  sbin = round(ws / WINDOW_S).  Windows of two reservations that land in the
    same sbin are paired; their sub-window misalignment |ws/WINDOW_S - sbin| (<= 0.5) is reported.
Cost = urllc_frac_viol of the window (raw, not the fitted `cost_hat` table). Reward = reward_embb_Mbps.
Nothing here is random: no seed is needed.
"""
import argparse
import glob
import hashlib
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from src.build_dataset import WINDOW_S, _enb_stream
from src.checks import common as C

ORIGIN_TOL_S = 1.5
_PERIODIC = re.compile(r"PERIODIC\s*\[\s*([0-9.]+)\s+([0-9.]+)\s*\]")


# ---------------------------------------------------------------- script parsing / hashing
def script_path(res):
    f = sorted(glob.glob(os.path.join(res, "bs", "mgen-script-scope.mg*")))
    return f[0] if f else None


def script_md5(res):
    p = script_path(res)
    if p is None:
        return None
    with open(p, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def parse_script(text):
    """List of {t, op, flow, rate, size}; blank lines and LISTEN lines are ignored."""
    ev = []
    for line in text.splitlines():
        p = line.split()
        if len(p) < 3 or p[1] not in ("ON", "OFF"):
            continue
        e = {"t": float(p[0]), "op": p[1], "flow": int(p[2]), "rate": None, "size": None}
        m = _PERIODIC.search(line)
        if m:
            e["rate"], e["size"] = float(m.group(1)), float(m.group(2))
        ev.append(e)
    return ev


def first_on(events, flow):
    for e in events:
        if e["op"] == "ON" and e["flow"] == flow and e["rate"]:
            return e
    return None


# ---------------------------------------------------------------- time alignment
def sod_to_abs_s(sod, t0_ms):
    """Seconds-of-day -> UTC epoch seconds, whole-hour shift chosen to land nearest to t0 (as build_dataset)."""
    day0 = pd.Timestamp(t0_ms, unit="ms", tz="UTC").normalize().timestamp()
    tz_h = int(round((day0 + sod - t0_ms / 1000.0) / 3600.0))
    return day0 + sod - 3600.0 * tz_h


def origin_from_first_packet(sent_sod, seq, rate, t_on, t0_ms):
    """Absolute time (UTC s) of script time 0, from one flow's first logged packet."""
    start_abs = sod_to_abs_s(sent_sod, t0_ms) - (seq - 1) / rate
    return start_abs - t_on


def script_origin(res, t0_ms):
    """(origin_abs_s or None, diag). Reads the script and the first data line of the URLLC mgen.csv files."""
    diag = {"origin_flows": 0, "origin_flow_gap_s": None}
    p = script_path(res)
    if p is None:
        return None, diag
    with open(p) as f:
        events = parse_script(f.read())
    ests = []
    for u in C.ue_dirs(res):
        m = re.search(r"ue_0*(\d+)$", u)
        mp = os.path.join(u, "mgen.csv")
        if not m or m.group(1)[-3:] not in {"006", "007", "008", "009"} or not os.path.exists(mp):
            continue
        try:
            hdr, first, _ = C.first_last_lines(mp)
            cols = hdr.split(",")
            v = first.split(",")
            sent, flow, seq = float(v[cols.index("Sent Time")]), int(v[cols.index("Flow ID")]), int(v[cols.index("Sequence No.")])
        except (ValueError, IndexError):
            continue
        e = first_on(events, flow)
        if e is not None:
            ests.append(origin_from_first_packet(sent, seq, e["rate"], e["t"], t0_ms))
    diag["origin_flows"] = len(ests)
    if not ests:
        return None, diag
    diag["origin_flow_gap_s"] = float(max(ests) - min(ests))
    return float(np.median(ests)), diag


def origin_ok(n_flows, gap_s, allow_single=False, tol=ORIGIN_TOL_S):
    if n_flows >= 2:
        return gap_s is not None and gap_s <= tol
    return bool(allow_single and n_flows == 1)


def add_script_bins(df, t0_ms, origin_abs_s):
    """Adds `ws_s` (script time of window start), `sbin`, `sbin_resid` to a single-reservation frame."""
    ws = t0_ms / 1000.0 + df["win"].to_numpy() * WINDOW_S - origin_abs_s
    out = df.copy()
    out["ws_s"] = ws
    out["sbin"] = np.round(ws / WINDOW_S).astype(int)
    out["sbin_resid"] = np.abs(ws / WINDOW_S - out["sbin"])
    return out


# ---------------------------------------------------------------- per-reservation info (raw files)
def reservation_info(args):
    res, need_origin, allow_single = args
    pc = C.path_cfg(res)
    out = {**pc, "md5": script_md5(res), "t0_ms": None, "origin_abs_s": None, "origin_flows": 0, "origin_flow_gap_s": None, "origin_ok": False}
    if need_origin:
        t0, _ = _enb_stream(res)
        if t0 is not None:
            out["t0_ms"] = t0
            o, d = script_origin(res, t0)
            out["origin_abs_s"] = o
            out.update(d)
            out["origin_ok"] = origin_ok(d["origin_flows"], d["origin_flow_gap_s"], allow_single)
    return out


# ---------------------------------------------------------------- analysis (pure functions on frames)
def _cfg_label(slicing, sched):
    return f"s{slicing}/r{sched}"


def inventory(res_df, usable):
    """One row per (md5, cluster, slicing, sched): reservations in the raw tree and usable (in the canonical set)."""
    d = res_df.assign(usable=res_df["res"].isin(usable))
    g = d.groupby(["md5", "cluster", "slicing", "sched"]).agg(n_res_all=("res", "size"), n_res_usable=("usable", "sum")).reset_index()
    return g


def script_summary(inv):
    rows = []
    for h, g in inv.groupby("md5"):
        rows.append({
            "md5": h, "clusters": sorted(g.cluster.unique().tolist()), "n_res_all": int(g.n_res_all.sum()),
            "n_res_usable": int(g.n_res_usable.sum()), "n_configs": len(g),
            "n_configs_usable": int((g.n_res_usable > 0).sum()),
            "res_per_config": {_cfg_label(r.slicing, r.sched): f"{int(r.n_res_usable)}/{int(r.n_res_all)}" for r in g.itertuples()},
        })
    return pd.DataFrame(rows).sort_values("n_res_all", ascending=False).reset_index(drop=True)


def noise(w):
    """w: windows with md5, cluster, action, reservation, sbin, reward_embb_Mbps, urllc_frac_viol.
    Per (md5, cluster, action) with >= 2 repetitions:
      * var_*_raw : variance across reservations of the per-reservation mean (whole reservation; sensitive to
                    reservations that cover different parts of the script);
      * var_*_bin : mean over script bins covered by >= 2 repetitions of the across-repetition variance of the
                    window value (noise at fixed script time; robust to truncated reservations)."""
    rows = []
    for (h, cl, a), g in w.groupby(["md5", "cluster", "action"]):
        n = g["reservation"].nunique()
        if n < 2:
            continue
        row = {"md5": h, "cluster": cl, "action": a, "n_rep": n}
        for tag, col in (("reward", "reward_embb_Mbps"), ("cost", "urllc_frac_viol")):
            raw = g.groupby("reservation")[col].mean().to_numpy()
            row[f"mean_{tag}"], row[f"var_{tag}_raw"] = float(raw.mean()), float(raw.var(ddof=1))
            b = g.groupby("sbin")[col].agg(["var", "count"])
            b = b[b["count"] >= 2]
            row[f"var_{tag}_bin"] = float(b["var"].mean()) if len(b) else np.nan
            row["n_bins_ge2"] = len(b)
        rows.append(row)
    return pd.DataFrame(rows)


def _series(g, key, col):
    """Mean over repetitions of `col` per `key` bin, plus the per-reservation frames."""
    return g.groupby(key)[col].mean()


def action_diffs(w):
    """For each (md5, cluster) and action pair a < b: mean (b - a) of reward and cost over the script bins present
    for both actions (rep-averaged per bin). `*_win` is the same quantity aligned on the canonical window index
    (the previous, non script-aligned convention), to show what the alignment changes. `se_*` is
    sqrt(var_a/n_a + var_b/n_b) of the per-reservation means over the common bins (NaN if a side has 1 rep)."""
    rows = []
    for (h, cl), g in w.groupby(["md5", "cluster"]):
        acts = sorted(g["action"].unique())
        for i, a in enumerate(acts):
            for b in acts[i + 1:]:
                ga, gb = g[g.action == a], g[g.action == b]
                row = {"md5": h, "cluster": cl, "action_a": a, "action_b": b,
                       "n_rep_a": ga.reservation.nunique(), "n_rep_b": gb.reservation.nunique()}
                for key, sfx in (("sbin", ""), ("win", "_win")):
                    ca = set(ga[key]) & set(gb[key])
                    row[f"n_bins{sfx}"] = len(ca)
                    for tag, col in (("reward", "reward_embb_Mbps"), ("cost", "urllc_frac_viol")):
                        if not ca:
                            row[f"diff_{tag}{sfx}"] = np.nan
                            row[f"se_{tag}{sfx}"] = np.nan
                            continue
                        xa, xb = ga[ga[key].isin(ca)], gb[gb[key].isin(ca)]
                        row[f"diff_{tag}{sfx}"] = float(_series(xb, key, col).mean() - _series(xa, key, col).mean())
                        va = xa.groupby("reservation")[col].mean()
                        vb = xb.groupby("reservation")[col].mean()
                        if len(va) > 1 and len(vb) > 1:
                            row[f"se_{tag}{sfx}"] = float(np.sqrt(va.var(ddof=1) / len(va) + vb.var(ddof=1) / len(vb)))
                        else:
                            row[f"se_{tag}{sfx}"] = np.nan
                rows.append(row)
    return pd.DataFrame(rows)


def _q(x):
    x = np.asarray(x, dtype=float)
    if not len(x):
        return None
    return dict(zip(["min", "p25", "p50", "p75", "max"], np.percentile(x, [0, 25, 50, 75, 100]).round(2).tolist()))


def split_summary(res_df, usable):
    """Distinct scripts and reservations per script in train (clusters 2-3) and test (cluster 1), on all
    reservations of the raw tree and on the usable ones, plus the train/test script overlap."""
    out = {}
    for label, d in (("all", res_df), ("usable", res_df[res_df["res"].isin(usable)])):
        d = d[d["md5"].notna()]
        tr, te = d[d.cluster != 1], d[d.cluster == 1]
        s_tr, s_te = set(tr.md5), set(te.md5)
        both = s_tr & s_te
        out[label] = {
            "train": {"n_reservations": len(tr), "n_scripts": len(s_tr), "res_per_script": _q(tr.groupby("md5").size())},
            "test": {"n_reservations": len(te), "n_scripts": len(s_te), "res_per_script": _q(te.groupby("md5").size())},
            "n_scripts_in_both": len(both),
            "n_test_res_with_train_script": int(te.md5.isin(s_tr).sum()),
            "n_train_res_with_test_script": int(tr.md5.isin(s_te).sum()),
            "n_scripts_multi_cluster": int((d.groupby("md5")["cluster"].nunique() > 1).sum()),
            "n_scripts_single_reservation": int((d.groupby("md5").size() == 1).sum()),
        }
    return out


def attach_bins(canon, info):
    """Adds md5, sbin, sbin_resid to canonical windows; reservations without an ACCEPTED origin are dropped."""
    info = info.set_index("res")
    parts, dropped = [], []
    for r, g in canon.groupby("reservation"):
        if r not in info.index or not info.at[r, "origin_ok"] or pd.isna(info.at[r, "md5"]):
            dropped.append(r)
            continue
        x = add_script_bins(g, info.at[r, "t0_ms"], info.at[r, "origin_abs_s"])
        x["md5"] = info.at[r, "md5"]
        parts.append(x)
    return (pd.concat(parts, ignore_index=True) if parts else canon.iloc[0:0].assign(md5=None, sbin=0, sbin_resid=0.0)), dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", default="results/dataset_canonical.parquet")
    ap.add_argument("--data", default=C.DATA)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--allow-single-flow", action="store_true", help="accept origins estimated from one URLLC flow only")
    ap.add_argument("--out", default="results/d6")
    a = ap.parse_args()

    canon = pd.read_parquet(a.canonical)
    with open(a.canonical.replace(".parquet", ".meta.json")) as f:
        meta = json.load(f)
    usable = set(canon["reservation"].unique())
    resv = C.list_reservations(a.data)
    with ProcessPoolExecutor(a.workers) as ex:
        info = pd.DataFrame(ex.map(reservation_info, [(r, C.path_cfg(r)["res"] in usable, a.allow_single_flow) for r in resv], chunksize=8))
    inv = inventory(info, usable)
    summ_scripts = script_summary(inv)
    w, dropped = attach_bins(canon, info)
    nz, df_ = noise(w), action_diffs(w)

    ver = C.dataset_version(a.data)
    o = info[info["res"].isin(usable)]
    summary = {
        "dataset_version": ver, "canonical_dataset_version": meta.get("dataset_version"),
        "dataset_version_matches_canonical": ver == meta.get("dataset_version"),
        "deterministic_no_seed": True,
        "n_reservations_raw": len(info), "n_without_script": int(info.md5.isna().sum()), "n_distinct_scripts": int(info.md5.nunique()),
        "n_usable": len(usable), "n_usable_origin_rejected": len(dropped), "allow_single_flow": a.allow_single_flow,
        "origin_tol_s": ORIGIN_TOL_S,
        "alignment": {
            "origin_flow_gap_s_quantiles(min,p25,p50,p75,max)": _q(o.origin_flow_gap_s.dropna()),
            "n_origin_from_one_flow_only": int((o.origin_flows == 1).sum()),
            "n_origin_two_flows_disagree": int(((o.origin_flows >= 2) & ~o.origin_ok).sum()),
            "script_time_of_window0_s_quantiles(accepted origins)": _q((o.t0_ms / 1000.0 - o.origin_abs_s)[o.origin_ok]),
            "sbin_resid_windows_quantiles(min,p25,p50,p75,max)": _q(w.sbin_resid),
        },
        "split": split_summary(info, usable),
        "top_scripts": summ_scripts.head(10).to_dict(orient="records"),
        "noise_median_n_rep": float(nz.n_rep.median()) if len(nz) else None,
        "n_action_pairs": len(df_),
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    inv.to_csv(a.out + "_inventory.csv", index=False)
    summ_scripts.to_json(a.out + "_scripts.json", orient="records", indent=1)
    nz.to_csv(a.out + "_noise.csv", index=False)
    df_.to_csv(a.out + "_action_diffs.csv", index=False)
    info.to_csv(a.out + "_reservations.csv", index=False)
    with open(a.out + "_summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=str)
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
