# Audit report — Safe-CQL for eMBB/URLLC slicing in O-RAN

Read-only scientific and implementation audit of `Safe_CQL.pdf` and `Safe-CQL-Notebook.ipynb`, against `reviews/reviewer_comments.md`.

## 0. Scope, method, limits

**Method.** I read CLAUDE.md, the three reviews, all 6 pages of the PDF and the source and recorded output of all 31 notebook cells (all are code cells, no markdown cells). The notebook was only parsed as JSON. I changed no existing file.

**Limits.**
- No raw data was read and no cell was re-run. No training or GPU job was launched.
- Every number quoted from the notebook is a **recorded output, not a reproduced result**.
- Cell references use the 0-based notebook index. `Cellule n` is the label in the cell's header comment. `cell 22 l.35` means line 35 of that cell's source.

**Tags used throughout.**

| Tag | Meaning |
|---|---|
| **[V]** | Verified fact in code (or in the PDF text). |
| **[H]** | Hypothesis that needs the raw data to check. |
| **[P]** | Confirmed problem. It follows from the code or recorded output alone. |
| **[Q]** | Open question. |

---

## 1. Notebook inventory (31 cells, each with recorded output)

| Idx | Label | Purpose | Recorded output / status |
|---|---|---|---|
| 0 | Cellule 1 | Mount Drive, 7z and tar extraction of the 10.4 GB archive | 31,490 files under `dataset-kpm` (cluster_1..3) |
| 1 | 1bis | File census | 22,915 csv, 8,574 .mgn, 7,458 mgen.csv |
| 2 | 1ter | Experimental plan | 3 clusters × 5 slicing × 2 schedulers = 30 combinations. Output is truncated in the file |
| 3 | 1quater | Schema of `ue_metrics.csv` (21 columns, `;` separator) and `mgen.csv` | Schema only |
| 4 | 2bis | Per-cluster profile | Uses only the first 60 files per cluster (`N_SAMPLE_UE=60`). NaN rate 0.01% on that sample |
| 5 | 2ter | SLA calibration | 74,123,867 packets, 55.6% above 20 ms. Includes **all** mgen files, eMBB UEs included. This differs from the URLLC-only cost |
| 6 | 2quater | Latency by slicing/scheduler/cluster | Sample of 1,500 files |
| 7 | 2quinquies | Throughput vs latency per slicing | **[P]** `lat_p50` is hard-coded (l.51: 625.3/262.1/128.0/80.7/44.6). It does not match the cell 6 output (706.1/268.4/132.1/79.1/43.6) |
| 8 | 2sexies | Optimum vs load | Mostly NaN cells. sl5 exists only at low load |
| 9 | 2septies | Load/slicing confounding | sl5: 250 of 309 reservations at 4 UEs. sl1–4: about 8 UEs. Factors are confounded |
| 10 | Cellule 3 | `bs/` and `enb_metrics.csv` | Schema: `time, nof_ue, dl_brate, ul_brate` |
| 11 | Cellule 4 | Throughput↔latency trade-off, sl1–4 | r(PRB, throughput)=+0.753, r(PRB, latency p50)=+0.017, r(PRB, viol)=+0.039, n=384 |
| 12 | Cellule 5 | Trade-off stratified by eMBB demand | corr in the high-demand tercile = −0.011. The cell's own message: "~0 → no trade-off" |
| 13 | Cellule 6 | Intra-reservation variability | CV median 0.41, p90/p10 = 2.9, n=88 |
| 14 | Cellule 7 | RR vs PF | URLLC p99 18.3 ms (RR) vs 97.4 ms (PF), Mann-Whitney p=0.0000, n=426 |
| 15 | Cellule 8 | RR vs PF × load | PF violation 5.3/13.5/18.0%, RR 1.5/2.0/2.5% (low/mid/high load) |
| 16 | Cellule 9 | First window builder, tested on 1 reservation | `nof_ue` = 0.0 on the first 12 windows (bug fixed later) |
| 17 | 9bis | `nof_ue` diagnostic | eNB clock is epoch-ms, UE clock is ms since start. Different t0 |
| 18 | 9ter | Sparsity of the cost | PF windows: 61% have viol>0 |
| 19 | Cellule 10 | Builder v2, writes parquet | Reward summed over rows, inflated by about ×80 (mean 153 Mbps) |
| 20 | 10bis | Reward scale diagnosis | About 4 rows/s, 20 rows per 5 s window |
| 21 | Cellule 11 | Final builder, **overwrites the same parquet** | 706 OK / 101 skipped of 807. 225,313 transitions (train 163,960 / test 61,353). Reward 0–23.47, mean 7.65. Cost mean 0.053, >0 in 33% of windows |
| 22 | Cellule 12 | CQL tuples and train-only z-score | 12-dimensional state, 8 actions |
| 23 | Cellule 13 | BC baseline | Test accuracy 0.403, scheduler accuracy 0.664, PRB accuracy 0.576 |
| 24 | 13-VIZ | BC learning curves | Figure only. Computed on the **test** cluster |
| 25 | Cellule 14 | CQL, γ=0.7, α=0.5 | Matching 41.4%, reward 7.74, cost 0.040. Versions 14/14b are "deleted" |
| 26 | 14-VIZ | CQL curves | Figure only |
| 27 | Cellule 15 | Safe-CQL (CQL-Lagrangian, tabular cost) | λ=12.22 at epoch 99, train cost_π 0.032, test reward 7.70, cost 0.030. Versions 15/15b/15c are "deleted" |
| 28 | 15-VIZ | Safe-CQL curves | Figure only |
| 29 | Cellule 20 | FQE | CQL 26.63±0.18 / 0.088±0.020 (4 seeds). Safe 26.17±0.04 / 0.076±0.005 (2 seeds) |
| 30 | Cellule 21 | Final figures and LaTeX table | Table II, Fig. 1–3 |

**[V]** Header labels jump from Cellule 15 to Cellule 20, so cells 16–19 do not exist in this file.

**[Q]** Several versions were deleted: 14/14b, 15/15b/15c and the earlier FQE and deliverables versions. The evidence the paper uses to justify γ=0.7 ("loss diverges at γ=0.99") and the tabular cost ("learned Q_cost proved unstable") is **not in the notebook**. It cannot be audited.

---

## 2. Action assignment: from the folder path to `A_train` / `A_test`

**Trace [V].**
1. The path is `…/cluster_k/slicing_s/scheduling_m/RESERVATION-x/…`.
2. `cfg(res)` extracts `cl`, `sl`, `sc` from that path with regexes (cell 21 l.23-25).
3. In `build_reservation`, the dict `PRB_EMBB={'sl1':9,'sl2':21,'sl3':30,'sl4':39}` and `SCHED_BIN={'sc0':0,'sc2':1}` give `prb_embb` and `sched` (cell 21 l.93).
4. These are written as **scalar columns on every window** of the reservation (cell 21 l.93).
5. `action = prb_idx*2 + sched`, so values are 0..7 (cell 22 l.17-20).
6. `split = 'test' if cl=='cl1' else 'train'` (cell 21 l.94). Cluster 1 becomes the test set and clusters 2 and 3 the training set.
7. `A_train`, `A_test` are the `action` column of each split (cell 22 l.64).

**Findings.**
- **[V]** The action is constant within a reservation, by construction. No per-window action source is read. Nothing in the pipeline can produce a mid-reservation change.
- **[H]** The testbed never changed configuration during a run. The path alone cannot prove this. The paper states it itself (Sec. III-C.5, VI-E), and the header of cell 25 says "action quasi-figée par épisode".
- **[P]** Within an episode, s_{t+1} does not depend on any decision. The data contain no counterfactual transition. Q(s,a) for a ≠ logged action is identified only by variation **across** reservations, which is confounded with cluster, load and run time. This is the substance of Reviewer 2's point 2.
- **[V]** The behaviour policy differs between train and test (recorded, cell 22):

  | | a0 | a1 | a2 | a3 | a4 | a5 | a6 | a7 | PF share |
  |---|---|---|---|---|---|---|---|---|---|
  | train | 28482 | 11090 | 34865 | 8042 | 30300 | 9737 | 34465 | 6979 | about 25% |
  | test | 7185 | 5774 | 7621 | 7436 | 6937 | 7837 | 8429 | 10134 | about 48% |

  The held-out cluster is almost uniform over actions, while training is dominated by RR.
- **[V]** The fifth slicing (50 PRBs for eMBB, none for URLLC) is excluded (cell 21 l.97-98). It exists almost only at low load (cell 9).

---

## 3. State variables: pre-action vs same-window as the reward

State (cell 22 l.33-40, paper Eq. 2–3): `nof_ue, rsrp, dl_snr, dl_mcs, dl_bler, ul_buff, reward_embb_Mbps, urllc_p50` + lag1 and lag2 of `reward_embb_Mbps` and `urllc_p50`. This is 12 dimensions.

| Variable | Window | Available before the action? | Evidence |
|---|---|---|---|
| `rsrp, dl_snr, dl_mcs, dl_bler, ul_buff` (current) | same 5 s window as r and c | No | cell 21 l.42-53 |
| `nof_ue` (current) | same window (eNB rows), `ffill/bfill`-filled | No | cell 21 l.80-86 |
| `reward_embb_Mbps` (current) | the reward of this transition | **No, it is the reward** | state l.35, `R` in cell 22 l.65 |
| `urllc_p50` (current) | same packets that define the cost `urllc_frac_viol` | No | cell 21 l.67-71 |
| `*_lag1`, `*_lag2` | windows t−1, t−2 | Yes | cell 22 l.22-30 |

**Confirmed problems.**
- **[P] The state contains the reward of its own transition.** `reward_embb_Mbps` is a state column and is also `R`. The paper writes it as ρ_t in x_t (Eq. 2) and defines r_t from the same window (Eq. 5). Strictly, only the lag columns are pre-action. The standard layout would be to build s_t from window t−1 and (r_t, c_t) from window t.
- **[P]** `urllc_p50` of the same packets as the cost is another same-window leak (into the cost).
- **[H]** Since the action is fixed per reservation and throughput, MCS and BLER depend strongly on the PRB level, the state may leak the logged action. The recorded BC test accuracy is 40% against a 12.5% chance level for 8 classes, and scheduler accuracy is 66%. Quantifying this needs data (for example, BC on lag-only features).
- **[P] Windows are indexed from different time origins.**
  - eMBB windows use each UE's own `time.min()` (cell 21 l.42). UEs are therefore shifted relative to each other before being summed.
  - URLLC windows use `Received Time.min()` (cell 21 l.67).
  - eNB windows use `time.min()` after dropping rows with `nof_ue==0` (cell 21 l.80).
  - The three are joined on the relative window index.
  - Cell 17 shows the eNB clock is epoch-ms and the UE clock is ms since start.
  - **[H]** The three streams start at the same instant. Not checkable without the data.
- **[H]** `next_row = shift(-1)` and the lags (`shift(1/2)`) are taken on **rows** after an inner join (cell 22 l.26, l.45). If any window is missing, s' is not window t+1. Check that `win` is contiguous.
- **[V]** `df['nof_ue'].ffill().bfill()` (cell 21 l.86) can carry a later value backwards in time.

---

## 4. Cost-table bins: Safe-CQL cell vs FQE vs final deliverables

| Location | Edges on `nof_ue` | Bins | Minimum support, fallback | Used for |
|---|---|---|---|---|
| cell 27 l.22-35 (Cellule 15, Safe-CQL) | [0, 3.5, 5.5, 8.1] | 3 | >20, else per-action mean | training, λ update, policy |
| cell 29 l.21-31 (FQE, CQL branch) | [0, 2.5, 4.5, 6.5, 8.1] | 4 | >50, else per-action mean | CQL (λ=0, so the term is inert) |
| cell 29 l.36-52 (FQE, Safe branch) | [0, 3.5, 5.5, 8.1] | 3 | >20 | Safe-CQL retraining and FQE |
| cell 30 l.23-34 (deliverables) | [0, 2.5, 4.5, 6.5, 8.1] | 4 | >50 | `ope()` for **all** agents, λ sweep, Fig. 3 |
| cell 30 l.87-102 (deliverables) | [0, 3.5, 5.5, 8.1] | 3 | >20 | `train_safecql` only |

**Inconsistencies.**
- **[P] Safe-CQL is trained against the 3-bin table, but Table II's "Tabular OPE" evaluates it on the 4-bin table** (`ope(pi_safe)`, cell 30 l.83 and l.182). Training and evaluation tables differ.
- **[P] The paper is inconsistent with itself.**
  - Sec. V-C describes three bins.
  - Fig. 1 and Fig. 3 of the notebook show four (`low / med- / med+ / high`, cell 30 l.262).
  - The 3-bin table printed in cell 27 differs from Fig. 1. For example, (30,RR) at low load is 0.147 in cell 27 and about 0.10 in the figure.
  - The minimum-support threshold is 20 in the paper but 50 in the 4-bin code.
- **[P] Tabular OPE is not a held-out evaluation.** Both tables are fitted on the training clusters. Test states only choose the row. It cannot reveal a cluster shift. It also measures the same kind of object the safe policy minimises, so "cost 0.030 = budget 0.03" is close to by-construction. Only the matching estimator uses test outcomes.
- **[P] The dual variable has not converged.** The recorded run shows λ increasing monotonically up to 12.22 at epoch 99, and `cost_π` at 0.032 stays above the budget 0.03 (cell 27). The paper says "converges near 12.9" and that the cost "settles onto the budget".
- **[P] The next-state bin is the current state's bin.** Cell 27 l.83 (`b_next=bin_tr_t[idx]`) and cell 29 l.114 use `idx`, the current row. The comment says "approx: bin stable dans l'épisode".
- **[V]** Fig. 1 draws the SLA line and a "SLA-violating region" at 2% (cell 30 l.219-220), while the safe agent sits at about 3% (budget 0.03). The agent is drawn inside the violating region. Cell 30 l.217 also draws a visual guide segment from the corner of the plot to the first point (acknowledged in the comment as "purement graphique").

---

## 5. FQE: is the bootstrap done with the target policy?

**Answer: no. [P]** (`fqe`, cell 29 l.135-160)

1. **Bootstrap action.** `an=(qe_r(sn)-lam*ct_tr_arg[idx]).argmax(1)` (l.150) uses the **FQE network's own Q-values**. The target policy is `argmax(Qr_te − λ·ĉ)`, with `Qr_te` coming from the trained agent. That policy is used only for the **final** action `a_te` (l.157). The evaluated quantity is therefore greedy fitted-Q-iteration on `qe_r`, not the value of the target policy. For CQL (λ=0) it is plain `argmax qe_r`, with no conservatism.
2. **Cost bootstrap.** `tc` (l.152) reuses the action `an` chosen with the reward network. This is consistent only if `an` is the target action, which it is not (point 1).
3. **Unit mismatch.** The agent Q is trained on normalised rewards `rn(R)` and λ lives in those units. FQE is trained on raw Mbps `R_tr` (l.142) but applies the same `lam*ct`. The penalty is relatively weaker by about `R_STD`. **[H]** `R_STD` is not printed (the train mean is 7.73).
4. **Wrong state for the cost row.** `ct_tr_arg[idx]` is the cost row of the current state, not of `sn`.
5. **No target network**, one network bootstraps from itself, 6 epochs only.
6. **The value scale differs from Table II.** With γ=0.7 the value is a discounted sum, about 3.3× the per-window value (26.6 vs 7.7 Mbps). It is not comparable to the matching and tabular columns.
7. **Seeds and spread.** CQL 0.088±0.020 (4 seeds) vs Safe 0.076±0.005 (2 seeds). `np.std` is used with ddof=0. The intervals overlap at 1σ, so "confirms the ranking" (paper Sec. VI-C) is weak. FQE is trained on clusters 2–3 and evaluated on cluster-1 states, including actions not supported by the data.

**Minimal fix.** Bootstrap with the target policy's own action:
`a' = argmax_a [Qr_agent(s',a) − λ·ĉ(a, bin(s'))]`, using the trained agent. Use the same reward units, a target network, the next-state bin, and at least 5 seeds for each agent. Report discounted values as such.

---

## 6. Reviewer concerns: code, scientific impact, minimal correction

| Concern | Where | Scientific impact | Minimal correction |
|---|---|---|---|
| **R1-W1.** State omits a_{t−1}, violates Markov | cell 22 l.22-41 (state, lags); paper Sec. III-C.1 | **[V]** The state does omit the action. More serious: the state also contains same-window outcomes (§3). Because the action is constant per reservation, adding a_{t−1} would make the action trivially predictable from the state and add no information. | Build s_t from window t−1 and take (r_t, c_t) from window t. State clearly that the problem is partially observed or is a contextual problem with history. Do not add a_{t−1} unless the action varies. Recurrent networks (reviewer's suggestion) are not the minimum. |
| **R1-W2.** Coarse tabular cost over 3 load bins | cell 27 l.18-35; cell 29 l.21-52; cell 30 l.23-34, l.87-102 | **[P]** Mean violation fraction over broad bins hides the tail. Per-cell sample sizes are not reported. Three different tables are in use (§4). | Use one table. Report N and a confidence interval per (action, bin) cell. Add a sensitivity analysis on bin count and edges. Show a tail metric (`urllc_p99` is already in the parquet) next to the mean. A continuous cost critic is an ablation for a later phase. |
| **R2-W1.** 5 s window is not Near-RT (10 ms–1 s) | `WINDOW_S=5.0` (cell 21 l.9); paper Sec. II says 10 ms–1 s | **[V]** The paper's own timescale statement contradicts its 5 s step. | Reframe as a slower-loop (Non-RT RIC / rApp-like) controller, or add a window-size sensitivity (KPM is about 4 Hz, cell 20). |
| **R2-W2.** Static data, config fixed per reservation | cell 21 l.93; cell 22 l.20 (§2) | **[P]** No counterfactual transitions. Policy ranking relies on cross-reservation differences. The sequential-RL framing is not identified by the data. | State it in the abstract and limitations. Claim configuration-level policy selection, not sequential control. Evaluate by reservation with a cluster/reservation bootstrap. |
| **R3-W1.** Only a BC baseline | cell 23 | **[V]** Confirmed: BC is the only baseline in the main table. | Add training-free baselines from existing tables: always-RR per PRB, always-PF, best fixed configuration, table-greedy (maximise reward s.t. ĉ ≤ d). The CQL + post-hoc penalty sweep already exists (cell 30 l.152-170). |
| **R3-W2.** Novelty is incremental | paper Sec. II | The paper already says "the algorithm itself is not novel". | Reposition the contribution on the audit. No code change. |
| **R3-W3.** Writing and references | PDF p.2, p.4, p.6 | **[V]** The "[?]" is present in Sec. II ("multi-agent xApp coordination [?]"). The paragraph in Sec. V-B starts with "γ = 0.7 (Fig. 2)". Typos: "reinforcementl earning", "load.The", "cost;In short". | Fix these. **[Q]** Verify that ref. [15] (title: "Open-source testing tools for smart grid communication network") is the right citation for MGEN. I did not check it. |

---

## 7. Claims: supported by the code vs unverified without the raw dataset

### 7.1 Supported by recorded notebook output (not reproduced)

| Claim | Source |
|---|---|
| 1,116 reservations, 30 configurations, up to 8 UEs | cells 2, 9 |
| PRB↔throughput about +0.75, PRB↔latency about +0.02 (paper writes +0.73) | cell 11 |
| RR p99 about 18 ms vs PF about 97 ms, Mann-Whitney significant | cell 14 |
| Configuration/load confounding, sl5 at low load | cell 9 |
| 5 s window ≈ 20 samples at 4 Hz | cell 20 |
| 225,313 transitions, reward 0–23.5 (mean 7.65), cost mean 0.053 in 33% of windows | cell 21 |
| Table II numbers, λ = 12.9 ± 0.6 | cells 27, 30 |
| RR beats or matches PF in throughput at every split | cell 14 |
| No online exploration | by construction |

### 7.2 Code-supported but with a caveat
- "Safe-CQL" is a reward Q-network plus a **lookup in an empirical cost table**. No cost critic is trained. The paper's cost discount `γ_c = 0` is therefore implicit.
- λ enters only the action choice (policy extraction) and the bootstrap action. It does not enter a loss.

### 7.3 Not supported, or only weakly supported
- **"Trained on roughly 2.25×10⁵ transitions"** (abstract). The training set has 163,960 transitions. 225,313 includes the 61,353 test transitions.
- **"PF p99 from 86 to 137 ms", "more than 130 ms"** (Sec. IV-B, abstract). The recorded cell 14 shows PF p99 of 80–127 ms by slicing. I could not locate the source of 86–137.
- **"≈0.01% missing"** comes from a 60-file sample per cluster (cell 4).
- **"λ converges near 12.9", "settles onto the budget"**. The recorded run is still rising and above budget (§4).
- **"FQE is structurally independent, guards against a shared bias"**. See §5.
- **"25–47% reduction"** mixes comparison baselines (BC vs CQL) and estimators (matching vs tabular):
  - 0.040 → 0.030 is −25% (CQL, matching).
  - 0.049 → 0.030 is −39% (CQL, tabular).
  - 0.057 → 0.030 is −47% (BC, tabular).
- **"1–2% throughput loss"**: 2.0% (CQL, matching), 1.2% (CQL, tabular), 2.4% (BC, tabular).
- **"RR stays safe across all loads (typically <6%)"**. Cell 27 shows 0.147 at (30,RR), low load.
- **Generalisation to an unseen deployment**. It rests on one held-out cluster, 2 seeds for Safe-CQL and no cluster-level interval.
- **"Validation" curves** (Fig. 2) are computed on the test cluster (cells 23–28). The test set was used for monitoring. **[Q]** whether it influenced the choices of γ, α, epochs or bins is unknown, because the deleted versions are gone.

---

## 8. Additional issues not raised by the reviewers

1. **[P]** Matching OPE compares policies on different subsets (match rates 38.7–41.4%). The subset depends on the policy.
2. **[P]** Seeds are 5 for BC and CQL but 2 for Safe-CQL, and `np.std` uses ddof=0. "0.030±0.000" hides the real spread.
3. **[P]** The behaviour policy shifts strongly between train and test (§2).
4. **[V]** γ=0.7 was chosen after observing divergence at 0.99 on this dataset (header of cell 25). The explanation offered ("near-immediate effect") may simply reflect the near-constant action per episode.
5. **[P]** The notebook has hard-coded values (cell 7, l.51).
6. **[V]** The reward is summed over four eMBB UEs. Each UE's windows start at its own t0 (§3).

---

## 9. Priority and minimal corrections

**Priority 1: invalidate or reshape the main claims.**
1. Remove the same-window reward and median latency from the state, or shift the state to window t−1 (§3).
2. Evaluate FQE with the target policy's actions and consistent units (§5).
3. Use one cost table (bins and thresholds). Evaluate Tabular OPE with the table the agent was trained on, and say it is not held-out (§4).
4. State the static-action limitation in the abstract and conclusion. Rename the contribution accordingly (§2, R2-W2).

**Priority 2: strengthen the evidence.**
5. Report λ convergence honestly, or train longer. Report N and CI per cost cell.
6. More seeds for Safe-CQL, ddof=1, and a reservation- or cluster-level bootstrap.
7. Add training-free baselines (R3-W1).
8. Clarify the O-RAN framing (R2-W1).

**Priority 3: presentation.**
9. Fix the "[?]", the typos, the 2% vs 3% SLA drawing, the transition count in the abstract and the p99 range.

**Open questions (need data, authors or deleted versions).**
- Did the configuration ever change within a reservation?
- Do the three time origins coincide (eMBB, URLLC, eNB)? Is `win` contiguous?
- What evidence justified γ=0.7 and the tabular cost (deleted cells)?
- What is `R_STD`, and how large is the unit mismatch in FQE?
- Was the test cluster used for any model or hyperparameter choice?
- Is ref. [15] correct for MGEN?
