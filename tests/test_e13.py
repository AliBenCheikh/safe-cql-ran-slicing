"""E13a: edges, binning, cell stats, no leakage of the validation fold into the edges, no test read, reproduction guard.
Synthetic data except `test_reproduction_guard` (real TRAIN parquet, train split only)."""
import inspect
import os

import numpy as np
import pandas as pd
import pytest

import src.e13_load_levels as e13
from src.build_dataset import LOAD_EDGES, load_bin
from src.common import PARQUET


def test_quantile_edges_and_ties():
    x = np.arange(1, 101, dtype=float)
    assert len(e13.quantile_edges(x, 4)) == 3 and len(e13.quantile_edges(x, 2)) == 1
    tied = np.array([1.0] * 90 + [2.0] * 10)
    assert len(e13.quantile_edges(tied, 5)) < 4          # duplicates merged, realised k reported, nothing substituted


def test_assign_bins_right_closed_open_ends():
    e = np.array([3.5, 5.5])
    assert e13.assign_bins([0.1, 3.5, 3.51, 5.5, 5.51, 99.0], e).tolist() == [0, 0, 1, 1, 2, 2]


def test_current_edges_equal_pipeline_load_bin():
    x = np.random.default_rng(0).uniform(0.2, 9.0, 2000)
    x = np.concatenate([x, [3.5, 5.5, 8.1, 8.5]])
    got = e13.assign_bins(x, LOAD_EDGES[1:-1])
    assert np.array_equal(got, load_bin(x).to_numpy(int))


def synth(n_res=16, per_res=30, seed=0, offset=0, shift=0.0):
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(n_res):
        for _ in range(per_res):
            rows.append({"reservation": f"r{offset + r}", "action": r % 8, "nof_ue": float(rng.uniform(1, 8)) + shift,
                         "reward_embb_Mbps": float(rng.normal(8, 2)), "urllc_frac_viol": float(rng.uniform(0, 0.1))})
    return pd.DataFrame(rows)


def test_edges_use_source_only():
    a, b = synth(seed=1), synth(seed=2, offset=100, shift=50.0)    # validation load is wildly different
    ea = e13.edge_sets(a["nof_ue"])
    eb_changed = e13.edge_sets(pd.concat([a, b])["nof_ue"])
    assert not np.allclose(ea["k3"], eb_changed["k3"][: len(ea["k3"])])
    for k in (2, 3, 4, 5):
        assert np.allclose(ea[f"k{k}"], e13.quantile_edges(a["nof_ue"], k))     # edges depend on the source frame alone


def test_cells_counts_and_ci():
    a = synth(seed=3)
    a["bin"] = e13.assign_bins(a["nof_ue"], e13.quantile_edges(a["nof_ue"], 3))
    Sc, Sr, N = e13.res_sums(a, 3)
    assert N.sum() == len(a) and Sc.shape == (16, 8, 3)
    cells = e13.cell_stats(Sc, N, np.random.default_rng(0), boot=200)
    assert (cells["n_res"] == 2).all()                               # 2 reservations per action in this synthetic fold
    s = e13.side_summary(cells)
    assert s["n_cells_without_ci"] == 0 and s["n_cells_with_ci"] == 24
    one = e13.cell_stats(Sc[:1], N[:1], np.random.default_rng(0), boot=50)
    assert one["ci_has_d"].isna().all() or all(v is None for v in one["ci_has_d"])   # < 2 reservations: no CI


def test_direction_runs_and_reports_every_k():
    scripts = {"A": synth(seed=5), "B": synth(seed=6, offset=100)}
    ((rec, _, _),) = e13.analyse_direction("A", "B", scripts, {"k3": e13.quantile_edges(scripts["A"]["nof_ue"], 3)}, 0, boot=20)
    assert rec["k_realised"] == 3 and len(rec["table_greedy_policy_by_level"]) == 3
    assert rec["transferred_boot"]["n_invalid"] <= 20
    assert set(e13.edge_sets(scripts["A"]["nof_ue"])) == {"k2", "k3", "k4", "k5", e13.REF}


def test_no_test_split_read():
    src = inspect.getsource(e13.load_scripts)
    assert '("split", "==", "train")' in src and "assert" in src


@pytest.mark.skipif(not os.path.exists(PARQUET), reason="canonical parquet absent")
def test_reproduction_guard():
    """Must pass BEFORE any other computation of this step (0.0520 / 0.0303 and the E11 oracles)."""
    ok, det = e13.reproduction_guard(e13.load_scripts())
    assert ok, det
