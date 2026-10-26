"""Faithful re-implementation of notebook cell 21 (build_reservation) for audit purposes.

It reproduces the window logic *as in the notebook* (per-UE t0 for eMBB, first Received Time for URLLC,
first eNB row with nof_ue>0 for load) and additionally returns diagnostics about window coverage.
Read-only on the dataset. Nothing here is a training step.
"""
import os
import re

import numpy as np
import pandas as pd

from src.checks import common as C

WINDOW_S = 5.0
SLA_MS = 20.0
SCHED_BIN = {0: 0, 2: 1}
EMBB_IMSI = {"002", "003", "004", "005"}
URLLC_IMSI = {"006", "007", "008", "009"}
RADIO_COLS = ["rsrp", "dl_snr", "dl_mcs", "dl_bler", "ul_buff"]


def _imsi3(d):
    m = re.search(r"ue_0*(\d+)$", d)
    return m.group(1)[-3:] if m else None


def _safe(path, sep, **kw):
    try:
        if os.path.getsize(path) == 0:
            return None
        df = pd.read_csv(path, sep=sep, **kw)
    except Exception:
        return None
    if df.shape[1] <= 1:
        return None
    df.columns = [c.strip() for c in df.columns]
    return df


def build_reservation(res):
    """Returns (df or None, diag dict). df has the notebook columns + `win`."""
    pc = C.path_cfg(res)
    diag = {**pc, "built": False}
    if pc["slicing"] not in (1, 2, 3, 4) or pc["sched"] not in SCHED_BIN:
        diag["skip"] = "slicing_5_or_unknown"
        return None, diag
    ue_dirs = [d for d in C.ue_dirs(res) if os.path.isdir(d)]

    per_ue_win, radio_frames = [], []
    for d in ue_dirs:
        if _imsi3(d) in EMBB_IMSI:
            x = _safe(os.path.join(d, "ue_metrics.csv"), ";")
            if x is None or "time" not in x or "dl_brate" not in x:
                continue
            if "is_attached" in x:
                x = x[x["is_attached"] == 1]
            x["time"] = pd.to_numeric(x["time"], errors="coerce")
            x = x.dropna(subset=["time"])
            if len(x) == 0:
                continue
            x["win"] = ((x["time"] - x["time"].min()) / 1000.0 // WINDOW_S).astype(int)
            per_ue_win.append(x.groupby("win")["dl_brate"].mean())
            radio_frames.append(x)
    diag["n_embb_ue_used"] = len(per_ue_win)
    if not per_ue_win:
        diag["skip"] = "no_embb"
        return None, diag
    g_embb = pd.DataFrame({"embb_slice_bps": pd.concat(per_ue_win, axis=1).sum(axis=1)})
    radio = pd.concat(radio_frames, ignore_index=True)
    for c in RADIO_COLS:
        if c in radio.columns:
            g_embb[c] = radio.groupby("win")[c].mean()

    lat_frames, n_urllc = [], 0
    for d in ue_dirs:
        if _imsi3(d) in URLLC_IMSI:
            m = _safe(os.path.join(d, "mgen.csv"), ",", usecols=["Received Time", "Sent Time"])
            if m is None:
                continue
            t = m[["Received Time", "Sent Time"]].copy()
            t["lat"] = (t["Received Time"] - t["Sent Time"]) * 1000.0
            t = t[(t["lat"] >= 0) & (t["lat"] < 20000)]
            if len(t):
                lat_frames.append(t)
                n_urllc += 1
    diag["n_urllc_ue_used"] = n_urllc
    if not lat_frames:
        diag["skip"] = "no_urllc"
        return None, diag
    urllc = pd.concat(lat_frames, ignore_index=True)
    urllc["win"] = ((urllc["Received Time"] - urllc["Received Time"].min()) // WINDOW_S).astype(int)
    g_urllc = urllc.groupby("win")["lat"].agg(
        urllc_frac_viol=lambda s: (s > SLA_MS).mean(),
        urllc_p99=lambda s: np.percentile(s, 99),
        urllc_p50="median", urllc_mean="mean", n_pkts="size",
    )

    enb = _safe(os.path.join(res, "bs", "enb_metrics.csv"), ",")
    nof = None
    if enb is not None and "time" in enb and "nof_ue" in enb:
        enb["time"] = pd.to_numeric(enb["time"], errors="coerce")
        enb = enb.dropna(subset=["time"])
        enb = enb[enb["nof_ue"] > 0]
        if len(enb):
            enb["win"] = ((enb["time"] - enb["time"].min()) / 1000.0 // WINDOW_S).astype(int)
            nof = enb.groupby("win")["nof_ue"].mean()

    def cover(idx):
        idx = np.asarray(sorted(idx))
        return {"n": int(len(idx)), "min": int(idx.min()), "max": int(idx.max()),
                "n_missing_inside": int(idx.max() - idx.min() + 1 - len(idx))} if len(idx) else None

    diag["cov_embb"], diag["cov_urllc"] = cover(g_embb.index), cover(g_urllc.index)
    diag["cov_enb"] = cover(nof.index) if nof is not None else None

    df = g_embb.join(g_urllc, how="inner")
    diag["cov_joined"] = cover(df.index)
    if nof is not None:
        df = df.join(nof.rename("nof_ue"), how="left")
        diag["n_nof_ue_filled"] = int(df["nof_ue"].isna().sum())  # rows that ffill/bfill will invent
        df["nof_ue"] = df["nof_ue"].ffill().bfill()
    else:
        df["nof_ue"] = np.nan
        diag["n_nof_ue_filled"] = len(df)
    df = df.reset_index().rename(columns={"index": "win"})
    if "win" not in df:
        df = df.rename(columns={df.columns[0]: "win"})
    df["reward_embb_Mbps"] = df["embb_slice_bps"] / 1e6
    df["cluster"], df["reservation"] = pc["cluster"], pc["res"]
    df["slicing"], df["sched_raw"] = pc["slicing"], pc["sched"]
    df["prb_embb"] = C.PRB_EMBB[f"sl{pc['slicing']}"]
    df["sched"] = SCHED_BIN[pc["sched"]]
    df["action"] = {9: 0, 21: 1, 30: 2, 39: 3}[int(df["prb_embb"].iloc[0])] * 2 + int(df["sched"].iloc[0]) if len(df) else -1
    diag["built"], diag["n_rows"] = len(df) > 0, len(df)
    return df, diag
