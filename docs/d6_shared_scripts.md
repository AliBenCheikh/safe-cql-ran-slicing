# D6 — Scripts de trafic partagés (branche `revision/05-d6-scripts-partages`)

Code : `src/checks/d6_shared_scripts.py` (lecture seule sur `data/`). Tests : `tests/test_d6.py` (12 tests synthétiques).
Lancement : `python -m src.checks.d6_shared_scripts` → `results/d6_{summary.json,scripts.json,inventory.csv,noise.csv,action_diffs.csv,reservations.csv}`.
Dataset version `268d524c117eb6de` (identique à celle du parquet canonique). Déterministe, aucun seed. Aucun entraînement.
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée · **[P]** problème confirmé · **[Q]** question ouverte.

## 1. Scripts, clusters, configurations (19 scripts distincts, 1 116 réservations, 0 sans script)
- **[V]** Aucun script n'est présent dans deux clusters. Aucun script commun au train et au test.
- **[V]** Les 3 scripts dominants *utilisables* couvrent chacun 4 slicings × 2 schedulers (réservations utilisables / totales par configuration dans `d6_scripts.json`) :

| script (md5) | cluster | rés. totales | rés. utilisables | par config (utilisables) |
|---|---|---|---|---|
| a908e4cc | 2 | 275 | 247 | 8 à 55 |
| a53521b2 | 3 | 270 | 231 | 12 à 44 |
| c40f2fe7 | 1 | 187 | 177 | 18 à 29 |

- **[P] Correction à `dataset_notes.md`** : « le slicing 5 n'apparaît dans aucun script dominant » est faux pour les scripts 120, 115 et 60 : ils sont presque entièrement en slicing 5 (99+20, 31+84, 26+29 réservations) et donc 0 utilisable (slicing 5 = pas de slicing, exclu).
- **[V]** 11 scripts ont au moins une réservation utilisable ; les 8 autres ont 1 à 15 réservations et 1 à 5 configurations sur 8 : aucun ne permet de comparer toutes les actions.

## 2. Bruit entre répétitions (`d6_noise.csv`)
Deux mesures par (script, cluster, action) avec ≥ 2 répétitions : variance entre réservations de la moyenne par réservation (`_raw`), et variance entre répétitions à temps-script fixe, moyennée sur les bins (`_bin`).
- **[V]** Écart-type (`_raw`) du reward moyen par réservation, 3 scripts dominants : 0,4 à 5,0 Mbps pour des moyennes de 3 à 12 Mbps. Cas extrêmes : action 7 du script a53521, sd 4,95 pour une moyenne 8,8 (n=10).
- **[V]** Écart-type du coût moyen : 0,002 à 0,22 pour des moyennes de 0,002 à 0,23. À l'échelle du budget 0,03, le bruit entre répétitions est du même ordre que le budget.
- **[V]** Le bruit `_bin` (fenêtre à temps-script fixe) est supérieur au bruit `_raw` (coût : sd 0,009 à 0,29).

## 3. Différence entre actions, alignée sur le temps du script (`d6_action_diffs.csv`)
**Alignement** (voir docstring) : origine du script = `Sent Time` du premier paquet URLLC loggé − (`Sequence No.`−1)/débit − t du premier ON du flux ; fenêtre canonique `win` ↔ temps-script `t0 + 5·win − origine`, bin `round(·/5)`.
- **[V]** Sur les 621 réservations utilisables dont l'origine est acceptée (2 flux concordants à 1,5 s), la fenêtre 0 tombe à 71,2 s du script (min 69,6 · p25 70,9 · p75 71,8 · max 76,3), le premier ON étant à 70 s. **Le t0 actuel est déjà aligné sur le temps du script à ≈ 1 s.**
- **[V]** Conséquence : différence alignée script vs alignée sur `win` : écart absolu médian 0,001 Mbps (max 0,017) et 0,000 sur le coût (77 paires avec ≥ 10 répétitions de chaque côté). L'alignement ne change pas les résultats.
- 85 des 706 réservations utilisables sont rejetées pour l'alignement : 75 avec un seul flux URLLC observé (non vérifiable), 10 avec deux flux discordants (écart de 60 s ou 1 021 s : ma formule est fausse quand le premier paquet loggé n'est pas du premier segment ON). Elles restent dans le train/test, seulement exclues de la partie 3.
- **[V]** Exemple (script c40f2fe7, test) : 0 → 2 : +3,98 Mbps (SE 0,21), coût −0,010 (SE 0,015) ; 0 → 4 : +5,56 (0,46), coût −0,030 (0,012). La SE traite les moyennes par réservation comme indépendantes **[H]**.
- **[V]** Chaque réservation ne couvre que ≈ 350 fenêtres (≈ 29 min, script de 6 490 s) : de t=70 s à ≈ 1 800 s du script.

## 4. Train / test
| | réservations utilisables | scripts distincts | réservations par script (min / p25 / p50 / p75 / max) |
|---|---|---|---|
| train (clusters 2-3) | 510 | 8 | 1 / 2,5 / 6 / 69 / 247 |
| test (cluster 1) | 196 | 3 | 9 / 9,5 / 10 / 93,5 / 177 |
| (toutes réservations) train | 781 | 13 | 2 / 5 / 8 / 60 / 275 |
| (toutes réservations) test | 335 | 6 | 3 / 6,75 / 9,5 / 92,5 / 187 |

- **[P] Le test est de fait un seul script** : c40f2fe7 = 177 des 196 réservations utilisables (90 %). Le train est de fait deux scripts : 478 / 510 (94 %).
- **[P]** Le « nombre de réservations » n'est donc pas la taille d'échantillon effective pour la généralisation : n efficace pour la charge ≈ 1 script (test) et 2 scripts (train).

## Hypothèses non vérifiées
1. **[H] Exogénéité du trafic.** Fait vérifié dans le script : les 3 705 lignes `ON` des 19 scripts sont `UDP … PERIODIC` (émission pilotée par l'émetteur, boucle ouverte par construction MGEN). Non vérifié : que le débit *émis* soit identique entre réservations (seul le script l'est ; 3 scripts ne garantissent pas la même charge, cf. notes) et que le débit *reçu*/la charge `nof_ue` ne dépende pas de l'action.
2. **[H] Alignement temporel** : l'origine suppose que MGEN numérote à partir de 1 au démarrage du flux, un débit constant, et des horloges émetteur/eNB synchronisées (aucune correction d'offset). La concordance des deux flux est un contrôle de cohérence, pas une preuve.
3. **[H] Confusion avec l'ordre d'exécution.** Les IDs de réservation (supposés chronologiques **[H]**) montrent que le scheduler est exécuté par blocs : pour c40f2fe7, RR (sched 0) vers 142 703–142 714 et PF (sched 2) vers 141 833–142 515 ; même structure pour les deux autres scripts. Les slicings sont entrelacés dans chaque bloc. L'effet scheduler est donc confondu avec le moment de l'exécution ; l'effet slicing l'est peu.
4. **[Q]** `nof_ue`, radio : même script ne garantit pas la même charge observée ; non quantifié ici.
5. **[Q]** Lmax et budget 0,03 (voir `dataset_notes.md`).
