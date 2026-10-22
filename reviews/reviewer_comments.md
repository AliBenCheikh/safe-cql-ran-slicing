# Rapports des reviewers — GC 2026-review
# Safe-CQL pour l'allocation eMBB/URLLC en O-RAN
# Document de référence. Ne pas modifier.

---

## Reviewer 1 — GC 2026-review

| Critère | Note |
|---|---|
| Relevance and timeliness | Good (4) |
| Technical content and scientific rigour | Valid work but limited contribution (3) |
| Novelty and originality | Some interesting ideas and results on a subject well investigated (3) |
| Quality of presentation | Excellent (5) |

**Submission policy :** yes

### Strong aspects
1. Using real network traces from a digital twin avoids the simulation-to-reality gap common in RL networking research.
2. The data audit systematically isolates the effects of PRB allocation from MAC scheduling.

### Weak aspects
1. The state formulation explicitly removes the current PRB split and scheduler. In wireless networks, the previous action fundamentally shapes the current buffer occupancy and observed metrics. Removing the action from the state space violates the Markov property, reducing the MDP to a Partially Observable MDP without the necessary mathematical treatment for hidden states. This is a fatal flaw in the theoretical foundation.
2. The empirical cost model relies on a tabular average of URLLC violation rates mapped to just three active-UE load bins. This coarse discretization destroys the high-resolution channel dynamics essential for URLLC modeling. Averaging tail probabilities over broad load bins is mathematically inadequate for strict SLA enforcement and physical layer realities.

### Recommended changes
1. Reformulate the state space s_t to include previous actions a_{t-1} and apply recurrent architectures to satisfy the Markov property accurately.
2. Replace the coarse tabular cost model with a continuous, distribution-aware safety critic that accurately captures URLLC tail latencies without collapsing metrics into bins.

---

## Reviewer 2 — GC 2026-review

| Critère | Note |
|---|---|
| Relevance and timeliness | Good (4) |
| Technical content and scientific rigour | Marginal work and simple contribution. Some flaws. (2) |
| Novelty and originality | Minor variations on a well investigated subject (2) |
| Quality of presentation | Readable, but revision is needed in some parts (3) |

**Submission policy :** yes

### Strong aspects
- This paper investigates the problem of safe resource allocation in O-RAN slicing by proposing an offline reinforcement learning framework for Near-RT RIC xApps.

### Weak aspects
1. The paper positions the control framework as a Near-RT RIC xApp. However, each decision step is defined as a 5-second non-overlapping window. According to O-RAN Alliance specifications, Near-RT RIC control loops operate strictly within 10 ms to 1 second, whereas control intervals of 5 seconds belong to Non-RT RIC rApps.
2. Standard offline reinforcement learning relies on datasets collected by behavior policies dynamically changing actions across states, thereby capturing the causal impact of decisions on subsequent state transitions. In contrast, the dataset here consists of static benchmark experiments where the slicing configuration and scheduler were held strictly constant throughout each reservation.

### Recommended changes
1. Clarify the architectural alignment with O-RAN.
2. Address the static nature of the underlying data.

---

## Reviewer 3 — GC 2026-review

| Critère | Note |
|---|---|
| Relevance and timeliness | Acceptable (3) |
| Technical content and scientific rigour | Marginal work and simple contribution. Some flaws. (2) |
| Novelty and originality | Minor variations on a well investigated subject (2) |
| Quality of presentation | Substantial revision work is needed (2) |

**Submission policy :** yes

### Strong aspects
1. The motivation for offline and safe offline training is good.
2. The scope is relevant and the topic is well presented and organized.

### Weak aspects
1. Only a BC baseline is considered, which is expected to perform bad given that the training happens offline without exploration. Additional baselines are needed.
2. Offline RL and safe offline RL, including CQL and safe CQL, have been studied a lot in the literature. The novelty seems to be incremental.
3. The manuscript writing should be double checked again. Missing reference in Section II in page 2: "multi-agent xApp coordination [?]", Section V.B. paragraph starts with \gamma = 0.7 (Fig. 2). Overall, the writing is heavily affected with AI writing and should be double checked for technical / writing mistakes.

### Recommended changes
- Please refer to the weak aspects.
