# E11 — Grille d'α pour Safe-CQL, validation par script (branche `revision/11-alpha-grid`)

Code : `src/e11_alpha_grid.py`. Tests : `tests/test_e11.py` (étanchéité par empreinte sha256 des constantes et des fonctions gelées).
Lancement : `python -m src.e11_alpha_grid --out results/e11` puis `--summarize results/e11` → `results/e11_{runs.json,runs.csv,summary.csv,selection.json}` (gitignorés, non commités). Journal : `results/e11_grid.log`.
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée · **[P]** problème confirmé · **[Q]** question ouverte.

## Ce que ce diagnostic est, et n'est pas
- **Un diagnostic, pas une performance.** Tous les coûts et rewards sont des valeurs *selon des tables* (estimateur DM, lues par (action × bin de charge)), pas des mesures sur le système. Le split test n'est pas lu (`test_split_read: false`).
- Il ne sélectionne pas un hyperparamètre de la méthode finale : il documente comment le coût et le reward de validation varient avec α sur deux scripts.

## Protocole
- **Code** : commit gelé `7e9be78` ; le run a enregistré `git_commit = 7e9be78d…`, `git_dirty_src_tests = false` [V]. Empreinte `33e458b2baf1a9e5438d9f2019a34790b6352ecb545eb7a0d1720faf7a1664aa`. Version du dataset : `268d524c117eb6de`. Budget d = 0,03. Durée : 1 973 s.
- **Plis** : A = script `a908e4cc`, B = `a53521b2`, split **train** uniquement (mêmes plis qu'en E1/E2). « A→B » : Q-net entraînée sur A, **validée sur B** (fenêtres de B comme états, tables de B pour coût et reward, z-score appris sur A). « B→A » : l'inverse.
- **Grille** : α ∈ {0, 0,02, 0,05, 0,1, 0,2, 0,5} × 2 sens × seeds 0–4 = **60 runs, 60/60 terminés** [V]. Autres réglages comme E2 (`SAFE_CFG` : hidden 256, batch 1024, lr 3e-4, τ 0,005, η 0,1), γ = 0,7, 100 epochs.
- γ = 0 n'est pas dans cette grille (ablation à l'α retenu, étape 12).

### Règle de sélection gelée (avant la grille)
Sur le coût et le reward de **validation** moyens sur les 5 seeds :
1. α *faisable* := coût de validation moyen ≤ d dans **les deux** sens.
2. S'il existe des α faisables : garder celui au reward moyen (sur les deux sens) maximal ; les α à moins de 0,01 Mbps du maximum sont à égalité → le plus petit.
3. **Sinon** (repli) : garder l'α au coût de validation moyen (sur les deux sens) le plus bas, et marquer `infeasible: no configuration is feasible`.

### Critère de convergence révisé (gelé)
Sur les 20 dernières epochs : R1 l'IC 95 % de la pente de λ contient 0 ; R2 si λ > 0 sur la fenêtre, |coût greedy moyen − d| ≤ `BAND_TOL` = 0,0025 (si λ = 0 partout : coût moyen ≤ d) ; R3 l'IC 95 % de la pente du coût greedy contient 0. Le critère E2 est calculé en parallèle, inchangé.

## Verdict
- **[V] Aucune configuration faisable** : pour tous les α, le coût de validation moyen dépasse d = 0,03 dans le sens B→A (0,0405 à 0,0504). Le statut enregistré est `infeasible: no configuration is feasible`, `feasible_alphas = []`.
- **[V] α = 0,1 est retenu par le repli** (coût de validation moyen sur les deux sens le plus bas). Ce n'est **pas** un α « faisable » retenu sur ses mérites.
- **[V] Mais α = 0,05, 0,1 et 0,2 sont à égalité en pratique.** Coût de validation moyen sur les deux sens : 0,03440 (α = 0,1), 0,03464 (α = 0,2), 0,03470 (α = 0,05) ; écart maximal 0,0003, alors que l'écart-type entre seeds du coût de validation en B→A est de 0,0021 (α = 0,05), 0,0019 (0,1) et 0,0010 (0,2). Le choix de 0,1 parmi ces trois tient à la règle de repli, pas à une différence distinguable de la dispersion entre seeds. Les trois autres valeurs ont un coût moyen plus élevé (0 : 0,03668 ; 0,02 : 0,03598 ; 0,5 : 0,03694) [V, calculé à partir du tableau].
- **[V]** Aucun run ne passe le critère E2 (0/60), comme en E2.

## Tableau complet par α
Moyenne ± écart-type (ddof = 1) sur 5 seeds. Coût et reward de **validation** (Q-net sur l'autre pli) ; λ final = dernière epoch. « Révisé » et « E2 » = nombre de runs (sur 5) qui passent le critère correspondant. d = 0,03.

### Sens A→B (entraînée sur A, validée sur B)
| α | coût val. | reward val. (Mbps) | λ final | révisé | E2 |
|---|---|---|---|---|---|
| 0 | 0,0329 ± 0,0044 | 9,115 ± 0,221 | 0,151 ± 0,029 | 2/5 | 0/5 |
| 0,02 | 0,0260 ± 0,0009 | 8,753 ± 0,160 | 0,220 ± 0,031 | 1/5 | 0/5 |
| 0,05 | 0,0248 ± 0,0007 | 8,388 ± 0,147 | 0,311 ± 0,010 | 0/5 | 0/5 |
| 0,1 | 0,0234 ± 0,0004 | 8,056 ± 0,114 | 0,520 ± 0,015 | 0/5 | 0/5 |
| 0,2 | 0,0227 ± 0,0003 | 7,969 ± 0,069 | 0,973 ± 0,033 | 0/5 | 0/5 |
| 0,5 | 0,0235 ± 0,0003 | 7,864 ± 0,071 | 1,935 ± 0,045 | 0/5 | 0/5 |

### Sens B→A (entraînée sur B, validée sur A)
| α | coût val. | reward val. (Mbps) | λ final | révisé | E2 |
|---|---|---|---|---|---|
| 0 | 0,0405 ± 0,0048 | 10,063 ± 0,090 | 0,053 ± 0,012 | 5/5 | 0/5 |
| 0,02 | 0,0460 ± 0,0047 | 8,885 ± 0,082 | 0,030 ± 0,017 | 5/5 | 0/5 |
| 0,05 | 0,0446 ± 0,0021 | 8,531 ± 0,088 | 0,034 ± 0,012 | 5/5 | 0/5 |
| 0,1 | 0,0454 ± 0,0019 | 8,321 ± 0,061 | 0,051 ± 0,012 | 4/5 | 0/5 |
| 0,2 | 0,0465 ± 0,0010 | 8,088 ± 0,035 | 0,093 ± 0,015 | 0/5 | 0/5 |
| 0,5 | 0,0504 ± 0,0009 | 7,897 ± 0,024 | 0,283 ± 0,011 | 0/5 | 0/5 |

Décomposition du critère révisé (runs sur 5 qui passent R1 / R2 / R3, d'après `n_r1`, `n_r2`, `n_r3` du CSV) [V] : **R1 (λ sans pente) est la condition qui échoue partout** — le nombre de runs convergés est égal au nombre de runs passant R1. R2 et R3 passent 5/5 dans presque toutes les cellules ; exceptions : R2 = 0/5 en A→B à α = 0,2 et 0,5, R3 = 4/5 en A→B à α = 0,5. R1 passe 5/5 en B→A pour α ≤ 0,05, 4/5 à 0,1, 0/5 à 0,2 et 0,5 ; en A→B 2/5, 1/5 puis 0/5.

## Les deux sens évoluent en sens inverse quand α augmente
- **[V] Reward de validation** : décroît avec α dans les **deux** sens (A→B : 9,12 → 7,86 ; B→A : 10,06 → 7,90).
- **[V] Coût de validation** : en A→B il **baisse** quand α augmente (0,0329 → 0,0227 à α = 0,2, puis 0,0235 à 0,5) et passe sous d dès α = 0,02 ; en B→A il **monte** (0,0405 à α = 0 → 0,0504 à α = 0,5, avec une non-monotonie à 0,02) et reste au-dessus de d pour tout α.
- **[V]** Moyenner les deux sens pour le repli masque donc deux comportements opposés : un α qui améliore la faisabilité dans un sens la dégrade dans l'autre.
- **[H]** α pénalise le Q de toutes les actions hors-données (régularisation CQL) ; avec des tables bruitées, cette pénalité pourrait pousser la politique greedy vers des actions que les tables d'un pli jugent peu coûteuses sans que celles de l'autre pli le confirment. Non testé ; aucune ablation ne l'isole ici.
- **[H]** Le λ final croît avec α dans les deux sens (A→B : 0,15 → 1,94 ; B→A : 0,05 → 0,28) ; on n'a pas testé si cela reflète la contrainte ou une compensation de la pénalité CQL.

## Références
Toutes les valeurs sont lues dans les tables du pli indiqué, avec ses parts de bins. d = 0,03.

- **Oracle** = table-greedy(T) évalué sur **les tables de validation T elles-mêmes** (il les utilise pour choisir : c'est une borne, pas une politique réalisable).
- **Table-greedy transféré** = table-greedy construit sur les tables d'**entraînement**, évalué sur les tables de **validation** : c'est la comparaison honnête avec la Q-net.
- **LP** = LP randomisé à une étape d'E1 sur les tables de validation (oracle aussi).

| sens | oracle table-greedy (reward / coût) | LP (reward / coût) | table-greedy transféré (reward / coût) |
|---|---|---|---|
| A→B | 10,765 / 0,0286 | 10,778 / 0,0300 | 10,352 / **0,0520** |
| B→A | 11,703 / 0,0215 | 11,703 / 0,0215 | 11,370 / **0,0303** |

- **[V]** En A→B, le table-greedy transféré dépasse nettement d (0,0520 contre 0,03) : une politique construite sur des tables pour respecter d sur elles ne le respecte pas sur le pli de validation. L'absence de configuration faisable pour Safe-CQL n'est donc pas propre à la Q-net **dans ce sens**.
- **[H]** En B→A, le coût du table-greedy transféré (0,0303) est à 1 % de d (+0,0003), ce qui est dans le bruit possible des tables (limite 2) : on ne peut pas dire qu'il viole d. Il est aussi nettement plus bas que celui des Q-nets (0,040 à 0,047). La conclusion « l'absence de configuration faisable n'est pas propre à la Q-net » ne vaut donc fortement qu'en A→B ; en B→A elle n'est pas établie, et les Q-nets sont plus loin de d qu'un simple table-greedy transféré.
- **[Q]** Intervalle sur le 0,0303 de B→A : non calculé. Le bootstrap par réservation d'E1 (B = 1 000) porte sur le coût minimal, λ* et le reward LP, pas sur le coût d'une politique transférée ; aucun script de `src/` ne le produit aujourd'hui. Un tel intervalle, s'il est ajouté, sera conditionnel au script B (réservations rééchantillonnées dans le script, non indépendantes, cellules à 2–6 réservations) et ne mesurera pas la variabilité entre scripts.
- **[V]** Écart de reward de la Q-net validée à l'**oracle** (α = 0,1) : A→B −2,71 ; B→A −3,38. Écart au **transféré** : A→B 8,056 − 10,352 = −2,30 (avec un coût plus bas : 0,0234 contre 0,0520) ; B→A 8,321 − 11,370 = −3,05 (avec un coût plus haut : 0,0454 contre 0,0303). En B→A la Q-net est donc moins bonne que le transféré sur les deux axes ; en A→B elle échange du reward contre du coût.
- Le diagnostic circulaire (Q-net sur tables d'entraînement vs table-greedy d'entraînement, `gap_reward_to_tg_train_circular`) est dans le CSV ; il n'est pas utilisé ici, la Q-net ayant vu ces tables dans sa cible.

## Limites
1. **Deux scripts seulement** (deux plis, un seul pli de validation par sens) : les sens A→B et B→A divergeant sur le coût, rien ne dit que ce comportement se généralise ; les écarts-types sont sur 5 seeds, pas sur des scripts indépendants.
2. **Tables bruitées** (E1 : certaines cellules reposent sur 2 à 6 réservations) : coût et reward de validation sont des estimations DM bruitées, et le seuil d = 0,03 est comparé à des valeurs dont l'incertitude n'est pas propagée ici.
3. **Valeurs d'α choisies après E2** (E2 avait α ∈ {0, 0,1, 0,5}) : la grille n'est pas une recherche aveugle ; elle raffine [0, 0,2] à partir de ce qu'E2 avait montré.
4. **Tolérance de bande calibrée sur des runs déjà observés** : `BAND_TOL` = 0,0025 est le 90ᵉ percentile (0,00243 arrondi) de l'écart-type intra-fenêtre du coût sur les 60 runs d'E2 ; elle n'est pas indépendante des données auxquelles elle est appliquée. Le critère révisé doit être lu comme descriptif.
5. Le critère E2 donne 0/60 ; le critère révisé donne des runs convergés surtout à α bas (et en B→A), ce qui dépend de la tolérance choisie [H].
6. Aucune interprétation causale ici n'est testée ; les points marqués [H] sont des hypothèses.

## Questions ouvertes
- **[Q]** La règle de repli (coût moyen le plus bas) ne distingue pas α = 0,05, 0,1 et 0,2 ; faut-il une règle qui tienne compte de la dispersion, ou le fixer par convention ?
- **[Q]** L'asymétrie A→B / B→A tient-elle aux scripts, aux tables ou à la méthode ? Ce diagnostic ne permet pas de le dire.
