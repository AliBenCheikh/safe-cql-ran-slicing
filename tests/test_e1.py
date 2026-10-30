"""E1 tests on synthetic tables / frames. Never read ./data nor ./results."""
import numpy as np
import pandas as pd
import pytest

from src import lp_diagnostic as E1
from src.build_dataset import fit_cost_table
from src.common import N_ACTIONS, N_BINS, reward_table


def _frame(seed=0, n_res=12, n_win=30):
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(n_res):
        a = r % N_ACTIONS
        for _ in range(n_win):
            rows.append({"reservation": f"RESERVATION-{r}", "split": "train", "action": a,
                         "load_bin": int(rng.integers(0, N_BINS)), "reward_embb_Mbps": float(rng.normal(5 + a, 1)),
                         "urllc_frac_viol": float(rng.random() * 0.1 * (a + 1))})
    return pd.DataFrame(rows)


def test_tables_match_pipeline_tables():
    df = _frame()
    Sc, Sr, N = E1.cell_sums(df)
    R, C, p, _ = E1.tables_from_sums(Sc.sum(0), Sr.sum(0), N.sum(0))
    np.testing.assert_allclose(R, reward_table(df))
    t = fit_cost_table(df)
    ref = np.full((N_ACTIONS, N_BINS), np.nan)
    ref[t["action"].to_numpy(int), t["load_bin"].to_numpy(int)] = t["cost_hat"].to_numpy()
    np.testing.assert_allclose(C, ref)
    np.testing.assert_allclose(p, df["load_bin"].value_counts(normalize=True).sort_index().to_numpy())


def test_lp_known_solution_randomises():
    R, C, p = np.array([[1.0], [3.0]]), np.array([[0.0], [0.1]]), np.array([1.0])
    lp = E1.solve_lp(R, C, p, 0.05)
    assert lp["reward"] == pytest.approx(2.0) and lp["cost"] == pytest.approx(0.05)
    np.testing.assert_allclose(lp["x"][:, 0], [0.5, 0.5])
    assert lp["mu_marginal"] == pytest.approx(20.0)           # (3-1)/(0.1-0)
    assert E1.value_slopes(R, C, p, 0.05) == pytest.approx((20.0, 20.0), rel=1e-3)


def test_lp_budget_not_binding_gives_zero_dual():
    R, C, p = np.array([[1.0], [3.0]]), np.array([[0.0], [0.1]]), np.array([1.0])
    lp = E1.solve_lp(R, C, p, 0.5)
    assert lp["reward"] == pytest.approx(3.0) and lp["mu_marginal"] == pytest.approx(0.0)


def test_lp_infeasible_reports_min_cost_without_changing_d():
    R, C, p = np.array([[1.0, 1.0], [3.0, 3.0]]), np.array([[0.2, 0.3], [0.5, 0.4]]), np.array([0.5, 0.5])
    rep, lp = E1.lp_report(R, C, p, 0.03, r_scale=1.0)
    assert not rep["feasible"] and rep["cost_min"] == pytest.approx(0.25) and "reward" not in rep
    assert rep["reward_at_min_cost"] == pytest.approx(1.0)


def test_lp_upper_bounds_best_deterministic():
    rng = np.random.default_rng(1)
    R, C = rng.random((4, 3)) * 10, rng.random((4, 3)) * 0.1
    p = np.array([0.2, 0.3, 0.5])
    det = E1.enumerate_det(R, C, p)
    assert len(det) == 4 ** 3
    d = float(np.median(det["cost"]))
    lp, bd = E1.solve_lp(R, C, p, d), E1.best_det(det, d)
    assert lp["reward"] >= bd["reward"] - 1e-9 and bd["cost"] <= d


def test_argmax_cannot_hit_d_but_softmax_can():
    R, C, p = np.array([[1.0], [3.0]]), np.array([[0.0], [0.1]]), np.array([1.0])
    d = 0.05
    lam = np.linspace(0, 50, 5001)
    _, cost, _ = E1.argmax_curve(R, C, p, d, 1.0, lam)
    assert set(np.round(cost, 6)) == {0.0, 0.1}                # a step: never d
    l = E1.softmax_lambda(R, C, p, d, 1.0, tau=0.5)
    assert E1.softmax_cost(R, C, p, d, 1.0, l, 0.5)[1][0] == pytest.approx(d, abs=1e-6)


def test_cross_eval_uses_destination_tables():
    R, C, p = np.array([[1.0], [3.0]]), np.array([[0.0], [0.1]]), np.array([1.0])
    lp = E1.solve_lp(R, C, p, 0.05)
    src = (R, C, p, 1.0, lp)
    dst_lp = E1.solve_lp(R, C * 2, p, 0.05)
    out = E1.cross_eval(src, (R, C * 2, p, 1.0, dst_lp), 0.05)
    assert out["lp_policy"]["cost"] == pytest.approx(0.1)     # same policy, costs doubled
    assert out["oracle_lp_dst"]["cost"] == pytest.approx(0.05)


def test_load_fold_never_returns_test_rows(tmp_path):
    df = _frame()
    df.loc[df["reservation"].isin(["RESERVATION-0", "RESERVATION-1"]), "split"] = "test"
    df.to_parquet(tmp_path / "d.parquet")
    pd.DataFrame({"res": [f"RESERVATION-{i}" for i in range(12)], "md5": ["abcd" + str(i) for i in range(12)]}).assign(
        md5=lambda x: "abcd" + x["res"].str[-1].where(x["res"].str.len() == 13, "0")).to_csv(tmp_path / "d6.csv", index=False)
    out = E1.load_fold(str(tmp_path / "d.parquet"), str(tmp_path / "d6.csv"), "abcd")
    assert (out["split"] == "train").all()
    assert not out["reservation"].isin(["RESERVATION-0", "RESERVATION-1"]).any()


def test_bootstrap_is_deterministic_and_resamples_reservations():
    df = _frame(n_res=96)
    a = E1.run_fold(df, 0.1, boot=20, seed=3)[3]
    b = E1.run_fold(df, 0.1, boot=20, seed=3)[3]
    pd.testing.assert_frame_equal(a, b)
    assert a["valid"].all()


def test_load_fold_none_keeps_all_train_rows(tmp_path):
    df = _frame()
    df.loc[df["reservation"] == "RESERVATION-0", "split"] = "test"
    df.to_parquet(tmp_path / "d.parquet")
    out = E1.load_fold(str(tmp_path / "d.parquet"), str(tmp_path / "unused.csv"), None)
    assert (out["split"] == "train").all() and out["reservation"].nunique() == 11
