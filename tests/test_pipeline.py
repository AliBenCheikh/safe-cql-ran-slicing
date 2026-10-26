"""Tests of src/build_dataset.py on synthetic data in tmp_path. Never reads ./data."""
import numpy as np
import pandas as pd

from src import build_dataset as B

T0 = 1_700_000_000_000  # epoch ms of the first eNB row with nof_ue > 0


def make_res(root, name="RESERVATION-1", cluster=2, slicing=2, sched=0, ue_starts=(0, 20_000),
             skip_windows=(), n_s=120):
    """Two eMBB UEs whose loggers start at different absolute times (ue_starts, ms after T0),
    one URLLC UE whose packets start 10 s after T0. skip_windows: URLLC windows (relative to
    the first packet) without packets."""
    res = root / f"cluster_{cluster}/slicing_{slicing}/scheduling_{sched}/{name}"
    (res / "bs").mkdir(parents=True)
    t = np.arange(0, n_s * 1000, 250)
    pd.DataFrame({"time": T0 + t, "nof_ue": 4, "dl_brate": 0.0, "ul_brate": 0.0}).to_csv(res / "bs/enb_metrics.csv", index=False)
    for i, start in enumerate(ue_starts):
        imsi = f"101012345600{2 + i}"
        # UE logger clock starts at `start`; BS file first row is 500 ms after the first attach
        ut = np.arange(0, (n_s - 5) * 1000 - start, 250)
        pd.DataFrame({"Timestamp": T0 + start + 500 + ut}).to_csv(res / f"bs/{imsi}_metrics.csv", index=False)
        ue = res / f"ue_00{imsi}"
        ue.mkdir()
        pd.DataFrame({"time": ut + 500, "is_attached": 1, "dl_brate": 1e6 * (i + 1), "rsrp": -60.0,
                      "dl_snr": 20.0, "dl_mcs": 10.0, "dl_bler": 0.0, "ul_buff": 0.0}).to_csv(
            ue / "ue_metrics.csv", sep=";", index=False)
    ur = res / "ue_001010123456006"
    ur.mkdir()
    rt = np.arange(0, n_s - 15, 0.05)
    rt = rt[np.array([int(x // 5) not in skip_windows for x in rt])]
    sod = (T0 / 1000) % 86400 + 10
    pd.DataFrame({"Received Time": sod + rt + 0.005, "Sent Time": sod + rt}).to_csv(ur / "mgen.csv", index=False)
    return str(res)


def synthetic_parts():
    """Hand-made reservations, no I/O: reward = window index, one gap in the first one."""
    def mk(name, cluster, wins, action=0):
        d = pd.DataFrame({"win": wins})
        d["reward_embb_Mbps"] = d["win"] * 1.0 + 100 * (cluster == 1)
        d["urllc_p50"] = d["win"] * 0.5 + 100 * (cluster == 1)
        d["urllc_frac_viol"] = 0.1
        d["nof_ue"] = 4.0
        for c in B.RADIO_COLS:
            d[c] = 1.0
        d["reservation"], d["cluster"], d["action"] = name, cluster, action
        d["prb_embb"], d["sched"] = 9, 0
        return B.assign_episodes(d)
    return [mk("RESERVATION-A", 2, [0, 1, 2, 3, 10, 11, 12]), mk("RESERVATION-B", 3, [0, 1, 2]),
            mk("RESERVATION-C", 1, [0, 1, 2, 3])]


def test_state_has_no_current_reward_or_cost():
    forbidden = {"reward_embb_Mbps", "urllc_p50", "urllc_frac_viol", "urllc_p99", "urllc_mean", "n_pkts"}
    assert not forbidden & set(B.STATE_COLS)
    assert set(B.LAG_COLS) <= set(B.STATE_COLS)
    assert len(B.STATE_COLS) == 10


def test_lags_use_only_past_windows_and_stay_in_episode():
    df, _, _ = B.assemble(synthetic_parts())
    a = df[df["reservation"] == "RESERVATION-A"].sort_values("win")
    # inside an episode lag1(t) is the reward of window t-1, lag2(t) of t-2
    ep0 = a[a["episode_idx"] == 0]
    assert ep0["reward_embb_Mbps_lag1"].iloc[1:].tolist() == ep0["reward_embb_Mbps"].iloc[:-1].tolist()
    assert ep0["reward_embb_Mbps_lag2"].iloc[2:].tolist() == ep0["reward_embb_Mbps"].iloc[:-2].tolist()
    # first window of the second episode (win 10) must not inherit win 3 (reward 3.0)
    first2 = a[a["win"] == 10].iloc[0]
    assert first2["lag_imputed"]
    assert first2["reward_embb_Mbps_lag1"] != 3.0 and first2["reward_embb_Mbps_lag2"] != 2.0


def test_imputation_uses_train_only_and_no_bfill():
    df, med, _ = B.assemble(synthetic_parts())
    train = df[df["split"] == "train"]
    obs = train[B.LAG_COLS].where(~train["lag_imputed"])  # imputed rows are not an independent sample
    raw = B.add_lags(pd.concat(synthetic_parts()[:2], ignore_index=True))
    assert np.isclose(med["reward_embb_Mbps_lag1"], raw["reward_embb_Mbps_lag1"].median())
    assert med["reward_embb_Mbps_lag1"] < 50  # the test cluster (rewards ~100) did not leak in
    # no bfill: a first-window lag equals the train median, not the next window's value
    c = df[(df["reservation"] == "RESERVATION-C") & (df["win"] == 0)].iloc[0]
    assert c["reward_embb_Mbps_lag1"] == med["reward_embb_Mbps_lag1"]
    assert obs.shape == train[B.LAG_COLS].shape


def test_episode_boundaries():
    df, _, _ = B.assemble(synthetic_parts())
    a = df[df["reservation"] == "RESERVATION-A"]
    assert sorted(a["episode_id"].unique()) == ["RESERVATION-A_0", "RESERVATION-A_1"]
    for _, ep in df.groupby("episode_id"):
        assert (ep["win"].diff().dropna() == 1).all()  # contiguous inside an episode


def test_next_state_nan_at_episode_end_and_equals_next_row_elsewhere():
    df, _, _ = B.assemble(synthetic_parts())
    for _, ep in df.groupby("episode_id"):
        ep = ep.sort_values("win")
        assert ep[B.NS_COLS].iloc[-1].isna().all()
        assert ep["done"].iloc[-1] and not ep["done"].iloc[:-1].any()
        np.testing.assert_allclose(ep[B.NS_COLS].iloc[:-1].to_numpy(), ep[B.STATE_COLS].iloc[1:].to_numpy())
    # the last window before the gap (win 3) does not point at win 10
    row = df[(df["reservation"] == "RESERVATION-A") & (df["win"] == 3)].iloc[0]
    assert row["done"] and np.isnan(row["ns_nof_ue"])


def test_counts_are_consistent():
    df, _, _ = B.assemble(synthetic_parts())
    rep = B.count_report(df)
    assert rep["train"] == {"n_reservations": 2, "n_episodes": 3, "n_rows": 10, "n_transitions": 7}
    assert rep["test"] == {"n_reservations": 1, "n_episodes": 1, "n_rows": 4, "n_transitions": 3}
    for r in rep.values():
        assert r["n_transitions"] == r["n_rows"] - r["n_episodes"]


def test_cost_table_fitted_on_train_only_with_three_bins():
    parts = synthetic_parts()
    parts[2]["urllc_frac_viol"] = 0.9  # test cluster: must not influence the table
    df, _, table = B.assemble(parts)
    assert B.LOAD_EDGES == [0, 3.5, 5.5, 8.1]
    assert set(table["load_bin"]) <= {0, 1, 2}
    assert np.allclose(table["cost_mean"], 0.1)
    assert df["load_bin"].tolist() == [1] * len(df)  # nof_ue = 4 -> (3.5, 5.5]


def test_load_bin_edges():
    assert B.load_bin([1, 3.5, 3.6, 5.5, 5.6, 8.1, 9.0]).tolist() == [0, 0, 1, 1, 2, 2, 2]


def test_common_origin_aligns_shifted_ue_clocks(tmp_path):
    res = make_res(tmp_path, ue_starts=(0, 20_000))
    df, diag = B.build_reservation(res)
    assert diag["skip"] is None and df["n_embb_ue"].iloc[0] == 2
    # both eMBB UEs contribute from the same first window (the eNB origin), not 4 windows apart
    assert df["win"].min() == 2  # URLLC traffic starts 10 s = 2 windows after t0
    assert df["win"].is_monotonic_increasing and (df["win"].diff().dropna() == 1).all()
    # UE 2 logs from t0+20 s: it adds its 2 Mbps from window 4 on, not from its own first window
    r = df.set_index("win")["reward_embb_Mbps"]
    assert np.allclose(r[r.index < 4], 1.0) and np.allclose(r[r.index >= 4], 3.0)
    offs = diag["embb_ue_t0_offsets_s"]
    assert np.allclose(sorted(offs), [0.25 + 0.0, 20.25 + 0.0], atol=0.6)


def test_gap_in_urllc_splits_reservation_into_two_episodes(tmp_path):
    res = make_res(tmp_path, skip_windows=(4, 5))
    df, diag = B.build_reservation(res)
    assert df["episode_id"].nunique() == 2
    assert df["episode_id"].iloc[0] == "RESERVATION-1_0"
    assert set(df["episode_idx"]) == {0, 1}
    full, _, _ = B.assemble([df])
    ends = full.groupby("episode_id").tail(1)
    assert ends[B.NS_COLS].isna().all().all()
