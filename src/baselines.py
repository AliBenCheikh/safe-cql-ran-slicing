"""Training-free baselines. Each function returns an action (0..7) per window.

action = prb_idx * 2 + sched, sched 0 = RR, 1 = PF.
"""
import numpy as np

from src.common import BUDGET


def always_rr(action):
    """Same PRB level as the logged action, RR scheduler. Reads the logged action, so it is not
    a deployable policy: it isolates the scheduler effect at the logged PRB level."""
    return (np.asarray(action) // 2) * 2


def always_pf(action):
    """Same PRB level as the logged action, PF scheduler (same caveat as always_rr)."""
    return (np.asarray(action) // 2) * 2 + 1


def best_fixed(val_df, budget=BUDGET):
    """Single action with the highest mean observed reward on the validation set among those
    with mean observed cost <= budget. Returns (action, info). If none is feasible, the action
    with the lowest mean cost is returned and info['feasible'] is False."""
    g = val_df.groupby("action").agg(reward=("reward_embb_Mbps", "mean"),
                                     cost=("urllc_frac_viol", "mean"))
    feasible = g[g["cost"] <= budget]
    if len(feasible):
        a, ok = int(feasible["reward"].idxmax()), True
    else:
        a, ok = int(g["cost"].idxmin()), False
    info = {"feasible": ok, "val_reward": g["reward"].to_dict(), "val_cost": g["cost"].to_dict()}
    return a, info


def table_greedy_map(reward_tbl, cost_tbl, budget=BUDGET):
    """Per load_bin: argmax reward_tbl[a, bin] s.t. cost_tbl[a, bin] <= budget; if no action is
    feasible in a bin, argmin cost. Returns (array[n_bins] of actions, array[n_bins] feasible)."""
    n_bins = reward_tbl.shape[1]
    out, feas = np.zeros(n_bins, dtype=int), np.zeros(n_bins, dtype=bool)
    for b in range(n_bins):
        ok = cost_tbl[:, b] <= budget
        if ok.any():
            out[b] = int(np.argmax(np.where(ok, reward_tbl[:, b], -np.inf)))
            feas[b] = True
        else:
            out[b] = int(np.argmin(cost_tbl[:, b]))
    return out, feas


def table_greedy(load_bin, reward_tbl, cost_tbl, budget=BUDGET):
    m, _ = table_greedy_map(reward_tbl, cost_tbl, budget)
    return m[np.asarray(load_bin, dtype=int)]

