"""D3: is the window index contiguous after the notebook's joins? Also builds results/windows/*.parquet for D4/D5."""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from src.checks import common as C
from src.checks import windows as W

OUTDIR = "results/windows"


def run_one(res):
    df, diag = W.build_reservation(res)
    if df is not None and len(df):
        os.makedirs(OUTDIR, exist_ok=True)
        df.to_parquet(os.path.join(OUTDIR, f"{diag['cluster']}_{diag['slicing']}_{diag['sched']}_{diag['res']}.parquet"), index=False)
        w = np.sort(df["win"].to_numpy())
        step = np.diff(w)
        diag["n_gaps"] = int((step > 1).sum())
        diag["gap_sizes"] = (step[step > 1] - 1).tolist()
        diag["n_missing_inside"] = int((step[step > 1] - 1).sum())
        diag["first_win"], diag["last_win"] = int(w[0]), int(w[-1])
        # rows whose next/lag-1/lag-2 row (as built in cell 22 via shift on rows) is NOT window t+1/t-1/t-2
        diag["n_next_not_consecutive"] = int((step != 1).sum())
        diag["n_lag2_not_consecutive"] = int((w[2:] - w[:-2] != 2).sum()) if len(w) > 2 else 0
        diag["n_first_windows_missing_lead"] = int(w[0])
    return diag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="results/d3.json")
    a = ap.parse_args()
    resv = C.sample_reservations([r for r in C.list_reservations() if C.path_cfg(r)["slicing"] != 5], a.sample, a.seed)
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(run_one, resv, chunksize=2))
    df = pd.DataFrame(rows)
    ok = df[df["built"] == True]  # noqa: E712
    gaps = ok["n_gaps"] > 0
    allgaps = [g for gs in ok["gap_sizes"] for g in gs]
    def cnt(col):
        return int(ok[col].map(lambda c: bool(c) and c["n_missing_inside"] > 0).sum())
    summ = {
        "n_reservations_considered": len(df), "n_built": len(ok), "n_skipped": int((df["built"] != True).sum()),  # noqa: E712
        "skip_reasons": df["skip"].value_counts(dropna=True).to_dict() if "skip" in df else {},
        "n_res_with_gap_after_join": int(gaps.sum()),
        "pct_res_with_gap": round(100 * gaps.mean(), 1),
        "gap_run_length_windows": {"n_gaps": len(allgaps), "median": float(np.median(allgaps)) if allgaps else None,
                                   "p90": float(np.percentile(allgaps, 90)) if allgaps else None, "max": int(max(allgaps)) if allgaps else None},
        "rows_total": int(ok["n_rows"].sum()),
        "rows_whose_next_row_is_not_t_plus_1": int(ok["n_next_not_consecutive"].sum()),
        "rows_whose_lag2_is_not_t_minus_2": int(ok["n_lag2_not_consecutive"].sum()),
        "n_res_gap_in_embb_stream": cnt("cov_embb"), "n_res_gap_in_urllc_stream": cnt("cov_urllc"),
        "n_res_gap_in_enb_stream": cnt("cov_enb"),
        "n_res_first_joined_win_gt0": int((ok["first_win"] > 0).sum()),
        "rows_with_nof_ue_filled_by_ffill_bfill": int(ok["n_nof_ue_filled"].sum()),
        "n_res_with_embb_ue_less_than_4": int((ok["n_embb_ue_used"] < 4).sum()),
        "by_cluster_res_with_gap": {f"cl{k}": [int(g.n_gaps.gt(0).sum()), len(g)] for k, g in ok.groupby("cluster")},
        "seed": a.seed, "sample": a.sample,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    df.to_json(a.out.replace(".json", "_rows.json"), orient="records")
    json.dump(summ, open(a.out, "w"), indent=1, default=str)
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
