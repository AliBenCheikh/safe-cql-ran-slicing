"""E13c: do the E13b timestamp anomalies affect the usable TRAIN reservations? READ-ONLY, timestamp columns only.
Scope: the 510 usable reservations of the TRAIN split (clusters 2-3). The 196 usable reservations of the test split
(cluster 1) are NOT read, so the answer covers 510 of the 706 usable reservations.

Flags (thresholds fixed before the read, from the E13b values):
  sent_gap     max successive step of `Sent Time` > 60 s in some URLLC mgen file   (E13b: 31 507 s)
  recv_gap     same for `Received Time` (comparison; E13b max 2.3 s)
  bs_gap       max step > 10 s (40x the 0.25 s step) in some bs/<IMSI>_metrics file
  bs_files_lt8 fewer than 8 bs/<IMSI>_metrics files
  dur_ratio    median over UE files of duration(ue_metrics)/duration(enb) outside [0.9, 1.1]
  urllc_empty  at least one of the 4 URLLC mgen files has no row

    python -m src.e13c_anomalies --out results/e13c_anomalies.csv
"""
import argparse
from multiprocessing import Pool
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.e13b_sampling_check import SCHED_DIR, read_reservation, res_path

SENT_GAP_S, BS_GAP_S, RATIO = 60.0, 10.0, (0.9, 1.1)


def _max_step(files):
    m = [np.diff(np.sort(f[np.isfinite(f)])).max() for f in files if np.isfinite(f).sum() > 1]
    return float(max(m)) if m else np.nan


def flags(streams):
    """streams: output of `read_reservation`. Returns the flag dict of one reservation."""
    enb = streams["enb"][0] if streams["enb"] else np.array([])
    d_enb = np.ptp(enb[np.isfinite(enb)]) if np.isfinite(enb).sum() > 1 else np.nan
    d_ue = [np.ptp(f[np.isfinite(f)]) for f in streams["ue_metrics"] if np.isfinite(f).sum() > 1]
    ratio = float(np.median(d_ue) / d_enb) if d_ue and d_enb > 0 else np.nan
    sent, recv, bs = _max_step(streams["mgen_sent"]), _max_step(streams["mgen_recv"]), _max_step(streams["bs_ue"])
    return {"sent_max_step": sent, "recv_max_step": recv, "bs_max_step": bs, "n_bs_files": len(streams["bs_ue"]),
            "n_urllc_files": len(streams["mgen_recv"]), "n_urllc_empty": int(sum(np.isfinite(f).sum() == 0 for f in streams["mgen_recv"])),
            "dur_ratio": ratio, "sent_gap": bool(sent > SENT_GAP_S), "recv_gap": bool(recv > SENT_GAP_S), "bs_gap": bool(bs > BS_GAP_S),
            "bs_files_lt8": bool(len(streams["bs_ue"]) < 8), "dur_ratio_out": bool(not (RATIO[0] <= ratio <= RATIO[1])) if ratio == ratio else True,
            "urllc_empty": bool(sum(np.isfinite(f).sum() == 0 for f in streams["mgen_recv"]) > 0)}


def _one(rec):
    row = SimpleNamespace(**rec)
    try:
        s, errs = read_reservation(res_path(row))
        return {"reservation": row.reservation, "cluster": row.cluster, "sched": row.sched, "slicing": row.slicing, **flags(s), "errors": len(errs)}
    except Exception as e:
        return {"reservation": row.reservation, "cluster": row.cluster, "sched": row.sched, "slicing": row.slicing, "errors": -1, "exc": repr(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/e13c_anomalies.csv")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    usable = pd.read_parquet("results/dataset_canonical.parquet", columns=["reservation", "split"], filters=[("split", "==", "train")])
    t = pd.read_csv("results/d8_times.csv")
    t = t[t["reservation"].isin(set(usable["reservation"])) & t["cluster"].isin([2, 3])]
    assert len(t) == 510 and (t["split"] == "train").all(), len(t)
    with Pool(a.workers) as p:
        rows = list(p.imap_unordered(_one, t.to_dict('records'), chunksize=4))
    pd.DataFrame(rows).sort_values("reservation").to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
