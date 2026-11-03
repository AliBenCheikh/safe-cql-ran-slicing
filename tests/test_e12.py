"""E12: frozen fingerprint, test-split sealing (AST checks + synthetic end-to-end), lock, estimators, expectations.
Synthetic data only: the real dataset and the real test split are never read here."""
import ast
import inspect
import json

import numpy as np
import pandas as pd
import pytest
import torch

import src.e12_final as e12
from tests.test_e2 import synth

FROZEN_SHA256 = "c88c288ea41dd1cb05b9a66b1574e4180bf6a2d562e37c9bb42198d74536d854"      # pinned at the freeze commit
TINY = {"hidden": 8, "batch": 64}


def test_frozen_fingerprint_is_pinned():
    assert FROZEN_SHA256 != "UNSET"
    assert e12.frozen_fingerprint() == FROZEN_SHA256 == e12.PINNED_SHA256


def test_frozen_configuration():
    assert e12.SEEDS == (0, 1, 2, 3, 4) and e12.EPOCHS == 100 and e12.B_BOOT == 2000 and e12.BOOT_SEED == 0
    assert e12.CONFIGS == {"safe_cql_a0.1": ("safe_cql", {"alpha": 0.1}), "cql_a0.1": ("cql", {"alpha": 0.1}),
                           "safe_cql_a0.5": ("safe_cql", {"alpha": 0.5}), "cql_a0.5": ("cql", {"alpha": 0.5}),
                           "safe_cql_a0.1_g0": ("safe_cql", {"alpha": 0.1, "gamma": 0.0}), "iql": ("iql", {})}
    assert e12.BASELINES == ("always_rr", "always_pf", "best_fixed", "table_greedy") and e12.PRIMARY == "safe_cql_a0.1"
    assert e12.BUDGET == 0.03 and e12.DATASET_VERSION == "268d524c117eb6de"


# ----------------------------------------------------------------------------- sealing (static)
def _tree():
    return ast.parse(inspect.getsource(e12))


def test_split_name_test_appears_only_inside_load_test():
    tree = _tree()
    loads = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_test")
    inside = {id(n) for n in ast.walk(loads)}
    doc_nodes = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Module)) and n.body
                 and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    lits = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and n.value == "test" and id(n) not in doc_nodes]
    assert lits and all(id(n) in inside for n in lits)


def test_load_test_is_called_only_from_evaluate_once():
    tree = _tree()
    for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
        if fn.name not in ("evaluate_once", "load_test"):
            assert "load_test" not in names, fn.name
    # and the training path never reaches the evaluation code
    for fn in ("train_job", "train_phase", "_train_one", "load_train"):
        src = inspect.getsource(getattr(e12, fn))
        assert "load_test" not in src and "evaluate_once" not in src and "script_of" not in src


def test_cli_calls_evaluate_once_with_the_output_dir_only():
    main = next(n for n in _tree().body if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n for n in ast.walk(main) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "evaluate_once"]
    assert len(calls) == 1 and len(calls[0].args) == 1 and not calls[0].keywords      # no guard bypass from the CLI
    opts = {a.value for n in ast.walk(main) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "add_argument"
            for a in n.args if isinstance(a, ast.Constant)}
    assert opts == {"--out", "--workers", "--train", "--evaluate"}


# ----------------------------------------------------------------------------- synthetic dataset
def _write_dataset(tmp_path, poison_test=False, with_test=True):
    tr = synth(n_res=16, per_res=8, seed=1)
    tr["cost_hat"] = np.random.default_rng(0).uniform(0.0, 0.08, len(tr))
    tr["load_bin"] = np.arange(len(tr)) % 3
    te = synth(n_res=16, per_res=8, seed=2, offset=1000).assign(split="test", cost_hat=0.0)
    te["load_bin"] = np.arange(len(te)) % 3
    if poison_test:
        te["reward_embb_Mbps"], te["urllc_frac_viol"] = 1e6, 1.0
    df = pd.concat([tr, te] if with_test else [tr], ignore_index=True)
    p = tmp_path / "ds.parquet"
    df.to_parquet(p)
    (tmp_path / "ds.meta.json").write_text(json.dumps({"dataset_version": e12.DATASET_VERSION}))
    cost = pd.DataFrame([{"action": a, "load_bin": b, "cost_hat": 0.02 + 0.005 * a} for a in range(8) for b in range(3)])
    cost.to_csv(tmp_path / "cost.csv", index=False)
    res = sorted(te["reservation"].unique())
    pd.DataFrame({"res": res, "md5": ["c40f2fe7aa" if i < 12 else "0123abcd55" for i in range(len(res))]}).to_csv(tmp_path / "d6.csv", index=False)
    return str(p), str(tmp_path / "cost.csv"), str(tmp_path / "d6.csv")


@pytest.fixture
def tiny(monkeypatch):
    monkeypatch.setattr(e12, "EPOCHS", 2)


def test_training_never_reads_the_test_split(tmp_path, tiny, monkeypatch):
    seen = []
    real = pd.read_parquet
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **k: (seen.append(k.get("filters")), real(*a, **k))[1])
    pq, cost, _ = _write_dataset(tmp_path)
    out = str(tmp_path / "out")
    summ = e12.train_phase(out, pq, workers=1, epochs=2, cost_path=cost, extra_cfg=TINY)
    assert seen and all(f == [("split", "==", "train")] for f in seen)
    assert summ["meta"]["test_split_read"] is False and len(summ["runs"]) == len(e12.CONFIGS) * len(e12.SEEDS)


def test_trained_weights_do_not_depend_on_test_rows(tmp_path, tiny):
    outs = []
    for i, (poison, with_test) in enumerate(((True, True), (False, False))):
        d = tmp_path / f"d{i}"
        d.mkdir()
        pq, cost, _ = _write_dataset(d, poison_test=poison, with_test=with_test)
        job = ("safe_cql_a0.1", 0, 2, pq, str(d / "out"), cost, TINY)
        e12.train_job(job)
        outs.append(torch.load(d / "out" / "checkpoints" / "safe_cql_a0.1_seed0.pt", weights_only=False)["state_dict"])
    for k in outs[0]:
        assert torch.equal(outs[0][k], outs[1][k])


def _trained(tmp_path):
    pq, cost, d6 = _write_dataset(tmp_path)
    out = str(tmp_path / "out")
    summ = e12.train_phase(out, pq, workers=1, epochs=2, cost_path=cost, extra_cfg=TINY)
    fake = lambda: {"git_commit": "x", "git_dirty": False, "fingerprint": summ["meta"]["fingerprint"]}
    return pq, cost, d6, out, fake


def test_end_to_end_single_reading_and_lock(tmp_path, tiny):
    pq, cost, d6, out, fake = _trained(tmp_path)
    res = e12.evaluate_once(out, pq, d6, cost, guard_fn=fake)
    assert list(res["groups"]) == ["c40f2fe7", "0123abcd", "pooled"] and res["meta"]["reading"].startswith("final")
    g = res["groups"]["c40f2fe7"]
    assert g["n_reservations"] == 12 and res["groups"]["0123abcd"]["n_reservations"] == 4 and res["groups"]["0123abcd"]["low_n"]
    assert set(g["policies"]) == set(e12.CONFIGS) | set(e12.BASELINES)
    for st in g["policies"].values():
        assert st["dm_cost"]["ci_lo"] <= st["dm_cost"]["mean"] <= st["dm_cost"]["ci_hi"] or np.isnan(st["dm_cost"]["mean"])
    assert np.isnan(g["policies"]["table_greedy"]["dm_cost"]["seed_sd"]) and not np.isnan(g["policies"][e12.PRIMARY]["dm_cost"]["seed_sd"])
    assert json.load(open(f"{out}/{e12.LOCK_NAME}"))["status"] == "completed"
    assert set(res["expectations"]) == {"c40f2fe7", "pooled"}
    with pytest.raises(RuntimeError):                                   # a second reading is refused
        e12.evaluate_once(out, pq, d6, cost, guard_fn=fake)


def test_crash_before_results_allows_one_more_attempt_and_counts_it(tmp_path, tiny):
    pq, cost, d6, out, fake = _trained(tmp_path)
    e12.acquire_lock(out, {"git_commit": "x"})                          # a first attempt that crashed: lock without results
    res = e12.evaluate_once(out, pq, d6, cost, guard_fn=fake)
    assert res["meta"]["lock"]["attempts"] == 2


def test_missing_checkpoint_does_not_consume_the_lock(tmp_path, tiny):
    pq, cost, d6, out, fake = _trained(tmp_path)
    import os
    os.remove(f"{out}/checkpoints/iql_seed3.pt")
    with pytest.raises(AssertionError):
        e12.evaluate_once(out, pq, d6, cost, guard_fn=fake)
    assert not os.path.exists(f"{out}/{e12.LOCK_NAME}")


def test_trained_under_other_code_is_refused(tmp_path, tiny):
    pq, cost, d6, out, _ = _trained(tmp_path)
    with pytest.raises(AssertionError):
        e12.evaluate_once(out, pq, d6, cost, guard_fn=lambda: {"git_commit": "x", "git_dirty": False, "fingerprint": "other"})


def test_guard_refuses_dirty_tree_and_unset_pin(monkeypatch):
    monkeypatch.setattr(e12, "git_state", lambda: {"git_commit": "x", "git_dirty": True})
    with pytest.raises(AssertionError):
        e12.guard()
    monkeypatch.setattr(e12, "git_state", lambda: {"git_commit": "x", "git_dirty": False})
    monkeypatch.setattr(e12, "PINNED_SHA256", "0" * 64)
    with pytest.raises(AssertionError):
        e12.guard()


def test_lock_refuses_when_completed_or_results_exist(tmp_path):
    e12.acquire_lock(str(tmp_path), {})
    (tmp_path / e12.RESULTS_NAME).write_text("{}")
    with pytest.raises(RuntimeError):
        e12.acquire_lock(str(tmp_path), {})


# ----------------------------------------------------------------------------- estimators
def _frame():
    return pd.DataFrame({"load_bin": [0, 1, 0, 1], "action": [0, 1, 0, 1], "reward_embb_Mbps": [1.0, 2.0, 3.0, 4.0],
                         "urllc_frac_viol": [0.0, 0.1, 0.2, 0.3], "reservation": ["a", "a", "b", "b"]})


def test_res_sums_dm_and_matched():
    f = _frame()
    r_tbl, c_tbl = np.arange(24, dtype=float).reshape(8, 3), np.full((8, 3), 0.02)
    codes = np.array([0, 0, 1, 1])
    p = e12._res_sums(f, [0, 0, 1, 1], codes, 2, r_tbl, c_tbl, 0.03)
    assert p["dm_reward"][0].tolist() == [r_tbl[0, 0] + r_tbl[0, 1], r_tbl[1, 0] + r_tbl[1, 1]]
    assert p["dm_cost"][0].tolist() == [0.04, 0.04] and p["dm_pct_safe"][0].tolist() == [1.0, 1.0]
    assert p["matched_coverage"][0].tolist() == [1.0, 1.0]                     # only the first window of "a", the last of "b"
    assert p["matched_cost"][0].tolist() == [0.0, 0.3] and p["matched_pct_safe"][0].tolist() == [1.0, 0.0]


def test_boot_stats_constant_policy_has_degenerate_interval_and_seed_sd():
    f = _frame()
    codes = np.array([0, 0, 1, 1])
    r_tbl, c_tbl = np.ones((8, 3)), np.full((8, 3), 0.01)
    idx = np.random.default_rng(0).integers(0, 2, size=(200, 2))
    parts = [e12._res_sums(f, a, codes, 2, r_tbl, c_tbl, 0.03) for a in ([0, 1, 0, 1], [0, 1, 0, 1], [2, 2, 2, 2])]
    st = e12.boot_stats(parts, idx)
    assert st["dm_cost"]["mean"] == pytest.approx(0.01) and st["dm_cost"]["ci_lo"] == st["dm_cost"]["ci_hi"] == pytest.approx(0.01)
    assert st["dm_cost"]["seed_sd"] == 0.0 and st["matched_coverage"]["seed_sd"] > 0
    assert e12.demonstrated_safe({"dm_cost": {"ci_hi": 0.02}, "matched_cost": {"ci_hi": float("nan")}}) is False


# ----------------------------------------------------------------------------- expectations
def _pol(rew, cost, hi=None, cov=0.2, mcost=None, sd=0.001):
    s = lambda m, h=None: {"mean": m, "seed_sd": sd, "ci_lo": m - 0.001, "ci_hi": m + 0.002 if h is None else h}
    return {"dm_reward": s(rew), "dm_cost": s(cost, hi), "matched_reward": s(rew), "matched_cost": s(cost if mcost is None else mcost),
            "matched_coverage": s(cov), "dm_pct_safe": s(0.5), "matched_pct_safe": s(0.5)}


def test_check_expectations_true_and_false_cases():
    P = {n: _pol(8.0, 0.05) for n in (*e12.CONFIGS, *e12.BASELINES)}
    P["table_greedy"] = _pol(10.0, 0.02, hi=0.025, mcost=0.5)
    P["safe_cql_a0.1"], P["safe_cql_a0.5"] = _pol(8.0, 0.04), _pol(8.0, 0.04)
    res = {"groups": {"c40f2fe7": {"policies": P}, "pooled": {"policies": P}}}
    ex = e12.check_expectations(res)["c40f2fe7"]
    assert ex["a"]["holds"] and ex["b"]["holds"] and ex["c"]["holds"] and ex["d"]["holds"] and not ex["d"]["net_improvement"]
    assert ex["e"]["holds"]                           # table-greedy: matched cost 0.5 -> not demonstrated safe, nobody else is
    P["table_greedy"] = _pol(10.0, 0.02, hi=0.025, mcost=0.01)
    ex = e12.check_expectations(res)["c40f2fe7"]
    assert ex["e"]["demonstrated_safe"]["table_greedy"] and not ex["e"]["holds"]
    P["safe_cql_a0.1_g0"] = _pol(8.0, 0.01)           # gamma 0 clearly better -> net improvement, (d) fails
    ex = e12.check_expectations(res)["c40f2fe7"]
    assert ex["d"]["net_improvement"] and not ex["d"]["holds"]
