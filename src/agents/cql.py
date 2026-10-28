"""Discrete Conservative Q-Learning (no constraint).

loss = Bellman (double-DQN target, soft-updated target net) + alpha * mean(logsumexp_a Q(s,a) - Q(s,a_logged))
Trained on the train split only. The state is z-scored with train statistics (src.common).
"""
import os

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.common import GAMMA, N_ACTIONS, cost_table_array, fit_zscore, make_arrays, set_seed, state_tensor

CFG = {"hidden": 256, "gamma": GAMMA, "alpha": 0.5, "epochs": 100, "batch": 1024, "lr": 3e-4, "tau": 0.005}
CKPT_DIR = "results/checkpoints"


def mlp(in_dim, out_dim, hidden=256):
    return nn.Sequential(nn.Linear(in_dim, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU(),
                         nn.Linear(hidden, out_dim))


def soft_update(target, online, tau):
    with torch.no_grad():
        for pt, p in zip(target.parameters(), online.parameters()):
            pt.mul_(1 - tau).add_(tau * p)


def cql_loss(q_net, q_target, batch, gamma, alpha, r=None):
    """Returns (total, bellman, conservative). `r` overrides batch['r'] (used by Safe-CQL)."""
    r = batch["r"] if r is None else r
    q = q_net(batch["s"])
    q_sa = q.gather(1, batch["a"][:, None]).squeeze(1)
    with torch.no_grad():
        a2 = q_net(batch["s2"]).argmax(1, keepdim=True)
        target = r + gamma * batch["nd"] * q_target(batch["s2"]).gather(1, a2).squeeze(1)
    bellman = F.mse_loss(q_sa, target)
    cons = (torch.logsumexp(q, dim=1) - q_sa).mean()
    return bellman + alpha * cons, bellman, cons


@torch.no_grad()
def epoch_stats(q_fn, pi_fn, data, load_bin, cost_tbl, chunk=65536):
    """End-of-epoch diagnostics over the whole train set (forward only, no RNG):
    mean Q(s, a_logged), mean max_a Q(s, .) and the mean tabular cost_hat of the greedy policy
    (argmax of `pi_fn`, default `q_fn`). `load_bin` int64 [n], `cost_tbl` float [N_ACTIONS, N_BINS]."""
    pi_fn = pi_fn or q_fn
    n = len(data["a"])
    ql = qm = gc = 0.0
    for i in range(0, n, chunk):
        s, a = data["s"][i:i + chunk], data["a"][i:i + chunk]
        q = q_fn(s)
        ql += q.gather(1, a[:, None]).double().sum().item()
        qm += q.max(1).values.double().sum().item()
        ag = pi_fn(s).argmax(1)
        gc += cost_tbl[ag, load_bin[i:i + chunk]].double().sum().item()
    return {"q_logged": ql / n, "q_max": qm / n, "greedy_cost_train": gc / n}


def train_cql(train_df, seed, cfg=None, reward_fn=None, on_epoch_end=None, quiet=True,
              cost_tbl=None, monitor=None):
    """Trains on `train_df` (train split). reward_fn(batch) -> reward used in the Bellman target;
    on_epoch_end(q_net, epoch, data) is called after each epoch (Safe-CQL's lambda update).
    monitor(q_net, epoch, zs) -> dict is merged into the epoch's history entry (diagnostics only).
    Returns (q_net, zs, r_scale, history); history = one dict per epoch."""
    cfg = {**CFG, **(cfg or {})}
    set_seed(seed)
    zs = fit_zscore(train_df)
    r_scale = float(train_df["reward_embb_Mbps"].std())
    data = make_arrays(train_df, zs, r_scale)
    n, in_dim = data["s"].shape
    q_net = mlp(in_dim, N_ACTIONS, cfg["hidden"])
    q_target = mlp(in_dim, N_ACTIONS, cfg["hidden"])
    q_target.load_state_dict(q_net.state_dict())
    opt = torch.optim.Adam(q_net.parameters(), lr=cfg["lr"])
    gen = torch.Generator().manual_seed(seed)
    lb = torch.as_tensor(train_df["load_bin"].to_numpy().copy(), dtype=torch.int64)
    tbl = torch.as_tensor(cost_table_array() if cost_tbl is None else cost_tbl, dtype=torch.float32)
    hist = []
    for ep in range(cfg["epochs"]):
        perm = torch.randperm(n, generator=gen)
        tot = np.zeros(3)
        for i in range(0, n, cfg["batch"]):
            idx = perm[i:i + cfg["batch"]]
            batch = {k: v[idx] for k, v in data.items()}
            r = reward_fn(batch) if reward_fn else None
            loss, bell, cons = cql_loss(q_net, q_target, batch, cfg["gamma"], cfg["alpha"], r)
            opt.zero_grad()
            loss.backward()
            opt.step()
            soft_update(q_target, q_net, cfg["tau"])
            tot += np.array([loss.item(), bell.item(), cons.item()]) * len(idx)
        loss, bell, cons = (tot / n).tolist()
        rec = {"epoch": ep, "loss": loss, "bellman": bell, "cons": cons,
               **epoch_stats(q_net, None, data, lb, tbl)}
        if monitor:
            rec.update(monitor(q_net, ep, zs))
        hist.append(rec)
        if on_epoch_end:
            on_epoch_end(q_net, ep, data)
        if not quiet:
            print(f"epoch {ep}: {rec}")
    return q_net, zs, r_scale, hist


@torch.no_grad()
def greedy_actions(q_net, df, zs):
    return q_net(state_tensor(df, zs)).argmax(1).numpy()


def save_checkpoint(path, q_net, zs, r_scale, cfg, seed, **extra):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save({"state_dict": q_net.state_dict(), "zscore": zs, "r_scale": r_scale, "cfg": cfg,
                "seed": seed, **extra}, path)


def load_q_net(path):
    ck = torch.load(path, weights_only=False)
    cfg = ck["cfg"]
    net = mlp(len(ck["zscore"]["mean"]), N_ACTIONS, cfg["hidden"])
    net.load_state_dict(ck["state_dict"])
    return net, ck


def run(train_df, seed, cfg=None, ckpt_dir=CKPT_DIR):
    """Train CQL and save results/checkpoints/cql_seed{seed}.pt."""
    cfg = {**CFG, **(cfg or {})}
    q_net, zs, r_scale, hist = train_cql(train_df, seed, cfg)
    save_checkpoint(os.path.join(ckpt_dir, f"cql_seed{seed}.pt"), q_net, zs, r_scale, cfg, seed, history=hist)
    return q_net, zs, {"history_last": hist[-1], "history": hist}
