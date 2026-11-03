"""E13a2: integer-edge rules (synthetic). The real run is not exercised here (it needs the train parquet; E13a's guard covers it)."""
import numpy as np

import src.e13a2_integer_levels as m


def test_closest_integer_edge_and_merge():
    x = np.array([6.0] * 75 + [5.0] * 8 + [8.0] * 7 + [2.0] * 10)            # cum: <=2 .10, <=5 .18, <=6 .93, <=8 1
    assert m.integer_edges_closest(x, 2).tolist() == [5.0]                    # |.18-.5| < |.93-.5|
    e = m.integer_edges_closest(x, 5)
    assert len(e) < 4 and np.all(np.diff(e) > 0)                              # duplicates merged, not substituted


def test_tie_goes_to_smaller_integer():
    x = np.array([1.0] * 50 + [3.0] * 50)                                     # cum(1) = .5 = target, cum(2) = .5 too
    assert m.integer_edges_closest(x, 2).tolist() == [1.0]


def test_per_integer_merges_small_levels():
    x = np.array([1.0] * 5 + [2.0] * 200 + [3.0] * 300 + [4.0] * 400 + [8.0] * 95)
    e = m.per_integer_edges(x)
    b = np.bincount(np.searchsorted(e, x, side="left")) / len(x)
    assert (b >= m.MIN_LEVEL_SHARE).all() and 1.0 not in e                    # value 1 (0.5 %) merged into its upper neighbour
    assert m.per_integer_edges(np.repeat(np.arange(1, 9), 100).astype(float)).tolist() == list(map(float, range(1, 8)))


def test_edges_depend_on_source_only_and_ref_present():
    a, b = np.array([6.0] * 90 + [3.0] * 10), np.array([1.0] * 100)
    assert set(m.edge_sets(a)) == {"int_k2", "int_k3", "int_k4", "int_k5", "int_each", "edges3_current"}
