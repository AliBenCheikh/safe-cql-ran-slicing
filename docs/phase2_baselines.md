# Phase 2 — Baselines, agents, evaluation (branch `revision/02-baselines`)

Tags: **[V]** verified by a script here, **[H]** hypothesis, **[P]** problem confirmed, **[Q]** open question. All numbers below come from `results/evaluation_results.json` (gitignored), produced by `python -m src.evaluate --seeds 0 1 2 3 4`. Dataset version `268d524c117eb6de`, 224,193 rows, test = cluster 1 (196 reservations, 61,128 windows). Notebook, PDF, reviews and `data/` untouched.

## What was run
- Baselines (`src/baselines.py`): always-RR `(a//2)*2`, always-PF `(a//2)*2+1` (they read the logged action, so they are not deployable policies; they isolate the scheduler effect at the logged PRB level), best-fixed (20% of train reservations, seed 0, 102 reservations), table-greedy (argmax reward per load bin s.t. `cost_hat <= 0.03`).
- Agents (`src/agents/`): CQL (alpha 0.5), Safe-CQL (penalised reward `r - lambda (cost_hat/d - 1)`, dual ascent each epoch), IQL (expectile 0.7, beta 3.0, argmax policy net). MLP 2x256, gamma 0.7, 100 epochs, batch 1024, lr 3e-4, soft target update 0.005, seeds 0-4, **train split only**. Z-score and reward scale fitted on train. 15 checkpoints in `results/checkpoints/` (about 3.5 to 7 min per run on CPU).
- Not in the brief, my choices, none tuned on test: lr, target update rate, Safe-CQL eta = 0.1 with the cost expressed in units of the budget (raw `cost_hat` ~ 0.03 would make lambda steps negligible), IQL beta = 3.0 and weight clip 100.

## How to read the numbers (important)
The configuration is constant per reservation (D1), so the reward of an action other than the logged one is **not observed**.
- `dm_*` (direct method): reward = train mean `R[a, load_bin]`, cost = `cost_hat[a, load_bin]`. Model-based estimate, not a measured return. For table-greedy and for Safe-CQL's cost the DM cost uses the same table the method was built from, so it is partly circular. [P]
- `matched_*`: observed reward and cost on the windows where the chosen action equals the logged action. Independent of the tables but biased by the behaviour policy and based on few windows for some methods (coverage column).
- CI: 95% reservation-level bootstrap (B = 2000, seed 0). `pct_safe`: share of the 196 test reservations whose mean cost <= 0.03. RL rows: mean +- std (ddof = 1) over 5 seeds; the CI is the mean of the per-seed bounds.

## Results (test split)

| Method | DM reward (Mbps) [95% CI] | DM cost [95% CI] | DM pct_safe | Matched reward | Matched cost | Matched coverage |
|---|---|---|---|---|---|---|
| logged policy (reference) | 6.92 [6.41, 7.40] | 0.0665 [0.0579, 0.0754] | 35.2% | 7.456 | 0.0430 | 100% |
| always-RR | 7.21 [6.74, 7.65] | 0.0285 [0.0258, 0.0314] | 60.2% | 7.581 | 0.0191 | 49.1% |
| always-PF | 6.88 [6.35, 7.39] | 0.1272 [0.1168, 0.1368] | 6.1% | 7.335 | 0.0662 | 50.9% |
| best-fixed (action 0, fallback) | 2.77 [2.63, 2.89] | 0.0138 [0.0124, 0.0152] | 99.5% | 3.522 | 0.0308 | 11.7% |
| table-greedy | 9.14 [8.72, 9.49] | 0.0222 [0.0209, 0.0233] | 100% | 9.806 | 0.0280 | 9.5% |
| CQL | 6.951 +- 0.027 [6.51, 7.38] | 0.0533 +- 0.0011 [0.0476, 0.0590] | 27.7 +- 3.6% | 7.828 +- 0.037 | 0.0399 +- 0.0014 | 40.1% |
| Safe-CQL | 6.955 +- 0.053 [6.53, 7.35] | 0.0295 +- 0.0002 [0.0266, 0.0327] | 76.6 +- 2.4% | 7.579 +- 0.048 | 0.0315 +- 0.0010 | 36.4% |
| IQL | 7.005 +- 0.028 [6.56, 7.44] | 0.0569 +- 0.0004 [0.0510, 0.0629] | 23.2 +- 1.5% | 7.921 +- 0.026 | 0.0418 +- 0.0010 | 40.3% |

Matched pct_safe (reservations with at least one matched window): always-RR 82.1% (95 res.), always-PF 41.6% (101), best-fixed 73.9% (23), table-greedy 82.7% (52), CQL 64.1%, Safe-CQL 71.4%, IQL 63.2% (per-seed counts in the JSON).

## Findings
1. **[V] Safe-CQL moves the cost to the budget, CQL and IQL do not.** DM cost 0.0295 vs 0.053 / 0.057, DM pct_safe 76.6% vs 27.7% / 23.2%; the same ordering holds on the matched estimate (0.0315 vs 0.040 / 0.042). Rewards are within the bootstrap noise of each other on DM (6.95 vs 6.95 vs 7.01), and on the matched estimate Safe-CQL is lower (7.58 vs 7.83 / 7.92). The three agents' CIs on reward overlap fully; the cost CIs of Safe-CQL and CQL/IQL do not overlap (upper bound 0.0327 vs lower bounds 0.0476 / 0.0510), but the CIs are those of the seed-averaged DM estimate, not a paired test.
2. **[V] The budget is met on average, not for the upper CI.** The Safe-CQL DM cost CI is [0.0266, 0.0327], so it contains violations of 0.03. The dual variable ended at 0.75-0.91 (mean greedy cost on train 0.032-0.033), i.e. the constraint was not exactly satisfied on train after 100 epochs of dual ascent with eta = 0.1. [H] more epochs or a larger eta might close the gap; not tested.
3. **[P] The training-free table-greedy has the best DM reward (9.14) and 100% pct_safe, but this is the most circular number in the table**: it maximises the same train reward table and satisfies the same train cost table that the DM estimator uses. Its matched coverage is 9.5% (52 reservations), where it gets 9.81 Mbps at cost 0.028. It beats the RL agents on both estimates, so the contribution of the RL agents over a table lookup is **not supported** by this evaluation. [Q] Whether the agents can be made to match it (different state, longer training) is not tested here.
4. **[P] best-fixed is infeasible.** On the validation set no action has a mean cost <= 0.03 (lowest: action 0 at 0.0315; the others 0.035-0.279), so the documented fallback (lowest cost) selects action 0, reward 3.25 Mbps on validation. Its DM cost (0.0138, table) differs from the observed validation cost (0.0315): the table is fitted by load bin on all train, validation is a subset of reservations. This is an example of the reservation-to-reservation variation of D5.
5. **[V] always-RR is almost on the budget (DM cost 0.0285, CI [0.0258, 0.0314]) with reward comparable to the agents; always-PF is unsafe (0.127).** The scheduler explains most of the cost: PF at the logged PRB level raises the estimated cost by 4.5x.
6. **[H] Agent actions are spread over all 8 actions** (mean test counts per agent in the JSON `action_hist_mean`), with action 2 the most chosen by all three (CQL 13.6k, Safe-CQL 22.9k, IQL 11.5k of 61.1k windows). The D4 caveat (state identifies the logged configuration) still applies; the state-leak re-check on the 10-dim state is not done in this phase.
7. **Seed variation is small** (std of DM reward 0.03-0.05 Mbps, of cost 0.0002-0.001) against the reservation-bootstrap CI widths (about 0.9-1.0 Mbps and 0.006-0.012), so the reservation sampling dominates the uncertainty, not the training seed. [V]

## Tests
`pytest tests`: 31 pass (17 earlier plus 14 new). They use synthetic data only: always-RR even and same PRB level, always-PF odd and same PRB level, best-fixed cap and fallback, table-greedy and fallback, validation split by reservation, z-score on train only, evaluate_policy on a fully matched policy, IQL V / Q / policy losses lower after 10 steps, CQL gives lower Q on unseen actions and lower logsumexp than alpha = 0, lambda increases above the budget (and stays at 0 below), checkpoint round trip.

## Limits and open points
- **[P]** DM estimates depend on 24-cell train tables whose reservation-level CIs are wide (D5); table-greedy and Safe-CQL inherit this.
- **[H]** Hyper-parameters are not tuned; no model selection was done (fixed 100 epochs), so no test information leaks, but the agents may be under- or over-trained.
- **[Q]** No importance-weighted OPE or FQE (not in scope). A measured counterfactual would need runs with configuration switches (decision memo, option C).
- `results/evaluate_run.log` holds the console output; the smoke test (2 epochs) was run to the scratchpad and is not part of the results.
