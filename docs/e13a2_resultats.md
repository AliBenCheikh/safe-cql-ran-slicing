# E13a2 — Résultats : niveaux de charge à arêtes entières (R1-W2) — branche `revision/13-bins-fenetre`

Protocole gelé : `docs/e13a2_protocole_entiers.md` (commit `c699b57`). Exécution unique, sans variante ajoutée. Code : `src/e13a2_integer_levels.py` ; sortie `results/e13a2_{summary.json,cells.csv}`, journal `results/e13a2.log` (gitignorés).
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée · **[P]** problème constaté · **[Q]** question ouverte.

## Statut
- Descriptif, plis A et B du **train** ; le test n'est pas lu (`test_split_read: false`). Valeurs selon des tables (DM), pas des performances.
- La configuration gelée du papier (3 niveaux, 5 s) reste la principale ; cette analyse ne motive **aucune troisième lecture du test**. Aucun jeu d'arêtes n'est choisi ni classé.
- Run au commit `e2e89b6` (arbre propre), dataset `268d524c117eb6de`, seed 0, B = 2000. **Garde de reproduction : PASS** (0,0520 / 0,0303 retrouvés avec `edges3_current`, ligne ci-dessous).

## Coût et reward transférés (table-greedy construit sur la source, évalué sur la validation)
| sens | jeu | niveaux | arêtes | parts fenêtres (source) | action par niveau | reward transféré | coût transféré | IC 95 % bootstrap du coût (médiane) | part de réplicats ≤ d | réplicats invalides |
|---|---|---|---|---|---|---|---|---|---|---|
| A->B | int_k2 | 2 | [5.0] | [0.157, 0.843] | [7, 6] | 9.460 | 0.0463 | [0.0128 ; 0.0698] (0.0393) | 0.28 | 0 |
| A->B | int_k3 | 3 | [5.0, 6.0] | [0.157, 0.747, 0.097] | [7, 6, 6] | 9.471 | 0.0464 | [0.0141 ; 0.0707] (0.0401) | 0.26 | 1 |
| A->B | int_k4 | 3 | [5.0, 6.0] | [0.157, 0.747, 0.097] | [7, 6, 6] | 9.471 | 0.0464 | [0.0148 ; 0.0712] (0.0400) | 0.25 | 0 |
| A->B | int_k5 | 3 | [5.0, 6.0] | [0.157, 0.747, 0.097] | [7, 6, 6] | 9.471 | 0.0464 | [0.0146 ; 0.0722] (0.0403) | 0.26 | 2 |
| A->B | int_each | 7 | [2.0, 3.0, 4.0, 5.0, 6.0, 7.0] | [0.014, 0.039, 0.024, 0.079, 0.747, 0.023, 0.073] | [6, 7, 5, 7, 6, 6, 6] | 10.535 | 0.0448 | [0.0178 ; 0.0819] (0.0397) | 0.26 | 1 |
| A->B | edges3_current | 3 | [3.5, 5.5] | [0.053, 0.104, 0.842] | [7, 7, 6] | 10.352 | 0.0520 | [0.0146 ; 0.0830] (0.0382) | 0.30 | 2 |
| B->A | int_k2 | 2 | [5.0] | [0.356, 0.644] | [6, 6] | 11.406 | 0.0357 | [0.0138 ; 0.0579] (0.0316) | 0.45 | 1 |
| B->A | int_k3 | 3 | [5.0, 6.0] | [0.356, 0.419, 0.224] | [6, 6, 6] | 11.398 | 0.0357 | [0.0142 ; 0.0586] (0.0319) | 0.44 | 1 |
| B->A | int_k4 | 4 | [4.0, 5.0, 6.0] | [0.231, 0.125, 0.419, 0.224] | [6, 6, 6, 6] | 11.381 | 0.0339 | [0.0166 ; 0.0539] (0.0313) | 0.43 | 0 |
| B->A | int_k5 | 4 | [4.0, 5.0, 6.0] | [0.231, 0.125, 0.419, 0.224] | [6, 6, 6, 6] | 11.381 | 0.0339 | [0.0161 ; 0.0542] (0.0312) | 0.45 | 1 |
| B->A | int_each | 8 | [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0] | [0.055, 0.047, 0.033, 0.096, 0.125, 0.419, 0.081, 0.143] | [0, 6, 2, 6, 6, 6, 6, 6] | 11.115 | 0.0307 | [0.0164 ; 0.0536] (0.0314) | 0.44 | 0 |
| B->A | edges3_current | 3 | [3.5, 5.5] | [0.136, 0.222, 0.642] | [6, 4, 6] | 11.370 | 0.0303 | [0.0147 ; 0.0523] (0.0293) | 0.53 | 0 |

Les lignes `int_k3`, `int_k4`, `int_k5` en A→B, et `int_k4`, `int_k5` en B→A, sont la même partition (même résultat ponctuel) ; leurs IC diffèrent légèrement par le flux aléatoire.

## Effectifs et IC par cellule (action × niveau)
| sens | jeu | côté | rés./cellule min · méd · max | ≤ 2 rés. | ≤ 5 rés. | < 20 fenêtres (repli) | cellules | sans IC | IC contient d |
|---|---|---|---|---|---|---|---|---|---|
| A->B | int_k2 | source | 5 · 19.5 · 55 | 0 | 1 | 0 | 16 | 0 | 9/16 (0.56) |
| A->B | int_k2 | validation | 11 · 22 · 44 | 0 | 0 | 0 | 16 | 0 | 9/16 (0.56) |
| A->B | int_k3 | source | 5 · 19.5 · 55 | 0 | 1 | 0 | 24 | 0 | 13/24 (0.54) |
| A->B | int_k3 | validation | 8 · 22 · 41 | 0 | 0 | 0 | 24 | 0 | 13/24 (0.54) |
| A->B | int_k4 | source | 5 · 19.5 · 55 | 0 | 1 | 0 | 24 | 0 | 13/24 (0.54) |
| A->B | int_k4 | validation | 8 · 22 · 41 | 0 | 0 | 0 | 24 | 0 | 13/24 (0.54) |
| A->B | int_k5 | source | 5 · 19.5 · 55 | 0 | 1 | 0 | 24 | 0 | 13/24 (0.54) |
| A->B | int_k5 | validation | 8 · 22 · 41 | 0 | 0 | 0 | 24 | 0 | 13/24 (0.54) |
| A->B | int_each | source | 0 · 8 · 55 | 13 | 20 | 9 | 56 | 9 | 30/47 (0.64) |
| A->B | int_each | validation | 3 · 12 · 41 | 0 | 12 | 0 | 56 | 0 | 29/56 (0.52) |
| A->B | edges3_current | source | 2 · 11 · 55 | 1 | 4 | 1 | 24 | 0 | 16/24 (0.67) |
| A->B | edges3_current | validation | 5 · 14.5 · 44 | 0 | 1 | 0 | 24 | 0 | 15/24 (0.62) |
| B->A | int_k2 | source | 11 · 22 · 44 | 0 | 0 | 0 | 16 | 0 | 9/16 (0.56) |
| B->A | int_k2 | validation | 5 · 19.5 · 55 | 0 | 1 | 0 | 16 | 0 | 9/16 (0.56) |
| B->A | int_k3 | source | 8 · 22 · 41 | 0 | 0 | 0 | 24 | 0 | 13/24 (0.54) |
| B->A | int_k3 | validation | 5 · 19.5 · 55 | 0 | 1 | 0 | 24 | 0 | 13/24 (0.54) |
| B->A | int_k4 | source | 8 · 16.5 · 41 | 0 | 0 | 0 | 32 | 0 | 19/32 (0.59) |
| B->A | int_k4 | validation | 2 · 11.5 · 55 | 1 | 5 | 0 | 32 | 0 | 20/32 (0.62) |
| B->A | int_k5 | source | 8 · 16.5 · 41 | 0 | 0 | 0 | 32 | 0 | 19/32 (0.59) |
| B->A | int_k5 | validation | 2 · 11.5 · 55 | 1 | 5 | 0 | 32 | 0 | 20/32 (0.62) |
| B->A | int_each | source | 1 · 10 · 41 | 1 | 23 | 0 | 64 | 1 | 35/63 (0.56) |
| B->A | int_each | validation | 0 · 7 · 55 | 21 | 28 | 17 | 64 | 17 | 30/47 (0.64) |
| B->A | edges3_current | source | 5 · 14.5 · 44 | 0 | 1 | 0 | 24 | 0 | 15/24 (0.62) |
| B->A | edges3_current | validation | 2 · 11 · 55 | 1 | 4 | 1 | 24 | 0 | 16/24 (0.67) |

## Constats chiffrés (sans interprétation causale)
- **[V]** `int_k4`/`int_k5` atteignent 3 niveaux en A→B (A ne dépasse pas 3 niveaux par la règle des cibles) et 4 en B→A. Les niveaux 4 et 5 ne sont donc testés qu'en B→A (4 niveaux) ; `int_each` donne 7 niveaux (A→B) et 8 (B→A).
- **[V]** Coût transféré : A→B de 0,0448 à 0,0520 sur les 6 jeux ; B→A de 0,0303 à 0,0357. Les IC bootstrap sont larges (largeur de 0,037 à 0,068) et contiennent d = 0,03 dans les 12 lignes ; la part de réplicats ≤ d est de 0,25 à 0,30 en A→B et de 0,43 à 0,53 en B→A.
- **[V]** `int_each` : 9 cellules sources sans IC en A→B (13 à ≤ 2 réservations, 9 en repli) ; en B→A, 17 cellules de validation sans IC (21 à ≤ 2 réservations). Part des cellules dont l'IC contient d : 0,52 à 0,67 sur toutes les lignes.
- **[V]** En B→A `int_each`, table-greedy choisit l'action 0 au niveau 0 (nof_ue ≤ 1) et l'action 2 au niveau 2. Dans les tables sources de B, la cellule (action 0, niveau 0) repose sur 3 réservations et 487 fenêtres, avec un coût moyen de 0,00035 ; la cellule (action 2, niveau 2) sur 7 réservations. Rien n'indique que ces coûts soient fiables au vu des effectifs en réservations [H].
- **[V]** Avec les 3 niveaux actuels, le coût transféré (0,0520 en A→B, 0,0303 en B→A) est le plus haut des six jeux en A→B et le plus bas en B→A.

## Limites
1. **[H]** Deux scripts seulement ; IC conditionnels au script, réservations supposées échangeables ; l'effet scheduler reste confondu avec le moment d'exécution (D7/D8).
2. **[H]** Arêtes et `r_scale` fixés à leur valeur source dans le bootstrap : la variabilité due aux arêtes n'est pas propagée.
3. Les arêtes diffèrent entre sens (source A ≠ source B) : A→B et B→A ne comparent pas la même partition.
4. Les tables restent tabulaires ; R1-W2 critique aussi un critique continu, non traité ici.
5. Réplicats invalides : 0 à 2 sur 2000 par ligne (action absente d'une table rééchantillonnée), exclus.
