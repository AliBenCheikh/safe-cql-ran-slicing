"""D7 tests on synthetic frames. Never reads ./data nor ./results."""
import numpy as np
import pandas as pd
import pytest

from src.checks import d7_scheduler_order as D7


def _w(specs, n_win=20, start=0, noise=0.0, seed=0):
    """specs: list of dict(res, md5, slicing, sched, reward, cost, [nof_ue, n_pkts, start, n_win]).
    prb_embb = 9 + 12*(slicing-1) is only a label; action = 2*(slicing-1) + sched."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in specs:
        st, nw = s.get("start", start), s.get("n_win", n_win)
        for i in range(nw):
            sb = st + i
            rows.append({"md5": s["md5"], "reservation": s["res"], "slicing": s["slicing"], "sched": s["sched"],
                         "prb_embb": 9 + 12 * (s["slicing"] - 1), "action": 2 * (s["slicing"] - 1) + s["sched"],
                         "win": i, "sbin": sb, "ws_s": 5.0 * sb, "reward_embb_Mbps": s["reward"] + noise * rng.normal(),
                         "urllc_frac_viol": s["cost"], "nof_ue": s.get("nof_ue", 4.0) + noise * rng.normal(),
                         "n_pkts": s.get("n_pkts", 100)})
    return pd.DataFrame(rows)


def test_res_id():
    assert D7.res_id("RESERVATION-142703") == 142703


def test_target_scripts_needs_all_8_actions():
    full = pd.DataFrame({"md5": ["a"] * 8 + ["b"] * 7, "action": list(range(8)) + list(range(7))})
    assert D7.target_scripts(full) == ["a"]


def test_segment_same_vs_different():
    same = _w([dict(res=f"RESERVATION-{i}", md5="h", slicing=1, sched=i % 2, reward=1, cost=0) for i in range(4)])
    seg = D7.segment_report(D7.reservation_coverage(same))["h"]
    assert seg["same_segment"] and seg["overlap_ratio"] == 1.0 and seg["intersection_s"] == 100.0
    # one reservation starts 15 bins later and is only 5 bins long inside: union 35 bins, intersection 0
    diff = _w([dict(res="RESERVATION-1", md5="h", slicing=1, sched=0, reward=1, cost=0),
               dict(res="RESERVATION-2", md5="h", slicing=1, sched=1, reward=1, cost=0, start=30, n_win=5)])
    seg = D7.segment_report(D7.reservation_coverage(diff))["h"]
    assert not seg["same_segment"] and seg["intersection_s"] == 0.0


def test_coverage_fill_detects_missing_windows():
    w = _w([dict(res="RESERVATION-1", md5="h", slicing=1, sched=0, reward=1, cost=0)])
    w = w[w["win"] != 5]
    c = D7.reservation_coverage(w).iloc[0]
    assert c.fill == pytest.approx(19 / 20) and c.n_win == 19 and c.end_s == 100.0


def test_pair_effect_uses_common_bins_only():
    # reward = ramp in script bin + 2 for PF; RR covers bins 0..19, PF bins 5..24: a window-index comparison would be biased
    a = _w([dict(res="RESERVATION-1", md5="h", slicing=1, sched=0, reward=0, cost=0.1)])
    a["reward_embb_Mbps"] = 10.0 * a["sbin"]
    b = _w([dict(res="RESERVATION-2", md5="h", slicing=1, sched=1, reward=0, cost=0.0, start=5)])
    b["reward_embb_Mbps"] = 10.0 * b["sbin"] + 2.0
    e = D7.pair_effect(a, b)
    assert e["diff_reward"] == pytest.approx(2.0) and e["n_bins"] == 15 and e["diff_cost"] == pytest.approx(-0.1)
    assert np.isnan(e["se_reward"])  # one repetition per side


def test_consistency_sign_and_order_of_magnitude():
    eff = pd.DataFrame({"md5": ["a", "b", "c"] * 2, "slicing": [1] * 3 + [2] * 3,
                        "diff_reward": [1.0, 2.0, 3.0, 1.0, -2.0, 3.0], "se_reward": [0.1] * 6,
                        "diff_cost": [0.01, 0.5, 0.02, 0.01, 0.02, 0.03], "se_cost": [0.1] * 6})
    c = D7.consistency(eff).set_index(["slicing", "metric"])
    assert c.loc[(1, "reward"), "coherent"]
    assert not c.loc[(2, "reward"), "same_sign"] and not c.loc[(2, "reward"), "coherent"]
    assert c.loc[(1, "cost"), "same_sign"] and not c.loc[(1, "cost"), "same_order"]  # 0.5 / 0.01 = 50x
    assert c.loc[(1, "reward"), "n_distinguishable"] == 3 and c.loc[(1, "cost"), "n_distinguishable"] == 1
    assert ("mean", "reward") in c.index


def _blocks(early_rr, late_rr, early_pf, late_pf):
    """Scheduler run by blocks (ids 1-4 RR, 5-8 PF) with a level per half."""
    specs = []
    for i, lvl in enumerate([early_rr] * 2 + [late_rr] * 2):
        specs.append(dict(res=f"RESERVATION-{1 + i}", md5="h", slicing=1, sched=0, reward=lvl, cost=0))
    for i, lvl in enumerate([early_pf] * 2 + [late_pf] * 2):
        specs.append(dict(res=f"RESERVATION-{5 + i}", md5="h", slicing=1, sched=1, reward=lvl, cost=0))
    return _w(specs)


def test_order_blocks_and_sign_flip_when_time_drift_exceeds_effect():
    # no true scheduler effect (PF == RR at equal time) but a drift of -10 between early and late halves
    w = _blocks(10, 0, 10, 0)
    rng, combos, drift = D7.order_confusion(w)
    r = rng.iloc[0]
    assert r.n_switches == 1 and not r.id_ranges_overlap and r.n_RR == 4 and r.n_PF == 4
    assert len(combos) == 4
    v = D7.order_verdict(combos).set_index("metric")
    assert v.loc["reward", "sign_depends_on_order"] and v.loc["reward", "n_pos"] == 1 and v.loc["reward", "n_neg"] == 1
    # cost is constant: all four differences are exactly 0 -> no sign
    assert not v.loc["cost", "sign_depends_on_order"]
    d = drift.set_index("sched")
    assert d.loc["RR", "diff_reward"] == pytest.approx(-10.0) and d.loc["PF", "diff_reward"] == pytest.approx(-10.0)


def test_order_sign_stable_when_true_effect_dominates_drift():
    w = _blocks(10, 9, 15, 14)
    _, combos, _ = D7.order_confusion(w)
    v = D7.order_verdict(combos).set_index("metric")
    assert v.loc["reward", "n_pos"] == 4 and not v.loc["reward", "sign_depends_on_order"]


def test_order_detects_interleaved_schedulers():
    specs = [dict(res=f"RESERVATION-{i}", md5="h", slicing=1, sched=i % 2, reward=1, cost=0) for i in range(1, 9)]
    rng, _, _ = D7.order_confusion(_w(specs))
    assert rng.iloc[0].n_switches == 7 and rng.iloc[0].id_ranges_overlap


def test_order_single_reservation_scheduler_is_not_evaluable():
    specs = [dict(res="RESERVATION-1", md5="h", slicing=1, sched=0, reward=1, cost=0),
             dict(res="RESERVATION-2", md5="h", slicing=1, sched=1, reward=1, cost=0),
             dict(res="RESERVATION-3", md5="h", slicing=1, sched=1, reward=1, cost=0)]
    _, combos, drift = D7.order_confusion(_w(specs))
    assert combos.empty and list(drift["sched"]) == ["PF"]


def _exo_frame(action_effect_nof, n_res_per_action=4, seed=1):
    specs = []
    for a in range(D7.N_ACTIONS):
        for k in range(n_res_per_action):
            specs.append(dict(res=f"RESERVATION-{a * 100 + k}", md5="h", slicing=a // 2 + 1, sched=a % 2, reward=1.0, cost=0.0,
                              nof_ue=4.0 + action_effect_nof * a))
    w = _w(specs, noise=0.3, seed=seed)
    w["reward_embb_Mbps"] = 2.0 * w["action"] + np.random.default_rng(seed).normal(0, 0.3, len(w))
    # shared load shape over script time (must be absorbed by the bin fixed effect)
    w["nof_ue"] += np.sin(w["sbin"] / 3.0)
    return w


def _all(ex):
    return ex[ex["subset"] == "all"].set_index("variable")


def test_exogeneity_subsets_within_one_scheduler():
    ex = D7.exogeneity(_exo_frame(0.5))
    assert set(ex["subset"]) == {"all", "RR only", "PF only"}
    rr = ex[(ex.subset == "RR only") & (ex.variable == "nof_ue")].iloc[0]
    assert rr.n_res == 16 and rr.p_perm < 0.01  # slicing-driven load survives inside one scheduler


def test_segment_core_ignores_outlier_reservations():
    specs = [dict(res=f"RESERVATION-{i}", md5="h", slicing=1, sched=i % 2, reward=1, cost=0) for i in range(1, 9)]
    specs.append(dict(res="RESERVATION-9", md5="h", slicing=1, sched=0, reward=1, cost=0, start=200, n_win=3))
    seg = D7.segment_report(D7.reservation_coverage(_w(specs)))["h"]
    assert not seg["same_segment"] and seg["n_outside_core"] == 1 and seg["core_overlap_ratio"] == 1.0


def test_exogeneity_null_and_positive_control():
    ex = _all(D7.exogeneity(_exo_frame(0.0)))
    assert ex.loc["nof_ue", "p_perm"] > 0.01 and ex.loc["nof_ue", "eta2"] < 0.5  # null E[eta2] = 7/31 with 32 reservations in 8 groups
    assert ex.loc["embb_rate_Mbps (control)", "p_perm"] < 0.01 and ex.loc["embb_rate_Mbps (control)", "eta2"] > 0.9
    assert np.isnan(ex.loc["urllc_rx_pps", "eta2"])  # constant n_pkts: no variance to explain


def test_exogeneity_detects_action_dependent_load():
    ex = _all(D7.exogeneity(_exo_frame(0.5)))
    assert ex.loc["nof_ue", "p_perm"] < 0.01 and ex.loc["nof_ue", "eta2"] > 0.5
    assert ex.loc["nof_ue", "dev_by_action"][7] > ex.loc["nof_ue", "dev_by_action"][0]


def test_repetitions_counts_distinct_reservations():
    u = pd.DataFrame({"md5": ["h"] * 6, "slicing": [1, 1, 1, 1, 2, 2], "sched": [0, 0, 0, 1, 0, 0],
                      "reservation": ["a", "a", "b", "c", "d", "e"]})
    acc = u[u.reservation != "b"]
    r = D7.repetitions(u, acc).set_index(["slicing", "sched"])
    assert r.loc[(1, 0), "n_usable"] == 2 and r.loc[(1, 0), "n_origin_ok"] == 1
    assert r.loc[(1, 1), "n_usable"] == 1 and r.loc[(2, 0), "n_usable"] == 2
