# E2 — Diagnostic Safe-CQL par pli (branche `revision/10-safe-cql-g0`)

Code : `src/e2_safe_cql_diagnostic.py`. Tests : `tests/test_e2.py` (5 tests, passent : étanchéité des plis, garde désactivée = `train_safe_cql`, gel de λ, critère de convergence).
Lancement : `python -m src.e2_safe_cql_diagnostic --out results/e2` puis `--summarize results/e2` → `results/e2_{runs.json,runs.csv,summary.csv}` (gitignorés, non commités). Journal : `results/e2_grid.log`.
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée · **[P]** problème confirmé · **[Q]** question ouverte.

## Ce que ce diagnostic est, et n'est pas
- **Un diagnostic, pas une performance.** Tous les coûts et rewards ci-dessous sont des valeurs *selon des tables* (estimateur DM), pas des mesures sur le système. Le split test n'est pas lu (`test_split_read: false` dans les métadonnées du run).
- Il cherche à savoir pourquoi λ de Safe-CQL diverge (audit : λ = 12,22 à l'epoch 99, valeur **lue dans le notebook, non reproduite**) alors que E1 montre que d = 0,03 est faisable sur les tables avec un λ* petit.

## Protocole
- **Code** : commit `b2f9405` ; le run a enregistré `git_commit = b2f9405777620db0402e3ef06beea9b7e89ec5e1` et `git_dirty_src_tests = false` [V]. Version du dataset : `268d524c117eb6de`. Budget d = 0,03. Seeds 0–4. Durée : 2 715 s (6 workers).
- **Plis** : A = script `a908e4cc` (79 630 fenêtres), B = `a53521b2` (72 835 fenêtres), split **train** uniquement, mêmes plis qu'en E1. Un run entraîne la Q-net sur un pli ; « A→B » désigne l'évaluation sur les fenêtres de B.
- **Hygiène de pli** [V, tests] : `cost_hat` (le `c` de la cible de Bellman), la table de coût du coût greedy et de la mise à jour duale, `r_scale` et le z-score sont recalculés sur le seul pli d'entraînement.
- **Grille** : 6 variantes × 2 plis × 5 seeds = **60 runs**, tous terminés (60/60). Autres réglages = `SAFE_CFG` (hidden 256, batch 1024, lr 3e-4, τ 0,005, η 0,1).

| variante | changement |
|---|---|
| `current` | γ = 0,7 ; α = 0,5 ; 100 epochs |
| `gamma0` | γ = 0 |
| `alpha0.1` | α = 0,1 (valeur de diagnostic, **non réglée**) |
| `alpha0` | α = 0 |
| `guard10` | **variante** : λ gelé (pas d'augmentation) si le coût greedy n'est pas inférieur à celui d'il y a 10 epochs |
| `current_300ep` | comme `current`, 300 epochs |

- **Critères fixés avant le run, non modifiés après** (docstring du module, figés dans le commit `b2f9405`). Sur les **20 dernières epochs** (λ après mise à jour, coût greedy train en fin d'epoch), convergence si **toutes** les conditions :
  1. max(λ) − min(λ) < 0,02 ;
  2. soit λ > 0 sur les 20 epochs et 0,9·d ≤ coût greedy ≤ d sur les 20 ; soit λ = 0 sur les 20 et coût ≤ d ;
  3. l'IC à 95 % (t, 18 ddl) de la pente MCO de λ sur l'epoch contient 0 (λ constant : pente 0).
  Sinon « non converge » (aussi si moins de 20 epochs).

## Synthèse par pli et variante
Moyenne ± écart-type sur 5 seeds. λ et coût greedy à la **dernière epoch**. Le coût greedy est la moyenne, sur les fenêtres du pli, de `C_pli[argmax Q(s), bin]` (table de coût du pli d'entraînement).

| pli | variante | λ final | coût greedy final | convergé (3 conditions) |
|---|---|---|---|---|
| A | `current` | 1,935 ± 0,045 | 0,0358 ± 0,0003 | 0/5 |
| A | `gamma0` | 3,112 ± 0,045 | 0,0403 ± 0,0002 | 0/5 |
| A | `alpha0.1` | 0,520 ± 0,015 | 0,0314 ± 0,0003 | 0/5 |
| A | `alpha0` | 0,151 ± 0,029 | 0,0303 ± 0,0016 | 0/5 |
| A | `guard10` | 0,366 ± 0,016 | 0,0477 ± 0,0005 | 0/5 |
| A | `current_300ep` | 5,838 ± 0,128 | 0,0359 ± 0,0001 | 0/5 |
| B | `current` | 0,283 ± 0,011 | 0,0311 ± 0,0002 | 0/5 |
| B | `gamma0` | 0,595 ± 0,030 | 0,0320 ± 0,0002 | 0/5 |
| B | `alpha0.1` | 0,051 ± 0,012 | 0,0306 ± 0,0012 | 0/5 |
| B | `alpha0` | 0,053 ± 0,012 | 0,0309 ± 0,0048 | 0/5 |
| B | `guard10` | 0,260 ± 0,015 | 0,0313 ± 0,0005 | 0/5 |
| B | `current_300ep` | 0,906 ± 0,069 | 0,0310 ± 0,0003 | 0/5 |

Références E1 (tables du pli, LP à une étape) : A : coût minimal 0,0211, λ* = 0 (contrainte non active) ; B : coût minimal 0,0112, λ* = 0,065 (contrainte active). Ce sont des valeurs de table.

- **[V]** **0/60 run ne converge** selon le critère fixé.
- **[V]** Avec `current` (γ = 0,7, α = 0,5, 100 epochs), λ final vaut 1,94 (A) et 0,28 (B), contre λ* = 0 (A) et 0,065 (B) selon E1. Il n'atteint pas 12,22 (valeur du notebook, non reproduite) dans ces runs de 100 epochs sur un seul script ; `current_300ep` monte à 5,84 (A) et 0,91 (B). Cette valeur de 12,22 vient d'un entraînement sur tout le train (510 réservations), pas sur un pli : la comparaison directe n'est donc pas faite ici.
- **[V]** Sur A, aucune variante non nulle en α n'atteint d (coût greedy ≥ 0,0314). Sur B, toutes les variantes ont un coût greedy final voisin de d (0,0306–0,0320).

## Les trois conditions de convergence, séparément
Nombre de runs (sur 5) qui satisfont chaque condition. La convergence exige les trois.

| pli | variante | (1) λ stable (écart < 0,02) | (2) coût dans la bande | (3) pente de λ : IC ∋ 0 | les trois |
|---|---|---|---|---|---|
| A | `current` | 0/5 | 0/5 | 0/5 | 0/5 |
| A | `gamma0` | 0/5 | 0/5 | 0/5 | 0/5 |
| A | `alpha0.1` | 0/5 | 0/5 | 0/5 | 0/5 |
| A | `alpha0` | 1/5 | 0/5 | 2/5 | 0/5 |
| A | `guard10` | 5/5 | 0/5 | 5/5 | 0/5 |
| A | `current_300ep` | 0/5 | 0/5 | 0/5 | 0/5 |
| B | `current` | 0/5 | 0/5 | 0/5 | 0/5 |
| B | `gamma0` | 0/5 | 0/5 | 0/5 | 0/5 |
| B | `alpha0.1` | 1/5 | 0/5 | 4/5 | 0/5 |
| B | `alpha0` | 0/5 | 0/5 | 5/5 | 0/5 |
| B | `guard10` | 0/5 | 0/5 | 0/5 | 0/5 |
| B | `current_300ep` | 0/5 | 0/5 | 0/5 | 0/5 |

- **[V]** La condition (2) (bande de coût) n'est **satisfaite par aucun des 60 runs**. C'est elle qui rend la convergence inatteignable ici, y compris pour les cellules où (1) et (3) passent.
- **[V]** `guard10` sur A : λ est constant sur les 20 dernières epochs (écart 0, gelé 82–84 epochs sur 100), donc (1) et (3) passent trivialement, mais le coût greedy reste à 0,0477, au-dessus de d. Un λ immobile n'est pas un λ à l'équilibre : le critère le rejette à juste titre par (2). **[H]** La garde, telle que définie, fige λ tant que le coût ne baisse pas, y compris quand il est au-dessus de d ; cela empêche l'emballement mais aussi la correction.
- **[V]** Descriptif, calculé après coup et **hors critère** : sur les 20 dernières epochs de chaque run, le nombre d'epochs avec coût dans [0,9·d ; d] = [0,027 ; 0,03] vaut, sur 100 (5 runs × 20) : A `alpha0` 43, B `alpha0` 23, B `alpha0.1` 41 ; 0 pour toutes les autres cellules. Aucun run ne reste dans la bande pendant les 20 epochs, et la pente de λ varie tout de même dans ces cellules. Ce comptage n'est pas un critère révisé.

## Part d'actions égales aux actions loguées
Part (en %) des fenêtres du pli d'entraînement où `argmax Q(s)` = action loguée, à λ final, ± écart-type sur 5 seeds. Colonne de droite : accord avec l'argmax de la table du pli à ce même λ (par bin, pondéré par le nombre de fenêtres). Les deux sont mesurés sur les fenêtres d'entraînement du pli.

| pli | variante | Q-net = action loguée | Q-net = argmax de la table |
|---|---|---|---|
| A | `current` | 70,6 ± 0,6 | 38,7 ± 0,6 |
| A | `gamma0` | 74,2 ± 0,3 | 38,1 ± 0,3 |
| A | `alpha0.1` | 62,5 ± 0,8 | 43,7 ± 1,8 |
| A | `alpha0` | 31,5 ± 0,5 | 58,9 ± 4,9 |
| A | `guard10` | 81,5 ± 0,4 | 28,9 ± 0,6 |
| A | `current_300ep` | 63,6 ± 0,7 | 47,1 ± 0,7 |
| B | `current` | 78,0 ± 0,4 | 24,4 ± 0,2 |
| B | `gamma0` | 81,2 ± 0,4 | 24,8 ± 0,4 |
| B | `alpha0.1` | 61,4 ± 1,1 | 23,3 ± 0,8 |
| B | `alpha0` | 20,3 ± 0,8 | 40,6 ± 2,0 |
| B | `guard10` | 78,3 ± 0,5 | 24,2 ± 0,3 |
| B | `current_300ep` | 80,0 ± 0,4 | 25,9 ± 0,5 |

- **[V]** Avec α ≥ 0,5 (`current`, `gamma0`, `guard10`, `current_300ep`), la Q-net reproduit l'action loguée sur 64 à 82 % des fenêtres, et l'argmax de la table sur 24 à 47 %. La part « = loguée » décroît quand α diminue (α = 0,1 : 61–63 % ; α = 0 : 20–32 %).
- **Repère de hasard** : 8 actions, soit 12,5 % si les actions étaient équiprobables et indépendantes de l'état. Ce n'est pas un seuil calibré sur ces plis (la distribution des actions loguées n'est pas uniforme dans un pli).
- **[H, non testée]** Le conservatisme CQL (terme α) ramène l'argmax vers l'action loguée. La baisse monotone de la part « = loguée » avec α va dans ce sens, mais ce n'est pas un test causal : α change aussi l'échelle des Q et donc, indirectement, les épisodes de λ. Aucune expérience ici ne sépare ces deux effets.
- **[H, non testée]** Les actions loguées sont prédictibles par le script (D4) ; une Q-net peut les retrouver sans passer par la contrainte. Non vérifié par ce diagnostic.

## Coûts croisés : définition exacte
Quatre colonnes de coût existent dans les sorties ; le tableau montre celles qu'on demande, plus les deux repères.

| colonne | Q-net évaluée sur | table de coût utilisée | moyenne sur |
|---|---|---|---|
| **coût greedy** (`cost_own_tables`, `greedy_cost_final`) | les **fenêtres du pli d'entraînement** | `C` **du pli d'entraînement** (A pour un run A) | ces fenêtres (distribution empirique des bins) |
| **`cost_own_states_oth_tables`** | les **fenêtres du pli d'entraînement** (états de A pour un run A) | `C` **de l'autre pli** (B pour un run A) | les fenêtres de l'entraînement : `C_autre[a_Q, bin]` avec les bins du pli d'entraînement |
| **`cost_oth_states_oth_tables`** | les **fenêtres de l'autre pli** (états de B pour un run A, normalisés avec le z-score appris sur A) | `C` **de l'autre pli** | les fenêtres de l'autre pli (leur distribution de bins) |
| `table_argmax_cost` | n/a (pas de Q-net) | `C` du pli d'entraînement | pondéré par `p_b` du pli d'entraînement, à λ final ; politique = argmax de la table à ce λ |

Où `C` = coût moyen `urllc_frac_viol` par cellule (action × bin de charge), mêmes tables et mêmes règles de repli que E1, calculées sur le pli entier d'entraînement (pas de split interne).
Les deux colonnes demandées diffèrent donc par les **états** : `cost_own_states_oth_tables` garde les états du pli d'entraînement et ne change que la table (l'action est choisie sur ces états, puis son coût est lu dans l'autre table, bin du pli d'entraînement) ; `cost_oth_states_oth_tables` change aussi les états (la Q-net choisit ses actions sur les fenêtres de l'autre pli). Aucune des deux n'est un coût mesuré : ce sont des lectures de table.

| pli d'entraînement | variante | `table_argmax_cost` (λ final) | coût greedy (propre) | `own_states_oth_tables` | `oth_states_oth_tables` |
|---|---|---|---|---|---|
| A (autre = B) | `current` | 0,0215 | 0,0358 ± 0,0003 | 0,0264 ± 0,0004 | 0,0235 ± 0,0003 |
| A | `gamma0` | 0,0215 | 0,0403 ± 0,0002 | 0,0288 ± 0,0002 | 0,0243 ± 0,0003 |
| A | `alpha0.1` | 0,0215 | 0,0314 ± 0,0003 | 0,0242 ± 0,0003 | 0,0234 ± 0,0004 |
| A | `alpha0` | 0,0215 | 0,0303 ± 0,0016 | 0,0300 ± 0,0020 | 0,0329 ± 0,0044 |
| A | `guard10` | 0,0215 | 0,0477 ± 0,0005 | 0,0312 ± 0,0002 | 0,0287 ± 0,0009 |
| A | `current_300ep` | 0,0215 | 0,0359 ± 0,0001 | 0,0274 ± 0,0003 | 0,0238 ± 0,0005 |
| B (autre = A) | `current` | 0,0199 | 0,0311 ± 0,0002 | 0,0597 ± 0,0010 | 0,0504 ± 0,0009 |
| B | `gamma0` | 0,0199 | 0,0320 ± 0,0002 | 0,0617 ± 0,0004 | 0,0543 ± 0,0010 |
| B | `alpha0.1` | 0,0529 | 0,0306 ± 0,0012 | 0,0542 ± 0,0018 | 0,0454 ± 0,0019 |
| B | `alpha0` | 0,0481 | 0,0309 ± 0,0048 | 0,0434 ± 0,0030 | 0,0405 ± 0,0048 |
| B | `guard10` | 0,0199 | 0,0313 ± 0,0005 | 0,0598 ± 0,0008 | 0,0500 ± 0,0010 |
| B | `current_300ep` | 0,0199 | 0,0310 ± 0,0003 | 0,0601 ± 0,0008 | 0,0531 ± 0,0013 |

- **[V]** Entraînée sur B, la Q-net a un coût greedy ≈ 0,031 sur les tables de B mais **0,050–0,062** quand le même choix d'actions est lu dans les tables de A. Entraînée sur A, le coût lu dans les tables de B est **plus bas** (0,023–0,031) que le coût greedy propre (0,030–0,048).
- **[V]** Ces écarts sont de même ordre que ceux d'E1 (politique LP(A) lue dans les tables de B : 0,052 ; LP(B) lue dans A : 0,030). Avec 2 scripts, la direction de l'écart (A→B pire, B→A meilleur) ne peut pas être distinguée d'une propriété de ces deux paires.
- **[H, non testée]** Les tables de A et de B diffèrent par scheduler/slicing/bloc temporel (D6–D8), donc une politique réglée sur l'une n'est pas contrainte sur l'autre. Non testé ici.
- `table_argmax_cost` dépend du λ final de chaque variante : sur B, `alpha0.1` et `alpha0` finissent à λ ≈ 0,05, **en dessous** du λ où l'argmax de la table coûte ≤ d (≈ 0,07, E1) ; d'où 0,053 et 0,048. Ce n'est pas une anomalie de la table.

## Limites
1. **Coûts lus dans des tables bruitées [P]** : toutes les valeurs de coût (greedy, croisé, `table_argmax`) viennent de tables `C[a, b]` dont certaines cellules reposent sur 2 à 6 réservations (E1). Le bootstrap d'E1 donne un IC de λ* de 0 à ≈ 1–3 et un coût minimal de A au-dessus de d dans 2,1 % des rééchantillons. Les écarts-types ci-dessus sont des variances **entre seeds d'entraînement**, pas de l'incertitude sur les tables. Le coût greedy est évalué **sur les fenêtres mêmes d'entraînement** et dans la table construite sur ces mêmes fenêtres (en échantillon) : rien n'est hors-échantillon.
2. **2 scripts seulement [P]** : les plis A et B sont deux scripts parmi un nombre inconnu ; les différences entre plis (A : λ* = 0 ; B : λ* > 0 ; comportements opposés des coûts croisés) ne permettent pas d'estimer une variabilité entre scripts, ni de généraliser. Le script de test n'est pas utilisé.
3. **Critère de bande jamais satisfait [P]** : (2) vaut 0/60. Avec un critère à trois conditions et une bande de 10 % de d sur 20 epochs consécutives, la grille ne permet pas de dire quelles variantes « convergent » ; elle dit seulement qu'aucune ne le fait. Le critère n'a **pas** été modifié : il est celui figé dans le commit `b2f9405`. **[Q]** La bande est-elle trop étroite par rapport au bruit epoch à epoch du coût greedy, ou la condition (2) est-elle réellement violée ? Non tranché : la dispersion epoch à epoch n'a pas été quantifiée ici.
4. **[H]** Une seule valeur de α par palier (0,1 ; 0,5 ; 0), non réglée, et pas de validation par script : aucune conclusion sur un α « bon ».
5. **[H]** Les causes évoquées (conservatisme CQL, amorçage de Bellman, prédictibilité de l'action loguée) restent des hypothèses : la grille compare des variantes mais ne sépare pas les effets (α modifie aussi l'échelle des Q).
6. **[Q]** Entraînement sur un pli (≈ 73 000–80 000 fenêtres) contre tout le train (510 réservations) dans le notebook : le λ de 12,22 du notebook n'est pas reproduit ici, et on ignore si l'écart vient de la taille de l'entraînement, des tables, ou d'autre chose.
7. **[Q]** L'origine du budget d = 0,03 n'est toujours pas documentée (cf. E1).

## Suite
Le plan de l'étape 11 est proposé séparément, non lancé.
