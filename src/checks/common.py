"""Shared helpers for Phase-0 checks. Read-only on the dataset."""
import glob
import hashlib
import os
import re

import numpy as np

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PRB_EMBB = {"sl1": 9, "sl2": 21, "sl3": 30, "sl4": 39}  # as in notebook cell 21
CFG_COLS = ["slicing_enabled", "slice_id", "slice_prb", "power_multiplier", "scheduling_policy"]
_PATH_RE = re.compile(r"cluster_(\d+)/slicing_(\d+)/scheduling_(\d+)/(RESERVATION-[^/]+)")


def list_reservations(data=DATA):
    """Sorted list of reservation directories (no file content is read)."""
    return sorted(glob.glob(os.path.join(data, "cluster_*", "slicing_*", "scheduling_*", "RESERVATION-*")))


def path_cfg(res):
    m = _PATH_RE.search(res.replace(os.sep, "/"))
    cl, sl, sc, name = m.groups()
    return {"cluster": int(cl), "slicing": int(sl), "sched": int(sc), "res": name}


def bs_files(res):
    """Per-UE base-station metric files (excludes enb_metrics.csv)."""
    return sorted(f for f in glob.glob(os.path.join(res, "bs", "*_metrics.csv")) if not f.endswith("enb_metrics.csv"))


def ue_dirs(res):
    return sorted(glob.glob(os.path.join(res, "ue_*")))


def sample_reservations(resv, n, seed=0):
    """Stratified (cluster, slicing, sched) sample, deterministic for a seed."""
    if n is None or n >= len(resv):
        return list(resv)
    rng = np.random.default_rng(seed)
    strata = {}
    for r in resv:
        c = path_cfg(r)
        strata.setdefault((c["cluster"], c["slicing"], c["sched"]), []).append(r)
    keys = sorted(strata)
    out, i = [], 0
    pools = {k: list(rng.permutation(strata[k])) for k in keys}
    while len(out) < n and any(pools.values()):
        k = keys[i % len(keys)]
        if pools[k]:
            out.append(pools[k].pop())
        i += 1
    return sorted(out)


def dataset_version(data=DATA):
    """Short hash of the sorted (relative path, size) listing; cheap, content-free."""
    h = hashlib.sha256()
    root = os.path.realpath(data)
    for dp, _, fs in sorted(os.walk(root)):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            h.update(f"{os.path.relpath(p, root)}:{os.path.getsize(p)}\n".encode())
    return h.hexdigest()[:16]


def first_last_lines(path, n_tail=1, block=4096):
    """Header, first data line and last line(s) of a text file without reading it all."""
    with open(path, "rb") as f:
        header = f.readline().decode().rstrip("\n")
        first = f.readline().decode().rstrip("\n")
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - block))
        tail = f.read().decode(errors="ignore").splitlines()
    return header, first, tail[-n_tail:]


def safe_read_csv(path, problems=None, **kw):
    """read_csv that returns None (and logs the file) for missing, empty or unparsable files."""
    import pandas as pd
    try:
        d = pd.read_csv(path, **kw)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as e:
        if problems is not None:
            problems.append(f"{os.path.basename(path)}: {type(e).__name__}")
        return None
    if len(d) == 0:
        if problems is not None:
            problems.append(f"{os.path.basename(path)}: no rows")
        return None
    return d
