"""D8 tests on synthetic frames / files in tmp_path. Never reads ./data nor ./results."""
import numpy as np
import pandas as pd
import pytest

from src.checks import d8_chronology as D8

T0 = 1_708_463_000_000  # 2024-02-20 21:23:20 UTC
H_MS = 3_600_000
D_MS = 24 * H_MS


def _tab(specs):
    """specs: dict(res, md5, slicing, sched, t0 [ms], [cluster], [dur_ms])."""
    rows = []
    for s in specs:
        rows.append({"reservation": f"RESERVATION-{s['res']}", "rid": s["res"], "md5": s.get("md5", "h"), "cluster": s.get("cluster", 1),
                     "slicing": s["slicing"], "sched": s["sched"], "t0_ms": float(s["t0"]), "enb_last_ms": float(s["t0"] + s.get("dur_ms", 1_800_000))})
    return D8.add_utc(pd.DataFrame(rows))


# ---------------------------------------------------------------- 1. times
def _write_enb(tmp, name, rows, cfg=("cluster_1", "slicing_1", "scheduling_0")):
    d = tmp / cfg[0] / cfg[1] / cfg[2] / name / "bs"
    d.mkdir(parents=True)
    (d / "enb_metrics.csv").write_text("time,nof_ue,dl_brate,ul_brate\n" + "".join(f"{t},{n},0.0,0.0\n" for t, n in rows))
    return str(d.parent)


def test_reservation_times_uses_first_active_row(tmp_path):
    res = _write_enb(tmp_path, "RESERVATION-7", [(T0, 0), (T0 + 250, 0), (T0 + 500, 3), (T0 + 750, 4)])
    r = D8.reservation_times(res)
    assert r["enb_first_ms"] == T0 and r["enb_last_ms"] == T0 + 750 and r["t0_ms"] == T0 + 500 and r["res"] == "RESERVATION-7"
    assert r["cluster"] == 1 and r["sched"] == 0 and r["problem"] is None


def test_reservation_times_never_active_and_missing(tmp_path):
    res = _write_enb(tmp_path, "RESERVATION-8", [(T0, 0), (T0 + 250, 0)])
    r = D8.reservation_times(res)
    assert r["t0_ms"] is None and r["enb_first_ms"] == T0 and "never" in r["problem"]
    miss = tmp_path / "cluster_1" / "slicing_1" / "scheduling_0" / "RESERVATION-9"
    (miss / "bs").mkdir(parents=True)
    assert D8.reservation_times(str(miss))["problem"] is not None


def test_add_utc():
    d = D8.add_utc(pd.DataFrame({"t0_ms": [1_708_463_141_661.0]}))
    assert d["date_utc"][0] == "2024-02-20" and d["hour_utc"][0] == pytest.approx(21 + 5 / 60)
    assert str(d["start_utc"][0].tz) == "UTC"


# ---------------------------------------------------------------- 2. order
def test_order_monotone_and_inverted():
    good = _tab([dict(res=i, slicing=1, sched=0, t0=T0 + i * H_MS) for i in range(1, 8)])
    o, inv = D8.order_check(good)
    a = o[o.level == "all"].iloc[0]
    assert a.monotone and a.n_adjacent_inversions == 0 and a.spearman == pytest.approx(1.0) and a.kendall == pytest.approx(1.0) and inv.empty
    bad = _tab([dict(res=i, slicing=1, sched=0, t0=T0 + i * H_MS) for i in range(1, 8)])
    bad.loc[bad.rid == 5, "t0_ms"] = T0 + 2 * H_MS + 1  # reservation 5 started before 4
    o, inv = D8.order_check(D8.add_utc(bad))
    a = o[o.level == "all"].iloc[0]
    assert not a.monotone and a.n_adjacent_inversions == 1 and a.spearman < 1.0
    inv = inv[inv.level == "all"]
    assert list(inv.res) == ["RESERVATION-5"] and inv.backward_h.iloc[0] == pytest.approx(2.0, abs=0.01)


def test_order_ignores_missing_t0_and_per_script_rows():
    t = _tab([dict(res=i, slicing=1, sched=0, t0=T0 + i * H_MS, md5="a" if i < 5 else "b") for i in range(1, 9)])
    t.loc[0, "t0_ms"] = np.nan
    o, _ = D8.order_check(t)
    assert o[o.level == "all"].iloc[0].n == 7 and set(o[o.level == "script"].key) == {"a", "b"}


# ---------------------------------------------------------------- 3. separation
def test_classify_gap():
    assert D8.classify_gap(3 * 3600) == "heures" and D8.classify_gap(2 * 86400) == "jours" and D8.classify_gap(9 * 86400) == "semaines"
    assert D8.classify_gap(np.nan) is None


@pytest.mark.parametrize("gap_ms,cls", [(5 * H_MS, "heures"), (3 * D_MS, "jours"), (10 * D_MS, "semaines")])
def test_separation_two_blocks_gap_class(gap_ms, cls):
    pf = [dict(res=i, slicing=1, sched=1, t0=T0 + i * H_MS) for i in range(1, 5)]
    last = T0 + 4 * H_MS + 1_800_000
    rr = [dict(res=10 + i, slicing=1, sched=0, t0=last + gap_ms + i * H_MS) for i in range(4)]
    s = D8.separation(_tab(pf + rr)).iloc[0]
    assert s.n_switches == 1 and s.gap_class == cls and s.first_block == "PF" and s.min_misplaced == 0
    assert s.gap_h == pytest.approx(gap_ms / H_MS, abs=1e-6)


def test_separation_interleaved_and_strays():
    inter = _tab([dict(res=i, slicing=2, sched=i % 2, t0=T0 + i * H_MS) for i in range(8)])
    s = D8.separation(inter).iloc[0]
    assert s.gap_class == "entrelacées" and s.n_switches == 7 and s.min_misplaced == 3
    # two blocks with one stray RR inside the PF block
    seq = [1, 1, 0, 1, 1, 0, 0, 0]
    stray = D8.separation(_tab([dict(res=i, slicing=1, sched=sc, t0=T0 + i * H_MS) for i, sc in enumerate(seq)])).iloc[0]
    assert stray.n_switches == 3 and stray.min_misplaced == 1 and stray.gap_class == "entrelacées"


def test_separation_skips_single_scheduler():
    assert D8.separation(_tab([dict(res=i, slicing=1, sched=0, t0=T0 + i * H_MS) for i in range(4)])).empty


# ---------------------------------------------------------------- 4. nearest pairs
def test_greedy_pairs_nearest_first_one_to_one():
    pairs = D8.greedy_pairs([0, 10, 100], [1, 12, 50, 99])
    assert pairs == [(0, 0, 1.0), (2, 3, 1.0), (1, 1, 2.0)]
    assert D8.greedy_pairs([], [1]) == []
    p = D8.greedy_pairs([0, 0], [5])           # more PF than RR: one pair only, lowest index wins ties
    assert p == [(0, 0, 5.0)]


def _windows(specs, n_win=10, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for s in specs:
        for i in range(n_win):
            rows.append({"md5": s.get("md5", "h"), "reservation": f"RESERVATION-{s['res']}", "slicing": s["slicing"], "sched": s["sched"],
                         "sbin": i, "reward_embb_Mbps": s["reward"] + noise * rng.normal(), "urllc_frac_viol": s["cost"] + noise * rng.normal()})
    return pd.DataFrame(rows)


def _scenario(pf_cost_by_time):
    """6 PF + 6 RR reservations interleaved in time; cost = base + drift*time + PF effect given by pf_cost_by_time(res)."""
    specs, tabs = [], []
    for i in range(12):
        sched = i % 2
        specs.append(dict(res=i, slicing=1, sched=sched, reward=5.0, cost=pf_cost_by_time(i, sched)))
        tabs.append(dict(res=i, slicing=1, sched=sched, t0=T0 + i * H_MS))
    return _windows(specs), _tab(tabs)


def test_nearest_pair_effect_recovers_constant_effect_and_gaps():
    w, tab = _scenario(lambda i, s: 0.10 + 0.15 * s)
    near = D8.nearest_pair_effects(w, tab)
    assert list(near.frac) == [1.0, 0.5]
    full = near[near.frac == 1.0].iloc[0]
    assert full.n_pairs == 6 and full.diff_cost == pytest.approx(0.15) and full.diff_reward == pytest.approx(0.0)
    half = near[near.frac == 0.5].iloc[0]
    assert half.n_pairs == 3 and half.gap_max_h <= full.gap_max_h and half.diff_cost == pytest.approx(0.15)
    assert not (near.frac == 0.25).any()  # round(0.25*6)=2 pairs < MIN_PAIRS: not evaluated


def test_nearest_pairs_remove_a_time_drift_that_confounds_blocks():
    # PF block early, RR block late; the cost drifts upward in time (+0.01/h), true scheduler effect = +0.05
    specs, tabs = [], []
    for i in range(10):
        sched = 1 if i < 5 else 0
        t_h = i if i < 5 else 20 + i
        specs.append(dict(res=i, slicing=1, sched=sched, reward=1.0, cost=0.01 * t_h + 0.05 * sched))
        tabs.append(dict(res=i, slicing=1, sched=sched, t0=T0 + t_h * H_MS))
    w, tab = _windows(specs), _tab(tabs)
    near = D8.nearest_pair_effects(w, tab, fracs=(1.0, 0.6))
    ref = pd.DataFrame([{"md5": "h", "slicing": 1, "diff_cost": -0.05, "diff_reward": 0.0}])  # all-pairs: drift swamps the effect
    cmp_ = D8.compare_with_reference(near, ref)
    full, close = cmp_[cmp_.frac == 1.0].iloc[0], cmp_[cmp_.frac == 0.6].iloc[0]
    assert close.gap_max_h < full.gap_max_h
    assert close.diff_cost > full.diff_cost  # nearer pairs carry less of the drift...
    assert close.diff_cost < 0.05            # ...but with disjoint blocks the nearest pairs still carry some (true effect 0.05)


def test_compare_with_reference_sign_and_order():
    near = pd.DataFrame([{"md5": "h", "slicing": 1, "frac": 0.5, "diff_cost": 0.10, "se_cost": 0.01, "diff_reward": -1.0, "se_reward": 2.0,
                          "gap_median_h": 1.0, "gap_max_h": 2.0}])
    ref = pd.DataFrame([{"md5": "h", "slicing": 1, "diff_cost": 0.05, "diff_reward": 0.5}])
    c = D8.compare_with_reference(near, ref).iloc[0]
    assert c.same_sign_cost and c.same_order_cost and c.ratio_cost == pytest.approx(2.0) and c.distinguishable_cost
    assert not c.same_sign_reward and not c.distinguishable_reward
    ref.loc[0, "diff_cost"] = 0.001  # ratio 100 -> not the same order
    assert not D8.compare_with_reference(near, ref).iloc[0].same_order_cost


# ---------------------------------------------------------------- 5. drift
def test_best_split_finds_step_not_trend():
    rng = np.random.default_rng(1)
    step = np.concatenate([rng.normal(0, 0.05, 30), rng.normal(0.5, 0.05, 30)])
    r = D8.best_split(step, n_perm=200)
    assert r["k"] == 30 and r["step"] == pytest.approx(0.5, abs=0.05) and r["p_perm"] < 0.01 and r["sse_ratio"] > 1
    trend = np.linspace(0, 1, 60) + rng.normal(0, 0.02, 60)
    r2 = D8.best_split(trend, n_perm=200)
    assert r2["sse_ratio"] < 1  # a linear trend fits better than one step


def test_best_split_flat_series_and_short():
    rng = np.random.default_rng(2)
    r = D8.best_split(rng.normal(0, 1, 50), n_perm=200)
    assert r["p_perm"] > 0.01
    assert D8.best_split(np.arange(6.0), min_seg=5) is None


def _drift_frame(values, scheds=None, dt_h=1.0, md5="h"):
    n = len(values)
    scheds = scheds if scheds is not None else [0] * n
    df = pd.DataFrame({"md5": md5, "reservation": [f"RESERVATION-{i}" for i in range(n)], "slicing": 1, "sched": scheds,
                       "t0_ms": [T0 + i * dt_h * H_MS for i in range(n)], "value": values})
    df = D8.add_utc(df)
    return D8.add_residuals(df)


def test_residuals_remove_cell_means_only():
    v = _drift_frame([0.0, 0.0, 1.0, 1.0], scheds=[0, 0, 1, 1])
    assert v.resid_cell.abs().max() == 0.0          # a step aligned with the scheduler blocks is absorbed
    assert v.resid_slicing.tolist() == [-0.5, -0.5, 0.5, 0.5]  # and kept by the slicing-only residual


def test_drift_breaks_flags_sched_aligned_step():
    vals = [0.1] * 20 + [0.3] * 20
    v = _drift_frame(vals, scheds=[1] * 20 + [0] * 20)
    br = D8.drift_breaks(v, n_perm=200)
    b = br[br.kind == "resid_slicing"].iloc[0]
    assert b.k == 20 and b.flag_split and b.step_is_sched_switch and b.step == pytest.approx(0.2)
    assert b.split_utc == v.sort_values("t0_ms").iloc[20].start_utc


def test_daily_jumps_flags_day_change_and_ignores_small_days():
    # 24 h per day with 6 reservations every 4 h
    vals = list(np.random.default_rng(3).normal(0.1, 0.01, 12)) + list(np.random.default_rng(4).normal(0.4, 0.01, 12))
    v = _drift_frame(vals, dt_h=4.0)
    j = D8.daily_jumps(v)
    assert len(j) >= 1 and j.flag.any() and j.loc[j.flag, "jump"].iloc[0] == pytest.approx(0.3, abs=0.1)
    flat = _drift_frame(list(np.random.default_rng(5).normal(0.1, 0.01, 24)), dt_h=4.0)
    assert not D8.daily_jumps(flat).flag.any()
    tiny = _drift_frame([0.1, 0.9], dt_h=24.0)
    assert D8.daily_jumps(tiny).empty


def test_common_segment_values_uses_same_bins_for_everyone():
    rows = []
    for r, (lo, hi) in {"A": (0, 20), "B": (0, 20), "C": (0, 20), "D": (0, 20), "E": (10, 20)}.items():
        for b in range(lo, hi):
            rows.append({"md5": "h", "reservation": r, "sbin": b, "urllc_frac_viol": 1.0 if b < 10 else 0.0})
    v = D8.common_segment_values(pd.DataFrame(rows), "urllc_frac_viol")
    # bins 10-19 are covered by 5/5, bins 0-9 by 4/5 = 0.8 -> all 20 bins kept; E covers 10/20 = 0.5 < 0.9 -> dropped
    assert set(v.reservation) == {"A", "B", "C", "D"} and v.n_bins_segment.iloc[0] == 20 and v.value.iloc[0] == pytest.approx(0.5)
