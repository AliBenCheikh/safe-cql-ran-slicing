# Decision memo — Phase 0 (branch `revision/00-decision`)

Answers the open questions of section 9 of `docs/audit_report.md` using the raw data, read-only.

## 0. Method and provenance

- Dataset: `./data` → `~/data/safe-cql/dataset-kpm`, 1,116 reservations. Version id (SHA-256 of sorted relative path and size, first 16 hex) = `268d524c117eb6de`. Nothing was written inside `data/` (`find -L data -mtime -1` is empty).
- Scripts: `src/checks/{common,windows,d1..d5}*.py`. Tests: `tests/test_checks.py` (7 tests on a synthetic reservation; `pytest` passes). Outputs go to `results/` (gitignored). Seed 0 for every sampling and bootstrap.
- No RL model was trained. D4 uses logistic regression and histogram gradient boosting on CPU.
- `src/checks/windows.py` re-implements notebook cell 21 (read from the .ipynb JSON, not executed). **Reproduction check: it builds 706 reservations, skips 101 (95 without URLLC data, 6 without eMBB data) and yields 225,313 windows, identical to the counts recorded in the notebook (706 / 101 / 225,313).** Only these counts were compared. The window values were not compared.
- Tags: **[V]** verified on the data by a script here. **[H]** hypothesis. **[P]** problem confirmed. **[Q]** open question.

### Files in a reservation (inventory, one reservation then checked on all)

| File | Clock | Content |
|---|---|---|
| `bs/enb_metrics.csv` | epoch ms, 250 ms step | `time, nof_ue, dl_brate, ul_brate` |
| `bs/<IMSI>_metrics.csv` | epoch ms | `Timestamp, num_ues, slicing_enabled, slice_id, slice_prb, power_multiplier, scheduling_policy`, MCS, CQI, buffers, rates |
| `bs/mgen-script-scope.mgn` | seconds since start | traffic script, rate changes every 60 s |
| `ue_*/ue_metrics.csv` (`;`) | ms since the logger start (no absolute clock) | 21 KPM columns |
| `ue_*/mgen.csv` | wall clock `HH:MM:SS.us` and seconds of day | per-packet send and receive times |

## D1 — Does the configuration change inside a reservation?

**[V] No. 0 of 1,116 reservations vary.**

- The per-row config columns exist in `bs/<IMSI>_metrics.csv`, so the path is not the only source. A reservation counts as varying if one UE file holds more than one config tuple, or if the same `slice_id` has different `slice_prb`, scheduler, `slicing_enabled` or `power_multiplier` across UE files.
- 0 UE files contain a changing config. The file contents agree with the folder path for all 1,116 reservations (0 mismatches).
- Config values: `slice_prb` is 9/41, 21/29, 30/20, 39/11 for slicing 1–4. The first number is slice 0 (eMBB), the second is slice 1 (URLLC), and they add to 50 PRB. Scheduler is 0 or 2. `power_multiplier` is 1 everywhere.
- **[V] Slicing 5 is "no slicing"**: all 309 reservations have `slicing_enabled=0` and `slice_prb=0`. The audit read it as "50 PRB for eMBB". The files only show that slicing is disabled.
- 28 reservations of slicings 1–4 have only eMBB UE files and 7 have only URLLC UE files (the latter cannot produce a reward).
- **[V] Load is not constant inside a reservation.** The MGEN script changes the rate every 60 s. This is a scripted, exogenous load schedule, independent of the action.

## D2 — Clock alignment

Offsets in seconds, quantiles over reservations (`results/d2_full.json`).

| Pair | n | min | p5 | p50 | p95 | max |
|---|---|---|---|---|---|---|
| first BS-UE row − first eNB row with `nof_ue>0` | 1,096 | −673 | 0.25 | 0.49 | 0.50 | 1,011 |
| MGEN first packet − first eNB row with `nof_ue>0`, modulo whole hours (includes the traffic start delay) | 1,084 | −12.5 | 0.61 | 0.78 | 4.98 | 1,380 |
| UE KPM start (estimated from first `is_attached`) − first eNB row | 1,101 | −1,046 | 59.0 | 60.3 | 63.5 | 108 |
| spread of first BS timestamps across the UEs of one reservation | 1,101 | 0 | 2.2 | 5.0 | 62.5 | 1,164 |

- **[V]** eNB, BS-UE and MGEN files share one time base (UTC). The MGEN time-zone shift is 0 h in 1,080 reservations. The 4 reservations at −24 h are a day-wrap artefact of my comparison. 32 have no usable MGEN time (missing files).
- **[V]** In the typical case the eNB and BS streams start within 0.5 s of each other. This is below one window. Outliers: 12 of 1,096 reservations differ by more than 5 s, 11 by more than 30 s and 6 by more than 300 s.
- **[V] The eMBB window origin is per UE in the notebook (cell 21 l.42).** In 532 of 1,101 reservations (48%) the first BS rows of the UEs differ by more than 5 s, which is at least one window. The sum over eMBB UEs therefore mixes shifted windows in about half of the reservations.
- **[H]** The UE KPM absolute start is estimated as (first BS timestamp of the IMSI) − (first attached time). It is an inference. `ue_metrics.csv` has no absolute clock. The median of 60.3 s is similar to the delay between the first eNB row and the first eNB row with `nof_ue>0` (62.0 s), but this does not prove alignment.
- **[Q]** The MGEN row is a mix of clock offset and the traffic start delay. It is a bound, not a pure clock offset.
- Data quality: 20 reservations have an empty or missing file (`enb_metrics.csv` empty in 15, a `ue_metrics.csv` missing or empty in others).

## D3 — Is the window index contiguous after the joins?

**[P] No. 46 of 706 built reservations (6.5%) have gaps** (cl1: 17/196, cl2: 4/262, cl3: 25/248).

- 103 gap events. Run length: median 11 windows, p90 72, max 204.
- Source of the gaps (reservations with a gap inside the stream): URLLC 58, eNB 27, eMBB 1. **[H]** The gaps probably come from windows without URLLC packets (the inner join drops them). Not checked against the traffic script.
- Impact on the notebook's `shift` on rows: 103 of 225,313 rows have a "next" row that is not window t+1 (0.05%). 199 rows have a lag2 that is not t−2. These are small in count but they are wrong transitions across a gap of up to 204 windows (17 minutes).
- 2,559 rows (1.1%) have `nof_ue` invented by `ffill/bfill`.
- 98 of 706 reservations have fewer than 4 eMBB UEs contributing to the reward sum, so the "sum over 4 UEs" reward is not constant in scale.
- First joined window is 0 in all reservations.

## D4 — How well does the state predict the action?

Train on clusters 2–3 (n=163,960 windows), test on cluster 1 (61,353 windows, 196 reservations), 706 reservations in total. Accuracy on test windows with a reservation-level bootstrap 95% CI (1000 resamples, seed 0). Baseline = train majority class. Chance for 8 actions is 12.5%.

| Target | Features | Logistic regression | Hist. gradient boosting |
|---|---|---|---|
| action (8) | majority baseline | 0.124 | 0.124 |
| | lag-only (notebook lags) | 0.305 [0.252, 0.360] | 0.328 [0.276, 0.381] |
| | lag-only, first 2 windows dropped (no bfill) | 0.305 [0.252, 0.360] | 0.332 [0.280, 0.384] |
| | load only (`nof_ue`) | 0.128 [0.092, 0.164] | 0.134 [0.100, 0.168] |
| | current radio + load, no reward/latency | 0.205 [0.166, 0.249] | 0.206 [0.175, 0.240] |
| | current 8 columns (with reward, p50) | 0.354 [0.305, 0.408] | 0.416 [0.370, 0.466] |
| | all 12 | 0.356 [0.307, 0.410] | 0.423 [0.375, 0.472] |
| PRB level (4) | majority baseline | 0.245 | 0.245 |
| | lag-only | 0.555 [0.507, 0.600] | 0.556 [0.511, 0.599] |
| | all 12 | 0.589 [0.547, 0.630] | 0.611 [0.569, 0.655] |
| scheduler (2) | majority baseline | 0.492 | 0.492 |
| | lag-only | 0.495 [0.425, 0.565] | 0.540 [0.473, 0.604] |
| | current radio + load, no reward/latency | 0.549 [0.484, 0.609] | 0.712 [0.666, 0.755] |
| | all 12 | 0.547 [0.485, 0.609] | 0.704 [0.657, 0.753] |

- **[V] The state leaks the logged action.** Lags alone give 30–33% for the 8 actions and 55% for the PRB level, against 12.4% and 24.5% for the majority baselines. Adding the same-window columns gives 36–42% and 59–61%. Voting over the windows of a reservation raises the full-state PRB accuracy to 0.78 (logistic) and 0.77 (boosting).
- **[V]** The PRB level is mostly readable from throughput (reward lags). The scheduler is readable from the current radio state by a non-linear model (71% vs 49%) but not by a linear one (55%).
- **[V]** The notebook's recorded BC accuracies (0.403 / 0.576 / 0.664) fall in the same range as these trivial classifiers. This is a comparison of recorded numbers with new ones, not a reproduction.
- **[P]** The audit hypothesis is confirmed: a policy network can partly recover the behaviour action from the state, so "the agent learns a policy" and "the agent identifies which configuration produced the logs" are not separable here.
- **[V]** Even the lag-only features carry the action, so removing the same-window columns does not remove the leak.

## D5 — Cost cells: counts and reservation-level bootstrap CIs

Cost = `urllc_frac_viol` per window, load = window `nof_ue`, edges from the notebook (3 bins, 4 bins). Bootstrap resamples reservations inside the cell (B=2000, seed 0). Full table: `results/d5_cells.csv`.

| Subset / scheme | cells | min windows | min reservations | cells with < 10 reservations | median CI width (reservation) | median CI width (naive, windows) | cells whose CI contains the 0.03 budget |
|---|---|---|---|---|---|---|---|
| train cl2–3, 3 bins | 24 | 1,171 | 10 | 0 | 0.059 | 0.007 | 15 |
| train cl2–3, 4 bins | 32 | 523 | 6 | 5 | 0.048 | 0.006 | 18 |
| test cl1, 3 bins | 24 | 292 | 5 | 4 | 0.044 | 0.008 | 14 |
| test cl1, 4 bins | 32 | 97 | 1 | 6 | 0.055 | 0.010 | 15 |

- **[V]** No cell is empty and none has fewer than 20 or 50 windows in the training set. The window counts look comfortable.
- **[P]** The effective sample size is the number of reservations, not windows. The reservation CI is about 6–9× wider than the naive window CI. The training cells hold only 6–10 reservations at low load.
- **[V]** Between 47% and 63% of the cells (depending on subset and scheme) have a CI containing the 0.03 budget, so the tabular cost cannot separate "safe" from "unsafe" for most (action, load) pairs. The high-load PF cells are clearly unsafe (for example (9 PRB, PF) at high load: 0.290 [0.214, 0.374], 3 bins, training).
- **[V]** Example of a noisy cell: (30, RR) at low load = 0.142 [0.005, 0.227] over 20 reservations (3 bins, training). The audit recorded 0.147 in the notebook for this cell. The small difference is unexplained [Q] (bin edge convention is the likely cause, not checked).
- **[V]** Load is nearly a reservation-level covariate: the median within-reservation standard deviation of `nof_ue` is 0.74, while the reservation mean ranges from 4.3 to 5.7 across actions. Action and load are partly confounded across clusters (mean `nof_ue` 4.58 in cl1, 5.80 in cl2, 5.34 in cl3).
- Reservations per action and cluster are unbalanced: for example action 7 has 31 reservations in cl1 and 9 and 13 in cl2 and cl3.

## Evidence summary

| Question | Result | Consequence |
|---|---|---|
| Config changes inside a reservation? | **No (0/1,116)** | No within-run counterfactual. Q(s, a ≠ logged a) is identified only across reservations. |
| Clocks aligned? | Same UTC base; typical offset < 1 s; per-UE starts differ by ≥ 1 window in 48% of reservations | The eMBB sum is mis-windowed in about half of the reservations. Fixable by a common origin. |
| Window index contiguous? | **No, 46/706 reservations** | Small in rows (0.05%) but must be fixed (episode split at gaps). |
| State predicts action? | **Yes**: lags alone 30–33% vs 12.4% | The "policy" can be a configuration classifier. |
| Cost cells supported? | Many windows, few reservations; wide CIs | Cost table is a coarse, low-power estimate. |

## Options

### (A) Configuration selection (contextual, one-step)
- **Claim**: choose a configuration (PRB split, scheduler) for a load context to maximise eMBB throughput subject to a URLLC violation budget. Offline, reservation-level evaluation.
- **Requires** (all possible with the existing data): state built from window t−1 only, or episode-level context; drop `reward_embb_Mbps` and `urllc_p50` of the current window from the state; common window origin; split episodes at gaps; one cost table with per-cell N and reservation-bootstrap CI; training-free baselines (fixed config, always-RR, table-greedy); cluster/reservation bootstrap for every comparison; OPE with the target policy's own action.
- **Answers**: R2-W2 (static data, directly accepted), R1-W1 (Markov / `a_{t−1}`: not needed when the decision is one-step per context), R1-W2 (cell CIs, tail metric `urllc_p99`, bin sensitivity), R3-W1 (baselines), R2-W1 (reframe as slower-loop rApp-style, with a window-size sensitivity), R3-W3 (writing).
- **Does not answer**: R3-W2 (novelty stays modest). R1's request for recurrent/continuous critic remains an ablation.

### (B) Sequential control
- **Claim**: the agent changes the configuration over time and the dynamics respond.
- **Requires new data or simulation**: D1 shows that no run contains a config change, so transitions with a changed action do not exist. Needs experiments with scheduled config switches, or a simulator calibrated on these traces, plus the switching cost and transient. None of this exists today. It is a new data-collection effort, not a code change.
- **Answers**: R1-W1 and R2-W2 in full, R2-W1 only if the control period is changed.
- **Risk**: the claim cannot be supported by the present data. It would not fit a revision of this paper.

### (C) Hybrid
- **Claim**: (A) as the main result now, plus a small, explicit new experiment (a few configuration switches during runs, or a calibrated simulation) to test whether sequential effects exist.
- **Requires**: everything in (A), plus new experiments for the sequential part. The new data decide whether the sequential part makes it into this paper or into a follow-up.
- **Answers**: all concerns of (A), and R1-W1 / R2-W2 with evidence instead of by redefinition, if the experiment is done.

## Recommendation

**Choose (A) for the revision. Keep (B) as stated future work, and treat (C) as optional if new data can be collected before the deadline.**

Evidence: D1 (no config change in any of the 1,116 reservations) removes the data basis for sequential control. D4 shows that the state already identifies much of the logged action, which supports reframing the model as configuration selection and warns against reading it as a sequential policy. D3 and D2 show the window construction needs a common origin and episode splitting regardless of the option. D5 shows the cost estimates are uncertain at the reservation level, so the contribution should be evaluated by reservation-level statistics.

**[Q] Open questions for the authors:**
- Is any scheduled config switch available in a different dataset release, or can runs with switches be produced?
- What do the 95 reservations without URLLC data and the 20 with unreadable files contain? Were they known gaps?
- Why does slicing 5 have `slicing_enabled=0` when the paper presents it as a 50-PRB eMBB slice?
- (30, RR, low) cost: 0.142 here against 0.147 in the notebook. Which bin convention was used?

**Not done in this phase** (outside D1–D5): the end-to-end window-origin difference in windows between the three notebook sources (only the file-start offsets were measured), the FQE and OPE fixes, and any model training.
