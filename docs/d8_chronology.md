# D8 — Chronologie absolue, séparation PF/RR dans le temps, paires proches, ruptures du coût (branche `revision/07-d8-ordre-chronologique`)

Code : `src/checks/d8_chronology.py`. Tests : `tests/test_d8.py` (21 tests synthétiques).
Lancement : `python -m src.checks.d8_chronology --data /home/AliBen/data/safe-cql/dataset-kpm` → `results/d8_{summary.json,times,order,inversions,separation,nearest_pairs,nearest_summary,drift_values,daily,daily_jumps,drift_breaks}.csv`.
Fichiers bruts ouverts : **uniquement** `bs/enb_metrics.csv` (colonnes `time`, `nof_ue`) des 706 réservations utilisables ; le reste vient de `results/dataset_canonical.parquet` (version `268d524c117eb6de`) et `results/d6_reservations.csv`. Lecture seule, déterministe sauf les permutations de la partie 5 (seed 0, 1 000). Aucun entraînement.
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée · **[P]** problème confirmé · **[Q]** question ouverte.
Choix (pas des résultats) : classes d'écart heures (< 24 h) / jours (< 7 j) / semaines (≥ 7 j) ; appariement glouton un-pour-un par écart croissant ; parts gardées 100 / 50 / 25 % des paires (≥ 3 paires) ; « même ordre de grandeur » = rapport dans ]0,1 ; 10[ ; distinguable de 0 = |diff| > 2 SE ; jours = jours calendaires UTC.

## 1. Date et heure de début absolues (UTC), lues dans les données
- **[V]** `t0_ms` = premier échantillon eNB avec `nof_ue > 0` (définition de `build_dataset._enb_stream`, ancre de la fenêtre 0) ; `enb_first_ms` / `enb_last_ms` = premier / dernier échantillon du fichier. Les 706 réservations ont un `t0` ; les 706 sont en epoch ms plausible (2017-2030) ; **706/706 sont égaux au `t0_ms` stocké par D6**.
- **[V]** Période : 2024-02-09 23:45 UTC → 2024-02-26 04:43 UTC. Cluster 1 : 9→22 fév. ; cluster 2 : 12→24 fév. ; cluster 3 : 14→26 fév. **Les trois clusters se recouvrent dans le temps.**
- Table par réservation : `results/d8_times.csv` (`start_utc`, `date_utc`, `hour_utc`).
- **[H]** `time` est supposé en epoch ms UTC, sur l'horloge de l'hôte eNB ; aucune référence externe pour la vérifier (D2 n'a vérifié que la cohérence relative des fichiers). **[H]** `t0` est l'arrivée des UE, pas l'heure de réservation de la plateforme (inconnue).

## 2. L'ordre des identifiants est-il l'ordre chronologique ?
- **[V]** Oui, presque exactement : Spearman(id, `t0`) = 1,000 (706 réservations, et dans chaque cluster) ; Kendall 0,9999.
- **[V]** 5 inversions entre identifiants consécutifs (4 dans le cluster 2, 1 dans le cluster 3), toutes de **0,003 à 0,28 h** (≤ 17 min) : `results/d8_inversions.csv`. Le cluster 1 est strictement monotone.
- **Conséquence** : l'hypothèse « identifiants = ordre chronologique » de D6/D7 est **levée** pour l'ordre ; les analyses « moitié précoce / tardive » de D7 étaient donc bien temporelles. Elle ne dit rien des **durées** entre blocs (partie 3).

## 3. PF et RR : séparés par des heures, des jours ou des semaines ?
17 couples (script, slicing) ont les deux schedulers parmi les utilisables ; `results/d8_separation.csv`.
- **[V]** **Aucun couple n'est entrelacé** : 1 seule bascule dans la suite triée par heure de début pour les 17, 0 réservation à déplacer pour obtenir deux blocs propres.
- **[V]** Les 12 couples des 3 scripts à 8 actions :

| script (cluster) | bloc PF | bloc RR | écart fin du 1ᵉʳ bloc → début du 2ᵉ | classe |
|---|---|---|---|---|
| a908e4cc (2), 4 slicings | 12→14 fév. | 22→24 fév. | 193-194 h (≈ 8,0 j) | semaines |
| a53521b2 (3), 4 slicings | 14→16 fév. | 24→26 fév. | 194-202 h (≈ 8,1-8,4 j) | semaines |
| c40f2fe7 (1, test), 4 slicings | 9/10→20 fév. 08:00 | 20 fév. 20:30 → 22 fév. | 12,4-13,1 h | heures |

- **[V]** Pour c40f2fe7, les blocs sont contigus (≈ 13 h) mais le bloc PF dure ≈ 10 jours et le bloc RR ≈ 1,5 jour.
- **[V]** Les 5 petits couples (1 à 4 réservations par scheduler) : 2 en « heures » (1dd38082, 17-20 h), 3 en « semaines » (17c6c988, cb86fe34 ×2, 220-234 h).
- **[P]** Pour a908e4cc et a53521b2 (2 des 3 scripts), PF et RR ne se recouvrent jamais et sont à plus d'une semaine : l'effet scheduler est confondu avec tout ce qui varie en 8 jours (état de la plateforme, charge du réseau, maintenance). Le seuil de 7 j est un choix ; l'écart observé (≈ 8 j) le dépasse de peu.
- **[Q]** La cause du délai de ≈ 8 jours entre blocs (file d'attente de la plateforme, ordre de lancement choisi, maintenance) n'est pas documentée dans les données.

## 4. PF − RR sur les paires les plus proches dans le temps (`d8_nearest_pairs.csv`, `d8_nearest_summary.csv`)
Appariement un-pour-un, même script et même slicing, par écart de `t0` croissant ; on garde les 100 / 50 / 25 % de paires les plus proches (moins de 3 paires : non évalué). Différence calculée sur les bins de temps-script communs de chaque paire ; SE appariée = sd des différences / √n **[H : paires supposées indépendantes]**. Référence : l'estimation D7 (toutes réservations).

| paires gardées | écart médian des paires (h) | coût : même signe que D7 | même signe et ordre | > 2 SE | reward : même signe que D7 | > 2 SE |
|---|---|---|---|---|---|---|
| 100 % (12 cellules) | 222 | 12/12 | 12/12 | 10/12 | 11/12 | 0/12 |
| 50 % (12) | 205 | 12/12 | 12/12 | 9/12 | 11/12 | 0/12 |
| 25 % (8) | 201 | 8/8 | 8/8 | 3/8 | 5/8 | 2/8 |

- **[V] Coût** : PF − RR reste **positif dans toutes les cellules évaluables** et dans le même ordre de grandeur que D7 (rapport 0,30 à 2,9 ; +0,014 à +0,34). Cohérence entre scripts (critère D7 : même signe, rapport < 10) : 4/4 slicings à 100 % et 25 %, 3/4 à 50 %. La puissance diminue (SE plus grande, 3/8 distinguables à 25 % avec 3-5 paires).
- **[V] Reward** : même conclusion que D7 — pas d'effet cohérent (signe changeant avec la part gardée : a53521b2 slicing 1 passe de −0,27 à +1,09 ; c40f2fe7 slicing 3 de −0,07 à +0,14 puis −0,71).
- **[P] Limite essentielle** : pour a908e4cc et a53521b2, les paires « les plus proches » sont les deux réservations de part et d'autre de la bascule, donc **encore à 196-230 h d'écart médian (≈ 8-9 j)** (≈ 200 h pour les 25 % les plus proches). Ce contrôle ne rapproche pas ces deux scripts dans le temps. Seul c40f2fe7 donne des paires proches : écart médian 17-24 h (50 % les plus proches ; une paire du slicing 4 reste à 221 h) et 16-21 h (25 %) : l'effet y reste positif (coût +0,014 à +0,135 contre +0,042 à +0,107 en D7), mais avec un seul script (= l'unité indépendante, cf. D6), et 3 des 6 cellules (50 % / 25 %) ne sont pas distinguables de 0.
- **Réponse** : le **sens** et l'**ordre de grandeur** de l'effet coût restent les mêmes quand on ne garde que les paires les plus proches ; mais ce résultat ne réfute pas la confusion avec le moment d'exécution, car les paires les plus proches restent séparées de plus d'une semaine pour 2 scripts sur 3 et de ≈ 1 demi-journée pour le 3ᵉ.

## 5. Ruptures de la dérive temporelle du coût (`d8_drift_breaks.csv`, `d8_daily_jumps.csv`, `d8_daily.csv`)
Valeur = coût moyen par réservation sur le segment de temps-script couvert par ≥ 80 % des réservations du script (réservations couvrant ≥ 90 % de ce segment : 174 / 199 / 122 pour a53521b2 / a908e4cc / c40f2fe7). Résidus : `resid_slicing` (moyenne par script × slicing retirée : une marche due au scheduler reste visible) et `resid_cell` (moyenne par script × slicing × scheduler retirée : dérive à l'intérieur d'un bloc seulement).
- **[V] Meilleure coupure unique (`resid_slicing`)** : rupture signalée pour **les 3 scripts** (|t| 6,0 à 7,4 ; p de permutation 0,001 ; marche −0,06 à −0,13 du bloc PF au bloc RR), et **chaque coupure tombe exactement à la bascule PF → RR** (pause de 195 h, 193 h et 12,8 h entre les deux réservations adjacentes ; part de PF à gauche 1,0, à droite 0). La « rupture » du coût *est* l'effet scheduler : rien ne permet de les distinguer.
- **[V] À l'intérieur des blocs (`resid_cell`)** : aucune coupure significative (p = 0,13 / 0,32 / 0,66 ; |t| ≤ 2,9) pour le coût.
- **[V] Sauts entre jours consécutifs** (z de Welch, |z| > 3, ≥ 3 réservations de chaque côté) : un seul pour le coût, **c40f2fe7 20→21 fév.** (−0,045 ; z = −3,7), qui coïncide avec la bascule PF → RR (part de PF 0,82 → 0). Aucun saut signalé dans les blocs PF ou RR, mais plusieurs sont sous le seuil : a908e4cc PF 12→13 fév. **+0,116 (z = 1,96)** — le coût moyen du bloc PF passe de 0,118 à 0,231 en un jour (n = 17 et 12) — sans que le scheduler change. Le coût moyen par jour dans les blocs RR varie peu (0,010-0,043).
- **[V] Reward** : coupure signalée pour a53521b2 seulement (à la bascule), un saut isolé pour c40f2fe7 (PF, 11→12 fév., n = 3 d'un côté).
- **[P]** La variation jour-à-jour *dans* le bloc PF (a908e4cc : ×2 en un jour, sans significativité) est du même ordre que l'effet scheduler estimé (+0,10 à +0,20) : cohérent avec D7 (dérive PF du même ordre que l'effet), non tranché ici.

## Hypothèses non vérifiées
1. **[H]** `time` de `enb_metrics.csv` = epoch ms UTC fiable ; `t0` = arrivée des UE, pas l'heure de réservation.
2. **[H]** Seuils et choix de l'analyste (classes d'écart, parts de paires, ratio < 10, 2 SE, |z| > 3, p < 0,01).
3. **[H]** SE des paires et z journaliers : réservations/paires indépendantes (faux d'après D6 : l'unité est le script) ; p de permutation sans autocorrélation, donc une dérive lente produit aussi une coupure « significative » (le rapport SSE tendance linéaire / marche vaut seulement 1,08-1,18).
4. **[H]** Les parties 4-5 portent sur les 587 réservations des 3 scripts à 8 actions dont l'origine de temps-script est acceptée (D6) ; les parties 1-3 sur les 706 utilisables. Le caractère utilisable des réservations n'a pas été examiné comme fonction du temps **[Q]**.
5. **[Q]** Cause du délai de ≈ 8 jours entre blocs ; recouvrement temporel des trois clusters (même plateforme ou plateformes différentes ?) ; rien dans ces fichiers ne sépare le scheduler du moment d'exécution, ni pour a908e4cc/a53521b2 (≥ 8 j) ni pour c40f2fe7 (≈ 13 h).
