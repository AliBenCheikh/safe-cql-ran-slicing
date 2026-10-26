"""Shared helpers for Phase 2 (baselines, offline-RL agents, evaluation).

Everything that is fitted (z-score, reward table, validation split) is fitted on the train split
only. The test split is never passed to a fit function.
"""
import json
import random

import numpy as np
import pandas as pd
import torch

from src.build_dataset import NS_COLS, STATE_COLS

PARQUET = "results/dataset_canonical.parquet"
COST_TABLE = "results/cost_table.csv"
N_ACTIONS = 8
N_BINS = 3
BUDGET = 0.03
GAMMA = 0.7


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_canonical(path=PARQUET):
    """Returns (df, meta). Row count is checked against the Phase-1 metadata."""
    df = pd.read_parquet(path)
    with open(path.replace(".parquet", ".meta.json")) as f:
        meta = json.load(f)
    n_meta = sum(v["n_rows"] for v in meta["counts"].values())
    assert len(df) == n_meta, f"parquet has {len(df)} rows, meta says {n_meta}"
    return df, meta


def split_val(train_df, frac=0.2, seed=0):
    """Split a train frame into (sub-train, validation) BY RESERVATION."""
    res = np.sort(train_df["reservation"].unique())
    rng = np.random.default_rng(seed)
    val_res = set(rng.permutation(res)[: int(round(frac * len(res)))])
    is_val = train_df["reservation"].isin(val_res)
    return train_df[~is_val], train_df[is_val]


def fit_zscore(train_df):
    x = train_df[STATE_COLS].to_numpy(dtype=np.float64)
    return {"mean": x.mean(0), "std": np.maximum(x.std(0), 1e-8)}


def apply_zscore(x, zs):
    return (np.asarray(x, dtype=np.float64) - zs["mean"]) / zs["std"]


def reward_table(train_df):
    """Mean reward_embb_Mbps per (action, load_bin), shape [8, 3]; train only. A missing cell
    falls back to the per-action mean, as for the cost table."""
    g = train_df.groupby(["action", "load_bin"])["reward_embb_Mbps"].mean()
    per_action = train_df.groupby("action")["reward_embb_Mbps"].mean()
    t = np.full((N_ACTIONS, N_BINS), np.nan)
    for a in range(N_ACTIONS):
        for b in range(N_BINS):
            t[a, b] = g.get((a, b), per_action.get(a, np.nan))
    return t


def cost_table_array(path=COST_TABLE):
    """cost_hat per (action, load_bin), shape [8, 3], from the Phase-1 table (train only)."""
    t = pd.read_csv(path)
    out = np.full((N_ACTIONS, N_BINS), np.nan)
    out[t["action"].to_numpy(int), t["load_bin"].to_numpy(int)] = t["cost_hat"].to_numpy()
    assert not np.isnan(out).any(), "cost table has an empty cell"
    return out


def make_arrays(df, zs, r_scale):
    """Tensors for the RL agents. `ns` of terminal rows (NaN in the parquet) is zeros and is
    masked by `nd` (= 1 - done), so the Bellman target of a terminal row is r."""
    s = apply_zscore(df[STATE_COLS].to_numpy(), zs)
    nd = ~df["done"].to_numpy()
    ns = apply_zscore(df[NS_COLS].to_numpy(), zs)
    ns = np.where(nd[:, None], ns, 0.0)
    f = lambda x: torch.as_tensor(np.array(x), dtype=torch.float32)
    return {
        "s": f(s), "a": torch.as_tensor(df["action"].to_numpy().copy(), dtype=torch.int64),
        "r": f(df["reward_embb_Mbps"].to_numpy() / r_scale), "s2": f(ns), "nd": f(nd),
        "c": f(df["cost_hat"].to_numpy()),
    }


def state_tensor(df, zs):
    return torch.as_tensor(apply_zscore(df[STATE_COLS].to_numpy(), zs), dtype=torch.float32)
