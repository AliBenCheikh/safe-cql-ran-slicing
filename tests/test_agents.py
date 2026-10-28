"""Tests of src/agents/* on a tiny synthetic batch (no parquet)."""
import numpy as np
import pytest
import torch

from src.agents import cql, iql, safe_cql
from src.agents.cql import cql_loss, mlp, soft_update
from src.common import N_ACTIONS


def tiny_batch(n=64, d=10, seed=0, actions=(0, 1)):
    g = torch.Generator().manual_seed(seed)
    s = torch.randn(n, d, generator=g)
    return {"s": s, "a": torch.as_tensor(np.random.default_rng(seed).choice(actions, n)),
            "r": torch.randn(n, generator=g), "s2": torch.randn(n, d, generator=g),
            "nd": torch.ones(n), "c": torch.full((n,), 0.1)}


def test_iql_losses_decrease_over_10_steps():
    torch.manual_seed(0)
    cfg = {**iql.IQL_CFG, "hidden": 32}
    nets = iql.IQLNets(10, 32)
    params = [p for m in (nets.v, nets.q, nets.pi) for p in m.parameters()]
    opt = torch.optim.Adam(params, lr=1e-2)
    batch = tiny_batch()
    before = [x.item() for x in iql.iql_losses(nets, batch, cfg)]
    for _ in range(10):
        lv, lq, lp = iql.iql_losses(nets, batch, cfg)
        opt.zero_grad()
        (lv + lq + lp).backward()
        opt.step()
        soft_update(nets.q_target, nets.q, 0.005)
    after = [x.item() for x in iql.iql_losses(nets, batch, cfg)]
    for name, b, a in zip(("V", "Q", "policy"), before, after):
        assert a < b, f"{name} loss did not decrease: {b} -> {a}"


def test_expectile_loss_is_asymmetric():
    d = torch.tensor([1.0, -1.0])
    assert iql.expectile_loss(d[:1], 0.7) > iql.expectile_loss(d[1:], 0.7)


def _train_q(alpha, steps=50, seed=0):
    torch.manual_seed(seed)
    net, tgt = mlp(10, N_ACTIONS, 32), mlp(10, N_ACTIONS, 32)
    tgt.load_state_dict(net.state_dict())
    opt = torch.optim.Adam(net.parameters(), lr=1e-2)
    batch = tiny_batch()
    for _ in range(steps):
        loss, _, _ = cql_loss(net, tgt, batch, 0.7, alpha)
        opt.zero_grad()
        loss.backward()
        opt.step()
        soft_update(tgt, net, 0.05)
    with torch.no_grad():
        return net(batch["s"])


def test_cql_more_conservative_than_standard_q_learning():
    q_std, q_cql = _train_q(0.0), _train_q(0.5)
    unseen = list(range(2, N_ACTIONS))  # actions never logged in the batch
    assert q_cql[:, unseen].mean() < q_std[:, unseen].mean()
    assert torch.logsumexp(q_cql, 1).mean() < torch.logsumexp(q_std, 1).mean()


def test_update_lambda_direction():
    assert safe_cql.update_lambda(0.0, 0.06, 0.03, 0.1) > 0.0       # cost above budget: lambda rises
    assert safe_cql.update_lambda(1.0, 0.06, 0.03, 0.1) > 1.0
    assert safe_cql.update_lambda(0.5, 0.01, 0.03, 0.1) < 0.5       # below budget: decreases
    assert safe_cql.update_lambda(0.0, 0.01, 0.03, 0.1) == 0.0      # projected on >= 0


def test_safe_cql_lambda_increases_when_cost_exceeds_budget():
    import pandas as pd
    from src.build_dataset import NS_COLS, STATE_COLS
    rng = np.random.default_rng(0)
    n = 300
    df = pd.DataFrame(rng.normal(size=(n, 10)), columns=STATE_COLS)
    for c, c2 in zip(STATE_COLS, NS_COLS):
        df[c2] = rng.normal(size=n)
    df["action"] = rng.integers(0, 8, n)
    df["reward_embb_Mbps"] = rng.normal(5, 1, n)
    df["done"] = False
    df["load_bin"] = rng.integers(0, 3, n)
    df["cost_hat"] = 0.2
    over = np.full((8, 3), 0.2)    # every action is above the 0.03 budget
    _, _, _, _, lam_hist = safe_cql.train_safe_cql(df, 0, {"epochs": 5, "batch": 64, "hidden": 16}, over)
    lams = [h["lambda"] for h in lam_hist]
    assert lams[0] > 0 and all(b > a for a, b in zip(lams, lams[1:]))
    under = np.full((8, 3), 0.0)
    _, _, _, _, lam_hist = safe_cql.train_safe_cql(df, 0, {"epochs": 3, "batch": 64, "hidden": 16}, under)
    assert all(h["lambda"] == 0.0 for h in lam_hist)


def test_checkpoint_roundtrip(tmp_path):
    net = mlp(10, N_ACTIONS, 16)
    zs = {"mean": np.zeros(10), "std": np.ones(10)}
    p = str(tmp_path / "ck.pt")
    cql.save_checkpoint(p, net, zs, 2.0, {"hidden": 16}, 3)
    net2, ck = cql.load_q_net(p)
    x = torch.randn(4, 10)
    assert torch.allclose(net(x), net2(x)) and ck["seed"] == 3


# ----------------------------------------------------------------------------- per-epoch history

def _synth_df(n=300, seed=0):
    import pandas as pd
    from src.build_dataset import NS_COLS, STATE_COLS
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(size=(n, 10)), columns=STATE_COLS)
    for c in NS_COLS:
        df[c] = rng.normal(size=n)
    df["action"] = rng.integers(0, 8, n)
    df["reward_embb_Mbps"] = rng.normal(5, 1, n)
    df["urllc_frac_viol"] = rng.uniform(0, 0.1, n)
    df["done"] = False
    df["load_bin"] = rng.integers(0, 3, n)
    df["cost_hat"] = 0.2
    df["reservation"] = rng.integers(0, 20, n)
    df["split"] = "train"
    return df


EPOCHS = 4
SMALL = {"epochs": EPOCHS, "batch": 64, "hidden": 16}
COMMON_KEYS = {"epoch", "q_logged", "q_max", "greedy_cost_train"}


def test_history_one_entry_per_epoch():
    df, tbl = _synth_df(), np.full((8, 3), 0.1)
    runs = {
        "cql": (cql.train_cql(df, 0, SMALL, cost_tbl=tbl)[3], {"loss", "bellman", "cons"}),
        "safe_cql": (safe_cql.train_safe_cql(df, 0, SMALL, tbl)[3], {"loss", "bellman", "cons", "lambda"}),
        "iql": (iql.train_iql(df, 0, SMALL, cost_tbl=tbl)[3], {"loss_v", "loss_q", "loss_pi"}),
    }
    for name, (hist, keys) in runs.items():
        assert len(hist) == EPOCHS, name
        assert [h["epoch"] for h in hist] == list(range(EPOCHS)), name
        for h in hist:
            assert set(h) == COMMON_KEYS | keys, name
            assert all(np.isfinite(v) for v in h.values()), name
            assert h["greedy_cost_train"] == pytest.approx(0.1)   # constant cost table
        assert hist[-1]["q_max"] >= hist[-1]["q_logged"] - 1e-6


def test_safe_cql_history_lambda_is_value_used_during_epoch():
    df = _synth_df()
    _, _, _, hist, lam_hist = safe_cql.train_safe_cql(df, 0, SMALL, np.full((8, 3), 0.2))
    assert hist[0]["lambda"] == 0.0
    assert [h["lambda"] for h in hist[1:]] == [l["lambda"] for l in lam_hist[:-1]]


def test_monitor_does_not_change_training():
    df, tbl = _synth_df(), np.full((8, 3), 0.1)
    calls = []
    for train in (cql.train_cql, iql.train_iql):
        plain = train(df, 3, SMALL, cost_tbl=tbl)[0]
        mon = train(df, 3, SMALL, cost_tbl=tbl, monitor=lambda m, ep, zs: calls.append(ep) or {"x": 1.0})[0]
        sd = (lambda m: m.state_dict() if hasattr(m, "state_dict") else m)
        for (k, a), (_, b) in zip(sd(plain).items(), sd(mon).items()):
            assert torch.equal(a, b), k
    assert calls == list(range(EPOCHS)) * 2


def test_curves_val_uses_no_test_rows():
    from src.evaluate import prepare_curves_val
    df = _synth_df(600)
    df.loc[df["reservation"] >= 14, "split"] = "test"
    sub, val, r_tbl, c_tbl = prepare_curves_val(df)
    train_res = set(df.loc[df["split"] == "train", "reservation"])
    assert set(sub["reservation"]) | set(val["reservation"]) == train_res
    assert not set(sub["reservation"]) & set(val["reservation"])
    assert set(sub["split"]) == {"train"} and set(val["split"]) == {"train"}
    assert r_tbl.shape == c_tbl.shape == (8, 3) and np.isfinite(c_tbl).all()
