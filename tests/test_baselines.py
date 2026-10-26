"""Tests of src/baselines.py, src/common.py (split, z-score) and evaluate_policy on synthetic data."""
import numpy as np
import pandas as pd

from src import baselines as BL
from src import common as CM
from src.build_dataset import STATE_COLS
from src.evaluate import evaluate_policy


def synth(n_res=20, n_win=10, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_res):
        a = i % 8
        for w in range(n_win):
            rows.append({"reservation": f"R{i}", "action": a, "load_bin": w % 3,
                         "reward_embb_Mbps": float(a + rng.normal(0, 0.1)),
                         "urllc_frac_viol": 0.01 if a % 2 == 0 else 0.10,
                         **{c: rng.normal() for c in STATE_COLS}})
    return pd.DataFrame(rows)


def test_always_rr_even_same_prb():
    a = np.arange(8)
    out = BL.always_rr(a)
    assert (out % 2 == 0).all()
    assert (out // 2 == a // 2).all()


def test_always_pf_odd_same_prb():
    a = np.arange(8)
    out = BL.always_pf(a)
    assert (out % 2 == 1).all()
    assert (out // 2 == a // 2).all()


def test_best_fixed_respects_cost_cap():
    df = synth()
    a, info = BL.best_fixed(df, budget=0.03)
    assert info["feasible"] and a == 6  # highest-reward action among the even (cost 0.01) ones
    assert info["val_cost"][a] <= 0.03


def test_best_fixed_infeasible_fallback():
    df = synth()
    df["urllc_frac_viol"] = 0.5 + 0.01 * df["action"]
    a, info = BL.best_fixed(df, budget=0.03)
    assert not info["feasible"] and a == 0


def test_table_greedy_and_fallback():
    r = np.arange(24, dtype=float).reshape(8, 3)  # reward grows with the action index
    c = np.full((8, 3), 0.01)
    c[7:, 0] = 0.5   # bin 0: action 7 unsafe -> best safe is 6
    c[:, 2] = 0.2    # bin 2: nothing feasible -> argmin cost
    c[3, 2] = 0.1
    m, feas = BL.table_greedy_map(r, c, 0.03)
    assert m.tolist() == [6, 7, 3] and feas.tolist() == [True, True, False]
    assert BL.table_greedy([2, 0, 1], r, c, 0.03).tolist() == [3, 6, 7]


def test_split_val_by_reservation_and_deterministic():
    df = synth(n_res=40)
    sub, val = CM.split_val(df, 0.2, 0)
    assert set(sub["reservation"]).isdisjoint(set(val["reservation"]))
    assert val["reservation"].nunique() == 8 and len(sub) + len(val) == len(df)
    sub2, val2 = CM.split_val(df, 0.2, 0)
    assert val["reservation"].tolist() == val2["reservation"].tolist()


def test_zscore_fitted_on_train_only():
    tr, te = synth(seed=1), synth(seed=2)
    te[STATE_COLS] = te[STATE_COLS] + 100.0
    zs = CM.fit_zscore(tr)
    assert np.allclose(CM.apply_zscore(tr[STATE_COLS], zs).mean(0), 0, atol=1e-9)
    assert CM.apply_zscore(te[STATE_COLS], zs).mean() > 50  # test is not re-centred


def test_evaluate_policy_logged_is_fully_matched():
    df = synth()
    r_tbl = df.groupby(["action", "load_bin"])["reward_embb_Mbps"].mean().unstack().to_numpy()
    c_tbl = np.where(np.arange(8)[:, None] % 2 == 0, 0.01, 0.10) * np.ones((8, 3))
    boot = np.random.default_rng(0).integers(0, df["reservation"].nunique(), size=(50, df["reservation"].nunique()))
    m = evaluate_policy(df, df["action"].to_numpy(), r_tbl, c_tbl, 0.03, boot)
    assert m["matched_coverage"] == 1.0
    assert np.isclose(m["matched_reward_mean"], df["reward_embb_Mbps"].mean())
    assert np.isclose(m["dm_cost_mean"], m["matched_cost_mean"])
    assert np.isclose(m["dm_pct_safe"], 0.5)  # even actions safe, odd unsafe
    assert m["dm_cost_ci_lo"] <= m["dm_cost_mean"] <= m["dm_cost_ci_hi"]
