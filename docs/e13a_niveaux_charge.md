# E13a — Sensibilité au nombre de niveaux de charge (R1-W2) — branche `revision/13-bins-fenetre`

Code : `src/e13_load_levels.py`. Tests : `tests/test_e13.py`. Lancement : `python -m src.e13_load_levels --out results/e13a` → `results/e13a_{summary.json,cells.csv}`, journal `results/e13a.log` (gitignorés).
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée · **[P]** problème confirmé · **[Q]** question ouverte.

## Statut (à lire d'abord)
- **Descriptif, sur les plis A et B du train.** Aucune valeur n'est une performance : ce sont des valeurs selon des tables (DM). Le split test n'est pas lu (`test_split_read: false`) [V].
- **La configuration principale du papier reste celle qui a été gelée (3 niveaux, fenêtre de 5 s).** Cette analyse ne la modifie pas et **ne motive aucune troisième lecture du test**.
- Aucun nombre de niveaux n'est choisi, classé ou recommandé. Tous les jeux sont rapportés.

## Protocole
- Code : commit `ed677b6` ; run avec `git_dirty_src_tests = false` [V]. Dataset `268d524c117eb6de`. d = 0,03. Seed 0, B = 2000.
- Plis : A = `a908e4cc`, B = `a53521b2`. « A→B » : arêtes, tables et table-greedy construits sur A ; évalués sur les tables de B, fenêtres de B binnées avec les arêtes de A (idem B→A). Quantiles calculés sur le script **source** uniquement (décision validée).
- Table-greedy = celui d'E11 (plus petit λ de la grille tel que coût ≤ d). Tables = `tables_from_sums` (repli sur la moyenne par action si < 20 fenêtres).
- IC de cellule : bootstrap percentile par réservation dans la cellule, moyenne brute Σc/Σn. Cellules à < 2 réservations : pas d'IC, comptées à part.
- IC du coût transféré : réservations rééchantillonnées dans le script source et dans le script de validation (indépendamment), arêtes et r_scale fixes. **Conditionnel aux deux scripts** ; ne mesure pas la variabilité entre scripts [H : réservations échangeables].

## Garde de reproduction (lancée en premier) [V]
Avec les arêtes actuelles, la garde retrouve les valeurs d'E11 : transféré A→B 10,352 / 0,0520 ; B→A 11,370 / 0,0303 ; oracles 10,765 / 0,0286 (sur B) et 11,703 / 0,0215 (sur A) ; et le rebinning est identique à `load_bin` du parquet pour A et B. Tolérances : 5·10⁻⁴ (reward), 5·10⁻⁵ (coût), correspondant à l'arrondi imprimé en E11.

## [P] Résultat principal : les quantiles dégénèrent, k demandé ≠ k réalisé
- **[V]** `nof_ue` est entier pour 98,3 % (A) et 98,0 % (B) des fenêtres (202 et 217 valeurs distinctes). Mon hypothèse de départ, « `nof_ue` est continu », était **fausse** (je l'avais tirée de la note de phase 1 sans la vérifier).
- **[V]** Dans le script A, les quantiles de 20 % à 80 % valent tous 6,0 : la règle fixée d'avance (fusion des arêtes dupliquées, rien substitué) donne **2 niveaux pour k = 2, 3, 4 et 5 en A→B**. Les quatre lignes A→B sont donc la même partition ; leurs seules différences (IC bootstrap) sont du bruit Monte-Carlo, car le flux aléatoire diffère d'un jeu à l'autre.
- **[V]** En B→A : k = 2 → 2 niveaux ; k = 3 et 4 → 3 niveaux (même partition, arêtes 5 et 6) ; k = 5 → 4 niveaux (arêtes 4, 6, 7).
- **Conséquence :** les 4 et 5 niveaux ne sont pas testés en A→B, et seulement partiellement en B→A. **Cette analyse ne répond donc pas à la question « 4 ou 5 niveaux ».** Une découpe qui sépare les ex æquo (rangs, ou arêtes sur les entiers) n'a pas été faite : elle serait un nouveau protocole, à fixer avant d'être lancée (voir questions ouvertes).

## Résultats
Table-greedy construit sur la source, évalué sur la validation (DM).

| sens | jeu d'arêtes | k demandé → réalisé | arêtes | parts fenêtres (source) | action par niveau | reward transféré | coût transféré | IC 95 % bootstrap du coût | part de réplicats ≤ d |
|---|---|---|---|---|---|---|---|---|---|
| A->B | k2 | 2 → 2 | [6.0] | [0.903, 0.097] | [6, 6] | 11.209 | 0.0256 | [0.0073 ; 0.0473] | 0.78 |
| A->B | k3 | 3 → 2 | [6.0] | [0.903, 0.097] | [6, 6] | 11.209 | 0.0256 | [0.0072 ; 0.0448] | 0.79 |
| A->B | k4 | 4 → 2 | [6.0] | [0.903, 0.097] | [6, 6] | 11.209 | 0.0256 | [0.0074 ; 0.0470] | 0.78 |
| A->B | k5 | 5 → 2 | [6.0] | [0.903, 0.097] | [6, 6] | 11.209 | 0.0256 | [0.0071 ; 0.0408] | 0.80 |
| A->B | edges3_current | 3 → 3 | [3.5, 5.5] | [0.053, 0.104, 0.842] | [7, 7, 6] | 10.352 | 0.0520 | [0.0147 ; 0.0821] | 0.32 |
| B->A | k2 | 2 → 2 | [6.0] | [0.776, 0.224] | [6, 6] | 11.659 | 0.0295 | [0.0156 ; 0.0541] | 0.52 |
| B->A | k3 | 3 → 3 | [5.0, 6.0] | [0.356, 0.419, 0.224] | [6, 6, 6] | 11.398 | 0.0357 | [0.0142 ; 0.0586] | 0.44 |
| B->A | k4 | 4 → 3 | [5.0, 6.0] | [0.356, 0.419, 0.224] | [6, 6, 6] | 11.398 | 0.0357 | [0.0143 ; 0.0581] | 0.41 |
| B->A | k5 | 5 → 4 | [4.0, 6.0, 7.0] | [0.231, 0.545, 0.081, 0.143] | [6, 6, 6, 6] | 11.487 | 0.0311 | [0.0169 ; 0.0523] | 0.48 |
| B->A | edges3_current | 3 → 3 | [3.5, 5.5] | [0.136, 0.222, 0.642] | [6, 4, 6] | 11.370 | 0.0303 | [0.0149 ; 0.0522] | 0.56 |

Lecture : la ligne `edges3_current` redonne E11 (garde). Le coût transféré va de 0,0256 à 0,0520 (A→B) et de 0,0295 à 0,0357 (B→A) selon la partition ; **les IC bootstrap sont larges (largeur 0,034 à 0,067) et contiennent d dans les 10 lignes**. Aucun écart entre jeux n'est donc distinguable du bruit de rééchantillonnage, même conditionnel aux scripts, et aucun classement n'en est tiré. Seule la ligne `edges3_current` A→B a une borne basse de l'IC (0,0147) et une médiane (0,0375) qui restent loin de sa valeur ponctuelle (0,0520) [V] : le point à 0,0520 est dans la queue haute de ses réplicats (part ≤ d : 0,32 ; elle est de 0,41 à 0,80 dans les autres lignes).

### Effectifs et IC par cellule (action × niveau)
| sens | jeu | côté | réservations/cellule min · méd · max | cellules vides | ≤ 2 rés. | ≤ 5 rés. | < 20 fenêtres (repli) | sans IC | IC contient d |
|---|---|---|---|---|---|---|---|---|---|
| A->B | k2 | source | 7 · 29.5 · 55 | 0/16 | 0 | 0 | 0 | 0 | 8/16 (0.50) |
| A->B | k2 | validation | 12 · 27 · 44 | 0/16 | 0 | 0 | 0 | 0 | 6/16 (0.38) |
| A->B | k3 | source | 7 · 29.5 · 55 | 0/16 | 0 | 0 | 0 | 0 | 8/16 (0.50) |
| A->B | k3 | validation | 12 · 27 · 44 | 0/16 | 0 | 0 | 0 | 0 | 6/16 (0.38) |
| A->B | k4 | source | 7 · 29.5 · 55 | 0/16 | 0 | 0 | 0 | 0 | 8/16 (0.50) |
| A->B | k4 | validation | 12 · 27 · 44 | 0/16 | 0 | 0 | 0 | 0 | 6/16 (0.38) |
| A->B | k5 | source | 7 · 29.5 · 55 | 0/16 | 0 | 0 | 0 | 0 | 8/16 (0.50) |
| A->B | k5 | validation | 12 · 27 · 44 | 0/16 | 0 | 0 | 0 | 0 | 6/16 (0.38) |
| A->B | edges3_current | source | 2 · 11 · 55 | 0/24 | 1 | 4 | 1 | 0 | 16/24 (0.67) |
| A->B | edges3_current | validation | 5 · 14.5 · 44 | 0/24 | 0 | 1 | 0 | 0 | 15/24 (0.62) |
| B->A | k2 | source | 12 · 27 · 44 | 0/16 | 0 | 0 | 0 | 0 | 6/16 (0.38) |
| B->A | k2 | validation | 7 · 29.5 · 55 | 0/16 | 0 | 0 | 0 | 0 | 8/16 (0.50) |
| B->A | k3 | source | 8 · 22 · 41 | 0/24 | 0 | 0 | 0 | 0 | 13/24 (0.54) |
| B->A | k3 | validation | 5 · 19.5 · 55 | 0/24 | 0 | 1 | 0 | 0 | 13/24 (0.54) |
| B->A | k4 | source | 8 · 22 · 41 | 0/24 | 0 | 0 | 0 | 0 | 13/24 (0.54) |
| B->A | k4 | validation | 5 · 19.5 · 55 | 0/24 | 0 | 1 | 0 | 0 | 13/24 (0.54) |
| B->A | k5 | source | 8 · 16 · 43 | 0/32 | 0 | 0 | 0 | 0 | 16/32 (0.50) |
| B->A | k5 | validation | 2 · 12.5 · 55 | 0/32 | 1 | 3 | 0 | 0 | 19/32 (0.59) |
| B->A | edges3_current | source | 5 · 14.5 · 44 | 0/24 | 0 | 1 | 0 | 0 | 16/24 (0.67) |
| B->A | edges3_current | validation | 2 · 11 · 55 | 0/24 | 1 | 4 | 1 | 0 | 16/24 (0.67) |


- **[V]** Sur les partitions à 2 niveaux, tous les effectifs sont élevés (≥ 7 réservations par cellule) ; sur les 3 niveaux actuels, une cellule source A→B n'a que 2 réservations et une cellule de validation B→A aussi.
- **[V]** La part de cellules dont l'IC contient d = 0,03 va de 0,38 à 0,67 selon les lignes (dénominateurs 16 à 32). Elle n'est pas monotone en k, et l'ordre de grandeur dépend surtout des effectifs.
- **[V]** Aucune cellule n'est vide, aucune n'est sans IC.

## Limites et hypothèses
1. **[P]** Dégénérescence des quantiles (ci-dessus) : k = 4 et 5 ne sont pas réellement testés.
2. **[H]** Deux scripts seulement ; IC conditionnels au script ; rien n'est généralisable.
3. **[H]** Le bootstrap suppose les réservations échangeables dans un script ; l'effet scheduler reste confondu avec le moment d'exécution (D7/D8) : changer k ne lève pas cette confusion.
4. **[H]** Les arêtes et r_scale sont fixés à leur valeur du script source dans le bootstrap ; la variabilité due aux arêtes n'est pas propagée.
5. Les tables restent tabulaires : cette analyse ne répond que partiellement à R1-W2, dont la critique porte aussi sur un critique continu non binné.
6. 0 ou 1 réplicat invalide sur 2000 selon les lignes (action absente d'une table rééchantillonnée), exclu du calcul de l'IC (`n_invalid` dans le JSON).

## Questions ouvertes
- **[Q]** Faut-il fixer, avant exécution, une découpe tolérante aux ex æquo (arêtes sur les entiers 5/6/7, ou quantiles randomisés par rang) pour tester vraiment 4 et 5 niveaux ? Non faite ici.
- **[Q]** Un IC sur la différence de coût transféré entre deux jeux d'arêtes n'est pas calculé (réplicats non appariés).
