"""E11: frozen criterion / selection rule / constants (fingerprint), selection cases, references, and a tiny end-to-end
run on synthetic folds (nothing from the validation fold reaches training). Synthetic data only."""
import numpy as np
import pandas as pd

import src.e11_alpha_grid as e11
from src.e11_alpha_grid import convergence_r, frozen_fingerprint, references, select_alpha
from src.e2_safe_cql_diagnostic import prepare_fold
from tests.test_e2 import synth

# Pinned at the freeze commit. If this fails, the criterion, the selection rule or a constant was edited AFTER the freeze.
FROZEN_SHA256 = "33e458b2baf1a9e5438d9f2019a34790b6352ecb545eb7a0d1720faf7a1664aa"


def test_frozen_fingerprint_is_pinned():
    assert frozen_fingerprint() == FROZEN_SHA256


def test_frozen_constants():
    assert e11.ALPHAS == (0.0, 0.02, 0.05, 0.1, 0.2, 0.5)
    assert e11.BAND_TOL == 0.0025 and e11.WINDOW == 20 and e11.SEEDS == (0, 1, 2, 3, 4) and e11.EPOCHS == 100


def test_convergence_r_cases():
    d, flat = 0.03, [0.5] * 20
    assert convergence_r(flat, [0.03] * 20, d)["converged"]
    assert convergence_r(flat, [0.0324] * 20, d)["converged"]                     # above d but within the band
    assert not convergence_r(flat, [0.0330] * 20, d)["converged"]                  # beyond the band
    assert not convergence_r(flat, [0.0270] * 20, d)["converged"]                  # below the band
    assert convergence_r([0.0] * 20, [0.01] * 20, d)["converged"]                  # lambda 0: cost <= d is enough
    assert not convergence_r([0.0] * 20, [0.031] * 20, d)["converged"]
    assert not convergence_r(list(np.linspace(0.3, 0.7, 20)), [0.03] * 20, d)["converged"]   # lambda drifts
    r = convergence_r(flat, list(0.029 + 0.0001 * np.arange(20)), d)               # cost drifts, mean in the band
    assert r["r2_cost_level"] and not r["r3_cost_slope_ci_has_0"] and not r["converged"]
    rng = np.random.default_rng(0)
    assert convergence_r(0.5 + 0.001 * rng.normal(size=20), 0.03 + 0.0005 * rng.normal(size=20), d)["converged"]   # noise, no trend
    assert not convergence_r(flat[:19], [0.03] * 19, d)["converged"]


def _summ(table):
    return pd.DataFrame([{"alpha": a, "direction": dr, "val_cost_mean": c, "val_reward_mean": r}
                         for a, dr, c, r in table])


def test_select_alpha_feasible_picks_best_reward_then_smallest_alpha_on_ties():
    s = _summ([(0.0, "A->B", 0.02, 9.0), (0.0, "B->A", 0.02, 9.0), (0.1, "A->B", 0.029, 9.5), (0.1, "B->A", 0.03, 9.5),
               (0.2, "A->B", 0.029, 9.505), (0.2, "B->A", 0.029, 9.505), (0.5, "A->B", 0.01, 12.0), (0.5, "B->A", 0.04, 12.0)])
    r = select_alpha(s)
    assert r["status"] == "feasible" and r["feasible_alphas"] == [0.0, 0.1, 0.2]
    assert r["alpha"] == 0.1                       # 0.1 and 0.2 tied within 0.01 -> smaller; 0.5 infeasible in one direction


def test_select_alpha_infeasible_flags_and_takes_lowest_mean_cost():
    s = _summ([(0.0, "A->B", 0.03, 9.0), (0.0, "B->A", 0.05, 9.0), (0.1, "A->B", 0.04, 9.0), (0.1, "B->A", 0.04, 9.0),
               (0.2, "A->B", 0.02, 8.0), (0.2, "B->A", 0.0801, 8.0)])
    r = select_alpha(s)
    assert r["status"].startswith("infeasible") and r["feasible_alphas"] == []
    assert r["alpha"] == 0.0 and r["feasible_alphas"] == []       # mean costs: 0.04, 0.04, 0.05005 -> tie 0.0/0.1 -> smaller


def test_references_hold_on_synthetic_tables():
    a, b = synth(seed=1, offset=0), synth(seed=2, offset=100)
    both = pd.concat([a, b], ignore_index=True)
    folds = {"A": prepare_fold(both, a["reservation"].unique()), "B": prepare_fold(both, b["reservation"].unique())}
    ref = references(folds, d=0.05)
    for k in ("A", "B"):
        tg = ref[k]["table_greedy_on_own"]
        lp = ref[k]["lp_on_own"]
        assert len(ref[k]["table_greedy_policy"]) == 3
        if ref[k]["table_greedy_reached_d"]:
            assert tg["cost"] <= 0.05 + 1e-12
        if lp["feasible"]:
            assert lp["reward"] >= tg["reward"] - 1e-9 or not ref[k]["table_greedy_reached_d"]   # LP is an upper bound


def test_run_one_validates_on_the_other_fold_only(monkeypatch):
    a, b = synth(seed=1, offset=0), synth(seed=2, offset=100)
    both = pd.concat([a, b], ignore_index=True)
    folds = {"A": prepare_fold(both, a["reservation"].unique()), "B": prepare_fold(both, b["reservation"].unique())}
    monkeypatch.setattr(e11, "load_folds", lambda: folds)
    seen = {}
    real = e11.train_variant

    def spy(fold_df, seed, C, cfg=None, guard_n=None):
        seen["res"] = set(fold_df["reservation"])
        seen["alpha"] = cfg["alpha"]
        return real(fold_df, seed, C, {**cfg, "hidden": 16, "batch": 64}, guard_n)

    monkeypatch.setattr(e11, "train_variant", spy)
    r = e11.run_one(("A", 0.05, 0, 3))
    assert seen["res"] == set(a["reservation"]) and not (seen["res"] & set(b["reservation"]))   # training sees fold A only
    assert seen["alpha"] == 0.05 and r["direction"] == "A->B" and r["epochs"] == 3
    assert np.isfinite(r["val_cost"]) and np.isfinite(r["val_reward"])
    assert r["convergence_r"]["converged"] is False                  # 3 epochs < window
