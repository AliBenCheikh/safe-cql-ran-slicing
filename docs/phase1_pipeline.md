# Phase 1 — Canonical pipeline (branch `revision/01-pipeline`)

`src/build_dataset.py` replaces the notebook builder cells labelled "Cellule 11" and "Cellule 12" (0-based indices 21 and 22; indices 11-12 are unrelated trade-off analyses). The notebook is untouched. Tags: **[V]** verified by a script here, **[H]** hypothesis, **[Q]** open question.

## Provenance
- Command: `python -m src.build_dataset --seed 0` (CPU, about 14 s, read-only on `data/`; `find -L data -mtime -1` is empty afterwards).
- Dataset version `268d524c117eb6de` (same id as Phase 0), 1,116 reservation folders. Outputs in `results/` (gitignored): `dataset_canonical.parquet`, `dataset_canonical.meta.json` (seed, git commit, counts, lag medians), `cost_table.csv`.
- No model was trained. Tests: `tests/test_pipeline.py` (10 tests, synthetic data only). `pytest tests` passes (17 tests with Phase 0).

## What changed against the notebook
| Fix | Notebook | Here |
|---|---|---|
| 1. Window origin (D2) | eMBB: each UE's `time.min()`. URLLC: first `Received Time`. eNB: first row with `nof_ue>0` | One `t0` = first eNB row with `nof_ue>0`; all three streams use `win = floor((t − t0)/5 s)`; windows `< 0` dropped |
| 2. Gaps (D3) | `shift` on rows across gaps | New episode where `win` steps by more than 1; `episode_id = <reservation>_<idx>`; lags and `next_state` stay inside an episode; `ns_*` is NaN on the last window |
| 3. State (D4, audit §3) | 12 dims, includes current `reward_embb_Mbps` and `urllc_p50` | 10 dims: `nof_ue, rsrp, dl_snr, dl_mcs, dl_bler, ul_buff` (current window) + lag1/lag2 of reward and `urllc_p50`. `r` = `reward_embb_Mbps` and `c` = `urllc_frac_viol` are separate columns |
| Lags at episode start | `bfill` inside a reservation, then global median | Median of observed lags on the **train** split only, no `bfill`; flag `lag_imputed` |
| `nof_ue` | `ffill().bfill()` (invented in 1.1% of rows) | Inner join; windows without eNB data are dropped (1,512 windows) |
| Cost table | 3 tables with different bins | One: 3 bins `[0, 3.5, 5.5, 8.1]`, right edge included, fitted on train, fallback to the per-action mean below 20 windows (never triggered) |

Columns also stored: `ns_<state col>`, `done`, `load_bin`, `ns_load_bin`, `cost_hat`, `ns_cost_hat` (the next-state bin, which the notebook replaced by the current one), `n_embb_ue`, `urllc_p99`, `split`, `action = prb_idx*2 + sched`. Z-scoring is not applied here (it belongs to the training step, train statistics only).

## Counts [V]
| Split | n_reservations | n_episodes | n_rows | n_transitions |
|---|---|---|---|---|
| train (clusters 2-3) | 510 | 575 | 163,065 | 162,490 |
| test (cluster 1) | 196 | 242 | 61,128 | 60,886 |
| total | 706 | 817 | 224,193 | 223,376 |

`n_transitions = n_rows − n_episodes` holds. 46 reservations hold more than one episode (same 46 as D3). Skips: 309 slicing-5, 79 without URLLC, 15 without usable eNB, 7 without eMBB (the last three sum to 101, as in Phase 0; the split by cause differs from the memo's 95 / 6 only because the checks run in a different order). The notebook's recorded output is 706 reservations, 225,313 rows (train 163,960 / test 61,353). The new totals are 1,120 rows lower (0.5%). I did not attribute the difference among the three causes (windows before `t0`, dropped eNB-less windows, the new eMBB alignment). 98 reservations still have fewer than 4 eMBB UEs (`n_embb_ue`), so the reward scale is not constant. These are counts, not reproduced results.

Checks on the written parquet [V]: no NaN in the state, none in `ns_*` of non-final rows, no `win` step above 1 inside an episode, lags imputed on 0.7-0.8% of rows (1,625).

## Cost table [V]
24 cells (8 actions × 3 bins), train only. Minimum 997 windows and 9 reservations per cell. Cells are well supported in windows but not in reservations (see D5). Example: action 1 (21 PRB, PF), load bins 0/1/2: 0.014 / 0.101 / 0.289. Out-of-range load: 128 rows have `nof_ue > 8.1` and are put in the last bin.

## Limits and open points
- **[H] eMBB clock.** `ue_metrics.time` has no absolute clock. The UE start is estimated as `first bs/<IMSI> Timestamp − first is_attached time`. Over 2,923 UE files, the estimated start minus `t0` has median 0.51 s, p5 −1.7 s, p95 3.8 s. 124 are beyond ±5 s, 63 beyond ±30 s (40 of them earlier than `t0 − 30 s`; minimum −1,455 s). A UE that starts before `t0` is only trimmed. 240 UE files could not be aligned (no BS file or no attach) and are excluded from the reward sum. The estimate is not independently validated.
- **[H] URLLC clock.** `Received Time` is seconds of the day; the whole-hour shift is picked per reservation. The 0 h case covers 1,080 of 1,084 reservations in Phase 0.
- **[P] Not fixed here.** D4 showed radio+load features alone give 20.5% accuracy on the 8 actions, and the scheduler is readable at 71% by boosting. Removing the same-window reward does not remove that, so the "policy = configuration classifier" caveat stands. The configuration is constant per reservation, the window is 5 s, and the train/test behaviour policies still differ (train is RR-dominated: PF share is 25%).
- **[Q]** The notebook's bin convention at the edges is unchecked (right-inclusive here).  Window means of `nof_ue` are continuous, so only exact edge values are affected.
- **[Q]** Which of the 1,120 missing rows come from which change.

## Next
Phase 2 (not started): baselines and training-free policies on this parquet, then the state-leak re-check (D4) on the new 10-dim state.
