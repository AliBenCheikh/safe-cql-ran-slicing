"""E2: fold hygiene (nothing from the other fold reaches training), guard rule, convergence criterion,
equivalence with train_safe_cql when the guard is off. Synthetic data only."""
import numpy as np
import pandas as pd
import pytest
import torch

from src.agents.safe_cql import train_safe_cql
from src.build_dataset import NS_COLS, STATE_COLS
from src.e2_safe_cql_diagnostic import convergence, prepare_fold, train_variant

TINY = {"hidden": 16, "batch": 64, "epochs": 2}


def synth(n_res=8, per_res=6, seed=0, offset=0):
    """One action per reservation (like the dataset); every action present in every fold."""
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(n_res):
        for _ in range(per_res):
            rows.append({"reservation": f"r{offset + r}", "split": "train", "action": r % 8,
                         "load_bin": int(rng.integers(0, 3)), "reward_embb_Mbps": float(rng.normal(8, 2)),
                         "urllc_frac_viol": float(rng.uniform(0, 0.1)), "done": bool(rng.random() < 0.1),
                         **{c: float(rng.normal()) for c in STATE_COLS}, **{c: float(rng.normal()) for c in NS_COLS}})
    return pd.DataFrame(rows)


def two_folds():
    a, b = synth(seed=1, offset=0), synth(seed=2, offset=100)
    return a, b, pd.concat([a, b], ignore_index=True)


def test_prepare_fold_keeps_only_own_reservations():
    a, b, both = two_folds()
    fold, tab = prepare_fold(both, a["reservation"].unique())
    assert set(fold["reservation"]) == set(a["reservation"])
    assert (fold["cost_hat"].to_numpy() == tab["C"][fold["action"], fold["load_bin"]]).all()


def test_no_information_from_other_fold():
    a, b, both = two_folds()
    ids = a["reservation"].unique()
    wild = b.copy()                                     # same reservations, absurd values
    wild["reward_embb_Mbps"] *= 100.0
    wild["urllc_frac_viol"] = 0.9
    wild[STATE_COLS] += 50.0
    wild[NS_COLS] += 50.0
    wild["load_bin"] = 2
    f1, t1 = prepare_fold(both, ids)
    f2, t2 = prepare_fold(pd.concat([a, wild], ignore_index=True), ids)
    pd.testing.assert_frame_equal(f1, f2)
    for k in ("R", "C", "p"):
        np.testing.assert_array_equal(t1[k], t2[k])
    assert t1["r_scale"] == t2["r_scale"]
    # end to end: identical weights and lambda path
    n1 = train_variant(f1, 0, t1["C"], TINY)
    n2 = train_variant(f2, 0, t2["C"], TINY)
    for p1, p2 in zip(n1[0].parameters(), n2[0].parameters()):
        assert torch.equal(p1, p2)
    assert n1[4] == n2[4]
    # and the fold's r_scale / cost_hat are NOT those of the pooled data
    pooled = prepare_fold(both, both["reservation"].unique())
    assert pooled[1]["r_scale"] != t1["r_scale"]
    assert not np.array_equal(pooled[1]["C"], t1["C"])


def test_guard_off_equals_train_safe_cql():
    a, _, both = two_folds()
    fold, tab = prepare_fold(both, a["reservation"].unique())
    q1, _, _, _, lam1 = train_variant(fold, 3, tab["C"], TINY, guard_n=None)
    q2, _, _, _, lam2 = train_safe_cql(fold, 3, {**TINY}, cost_tbl=tab["C"])
    for p1, p2 in zip(q1.parameters(), q2.parameters()):
        assert torch.equal(p1, p2)
    assert [e["lambda"] for e in lam1] == [e["lambda"] for e in lam2]


def test_guard_freezes_increase_only_when_cost_not_lower():
    a, _, both = two_folds()
    fold, tab = prepare_fold(both, a["reservation"].unique())
    C = np.full_like(tab["C"], 0.5)                      # cost far above d whatever the action: lambda wants to rise
    fold = fold.assign(cost_hat=0.5)
    _, _, _, _, lam = train_variant(fold, 0, C, {**TINY, "epochs": 14}, guard_n=10)
    lams = [e["lambda"] for e in lam]
    assert not any(e["frozen"] for e in lam[:10])        # needs 10 epochs of history
    assert all(e["frozen"] for e in lam[10:])            # constant cost: never lower than 10 epochs ago
    assert lams[10:] == [lams[9]] * 4
    assert lams[9] > 0


def test_convergence_criterion():
    d = 0.03
    flat = [0.5] * 20
    assert convergence(flat, [0.028] * 20, d)["converged"]
    assert convergence([0.0] * 20, [0.02] * 20, d)["converged"]
    assert not convergence([0.0] * 20, [0.031] * 20, d)["converged"]          # lambda 0 but over budget
    assert not convergence(flat, [0.033] * 20, d)["converged"]                # over budget
    assert not convergence(flat, [0.02] * 20, d)["converged"]                 # below 0.9 d with lambda > 0
    assert not convergence(list(np.linspace(0.3, 0.7, 20)), [0.028] * 20, d)["converged"]   # lambda drifting
    ramp = list(0.5 + 0.0005 * np.arange(20))                                  # spread 0.0095 < 0.02 but a clear slope
    r = convergence(ramp, [0.028] * 20, d)
    assert r["c1_lambda_spread"] and not r["c3_slope_ci_has_0"] and not r["converged"]
    assert not convergence(flat[:19], [0.028] * 19, d)["converged"]           # window too short
