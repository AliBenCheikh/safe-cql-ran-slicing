"""D1: does the configuration vary inside a reservation? Uses per-row config columns of bs/<IMSI>_metrics.csv."""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from src.checks import common as C


def check_reservation(res):
    """Config is recorded per row and per slice (slice 0 = eMBB, slice 1 = URLLC), so
    'varies' means: (i) >1 distinct config tuple inside one UE file (time variation), or
    (ii) the same slice_id with different slice_prb / scheduler across UE files."""
    pc = C.path_cfg(res)
    out = {**pc, "n_files": 0, "n_rows": 0}
    per_slice, scheds, enabled, powers, within_file = {}, set(), set(), set(), 0
    for f in C.bs_files(res):
        d = pd.read_csv(f, usecols=lambda c: c in C.CFG_COLS)
        out["n_files"] += 1
        out["n_rows"] += len(d)
        within_file += int(len(d.drop_duplicates()) > 1)
        for sid, g in d.groupby("slice_id"):
            per_slice.setdefault(int(sid), set()).update(g["slice_prb"].unique().tolist())
        scheds.update(d["scheduling_policy"].unique().tolist())
        enabled.update(d["slicing_enabled"].unique().tolist())
        powers.update(d["power_multiplier"].unique().tolist())
    if not out["n_files"]:
        out["no_bs_files"] = True
        return out
    out["n_files_time_varying"] = within_file
    out["slice_prb"] = {k: sorted(v) for k, v in sorted(per_slice.items())}
    out["sched_values"] = sorted(scheds)
    out["slicing_enabled"] = sorted(enabled)
    out["power_values"] = sorted(powers)
    cross = any(len(v) > 1 for v in per_slice.values()) or len(scheds) > 1 or len(enabled) > 1 or len(powers) > 1
    out["varies"] = bool(within_file or cross)
    out["no_embb_ue"] = 0 not in per_slice
    exp = C.PRB_EMBB.get(f"sl{pc['slicing']}")
    embb = per_slice.get(0, set())
    out["path_mismatch"] = bool(
        sorted(scheds) != [pc["sched"]] or (exp is not None and embb and sorted(embb) != [exp])
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="results/d1.json")
    a = ap.parse_args()
    resv = C.sample_reservations(C.list_reservations(), a.sample, a.seed)
    with ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(check_reservation, resv, chunksize=4))
    df = pd.DataFrame(rows)
    summ = {
        "n_reservations": len(df),
        "n_varying": int(df.get("varies", pd.Series(dtype=bool)).fillna(False).sum()),
        "n_path_mismatch": int(df.get("path_mismatch", pd.Series(dtype=bool)).fillna(False).sum()),
        "n_no_embb_ue": int(df.get("no_embb_ue", pd.Series(dtype=bool)).fillna(False).sum()),
        "n_no_bs": int(df.get("no_bs_files", pd.Series(dtype=bool)).fillna(False).sum()),
        "n_with_time_varying_file": int((df.get("n_files_time_varying", pd.Series(dtype=float)).fillna(0) > 0).sum()),
        "slice_prb_by_slicing": {f"sl{k}": g["slice_prb"].astype(str).value_counts().to_dict() for k, g in df.groupby("slicing")},
        "sched_values_by_sched": {f"sc{k}": g["sched_values"].astype(str).value_counts().to_dict() for k, g in df.groupby("sched")},
        "power_values": df["power_values"].astype(str).value_counts().to_dict(),
        "seed": a.seed, "sample": a.sample,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    df.to_json(a.out.replace(".json", "_rows.json"), orient="records")
    json.dump(summ, open(a.out, "w"), indent=1, default=str)
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
