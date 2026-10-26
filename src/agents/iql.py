"""Implicit Q-Learning (Kostrikov et al. 2021), discrete actions.

  V loss      : expectile regression (tau) of Q_target(s,a_logged) on V(s)
  Q loss      : (Q(s,a) - (r + gamma * nd * V(s')))^2
  policy loss : advantage-weighted cross-entropy on the logged action, w = min(exp(beta * (Q_t - V)), 100)
The policy is deterministic at evaluation (argmax of its logits). Train split only.
"""
import os

import numpy as np
import torch
import torch.nn.functional as F

from src.agents.cql import CKPT_DIR, mlp, soft_update
from src.common import GAMMA, N_ACTIONS, fit_zscore, make_arrays, set_seed, state_tensor

IQL_CFG = {"hidden": 256, "gamma": GAMMA, "expectile": 0.7, "beta": 3.0, "epochs": 100, "batch": 1024,
           "lr": 3e-4, "tau": 0.005, "w_max": 100.0}


class IQLNets(torch.nn.Module):
    def __init__(self, in_dim, hidden=256):
        super().__init__()
        self.v = mlp(in_dim, 1, hidden)
        self.q = mlp(in_dim, N_ACTIONS, hidden)
        self.q_target = mlp(in_dim, N_ACTIONS, hidden)
        self.pi = mlp(in_dim, N_ACTIONS, hidden)
        self.q_target.load_state_dict(self.q.state_dict())
        for p in self.q_target.parameters():
            p.requires_grad_(False)


def expectile_loss(diff, tau):
    w = torch.abs(tau - (diff < 0).float())
    return (w * diff ** 2).mean()


def iql_losses(nets, batch, cfg):
    """Returns (v_loss, q_loss, pi_loss), each a scalar tensor."""
    s, a = batch["s"], batch["a"][:, None]
    with torch.no_grad():
        q_t = nets.q_target(s).gather(1, a).squeeze(1)
        v_next = nets.v(batch["s2"]).squeeze(1)
        target = batch["r"] + cfg["gamma"] * batch["nd"] * v_next
    v = nets.v(s).squeeze(1)
    v_loss = expectile_loss(q_t - v, cfg["expectile"])
    q_loss = F.mse_loss(nets.q(s).gather(1, a).squeeze(1), target)
    with torch.no_grad():
        w = torch.exp(cfg["beta"] * (q_t - v)).clamp(max=cfg["w_max"])
    logp = F.log_softmax(nets.pi(s), dim=1).gather(1, a).squeeze(1)
    pi_loss = -(w * logp).mean()
    return v_loss, q_loss, pi_loss


def train_iql(train_df, seed, cfg=None, quiet=True):
    cfg = {**IQL_CFG, **(cfg or {})}
    set_seed(seed)
    zs = fit_zscore(train_df)
    r_scale = float(train_df["reward_embb_Mbps"].std())
    data = make_arrays(train_df, zs, r_scale)
    n, in_dim = data["s"].shape
    nets = IQLNets(in_dim, cfg["hidden"])
    params = [p for m in (nets.v, nets.q, nets.pi) for p in m.parameters()]
    opt = torch.optim.Adam(params, lr=cfg["lr"])
    gen = torch.Generator().manual_seed(seed)
    hist = []
    for ep in range(cfg["epochs"]):
        perm = torch.randperm(n, generator=gen)
        tot = np.zeros(3)
        for i in range(0, n, cfg["batch"]):
            idx = perm[i:i + cfg["batch"]]
            batch = {k: v[idx] for k, v in data.items()}
            lv, lq, lp = iql_losses(nets, batch, cfg)
            opt.zero_grad()
            (lv + lq + lp).backward()
            opt.step()
            soft_update(nets.q_target, nets.q, cfg["tau"])
            tot += np.array([lv.item(), lq.item(), lp.item()]) * len(idx)
        hist.append((tot / n).tolist())
        if not quiet:
            print(f"epoch {ep}: v/q/pi = {hist[-1]}")
    return nets, zs, r_scale, hist


@torch.no_grad()
def greedy_actions(nets, df, zs):
    return nets.pi(state_tensor(df, zs)).argmax(1).numpy()


def save_checkpoint(path, nets, zs, r_scale, cfg, seed, **extra):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save({"state_dict": nets.state_dict(), "zscore": zs, "r_scale": r_scale, "cfg": cfg,
                "seed": seed, **extra}, path)


def load_iql(path):
    ck = torch.load(path, weights_only=False)
    nets = IQLNets(len(ck["zscore"]["mean"]), ck["cfg"]["hidden"])
    nets.load_state_dict(ck["state_dict"])
    return nets, ck


def run(train_df, seed, cfg=None, ckpt_dir=CKPT_DIR):
    cfg = {**IQL_CFG, **(cfg or {})}
    nets, zs, r_scale, hist = train_iql(train_df, seed, cfg)
    save_checkpoint(os.path.join(ckpt_dir, f"iql_seed{seed}.pt"), nets, zs, r_scale, cfg, seed, history=hist)
    return nets, zs, {"history_last": hist[-1]}
