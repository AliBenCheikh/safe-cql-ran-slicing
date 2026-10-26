"""Tests on a synthetic reservation in tmp_path. Never reads ./data."""
import numpy as np
import pandas as pd
import pytest

from src.checks import common as C
from src.checks import d1_config_variation as D1
from src.checks import d2_clock_alignment as D2
from src.checks import d5_cost_cells as D5
from src.checks import windows as W

T0 = 1_700_000_000_000  # epoch ms


def make_res(root, prb=21, sched=0, skip_windows=(), prb_change_at=None, slicing=2):
    res = root / f"cluster_1/slicing_{slicing}/scheduling_{sched}/RESERVATION-1"
    (res / "bs").mkdir(parents=True)
    n_s = 60
    t = np.arange(0, n_s * 1000, 250)
    pd.DataFrame({"time": T0 + t, "nof_ue": 4, "dl_brate": 0.0, "ul_brate": 0.0}).to_csv(res / "bs/enb_metrics.csv", index=False)
    cfg = np.where((t >= prb_change_at) if prb_change_at else np.zeros(len(t), bool), prb + 5, prb)
    pd.DataFrame({"Timestamp": T0 + 500 + t, "slice_id": 0, "slice_prb": cfg, "slicing_enabled": 1,
                  "power_multiplier": 1, "scheduling_policy": sched}).to_csv(res / "bs/1010123456002_metrics.csv", index=False)
    ue = res / "ue_001010123456002"
    ue.mkdir()
    pd.DataFrame({"time": t + 250, "is_attached": 1, "dl_brate": 1e6, "rsrp": -60.0, "dl_snr": 20.0,
                  "dl_mcs": 10.0, "dl_bler": 0.0, "ul_buff": 0.0}).to_csv(ue / "ue_metrics.csv", sep=";", index=False)
    ur = res / "ue_001010123456006"
    ur.mkdir()
    rt = np.arange(0, n_s, 0.05)
    keep = np.array([int(x // 5) not in skip_windows for x in rt])
    rt = rt[keep]
    sod = (T0 / 1000) % 86400 + 10  # seconds of day (UTC) of the first packet, 10 s after eNB start
    pd.DataFrame({"Timestamp_recv": "00:00:00.0", "Timestamp_send": "00:00:00.0", "Received Time": sod + rt + 0.005,
                  "Sent Time": sod + rt}).to_csv(ur / "mgen.csv", index=False)
    return str(res)


def test_d1_constant_config(tmp_path):
    o = D1.check_reservation(make_res(tmp_path))
    assert not o["varies"] and not o["path_mismatch"]


def test_d1_detects_time_variation_and_path_mismatch(tmp_path):
    o = D1.check_reservation(make_res(tmp_path, prb_change_at=30000))
    assert o["varies"] and o["n_files_time_varying"] == 1 and o["path_mismatch"]


def test_d3_window_gap_detected(tmp_path):
    df, diag = W.build_reservation(make_res(tmp_path, skip_windows={4, 5}))
    assert diag["cov_joined"]["n_missing_inside"] == 2
    assert df["win"].is_monotonic_increasing and (np.diff(df["win"]) > 1).any()


def test_d3_contiguous(tmp_path):
    df, diag = W.build_reservation(make_res(tmp_path))
    assert diag["cov_joined"]["n_missing_inside"] == 0 and diag["n_nof_ue_filled"] == 0
    assert diag["built"] and (df["action"] == 2).all()  # prb 21 -> idx1, sched 0 -> 2


def test_d2_offsets(tmp_path):
    o = D2.check_reservation(make_res(tmp_path))
    assert o["bs_first_min"] - o["enb_first"] == 500
    assert o["n_mgen"] == 1 and o["mgen_tz_hours"] == 0
    assert abs(o["mgen_first_resid_s"] - 10.0) < 0.1


def test_d5_bootstrap_deterministic_and_wider_than_naive():
    rng = np.random.default_rng(1)
    res = np.repeat(np.arange(10), 50)
    x = np.repeat(rng.uniform(0, 0.2, 10), 50)  # strong reservation effect
    a = D5.res_boot(x, res, 500, np.random.default_rng(0))
    b = D5.res_boot(x, res, 500, np.random.default_rng(0))
    assert a == b
    naive = 2 * 1.96 * x.std(ddof=1) / np.sqrt(len(x))
    assert (a[1] - a[0]) > naive


def test_sampling_is_deterministic_and_stratified():
    fake = [f"/d/cluster_{c}/slicing_{s}/scheduling_{m}/RESERVATION-{i}" for c in (1, 2) for s in (1, 2) for m in (0, 2) for i in range(5)]
    a, b = C.sample_reservations(fake, 8, 3), C.sample_reservations(fake, 8, 3)
    assert a == b and len({C.path_cfg(r)["slicing"] for r in a}) == 2
