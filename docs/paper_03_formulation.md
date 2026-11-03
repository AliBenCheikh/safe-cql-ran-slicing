# Étape 15 : section 03 « Problem Formulation » (`paper/sections/03_formulation.tex`)

Réécriture de III-C (états, actions, récompense, coût, objectif) du PDF original. Le PDF et le notebook ne sont pas modifiés. III-A, III-B et IV sont dans `02_data_audit.tex` : la section 03 y renvoie sans les répéter.
Aucun chiffre ne vient de l'ancien PDF : tous viennent du registre (`docs/registre_affirmations.md`). Test : `tests/test_paper_03_formulation.py` (identifiants `% REG:` présents dans le registre, phrases sans `% REG:`, absence de chiffres retirés).

## Point à trancher avant d'écrire la section 05 (résultats)

La formulation demandée est **à un pas (γ = 0)**. Or l'agent principal de E12 (`safe_cql_a0.1`) a été entraîné avec **γ = 0,7** (`src/common.py`, `GAMMA = 0.7`) ; γ = 0 est l'ablation `safe_cql_a0.1_g0` (E12-i). Tous les chiffres E12 du registre, hors E12-i, décrivent donc un agent entraîné avec amorçage, évalué comme sélecteur à un pas. La section 03 le dit (§ Scope). Il faut soit présenter γ = 0,7 comme variante d'entraînement de la même cible, soit refaire l'évaluation principale avec γ = 0 (ce qui serait une troisième lecture du test, NO-blind).

## Liste 1 : phrases de l'original supprimées ou changées

| # | original | sort | raison |
|---|---|---|---|
| 1 | « We formulate the problem as a constrained MDP M = (S, A, P, R, C, γ) with unknown kernel P… » | remplacé par un bandit contextuel contraint, γ = 0 | D1-a, D1-c, NO-seq ; R1-W1, R2-W2 |
| 2 | « Each decision step is a non-overlapping 5 s window » | gardé (fenêtre de 5 s) | WIN-a |
| 3 | « ≈ 4 Hz… ≈ 20 samples per UE—enough to average out sub-second fading and yield a reliable violation estimate, yet short enough to track the traffic dynamics » | supprimé (la partie « 4 Hz, ≈ 20 échantillons » est dans la section 02) | E13b-c : le coût n'atteint le critère de 34 paquets que pour 7 réservations sur 12 ; E13b-e : aucune sensibilité à la fenêtre ; R2-W1 |
| 4 | « The state s_t = [x_t, h_t] ∈ R^12 » avec ρ_t et ℓ_t courants (éq. 2) | remplacé par 10 dimensions | AU-a ; R1-W1 |
| 5 | « …lets the policy track demand trends without a recurrent architecture » | supprimé | aucune ligne du registre ; suggère une dynamique (NO-seq) |
| 6 | « Each variable is z-scored on training-split statistics only » | retiré de la section | aucune ligne du registre (la mention n'existe que dans `phase1_pipeline.md`) |
| 7 | « The state excludes the current PRB split and scheduler: … would confound situation with action » | changé | D4-a : l'état prédit pourtant l'action (30,5-32,8 % avec les lags seuls, contre 12,4 %) ; D1-a ; R1-W1 |
| 8 | « The action jointly sets the PRB split and MAC scheduler… |A| = 8 » | gardé | PLAT-a |
| 9 | « The fifth configuration (no PRBs reserved for URLLC) is excluded as a degenerate, load-confounded case » | changé | D1-b : l'écart « pas de slicing » / « 50 PRB eMBB » n'est pas expliqué ; la qualification « dégénéré, confondu avec la charge » n'a pas de ligne dans le registre |
| 10 | « These actions are exactly those present in the traces, so the policy is optimized and evaluated only over decisions with real data support » | changé | D6-c (3 scripts sur 19 couvrent les 8 actions), D5-a (cellules pauvres en réservations) |
| 11 | Éq. (5), « rt ranges from 0 to 23.5 Mbps, with a mean of 7.65 Mbps » | chiffres supprimés | absents du registre |
| 12 | « Averaging each UE bitrate before aggregation avoids giving disproportionate weight to UEs with more samples » | justification supprimée, formule gardée en mots | aucune ligne du registre (la formule vient du code, liste 2) |
| 13 | « the reward is computed from all measured KPMs rather than predicted by a performance model » | reformulé en « lue dans les logs » | AU-a ; formulation minimale |
| 14 | « eMBB UEs… the eMBB slide » (coquille) | corrigé | R3-W3 |
| 15 | « Restricting the cost to the URLLC slice is essential… this tail-sensitive rate defines safety » | supprimé | NO-safe ; R1-W2 |
| 16 | « The mean per-window cost is 0.053 and 33% of windows contain a violation—dense enough to constrain directly » | supprimé | absents du registre ; E13d-c donne 0,056338 sur le train, différent de 0,053 |
| 17 | « We also report the URLLC 99th-percentile latency as a tail-aware secondary metric » | supprimé | R1W2-no : aucune analyse de queue n'existe ; R1-W2 |
| 18 | Éq. (7), objectif actualisé avec γ = 0,7 | remplacé par l'objectif à un pas, d = 0,03 | NO-seq, D1-c |
| 19 | « The asymmetry is deliberate: JR is discounted… since a decision already fixes the violation rate within its 5 s window and the operator only requires the average to stay below d » | supprimé | aucune ligne du registre ; « l'opérateur exige » n'a pas de source (NO-source) |
| 20 | « We set γ = 0.7: … empirically the loss diverges at γ = 0.99 but converges at γ = 0.7 » | supprimé | aucune ligne du registre ; E2-c : γ = 0 ne résout pas la dérive de λ |
| 21 | « We solve (7) by Lagrangian relaxation… deferring the cost estimate and adaptive optimization of λ to Sec. V-D » | gardé pour la relaxation ; « adaptive » non repris | NO-budget (le λ « converge près de 12,9 » est contredit : AU-f, E2-a) |
| 22 | « Safe-CQL », « safe » comme propriété de l'objectif | remplacé par « mean per-window cost budget » | NO-safe |

## Liste 2 : phrases de la section 03 que le registre ne suffit pas à soutenir

| # | phrase (section 03) | ce qui manque | support actuel |
|---|---|---|---|
| 1 | Les 10 composantes de l'état (éq. 1 : `nof_ue`, `rsrp`, `dl_snr`, `dl_mcs`, `dl_bler`, `ul_buff`, deux lags de la récompense et de `urllc_p50`) | AU-a ne donne que le nombre (10) et le retrait des colonnes courantes | `docs/phase1_pipeline.md` (ligne « State ») ; `src/build_dataset.py`, `STATE_COLS` |
| 2 | « averaged over the samples of the attached eMBB UEs » (agrégation des indicateurs radio) | aucune ligne du registre | `src/build_dataset.py`, `_embb_stream` (moyenne sur les échantillons des UE eMBB attachés) |
| 3 | Définition de la récompense : somme sur les UE eMBB attachés de la moyenne par fenêtre de `dl_brate`, en Mbps | D2-b ne dit que « sommait des fenêtres décalées » | `src/build_dataset.py`, `_embb_stream` et `reward_embb_Mbps = embb_slice_bps / 1e6` |
| 4 | « We frame the selector… in the style of an rApp hosted by the Non-RT RIC » | NO-nearrt dit « à justifier » ; la justification d'échelle de temps manque (l'échelle d'un rApp n'est pas dans le registre) | `\cite{TODO-oran-timescales}` ; E13b-d, E13b-e, WIN-a |
| 5 | « γ = 0 follows from D1… no logged data constrains a value that bootstraps » | D1 justifie de ne pas modéliser de transitions, pas que γ = 0 soit meilleur ; E2-c : γ = 0 ne résout pas la dérive de λ | D1-a, D1-c ; voir le point à trancher en tête |
| 6 | « The agents of the main comparison were trained with a discount of 0.7 » | E12-i le suppose (ablation γ = 0 « par rapport à γ = 0,7 ») sans le dire en une ligne | E12-i, E2-b ; `src/common.py` (`GAMMA = 0.7`) |
| 7 | « a decision per window is a modelling convention » (une action par réservation, une instance par fenêtre) | l'unité de décision (fenêtre ou réservation) n'est fixée par aucune ligne | D1-a, D1-c, NO-seq (« évaluée au niveau réservation ») |
| 8 | « Lags are formed inside an episode » | D3-a dit « épisodes séparés » ; la construction des lags n'est pas dans le registre | D3-a ; `docs/phase1_pipeline.md` |
| 9 | « the lags are outcomes recorded under the logged configuration… the context contains outcomes of the action » | raisonnement (D1-a et D4-a), non testé | D1-a, D4-a |
| 10 | « a learned selector may partly act as a classifier of the logged configuration » | D4-a est une mesure sur l'état à 12 dimensions ; D4-d [Q] : non re-mesuré sur 10 dimensions | D4-a, D4-d, NO-dyn |
| 11 | Éq. (3) : coût en pourcentage de paquets, latence `(Received − Sent) × 10³` ms | COST-a donne la formule en ms mais pas la forme de l'éq. (3) | COST-a, E13d-a |
| 12 | « The cost is a rate over a window and not a tail statistic » | seule R1W2-no (« non fait ») le soutient | R1W2-no |
| 13 | « a coarse estimate: 47 % to 63 % of its cells have… a CI that contains d » | D5-b porte sur 3 et 4 bins et sur train ; la table canonique à 3 bins est celle de « 15/24 » seulement | D5-b |
| 14 | « It also treats the load bin as if it were independent of the action » | le registre ne dit pas ce que fait la table ; D7-c dit seulement que le bin n'est pas démontré exogène | D7-c, D5-c |
| 15 | Éq. (4) : espérance sur « la distribution des contextes » | la distribution cible (test, déploiement) n'est définie par aucune ligne | — |
| 16 | « r(x, a) and c(x, a) denote the expected reward and cost » : identification de ces espérances | repose sur (A1) et (A2) ; (A2) est contredite pour le scheduler | D7-b, D8-b, D7-c |
| 17 | « a standard relaxation of constrained problems » | aucune ligne ; référence manquante | `\cite{TODO-lagrangian-relaxation}` |
| 18 | « it carries no probabilistic guarantee » | NO-safe interdit la garantie ; la phrase ne dit pas pourquoi (351/510 réservations seulement ont un coût ≤ d : E13d-d) | NO-safe, E13d-d |
| 19 | « the estimation of the cost and the update of λ are described in Sec. \ref{sec:method} » | la section 05 (méthode) n'existe pas encore ; les renvois `sec:method` et `sec:results` sont pendants | — |
| 20 | « 13 h to about 8 days apart » (A2) | D8-b donne ≈ 8 jours pour deux scripts, ≈ 13 h pour c40f2fe7 (formulation raccourcie) | D8-b |

## Renvois pendants

`sec:method` et `sec:results` n'existent pas encore dans `paper/sections/`. `\cite{TODO-oran-timescales}`, `\cite{TODO-budget-latency-source}` et `\cite{TODO-lagrangian-relaxation}` restent à créer (le premier et le deuxième existent déjà dans la section 02).
