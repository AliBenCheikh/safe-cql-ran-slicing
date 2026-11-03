# E13a2 — Protocole des niveaux de charge à arêtes entières (R1-W2) — GELÉ AVANT EXÉCUTION

Écrit et commité avant toute évaluation. Aucune table de coût, aucun coût ni reward n'a été calculé avec ces arêtes ; seules les **arêtes** et les parts de fenêtres du script source ont été calculées pour les montrer (`python -m src.e13a2_integer_levels --edges`).
Code : `src/e13a2_integer_levels.py` (réutilise E13a). Tests : `tests/test_e13a2.py`. **Une seule exécution, sans nouvelle variante.**

## Pourquoi
E13a : 98 % des fenêtres ont un `nof_ue` entier ; les quantiles de A (75 % des fenêtres à 6) ont fusionné, d'où 2 niveaux pour k = 2 à 5 en A→B. Les arêtes sont donc posées sur des entiers.

## Règles (dérivées du script source seul, train seul ; bins fermés à droite sur la valeur brute : x ≤ e)
1. `int_k{2,3,4,5}` : pour chaque probabilité cible i/k, l'entier e ∈ {1..8} dont la part cumulée mean(nof_ue ≤ e) est la plus proche de i/k (égalité → e le plus petit). Entiers dupliqués fusionnés : le k réalisé est rapporté, rien n'est substitué.
2. `int_each` : un niveau par valeur entière (arêtes 1..7). Un niveau à < 1 % des fenêtres source est fusionné avec le voisin de plus petite part (égalité → le plus bas), de façon répétée.
3. `edges3_current` : référence (3,5 / 5,5), qui sert aussi de garde de reproduction (0,0520 / 0,0303, abandon si échec).
4. Petites cellules : règle inchangée de `tables_from_sums` (coût d'une cellule < 20 fenêtres → moyenne par action ; reward → moyenne par action seulement si la cellule est vide). Le nombre de cellules en repli et les effectifs en réservations sont rapportés.
5. Mesures identiques à E13a (effectifs, part d'IC contenant d = 0,03 avec dénominateurs, actions, reward et coût transférés, bootstrap par réservation B = 2000, seed 0, conditionnel au script).

## Arêtes obtenues (règles 1 et 2, calculées sur le source ; part de fenêtres source par niveau)
| source | jeu | arêtes | niveaux | parts |
|---|---|---|---|---|
| A | int_k2 | 5 | 2 | 0,157 / 0,843 |
| A | int_k3, int_k4, int_k5 | 5, 6 | 3 | 0,157 / 0,747 / 0,097 |
| A | int_each | 2,3,4,5,6,7 | 7 | 0,014 / 0,040 / 0,025 / 0,079 / 0,747 / 0,023 / 0,073 |
| B | int_k2 | 5 | 2 | 0,356 / 0,644 |
| B | int_k3 | 5, 6 | 3 | 0,356 / 0,419 / 0,224 |
| B | int_k4, int_k5 | 4, 5, 6 | 4 | 0,231 / 0,125 / 0,419 / 0,224 |
| B | int_each | 1..7 | 8 | 0,055 / 0,047 / 0,033 / 0,096 / 0,125 / 0,419 / 0,081 / 0,143 |

## Limites déjà visibles avant exécution
- **A ne dépasse pas 3 niveaux** par la règle 1 (75 % des fenêtres à 6) : k = 3, 4, 5 y sont la même partition ; B atteint 4 niveaux. 4 et 5 niveaux ne seront donc toujours pas testés en A→B, sauf via `int_each` (7 niveaux, dont plusieurs à < 8 % des fenêtres).
- `int_each` produit 56 à 64 cellules (action × niveau) : beaucoup auront peu de réservations ou < 20 fenêtres (repli). Le rapport donnera les comptes ; aucune conclusion de type « meilleur découpage ».
- Les arêtes ne sont pas les mêmes dans les deux sens (source A ≠ source B), donc A→B et B→A ne comparent pas la même partition.
- Descriptif, deux scripts, train seul. La configuration gelée du papier (3 niveaux, 5 s) reste la principale ; aucune troisième lecture du test n'est motivée.
