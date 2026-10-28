"""Safe-CQL: CQL-Lagrangian with the tabular cost (`cost_hat`), budget d = 0.03.

Penalised reward in the Bellman target:  r - lambda * (cost_hat / d - 1)
  - cost_hat is the table value of the LOGGED action in the row's load bin (Phase-1 table, train only).
  - The cost is expressed in units of the budget so that lambda has the scale of the (train-std
    scaled) reward; with raw cost_hat ~ 0.03 a step of lambda would have almost no effect.
Dual ascent, once per epoch (projected on lambda >= 0):
  lambda <- max(0, lambda + eta * (mean cost_hat[greedy action, load_bin] / d - 1))
The mean is taken over the train rows with the CURRENT greedy policy of the Q-net.
"""
import os

import numpy as np
import torch

from src.agents.cql import CFG, CKPT_DIR, save_checkpoint, train_cql
from src.common import BUDGET, cost_table_array

SAFE_CFG = {**CFG, "budget": BUDGET, "eta": 0.1}


def update_lambda(lam, mean_cost, budget, eta):
    """Projected dual ascent step. The constraint violation is measured relative to the budget."""
    return max(0.0, lam + eta * (mean_cost / budget - 1.0))


def train_safe_cql(train_df, seed, cfg=None, cost_tbl=None, quiet=True, monitor=None):
    """Returns (q_net, zs, r_scale, hist, lam_hist). Tables are indexed [action, load_bin].
    hist entries also hold `lambda`, the value used DURING that epoch (lam_hist: value after the update)."""
    cfg = {**SAFE_CFG, **(cfg or {})}
    cost_tbl = cost_table_array() if cost_tbl is None else cost_tbl
    d, eta = cfg["budget"], cfg["eta"]
    state = {"lam": 0.0}
    lam_hist = []
    lb = torch.as_tensor(train_df["load_bin"].to_numpy().copy(), dtype=torch.int64)
    tbl = torch.as_tensor(cost_tbl, dtype=torch.float32)

    def reward_fn(batch):
        return batch["r"] - state["lam"] * (batch["c"] / d - 1.0)

    def on_epoch_end(q_net, ep, data):
        with torch.no_grad():
            a = q_net(data["s"]).argmax(1)
            mean_cost = tbl[a, lb].mean().item()
        state["lam"] = update_lambda(state["lam"], mean_cost, d, eta)
        lam_hist.append({"epoch": ep, "greedy_cost": mean_cost, "lambda": state["lam"]})

    def log_lambda(q_net, ep, zs):
        return {"lambda": state["lam"], **(monitor(q_net, ep, zs) if monitor else {})}

    q_net, zs, r_scale, hist = train_cql(train_df, seed, cfg, reward_fn, on_epoch_end, quiet,
                                         cost_tbl=cost_tbl, monitor=log_lambda)
    return q_net, zs, r_scale, hist, lam_hist


def run(train_df, seed, cfg=None, ckpt_dir=CKPT_DIR):
    cfg = {**SAFE_CFG, **(cfg or {})}
    q_net, zs, r_scale, hist, lam_hist = train_safe_cql(train_df, seed, cfg)
    save_checkpoint(os.path.join(ckpt_dir, f"safe_cql_seed{seed}.pt"), q_net, zs, r_scale, cfg, seed,
                    history=hist, lambda_history=lam_hist)
    return q_net, zs, {"final_lambda": lam_hist[-1]["lambda"], "greedy_cost_last": lam_hist[-1]["greedy_cost"],
                       "history": hist}
