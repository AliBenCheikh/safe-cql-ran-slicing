"""D6 tests on synthetic frames / files in tmp_path. Never reads ./data."""
import numpy as np
import pandas as pd
import pytest

from src.checks import d6_shared_scripts as D6

T0 = 1_700_000_000_000  # epoch ms, 22:13:20 UTC
SCRIPT = "70 ON 2 UDP DST 172.16.0.3/5000 PERIODIC [100 1250]\n70 ON 6 UDP DST 172.16.0.7/5000 PERIODIC [10 125]\n\n130 OFF 6\n0.0 LISTEN UDP 5000\n"


def test_parse_script_and_first_on():
    ev = D6.parse_script(SCRIPT)
    assert [(e["t"], e["op"], e["flow"]) for e in ev] == [(70, "ON", 2), (70, "ON", 6), (130, "OFF", 6)]
    e = D6.first_on(ev, 6)
    assert e["rate"] == 10 and e["size"] == 125 and D6.first_on(ev, 7) is None


def _res(tmp, name, text, mgen_rows=None, t0=T0, extra=""):
    r = tmp / name
    (r / "bs").mkdir(parents=True)
    (r / "bs" / "mgen-script-scope.mgn").write_text(text + extra)
    return r


def test_md5_same_content_same_hash_different_content_differs(tmp_path):
    a, b, c = _res(tmp_path, "a", SCRIPT), _res(tmp_path, "b", SCRIPT), _res(tmp_path, "c", SCRIPT, extra="190 OFF 2\n")
    assert D6.script_md5(str(a)) == D6.script_md5(str(b)) != D6.script_md5(str(c))
    assert D6.script_md5(str(tmp_path / "nope")) is None


def test_sod_to_abs_handles_timezone_and_midnight_wrap():
    sod_utc = (T0 / 1000) % 86400
    assert D6.sod_to_abs_s(sod_utc + 10, T0) == pytest.approx(T0 / 1000 + 10)
    assert D6.sod_to_abs_s(sod_utc + 10 + 7200, T0) == pytest.approx(T0 / 1000 + 10)  # +2 h local clock
    t0_late = int(pd.Timestamp("2024-01-01 23:59:50", tz="UTC").timestamp() * 1000)
    sod_after_midnight = 5.0  # 15 s after t0, next day
    assert D6.sod_to_abs_s(sod_after_midnight, t0_late) == pytest.approx(t0_late / 1000 + 15)


def test_origin_from_first_packet_recovers_script_zero():
    origin = T0 / 1000 - 40.0  # script t=0 happened 40 s before t0
    t_on, rate, seq = 70.0, 10.0, 35
    sent_abs = origin + t_on + (seq - 1) / rate
    sod = sent_abs % 86400
    assert D6.origin_from_first_packet(sod, seq, rate, t_on, T0) == pytest.approx(origin)


def test_script_origin_reads_first_packet(tmp_path):
    origin = T0 / 1000 - 40.0
    r = _res(tmp_path, "r", SCRIPT)
    ue = r / "ue_001010123456006"
    ue.mkdir()
    sent = (origin + 70 + 3.4) % 86400
    pd.DataFrame({"Timestamp_recv": ["x"], "Timestamp_send": ["x"], "Received Time": [sent + 0.005], "Sent Time": [sent],
                  "Flow ID": [6], "Sequence No.": [35]}).to_csv(ue / "mgen.csv", index=False)
    o, d = D6.script_origin(str(r), T0)
    assert o == pytest.approx(origin, abs=1e-3) and d["origin_flows"] == 1 and d["origin_flow_gap_s"] == 0.0


def test_same_script_time_lands_in_same_bin_despite_different_t0():
    # Two reservations replay the same script; the second one starts 12.3 s later, so its window 0 is later in script time.
    w = pd.DataFrame({"win": np.arange(20)})
    t0a, oa = T0, T0 / 1000 - 40.0
    t0b = T0 + 12_300
    ob = oa + 12.3 + 5 * 3  # script origin of B is 15 s later than that of A relative to the same t0 shift: ws differs by 15 s
    a = D6.add_script_bins(w, t0a, oa)
    b = D6.add_script_bins(w, t0b, ob)
    # A: ws = 40 + 5*win ; B: ws = 40 + 5*win - 15 + 0 => sbin_B(win) == sbin_A(win-3)
    assert list(b["sbin"]) == [x - 3 for x in a["sbin"]]
    assert (a["sbin_resid"] < 1e-6).all()
    assert (b["sbin_resid"] < 1e-6).all() or (b["sbin_resid"] <= 0.5).all()


def test_sbin_residual_bounded_by_half_window():
    out = D6.add_script_bins(pd.DataFrame({"win": np.arange(50)}), T0, T0 / 1000 - 37.7)
    assert (out["sbin_resid"] <= 0.5 + 1e-9).all()


def _windows(spec, n_win=30, shift=None):
    """spec: list of (md5, cluster, reservation, action, reward_level, cost_level); `shift` = bins offset of win vs sbin."""
    rows = []
    for md5, cl, res, act, rw, co in spec:
        s = (shift or {}).get(res, 0)
        for i in range(n_win):
            rows.append({"md5": md5, "cluster": cl, "reservation": res, "action": act, "win": i, "sbin": i + s,
                         "reward_embb_Mbps": rw + (i % 3), "urllc_frac_viol": co})
    return pd.DataFrame(rows)


def test_noise_variance_across_repetitions():
    w = _windows([("h", 2, "r1", 0, 5.0, 0.01), ("h", 2, "r2", 0, 7.0, 0.03), ("h", 2, "r3", 1, 9.0, 0.0)])
    n = D6.noise(w)
    assert len(n) == 1  # action 1 has a single repetition
    r = n.iloc[0]
    assert r.n_rep == 2 and r.var_reward_raw == pytest.approx(2.0) and r.var_cost_raw == pytest.approx(0.0002)
    assert r.var_reward_bin == pytest.approx(2.0) and r.var_cost_bin == pytest.approx(0.0002) and r.n_bins_ge2 == 30


def test_noise_per_bin_survives_truncated_repetition():
    w = pd.concat([_windows([("h", 2, "r1", 0, 5.0, 0.0)], n_win=30), _windows([("h", 2, "r2", 0, 7.0, 0.0)], n_win=10)])
    r = D6.noise(w).iloc[0]
    assert r.n_bins_ge2 == 10 and r.var_reward_bin == pytest.approx(2.0)


def test_origin_ok_rules():
    assert D6.origin_ok(2, 0.0) and D6.origin_ok(2, 1.4) and not D6.origin_ok(2, 60.1)
    assert not D6.origin_ok(1, 0.0) and D6.origin_ok(1, 0.0, allow_single=True) and not D6.origin_ok(0, None, True)


def test_action_diff_is_aligned_on_script_time_not_on_window_index():
    # Reservation r2 is shifted by 3 bins relative to r1. Reward is a function of script bin only (same script,
    # exogenous load, here a ramp) plus an action effect of +2, so the aligned difference must be exactly +2.
    rows = []
    for res, act, shift in (("r1", 0, 0), ("r2", 1, 3)):
        for i in range(30):
            sbin = i + shift
            rows.append({"md5": "h", "cluster": 2, "reservation": res, "action": act, "win": i, "sbin": sbin,
                         "reward_embb_Mbps": 10 * sbin + 2 * act, "urllc_frac_viol": 0.0})
    d = D6.action_diffs(pd.DataFrame(rows)).iloc[0]
    assert d.diff_reward == pytest.approx(2.0)
    assert d.diff_reward_win == pytest.approx(32.0)  # window-index alignment confounds the 3-bin shift (10 per bin) with the action
    assert d.n_bins == 27 and d.n_bins_win == 30


def test_inventory_and_split_summary():
    res = pd.DataFrame({
        "res": ["a", "b", "c", "d", "e"], "md5": ["h1", "h1", "h1", "h2", "h1"], "cluster": [2, 2, 3, 1, 1],
        "slicing": [1, 2, 1, 1, 5], "sched": [0, 0, 2, 0, 0]})
    usable = {"a", "b", "d"}
    inv = D6.inventory(res, usable)
    row = inv[(inv.md5 == "h1") & (inv.cluster == 1)].iloc[0]
    assert row.n_res_all == 1 and row.n_res_usable == 0
    s = D6.script_summary(inv).set_index("md5")
    assert s.loc["h1", "n_res_all"] == 4 and s.loc["h1", "n_res_usable"] == 2 and s.loc["h1", "clusters"] == [1, 2, 3]
    sp = D6.split_summary(res, usable)
    assert sp["all"]["train"]["n_scripts"] == 1 and sp["all"]["test"]["n_scripts"] == 2
    assert sp["all"]["n_scripts_in_both"] == 1 and sp["all"]["n_test_res_with_train_script"] == 1
    assert sp["usable"]["train"]["n_reservations"] == 2 and sp["usable"]["n_scripts_in_both"] == 0
