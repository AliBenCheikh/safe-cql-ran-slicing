"""Canonical dataset builder (replaces notebook "Cellule 11" and "Cellule 12", i.e. cells 21-22).

Read-only on data/. No model is trained here.

Differences from the notebook, one per audit/Phase-0 finding:
  Fix 1 (D2)  all three streams use ONE window origin t0 = first eNB row with nof_ue > 0.
  Fix 2 (D3)  reservations are split into sub-episodes wherever `win` jumps by more than 1;
              lags and next_state never cross a sub-episode boundary.
  Fix 3 (D4)  the state holds only lag1/lag2 of reward and urllc_p50 plus the current radio
              features; the current reward and urllc_p50 are NOT in the state.
Also: no bfill (lags at episode start get a train-only median), no ffill/bfill of nof_ue,
one cost table (3 bins on nof_ue) fitted on the train split only.

Clock assumptions
  eNB    : `time` is epoch ms.
  URLLC  : `Received Time` is seconds of day; mapped to epoch with the UTC day of t0 and a
           whole-hour shift (time zone), as in src/checks/d2_clock_alignment.py.
  eMBB   : `ue_metrics.time` is ms since the UE logger start, with no absolute clock. The
           absolute start is ESTIMATED per UE as (first Timestamp of bs/<IMSI>_metrics.csv)
           - (first is_attached time). This is a hypothesis (decision_memo D2, [H]).
"""
import argparse
import json
import os
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from src.checks import common as C

WINDOW_S = 5.0
SLA_MS = 20.0
SCHED_BIN = {0: 0, 2: 1}
PRB_LEVELS = [9, 21, 30, 39]
EMBB_IMSI = {"002", "003", "004", "005"}
URLLC_IMSI = {"006", "007", "008", "009"}
RADIO_COLS = ["rsrp", "dl_snr", "dl_mcs", "dl_bler", "ul_buff"]
LAG_BASE = ["reward_embb_Mbps", "urllc_p50"]
LAG_COLS = [f"{c}_lag{k}" for c in LAG_BASE for k in (1, 2)]
# Pre-action state: current radio/load features + lags of past windows. Neither the current
# reward (r_t) nor the current urllc_p50 / urllc_frac_viol (c_t) belongs here.
STATE_COLS = ["nof_ue", *RADIO_COLS, *LAG_COLS]
NS_COLS = [f"ns_{c}" for c in STATE_COLS]
LOAD_EDGES = [0.0, 3.5, 5.5, 8.1]
MIN_CELL_N = 20
TRAIN_CLUSTERS = (2, 3)
TEST_CLUSTERS = (1,)
WINDOW_BASE_COLS = [*RADIO_COLS, "reward_embb_Mbps", "urllc_p50"]


# ----------------------------------------------------------------------------- pure functions

def window_index(t_abs_ms, t0_ms):
    """win = floor((t - t0) / WINDOW_S), t and t0 in epoch ms. Same formula for all streams."""
    return np.floor((np.asarray(t_abs_ms, dtype=float) - t0_ms) / 1000.0 / WINDOW_S).astype(int)


def assign_episodes(df):
    """Sort by win and add episode_idx / episode_id; a new episode starts where win steps by > 1."""
    df = df.sort_values("win").reset_index(drop=True)
    df["episode_idx"] = (df["win"].diff().fillna(1) > 1).cumsum().astype(int)
    df["episode_id"] = df["reservation"] + "_" + df["episode_idx"].astype(str)
    return df


def add_lags(df):
    """lag1/lag2 inside each episode (NaN at the start of an episode, never taken across a gap)."""
    g = df.groupby("episode_id", sort=False)
    for c in LAG_BASE:
        for k in (1, 2):
            df[f"{c}_lag{k}"] = g[c].shift(k)
    return df


def fit_lag_medians(train_df):
    """Median of the observed lags on the train split only."""
    return train_df[LAG_COLS].median()


def impute_lags(df, medians):
    df["lag_imputed"] = df[LAG_COLS].isna().any(axis=1)
    df[LAG_COLS] = df[LAG_COLS].fillna(medians)
    return df


def add_next_state(df):
    """ns_<col> = state of the next row of the SAME episode; NaN on the last window."""
    df["done"] = df.groupby("episode_id", sort=False)["win"].shift(-1).isna()
    ns = df.groupby("episode_id", sort=False)[STATE_COLS].shift(-1)
    for c in STATE_COLS:
        df[f"ns_{c}"] = ns[c]
    return df


def load_bin(nof_ue, edges=LOAD_EDGES):
    """Bin index 0..len(edges)-2 on nof_ue, right edge included. Values above the last edge are
    clipped into the last bin (counted by the caller). NaN stays NaN."""
    x = pd.Series(nof_ue, dtype=float)
    b = pd.cut(x, bins=edges, labels=False, right=True, include_lowest=True)
    b = b.where(~(x > edges[-1]), len(edges) - 2)
    return b


def fit_cost_table(train_df, min_n=MIN_CELL_N):
    """Per (action, load_bin) cost table fitted on train only. `cost_hat` falls back to the
    per-action mean when the cell has fewer than min_n windows."""
    g = train_df.groupby(["action", "load_bin"])
    t = g.agg(n_windows=("urllc_frac_viol", "size"), n_reservations=("reservation", "nunique"),
              cost_mean=("urllc_frac_viol", "mean")).reset_index()
    per_action = train_df.groupby("action")["urllc_frac_viol"].mean().rename("cost_action_mean")
    t = t.merge(per_action, on="action")
    t["cost_hat"] = np.where(t["n_windows"] >= min_n, t["cost_mean"], t["cost_action_mean"])
    return t


def lookup_cost(df, table, bin_col="load_bin"):
    key = pd.MultiIndex.from_arrays([df["action"], df[bin_col]])
    s = table.set_index(["action", "load_bin"])["cost_hat"]
    fallback = df["action"].map(table.drop_duplicates("action").set_index("action")["cost_action_mean"])
    return pd.Series(s.reindex(key).to_numpy(), index=df.index).fillna(fallback)


def count_report(df):
    out = {}
    for sp, d in df.groupby("split"):
        out[sp] = {"n_reservations": int(d["reservation"].nunique()),
                   "n_episodes": int(d["episode_id"].nunique()),
                   "n_rows": int(len(d)),
                   "n_transitions": int(d[NS_COLS].notna().all(axis=1).sum())}
    return out


# ----------------------------------------------------------------------------- I/O

def _imsi_full(ue_dir):
    m = re.search(r"ue_0*(\d+)$", ue_dir)
    return m.group(1) if m else None


def _read(path, sep=",", **kw):
    try:
        if os.path.getsize(path) == 0:
            return None
        df = pd.read_csv(path, sep=sep, **kw)
    except Exception:
        return None
    if df.shape[1] <= 1 and "usecols" not in kw:  # wrong separator -> a single column
        return None
    df.columns = [c.strip() for c in df.columns]
    return df


def _enb_stream(res):
    enb = _read(os.path.join(res, "bs", "enb_metrics.csv"), usecols=["time", "nof_ue"])
    if enb is None:
        return None, None
    enb["time"] = pd.to_numeric(enb["time"], errors="coerce")
    enb = enb.dropna(subset=["time"])
    enb = enb[enb["nof_ue"] > 0]
    if not len(enb):
        return None, None
    t0 = float(enb["time"].iloc[0])
    enb = enb.assign(win=window_index(enb["time"], t0))
    return t0, enb[enb["win"] >= 0].groupby("win")["nof_ue"].mean()


def _embb_stream(res, ue_dirs, t0, diag):
    per_ue, frames, offsets = [], [], []
    for d in ue_dirs:
        imsi = _imsi_full(d)
        if imsi is None or imsi[-3:] not in EMBB_IMSI:
            continue
        x = _read(os.path.join(d, "ue_metrics.csv"), ";")
        if x is None or "time" not in x or "dl_brate" not in x or "is_attached" not in x:
            continue
        x["time"] = pd.to_numeric(x["time"], errors="coerce")
        x = x.dropna(subset=["time"])
        att = x.loc[x["is_attached"] == 1, "time"]
        bs = _read(os.path.join(res, "bs", f"{imsi}_metrics.csv"), usecols=["Timestamp"], nrows=1)
        if len(att) == 0 or bs is None:
            diag["n_embb_unaligned"] += 1
            continue
        ue_t0_abs = float(bs["Timestamp"].iloc[0]) - float(att.iloc[0])
        offsets.append((ue_t0_abs - t0) / 1000.0)
        x = x[x["is_attached"] == 1].copy()
        x["win"] = window_index(ue_t0_abs + x["time"], t0)
        x = x[x["win"] >= 0]
        if not len(x):
            continue
        per_ue.append(x.groupby("win")["dl_brate"].mean())
        frames.append(x)
    diag["embb_ue_t0_offsets_s"] = offsets
    if not per_ue:
        return None, 0
    g = pd.DataFrame({"embb_slice_bps": pd.concat(per_ue, axis=1).sum(axis=1)})
    radio = pd.concat(frames, ignore_index=True)
    for c in RADIO_COLS:
        g[c] = radio.groupby("win")[c].mean() if c in radio else np.nan
    return g, len(per_ue)


def _urllc_stream(ue_dirs, t0):
    frames = []
    for d in ue_dirs:
        imsi = _imsi_full(d)
        if imsi is None or imsi[-3:] not in URLLC_IMSI:
            continue
        m = _read(os.path.join(d, "mgen.csv"), ",", usecols=["Received Time", "Sent Time"])
        if m is None:
            continue
        m["lat"] = (m["Received Time"] - m["Sent Time"]) * 1000.0
        m = m[(m["lat"] >= 0) & (m["lat"] < 20000)]
        if len(m):
            frames.append(m[["Received Time", "lat"]])
    if not frames:
        return None
    u = pd.concat(frames, ignore_index=True)
    day0 = pd.Timestamp(t0, unit="ms", tz="UTC").normalize().timestamp()
    tz_h = int(round((day0 + u["Received Time"].min() - t0 / 1000.0) / 3600.0))
    t_abs = day0 + u["Received Time"].to_numpy() - 3600.0 * tz_h
    t_abs = np.where(t_abs < t0 / 1000.0 - 43200.0, t_abs + 86400.0, t_abs)  # midnight wrap
    u["win"] = window_index(t_abs * 1000.0, t0)
    u = u[u["win"] >= 0]
    if not len(u):
        return None
    return u.groupby("win")["lat"].agg(
        urllc_frac_viol=lambda s: (s > SLA_MS).mean(),
        urllc_p99=lambda s: np.percentile(s, 99),
        urllc_p50="median", urllc_mean="mean", n_pkts="size")


def build_reservation(res):
    """Returns (DataFrame or None, diag). One row per window, with episode ids."""
    pc = C.path_cfg(res)
    diag = {"reservation": pc["res"], "skip": None, "n_embb_unaligned": 0,
            "n_dropped_no_enb": 0, "n_dropped_nan": 0}
    if pc["slicing"] not in (1, 2, 3, 4) or pc["sched"] not in SCHED_BIN:
        diag["skip"] = "slicing_5_or_unknown"
        return None, diag
    ue_dirs = [d for d in C.ue_dirs(res) if os.path.isdir(d)]
    t0, nof = _enb_stream(res)
    if t0 is None:
        diag["skip"] = "no_enb"
        return None, diag
    g_embb, n_embb = _embb_stream(res, ue_dirs, t0, diag)
    if g_embb is None:
        diag["skip"] = "no_embb"
        return None, diag
    g_urllc = _urllc_stream(ue_dirs, t0)
    if g_urllc is None:
        diag["skip"] = "no_urllc"
        return None, diag

    df = g_embb.join(g_urllc, how="inner")
    n_pre = len(df)
    df = df.join(nof.rename("nof_ue"), how="inner")  # no ffill/bfill: windows without eNB data are dropped
    diag["n_dropped_no_enb"] = n_pre - len(df)
    df.index.name = "win"
    df = df.reset_index()
    df["reward_embb_Mbps"] = df["embb_slice_bps"] / 1e6
    df["n_embb_ue"] = n_embb
    n0 = len(df)
    df = df.dropna(subset=[*WINDOW_BASE_COLS, "nof_ue", "urllc_frac_viol"])
    diag["n_dropped_nan"] = n0 - len(df)
    if not len(df):
        diag["skip"] = "empty_after_join"
        return None, diag
    df["reservation"] = pc["res"]
    df["cluster"] = pc["cluster"]
    df["slicing"], df["sched_raw"] = pc["slicing"], pc["sched"]
    df["prb_embb"] = C.PRB_EMBB[f"sl{pc['slicing']}"]
    df["sched"] = SCHED_BIN[pc["sched"]]
    df["action"] = PRB_LEVELS.index(int(df["prb_embb"].iloc[0])) * 2 + int(df["sched"].iloc[0])
    df = assign_episodes(df)
    return df, diag


def assemble(parts):
    """Concatenate reservations and apply split, lags, imputation, next_state, cost table."""
    df = pd.concat(parts, ignore_index=True).sort_values(["reservation", "win"]).reset_index(drop=True)
    df["split"] = np.where(df["cluster"].isin(TEST_CLUSTERS), "test", "train")
    df = add_lags(df)
    medians = fit_lag_medians(df[df["split"] == "train"])
    df = impute_lags(df, medians)
    df = add_next_state(df)
    df["load_bin"] = load_bin(df["nof_ue"]).astype(int)
    df["ns_load_bin"] = load_bin(df["ns_nof_ue"])
    table = fit_cost_table(df[df["split"] == "train"])
    df["cost_hat"] = lookup_cost(df, table)
    df["ns_cost_hat"] = np.where(df["done"], np.nan,
                                 lookup_cost(df.assign(_b=df["ns_load_bin"].fillna(0).astype(int)), table, "_b"))
    return df, medians, table


def git_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/dataset_canonical.parquet")
    ap.add_argument("--sample", type=int, default=None, help="stratified sample of reservations (debug)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    resv = C.sample_reservations(C.list_reservations(), a.sample, a.seed)
    with ProcessPoolExecutor(a.workers) as ex:
        results = list(ex.map(build_reservation, resv, chunksize=4))
    parts = [d for d, _ in results if d is not None]
    diags = [g for _, g in results]
    df, medians, table = assemble(parts)

    skips = pd.Series([g["skip"] or "ok" for g in diags]).value_counts(dropna=False).to_dict()
    offs = np.array([o for g in diags for o in g.get("embb_ue_t0_offsets_s", [])])
    n_above = int((df["nof_ue"] > LOAD_EDGES[-1]).sum())
    meta = {
        "script": "src/build_dataset.py", "git_commit": git_hash(), "seed": a.seed, "sample": a.sample,
        "dataset_version": C.dataset_version(), "window_s": WINDOW_S, "sla_ms": SLA_MS,
        "state_cols": STATE_COLS, "load_edges": LOAD_EDGES, "min_cell_n": MIN_CELL_N,
        "lag_medians_train": medians.to_dict(),
        "n_reservation_dirs": len(resv), "skip_reasons": {str(k): int(v) for k, v in skips.items()},
        "n_windows_dropped_no_enb": int(sum(g["n_dropped_no_enb"] for g in diags)),
        "n_windows_dropped_nan": int(sum(g["n_dropped_nan"] for g in diags)),
        "n_embb_ue_unaligned": int(sum(g["n_embb_unaligned"] for g in diags)),
        "embb_ue_t0_offset_s_quantiles(min,p5,p50,p95,max)":
            [float(x) for x in np.percentile(offs, [0, 5, 50, 95, 100])] if len(offs) else None,
        "n_rows_nof_ue_above_last_edge_clipped": n_above,
        "n_rows_lag_imputed": int(df["lag_imputed"].sum()),
        "counts": count_report(df),
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    df.to_parquet(a.out, index=False)
    table.to_csv(os.path.join(os.path.dirname(a.out), "cost_table.csv"), index=False)
    with open(a.out.replace(".parquet", ".meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
