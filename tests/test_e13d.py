"""E13d: filter classification (matches the pipeline's mask), bounds, table construction, order check, test never opened."""
import inspect

import numpy as np
import pandas as pd

import src.e13d_latency_filter as m


def test_classify_matches_pipeline_filter():
    lat = np.array([-0.5, 0.0, 19.9, 20.0, 19999.9, 20000.0, 5e4, np.nan])
    kept, neg, big, nan = m.classify(lat)
    pipe = (lat >= 0) & (lat < 20000)                     # build_dataset._urllc_stream, verbatim
    assert np.array_equal(kept, pipe) and kept.sum() == 4
    assert neg.tolist() == [True] + [False] * 7 and big.tolist() == [False] * 5 + [True, True, False]
    assert nan.tolist() == [False] * 7 + [True]
    assert (kept | neg | big | nan).all() and not (kept & (neg | big | nan)).any()


def test_bounds():
    pipe, lo, hi = m.bounds([10, 10], [2, 0], [0, 10])
    assert np.allclose(pipe, [0.2, 0.0]) and np.allclose(lo, [0.2, 0.0]) and np.allclose(hi, [0.2, 0.5])
    pipe, lo, hi = m.bounds([8], [2], [2])                 # 2 violations of 8 kept, 2 dropped
    assert np.isclose(lo[0], 0.2) and np.isclose(hi[0], 0.4) and np.isclose(pipe[0], 0.25)


def test_cost_array_uses_pipeline_rule_with_fallback():
    rows = []
    for a in range(8):
        for b in range(3):
            n = 30 if (a, b) != (0, 0) else 5              # cell (0,0) has < 20 windows -> falls back to the action mean
            rows += [{"action": a, "load_bin": b, "reservation": f"r{a}", "c": 0.1 * b + 0.01 * a}] * n
    df = pd.DataFrame(rows)
    t = m.cost_array(df, "c")
    assert t.shape == (8, 3) and np.isclose(t[1, 2], 0.21)
    assert np.isclose(t[0, 0], df[df.action == 0]["c"].mean())


def test_order_holds():
    assert m.order_holds(0.03, 0.04, 0.05) and not m.order_holds(0.04, 0.03, 0.05) and not m.order_holds(0.03, 0.03, 0.05)


def test_dm_cost():
    tbl = np.arange(24, dtype=float).reshape(8, 3)
    assert m.dm_cost([0, 7], [0, 2], tbl) == (0 + 23) / 2


def test_test_split_is_never_opened():
    src = inspect.getsource(m)
    assert "evaluate_once" not in src.replace("evaluate_once (the test read) is never called", "")
    assert "test_results" not in src and "load_test" not in src
