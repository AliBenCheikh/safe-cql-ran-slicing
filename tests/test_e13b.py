"""E13b: step statistics, window criteria, timestamp-only reads (synthetic reservation in tmp_path)."""
import numpy as np
import pandas as pd

import src.e13b_sampling_check as m


def test_step_stats_regular_and_irregular():
    s = m.step_stats(np.arange(0, 100, 1.0))
    assert abs(s["step_median"] - 1.0) < 1e-12 and s["share_within_10pct_median"] == 1.0 and s["share_dup"] == 0
    t = np.concatenate([np.arange(0, 50, 1.0), np.arange(60, 100, 1.0)])
    s = m.step_stats(t)
    assert s["step_max"] == 11.0 and s["share_gt_2x_median"] > 0


def test_window_criteria():
    t = np.arange(0, 100, 1.0)                                  # 1 Hz
    assert m.window_report(t, 5.0, m.MIN_KPM)["possible"]       # 5 samples per 5 s
    assert not m.window_report(t, 2.0, m.MIN_KPM)["possible"]   # 2 samples per 2 s < 3
    assert not m.window_report(t, 0.5, m.MIN_KPM)["possible"]   # half the windows empty
    assert m.window_report(t, 0.5, m.MIN_KPM)["share_empty"] > 0.45


def test_reads_timestamp_columns_only(tmp_path):
    r = tmp_path / "RESERVATION-1"
    (r / "bs").mkdir(parents=True)
    (r / "ue_001").mkdir()
    n = 60
    pd.DataFrame({"time": np.arange(n) * 1000.0, "nof_ue": 5, "secret": "x"}).to_csv(r / "bs" / "enb_metrics.csv", index=False)
    pd.DataFrame({"Timestamp": np.arange(n) * 1000.0, "mcs": 3}).to_csv(r / "bs" / "1010123456002_metrics.csv", index=False)
    pd.DataFrame({"time": np.arange(n) * 1000.0, "dl_brate": 1.0}).to_csv(r / "ue_001" / "ue_metrics.csv", sep=";", index=False)
    pd.DataFrame({"Sent Time": np.arange(0, 60, 0.01), "Received Time": np.arange(0, 60, 0.01) + 0.005, "Seq": 1}).to_csv(r / "ue_001" / "mgen.csv", index=False)
    out, errs = m.read_reservation(str(r))
    assert not errs and set(out) == {"enb", "bs_ue", "ue_metrics", "mgen_sent", "mgen_recv"}
    rep = m.analyse_reservation(str(r))
    assert abs(rep["streams"]["enb"]["per_file_step_median_min_med_max"][1] - 1.0) < 1e-9
    assert rep["streams"]["mgen_recv"]["windows"]["1.0"]["possible"] and not rep["streams"]["mgen_recv"]["windows"]["0.1"]["possible"]
    assert abs(rep["ue_over_enb_duration_ratio_median"] - 1.0) < 1e-9


def test_source_has_no_unrestricted_read():
    import inspect
    src = inspect.getsource(m)
    assert src.count("read_csv") == 2 and "usecols" in src            # sample list + the single timestamp reader
