# Étape 16 : section 04 « Offline Agents and Baselines » (`paper/sections/04_methods.tex`)

Réécriture de V-A à V-D du PDF original. V-E (OPE) et VI-A (protocole) iront dans une autre section (`sec:results` est un renvoi pendant). Le PDF et le notebook ne sont pas modifiés.
Test : `tests/test_paper_04_methods.py` (identifiants `% REG:` présents dans le registre, phrases sans `% REG:`, motifs interdits, hyperparamètres de la section présents dans `src/agents/`).

## Trois points qui changent le texte par rapport à l'original (faits lus dans le code)

1. **Il n'y a pas d'agent BC dans `src/`**, et BC n'entre pas dans E12 (`CONFIGS` et `BASELINES` de `src/e12_final.py`). La sous-section BC dit donc qu'aucun résultat BC n'est rapporté. Il faut soit écrire un BC (étape à part, avec ses tests), soit assumer son absence.
2. **La pénalité de Safe-CQL est dans la cible de Bellman, pas à la décision.** La politique est l'argmax de Q ; l'éq. (11) de l'original (`argmax Q − λĉ`) est supprimée. La pénalité utilise le coût de table de l'action **loguée** de la ligne (`batch["c"]`), pas celui de l'action choisie. Le signal dual (éq. 12) utilise l'action greedy sur les fenêtres d'entraînement et la table d'entraînement : il est dans l'échantillon.
3. **Le code n'a ni Q double écrêté, ni écrêtage de gradient, et τ = 0,005** (l'original dit τ = 0,01, minimum de deux critiques, écrêtage). La cible est de type double DQN (argmax du réseau en ligne évalué par le réseau cible).

Rappel du point ouvert de l'étape 15 : la formulation est à γ = 0, mais l'agent principal de E12 est à γ = 0,7 (γ = 0 est l'ablation). La section 04 le dit en § Common setup et § Frozen configurations.

## Liste 1 : phrases de l'original supprimées ou changées

| # | original | sort | raison |
|---|---|---|---|
| 1 | « We propose a trace-driven pipeline that turns an audited safety signal into a deployable constrained policy » | supprimé | « deployable » et « constrained policy » : NO-safe, NO-budget |
| 2 | « three offline agents of increasing capability—BC, CQL, adaptive safe CQL-Lagrangian… so no unsafe configuration is ever explored during training » | changé : cinq éléments (BC, CQL, IQL, table-greedy, Safe-CQL) ; « adaptive » et « increasing capability » supprimés | R3-W1 (baselines) ; NO-rl ; « adaptive » interdit par le brief ; E12-k |
| 3 | « We formulate the task as sequential RL rather than supervised learning or a contextual bandit for two reasons… » (deux paragraphes) | supprimé | contredit la section 03 (bandit contextuel) ; « the cost evolves within a reservation, so the state carries temporal history » : D1-c, NO-seq ; « the cost is near-immediate… » sans ligne de registre |
| 4 | « The short horizon γ = 0.7 is the deliberate consequence of this near-immediate effect » | supprimé | aucune ligne du registre ; E2-c : γ = 0 ne règle pas la dérive de λ |
| 5 | V-A : « BC trains a classifier πBC… with class weighting… reproduces the behavior policy and therefore inherits its high-cost PF decisions, serving… as the lower bound a useful offline method must beat » | remplacé par un paragraphe disant qu'aucun BC n'existe dans `src/` | R3-W1 ; code ; « borne inférieure » non soutenue |
| 6 | V-A : « held-out action-matching accuracy plateaus near 40%, scheduler accuracy (66%) exceeding PRB-level accuracy (58%) » | supprimé | sortie enregistrée du notebook (NO-notebook) ; calculé sur le test (audit) ; D4-a donne les mesures reproduites |
| 7 | V-B : « CQL… built on a Deep Q-Network… clipped double-Q learning (target = minimum of two critics), a Polyak-averaged target network (τ = 0.01), and gradient-norm clipping » | changé : cible double DQN, τ = 0,005, pas d'écrêtage ni de Q double écrêté | `src/agents/cql.py` (`CFG`, `cql_loss`, `train_cql`) |
| 8 | V-B : TD target « y = r + γ(1 − done) max_a′ Q_θ̄(s′, a′) » | changé : argmax du réseau en ligne, valeur du réseau cible, récompense divisée par `r_scale` | `src/agents/cql.py` |
| 9 | V-B : « penalty weight α = 0.5 » | changé : α ∈ {0,1 ; 0,5} selon la configuration (Table des configurations) | E12-k |
| 10 | V-B : « Unconstrained CQL (λ = 0) shifts some mass from PF toward RR relative to BC, yet still selects PF often enough… so constraint-free value maximization is not safe » | supprimé | repose sur BC et sur la Fig. 2 du notebook ; NO-safe |
| 11 | V-C : « Learning a cost critic Qc(s, a) by Bellman backup proved unstable… in one run labeling a high-violation PF action as safe—corrupting the constrained policy » | supprimé | aucune ligne du registre ; aucun rapport ne contient ce run |
| 12 | V-C : « This estimate is exact in expectation, far more robust than a function approximator under rare violations, and fully transparent » | supprimé | « exact in expectation » : D5-a, D5-b, D7-c (IC larges, bin non exogène) ; « far more robust » non testé |
| 13 | V-C : éq. (10), « cells with support Na,β < 20 fall back to the action marginal c̄(a) » | déplacé dans la section 03 ; la cible du repli n'est pas reprise | AU-b ne donne que le seuil de 20 fenêtres, jamais déclenché en phase 1 |
| 14 | V-D : éq. (11) `πλ(s) = argmax Qr(s, a) − λĉ(a, β)` | supprimé | code : politique = argmax Q, pénalité dans la cible |
| 15 | V-D : « The cost is treated as immediate (γc = 0)… consistent with the short reward horizon » | supprimé | aucune ligne du registre ; D1-c |
| 16 | V-D : « Crucially, λ is learned, not swept: it is optimized jointly with the Q-function by a primal–dual update » | changé en « mis à jour une fois par époque par une montée duale projetée (η = 0,1) » ; « learned » et « Crucially » supprimés | NO-budget, E2-a |
| 17 | V-D : « Initialized small, λ grows monotonically and converges near 12.9±0.6 as the constrained cost settles at the 3% budget (Fig. 3)—the behavior of a shadow price rather than a tuned constant » | supprimé | AU-f : λ = 12,22 à l'époque 99, toujours croissant, coût 0,032 > 0,03 ; non reproduit (E2-b) ; E2-a ; NO-budget |
| 18 | V-D : « Training the constraint into the agent this way… is what distinguishes Safe-CQL from a post-hoc penalty sweep » | supprimé | aucune comparaison avec un balayage de pénalité dans le registre ; NO-novelty |
| 19 | V-D : éq. (12) `λ ← [λ + ηλ(ĴC(π) − d)]+` (non normalisée, ηλ non donné) | changé : écart relatif `(ĴC/d − 1)`, η = 0,1, λ₀ = 0 | `src/agents/safe_cql.py` (`update_lambda`) |
| 20 | V-A à V-D : « Safe-CQL with two seeds », « mean and std across seeds » avec `np.std` (ddof = 0) | supprimé | AU : 2 seeds, ddof = 0 ; E12 : 5 seeds (E12-k) |
| 21 | Fig. 2 et Fig. 3 (courbes du notebook) | non reprises | sorties enregistrées du notebook (NO-notebook) ; 0/60 convergés (E2-a) |

## Liste 2 : phrases de la section 04 que le registre ne suffit pas à soutenir

Ces phrases sont écrites avec `CODE:` (lu dans `src/`) ou `DOC:` (lu dans un rapport de `docs/` sans ligne de registre). Un `[H]` ou un `[Q]` est signalé dans la dernière colonne.

| # | phrase (section 04) | ce qui manque | support actuel |
|---|---|---|---|
| 1 | Valeur de `r_scale` (écart-type du reward d'entraînement) | **TODO** : aucune valeur dans le registre. `e1_lp_diagnostic.md` donne 4,08 pour « la table TRAIN », mais le code utilise l'écart-type des fenêtres d'entraînement (ligne 80 du rapport : [H]) ; je ne l'ai pas repris | `src/agents/cql.py` |
| 2 | Architecture (2 × 256 ReLU), Adam, lr 3·10⁻⁴, batch 1 024, τ = 0,005 | pas de ligne du registre ; le registre cite seulement η = 0,1 et γ (E2-b) | `src/agents/cql.py` (`CFG`, `mlp`) ; `phase2_baselines.md` ; `e2`/`e11` (« Autres réglages = SAFE_CFG ») |
| 3 | « The contexts are standardized with the training mean and standard deviation » | aucune ligne ; `e2` le dit au niveau du pli | `src/common.py` (`fit_zscore`) |
| 4 | « the last window of an episode is terminal… windows are never linked across a gap » | D3-a ne dit que « épisodes séparés » | `src/common.py` (`make_arrays`), `src/build_dataset.py` |
| 5 | « each record carries the table cost of its logged action in its own load bin » | AU-b décrit la table, pas son usage dans la cible | `src/common.py` (`make_arrays`, clé `c`) |
| 6 | « We use no gradient clipping, no clipped double-Q learning » | absence d'une propriété dans le code | `src/agents/cql.py` ; l'original affirme le contraire |
| 7 | Toute la mécanique de CQL, IQL et Safe-CQL (cibles, pertes, éq. 2 à 5) | aucune ligne du registre ne définit les algorithmes | `src/agents/*.py` |
| 8 | « The expectile, β and the weight clip are our choices and were not tuned » | aucune ligne | `phase2_baselines.md` (« my choices, none tuned on test ») |
| 9 | « it is built on the same tables as the direct-method estimator » (table-greedy) | E12-f dit « le plus circulaire » ; la raison est dans le rapport de phase 2 | E12-f, AU-c ; `phase2_baselines.md` finding 3 |
| 10 | « We include it because a learned selector is only worth reporting against a lookup » | justification d'auteur, non un fait | NO-rl |
| 11 | Définition de table-greedy (argmax du reward sous coût ≤ d, repli sur le coût minimal) | aucune ligne du registre | `src/baselines.py` (`table_greedy_map`) |
| 12 | « Best-fixed… falls back… which was the case » | E12-h donne « infeasible en validation en phase 2 » ; pas de vérification que ce fut aussi le cas pour la run E12 | E12-h |
| 13 | « We hypothesize that the penalty… reaches the other actions only through the conservative term… » | [H] déclarée ; non testée | D1-c, E2-d |
| 14 | « The cost signal in Eq. (dual) is read from the training table on the training windows, so it is an in-sample quantity » | AU-c parle du « Tabular OPE » du notebook ; l'extension au signal dual est une lecture du code | AU-c ; `src/agents/safe_cql.py` |
| 15 | « the policy of the last epoch, no convergence required » | E12 : procédure dans `e12_attente_pre_test.md` et E12-k seulement | `e12_attente_pre_test.md` §2 |
| 16 | « Every configuration was trained on the whole training split with seeds 0 to 4, 100 epochs » | idem | `src/e12_final.py` (`SEEDS`, `EPOCHS`) |
| 17 | Valeurs de η, α, γ de la Table des configurations | E12-i et E2-b donnent γ et η ; le tableau des 6 configurations est dans `e12_attente_pre_test.md` §2 | `src/e12_final.py` (`CONFIGS`) |
| 18 | « The final multipliers and the convergence status of these runs are not reported (TODO) » | les λ finaux des runs E12 ne sont pas dans le registre (§9.1) ; ils sont dans `train_summary.json` | registre §9.1 |
| 19 | Règle de sélection de α (faisable dans les deux sens ; reward maximal ; repli sur le coût moyen le plus bas) | E11-b dit « retenu par le repli » sans écrire la règle | `docs/e11_alpha_grid.md` (« Règle de sélection gelée ») |
| 20 | Grille α ∈ {0 ; 0,02 ; 0,05 ; 0,1 ; 0,2 ; 0,5}, 60 runs, validation par script | E11-a/b n'écrivent pas la liste de la grille | `docs/e11_alpha_grid.md` |
| 21 | « The grid was set after a first diagnostic… so it is not a blind search » | aucune ligne ; le rapport E11 le dit (limite 3) | `docs/e11_alpha_grid.md` (limite 3) |
| 22 | « validation: network trained on one of the two dominant training scripts, validated on the other » | D6-b dit le poids des scripts ; le montage des plis est dans E11 | `docs/e11_alpha_grid.md` |
| 23 | E1-b : comparaison λ\* (échelle table) et 12,22 (échelle agent) | la conversion `λ = μ·d/r_scale` est [H] pour `r_scale` ; E1-b la présente comme directe | `e1_lp_diagnostic.md` l. 24, 80 |
| 24 | « The divergence of λ therefore does not come from the cost table » | E1-b la tire du rapport E1 ; au-delà du chiffre, c'est une inférence | E1-b |
| 25 | « We hypothesize that the multiplier grows with α to compensate… or because it follows the constraint » | [H] déclarée ; E11 : « on n'a pas testé si cela reflète la contrainte ou une compensation » | E2-d, E2-e ; `e11_alpha_grid.md` |
| 26 | « The revised criterion… fails on the slope of λ everywhere » | E11-d dit « R1 échoue partout » ; le critère révisé est descriptif (tolérance calibrée sur E2) | E11-d |
| 27 | « 12.22 at the last epoch, still increasing, with a cost of 0.032 above d » | sortie enregistrée, non reproduite | AU-f, NO-notebook |
| 28 | « Always-RR and always-PF keep the logged PRB level… not deployable » | E12-g le dit ; l'implémentation est dans `src/baselines.py` | E12-g |

## Renvois pendants et références à créer

- Renvois : `sec:results` (n'existe pas encore).
- Références : `\cite{TODO-bc}`, `\cite{TODO-cql}`, `\cite{TODO-iql}`, `\cite{TODO-double-dqn}`. Le brief demandait aussi une référence « Lagrangian » : elle est déjà dans la section 03 (`TODO-lagrangian-relaxation`) et n'est pas répétée ici.

---

# Révision de l'étape 17 (branche `revision/16-section-methods`)

## Note sur la description des mécanismes

La description des mécanismes d'entraînement (cible de type double DQN, τ = 0,005, sans Q double écrêté ni écrêtage de gradient) corrige celle de la version initiale du manuscrit, pour correspondre au code (OPT-a, CQL-a). Elle figure aussi en commentaire en tête de `04_methods.tex`.

## 1. Résultats BC existants

- **Aucun résultat BC reproduit.** `src/` ne contient pas d'agent BC, et BC n'est ni dans `CONFIGS` ni dans `BASELINES` d'E12 (registre BC-a).
- **Seuls chiffres BC du dépôt** : ceux du notebook original, cellule 13 : exactitude de test 0,403, du scheduler 0,664, du niveau de PRB 0,576 (`audit_report.md`, ligne 23). La courbe d'apprentissage BC (cellule 13-VIZ) est « calculée sur le cluster de test » (`audit_report.md`, ligne 24). Ce sont des sorties enregistrées, non reproduites.
- **Comparaison faite en phase 0** (`decision_memo.md`, D4) : ces chiffres tombent dans la plage de classifieurs triviaux ; ce n'est pas une reproduction.
- **Rien dans `phase2_baselines.md` ni dans les rapports de phase 2 ou 3** (recherche de « BC », « behavior cloning », « imitation » dans `docs/` et `src/`).

## 2. γ dans 03 et 04

Les deux sections contiennent maintenant, mot pour mot, les deux mêmes phrases (test `test_gamma_sentences_identical_in_03_and_04`) :
1. « The agents of the main comparison are trained with a discount of γ = 0.7 on consecutive windows of an episode and are used as one-step selectors, each window receiving the greedy action of the learned network. » (E12P-b, E12P-d)
2. « The variant with γ = 0, which matches the one-step objective, is an ablation, and its outcome depends on the set of scripts considered. » (E12-i, E12P-b)

La section 03 dit en plus que *le problème* a un facteur d'actualisation γ = 0.

## 3. r_scale et λ finaux (artefacts d'entraînement)

Lecture par `src/checks/lit_artefacts_entrainement.py` → `docs/e12_artefacts_entrainement.md`. Sources : `results/e12/train_summary.json` (`meta.test_split_read` = false, commit d'entraînement `0fa5787`) et `results/e12/checkpoints/*.pt`. `test_results.json` n'est jamais ouvert (test `test_artefact_reader_never_opens_test_results`).

| valeur | chiffre | d'où il vient |
|---|---|---|
| `r_scale` | 4,0758 (4.0757787775968035), identique dans les 30 checkpoints | clé `r_scale` des checkpoints ; écart-type du reward des fenêtres d'entraînement |
| λ final, `safe_cql_a0.1` (5 seeds) | 0,1028 à 0,1272 | `final_lambda` de `train_summary.json` |
| λ final, `safe_cql_a0.5` | 0,7497 à 0,9046 | idem |
| λ final, `safe_cql_a0.1_g0` | 0,4398 à 0,4910 | idem |
| coût greedy d'entraînement, dernière époque | 0,0294-0,0306 ; 0,0323-0,0329 ; 0,0318-0,0324 | `last_epoch.greedy_cost_train` de `train_summary.json` (table d'entraînement, fenêtres d'entraînement) |
| λ(époque 79) < λ(époque 99) | vrai dans les 15 runs Safe-CQL | `lambda_history` des checkpoints |

Ces λ (≤ 0,9046) sont très loin des 12,22 du notebook, y compris sur tout le split d'entraînement (E2 n'avait testé qu'un pli).

## 4. Registre

Section 10 du registre : STATE-a, REW-a, REC-a, SCALE-a, SCALE-b, ARCH-a, OPT-a, CQL-a, IQL-a, SAFE-a, SAFE-b, TG-a, BASE-a, BC-a, E12P-a à E12P-d, GRID-a à GRID-c. Les annotations `CODE:` et `DOC:` des deux `.tex` sont remplacées par ces identifiants. La liste 2 de l'étape 16 est donc couverte, sauf : les justifications d'auteur (lignes 10, 13), l'hypothèse sur l'effet de la pénalité (13), et les lignes 23 à 27 (E1, E2).

## 5. `verifie_registre.py`

Avant : 132 OK, 0 ABSENT, 2 AMBIGU (D4-a, COST-a). Après ajout des lignes : voir `docs/verification_registre.md` (régénéré). Deux ABSENT sont apparus et ont été corrigés (un « 17 » de numéro d'étape, et « 15 » / « 12,22 » dans E12P-c, reformulés). Les 2 AMBIGU préexistants sont inchangés.

## 6. Plan BC proposé (non exécuté)

À décider avant tout calcul. Plis A→B et B→A du split d'entraînement uniquement, mêmes plis qu'E1/E2/E11 ; aucun accès au test.
- **Agent** : classifieur à 8 classes, même architecture (2 × 256), entropie croisée avec poids de classes inverses à la fréquence, Adam 3·10⁻⁴, batch 1 024, 100 époques, seeds 0-4, état de 10 dimensions, z-score appris sur le pli source.
- **Mesures de validation** : exactitude sur 8 actions, sur le niveau de PRB et sur le scheduler ; reward et coût DM de l'action prédite, avec les tables du pli de validation (comme E11) ; références : classe majoritaire, politique loguée, table-greedy transféré.
- **Attente écrite avant le calcul** (commit séparé, avec empreinte du code gelé comme E11) : (a) exactitude à 8 actions au-dessus de la classe majoritaire mais sous 50 %, cohérente avec D4-a ; (b) coût de validation de BC proche de celui de la politique loguée, donc au-dessus de d dans les deux sens ; (c) BC ne passe pas le critère « faisable » d'E11 ; (d) les deux sens diffèrent (E11-c) ; (e) tout point faux est rapporté tel quel. Seuils chiffrés à fixer par vous.
- **Ce que BC ne permettrait pas** : le présenter comme borne inférieure (le coût de BC dépend du script d'entraînement) ni comme résultat sur le test.

## 7. À décider par vous

1. BC : exécuter le plan ci-dessus (étape à part), ou assumer son absence (la section 04 dit déjà qu'aucun résultat BC n'est rapporté).
2. Seuils chiffrés de l'attente BC (point 6).
3. Reformulation « γ = 0 » : les chiffres E12 viennent d'un agent entraîné à γ = 0,7. Présenter les deux phrases harmonisées (point 2) telles quelles, ou refaire l'évaluation principale à γ = 0 (troisième lecture du test, NO-blind).
4. Écart entre les λ d'E12 (≤ 0,9046) et le λ du notebook (12,22) : à expliquer (taille d'entraînement, normalisation) ou à présenter comme non reproduit.
5. Le statut de convergence des runs E12 au sens d'E2 n'est pas calculé ; le critère E2 (bande [0,9 d ; d]) donnerait un résultat négatif pour α = 0,5 et γ = 0 (coût greedy 0,0318-0,0329 > d). Souhaitez-vous le calculer (lecture de checkpoints d'entraînement uniquement) ?
6. Références à créer : `TODO-bc`, `TODO-cql`, `TODO-iql`, `TODO-double-dqn`, `TODO-oran-timescales`, `TODO-budget-latency-source`, `TODO-lagrangian-relaxation`, `TODO-dataset`, `TODO-mgen`.
7. Source de d = 0,03 et de Lmax = 20 ms (NO-source) : non documentée.
8. Deux AMBIGU préexistants du vérificateur (D4-a : nombres trouvés seulement par conversion %/fraction ; COST-a : aucune source lisible par le script) : à lever ou à accepter.
9. Renvois pendants : `sec:results`.

---

# Décision sur BC (étape 19, branche `revision/16-section-methods`)

- La sous-section « Behavior Cloning » est retirée de `04_methods.tex` et remplacée, dans la sous-section de table-greedy, par trois phrases : BC n'est pas inclus parce qu'il reproduit la distribution des actions loguées ; la mention de D4 est limitée à l'état à 12 dimensions du notebook (30,5-32,8 % contre 12,4 %, non re-mesuré sur 10 dimensions) ; on compare plutôt à des références sans apprentissage.
- `\cite{TODO-bc}` et le label `sec:bc` disparaissent ; il n'y a plus de référence BC à créer.
- Registre : BC-a porte « Décision : non inclus » ; nouvelle ligne NO-bc en §8.6.
- « Reproduit la distribution des actions loguées, donc aucune information indépendante de la politique de collecte » est un argument d'auteur, pas une ligne [V] du registre (liste 2).
- Le plan BC sur plis de validation de l'étape 17 n'est plus à exécuter.
