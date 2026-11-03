"""E13c: flag logic on synthetic streams; the scope is TRAIN only."""
import inspect

import numpy as np

import src.e13c_anomalies as m


def streams(sent_gap=False, bs_gap=False, n_bs=8, ue_len=100.0, urllc_empty=False):
    t = np.arange(0, 100, 0.25)
    sent = np.concatenate([np.arange(0, 50, 0.1), np.arange(40000, 40050, 0.1)]) if sent_gap else np.arange(0, 100, 0.1)
    bs = np.concatenate([t[:100], t[100:] + 500]) if bs_gap else t
    return {"enb": [t], "bs_ue": [bs] * n_bs, "ue_metrics": [np.arange(0, ue_len, 0.25)] * 8,
            "mgen_sent": [sent] * 4, "mgen_recv": [np.array([])] + [np.arange(0, 100, 0.1)] * 3 if urllc_empty else [np.arange(0, 100, 0.1)] * 4}


def test_clean_reservation_has_no_flag():
    f = m.flags(streams())
    assert not any(f[k] for k in ("sent_gap", "recv_gap", "bs_gap", "bs_files_lt8", "dur_ratio_out", "urllc_empty"))


def test_each_flag_triggers():
    assert m.flags(streams(sent_gap=True))["sent_gap"] and not m.flags(streams(sent_gap=True))["recv_gap"]
    assert m.flags(streams(bs_gap=True))["bs_gap"]
    assert m.flags(streams(n_bs=4))["bs_files_lt8"]
    assert m.flags(streams(ue_len=150.0))["dur_ratio_out"]
    assert m.flags(streams(urllc_empty=True))["urllc_empty"]


def test_scope_is_train_only():
    src = inspect.getsource(m.main)
    assert '"train"' in src and "len(t) == 510" in src
