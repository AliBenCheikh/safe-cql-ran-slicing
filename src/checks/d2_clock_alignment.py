"""D2: compare start times of eNB metrics, per-UE BS/KPM, UE KPM and MGEN files in each reservation.

Clocks (verified on one reservation): enb_metrics.time and bs/<IMSI>_metrics.Timestamp are epoch ms;
ue_metrics.time is ms since the UE logger started (no absolute clock); mgen has wall-clock HH:MM:SS
(`Timestamp_recv`) and seconds-of-day (`Received Time`) in a local timezone that may differ from UTC.
Hence:
  * UE KPM absolute start is ESTIMATED as bs_first_ts(IMSI) - first_attached_ms(UE)   [hypothesis]
  * MGEN offset is computed modulo whole hours (timezone) and reported as tz_hours + residual.
"""
import argparse
import datetime as dt
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from src.checks import common as C


def _mgen_first_last(path):
    hdr, first, tail = C.first_last_lines(path)
    if not first or not tail or "," not in first:
        return None
    try:
        return float(first.split(",")[2]), float(tail[-1].split(",")[2])
    except (IndexError, ValueError):
        return None


def check_reservation(res):
    out = dict(C.path_cfg(res))
    problems = []
    out["problems"] = problems
    enb = C.safe_read_csv(os.path.join(res, "bs", "enb_metrics.csv"), problems, usecols=["time", "nof_ue"])
    if enb is None:
        return out
    enb_first, enb_last = int(enb.time.iloc[0]), int(enb.time.iloc[-1])
    act = enb.time[enb.nof_ue > 0]
    enb_act = int(act.iloc[0]) if len(act) else None
    out.update(enb_first=enb_first, enb_last=enb_last, enb_first_active=enb_act, enb_n=len(enb))
    # per-UE BS files (epoch ms)
    bs_first = {}
    for f in C.bs_files(res):
        imsi = os.path.basename(f).split("_")[0]
        d = C.safe_read_csv(f, problems, usecols=["Timestamp"])
        if d is None:
            continue
        ts = d.Timestamp
        bs_first[imsi] = (int(ts.iloc[0]), int(ts.iloc[-1]))
    out["n_bs"] = len(bs_first)
    if bs_first:
        f0 = [v[0] for v in bs_first.values()]
        out["bs_first_min"], out["bs_first_max"] = min(f0), max(f0)
        out["bs_last_max"] = max(v[1] for v in bs_first.values())
    # UE KPM + MGEN
    ue_abs, mg_first, mg_last, ue_len = [], [], [], []
    for u in C.ue_dirs(res):
        imsi = os.path.basename(u).replace("ue_00", "")
        m = C.safe_read_csv(os.path.join(u, "ue_metrics.csv"), problems, sep=";", usecols=["time", "is_attached"])
        if m is not None:
            ue_len.append(int(m.time.iloc[-1]))
            att = m.time[m.is_attached > 0]
            if len(att) and imsi in bs_first:
                ue_abs.append(bs_first[imsi][0] - int(att.iloc[0]))  # est. absolute t0 of ue_metrics
        mp = os.path.join(u, "mgen.csv")
        if os.path.exists(mp):
            r = _mgen_first_last(mp)
            if r:
                mg_first.append(r[0]); mg_last.append(r[1])
    out["n_ue"] = len(C.ue_dirs(res))
    out["ue_t0_est_min"] = min(ue_abs) if ue_abs else None
    out["ue_t0_est_max"] = max(ue_abs) if ue_abs else None
    out["n_mgen"] = len(mg_first)
    ref = enb_act or enb_first
    if mg_first:
        day0 = dt.datetime.fromtimestamp(ref / 1000, dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        cand = day0 + min(mg_first)
        # resolve day wrap and timezone in whole hours: choose the shift giving the smallest |diff|
        diff_s = cand - ref / 1000
        tz_h = int(round(diff_s / 3600.0))
        out["mgen_tz_hours"] = tz_h
        out["mgen_first_resid_s"] = diff_s - 3600 * tz_h   # includes the traffic start delay
        out["mgen_first_abs"] = (cand - 3600 * tz_h) * 1000
    return out


def q(x):
    x = pd.Series(x).dropna()
    if not len(x):
        return None
    return {k: float(np.round(v, 3)) for k, v in zip(["min", "p5", "p50", "p95", "max"], np.percentile(x, [0, 5, 50, 95, 100]))} | {"n": int(len(x))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="results/d2.json")
    a = ap.parse_args()
    resv = C.sample_reservations(C.list_reservations(), a.sample, a.seed)
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(check_reservation, resv, chunksize=4))
    df = pd.DataFrame(rows)
    summ = {
        "n_reservations": len(df), "seed": a.seed, "sample": a.sample,
        "bs_first_spread_across_UEs_s": q((df.bs_first_max - df.bs_first_min) / 1000),
        "bs_first_minus_enb_first_s": q((df.bs_first_min - df.enb_first) / 1000),
        "bs_first_minus_enb_first_active_s": q((df.bs_first_min - df.enb_first_active) / 1000),
        "ue_t0_est_minus_enb_first_s (hyp: attach-based)": q((df.ue_t0_est_min - df.enb_first) / 1000),
        "ue_t0_est_spread_across_UEs_s (hyp)": q((df.ue_t0_est_max - df.ue_t0_est_min) / 1000),
        "mgen_tz_hours_counts": df.mgen_tz_hours.value_counts(dropna=False).to_dict() if "mgen_tz_hours" in df else None,
        "mgen_first_minus_enb_first_active_resid_s (mod whole hours)": q(df.get("mgen_first_resid_s")),
        "enb_active_minus_first_s": q((df.enb_first_active - df.enb_first) / 1000),
        "n_res_with_unreadable_file": int((df.problems.map(len) > 0).sum()),
        "unreadable_files_sample": [p for ps in df.problems for p in ps][:10],
        "n_res_without_enb": int(df.enb_first.isna().sum()),
        "n_res_without_mgen": int((df.n_mgen == 0).sum()),
        "n_res_without_active_enb": int(df.enb_first_active.isna().sum()),
        "cluster_tz_hours": {f"cl{k}": g.mgen_tz_hours.value_counts().to_dict() for k, g in df.groupby("cluster")} if "mgen_tz_hours" in df else None,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    df.to_json(a.out.replace(".json", "_rows.json"), orient="records")
    json.dump(summ, open(a.out, "w"), indent=1, default=str)
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
