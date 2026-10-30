# D7 — Effet scheduler, couverture temporelle et ordre d'exécution (branche `revision/06-d7-ordre-scheduler`)

Code : `src/checks/d7_scheduler_order.py`. Tests : `tests/test_d7.py` (15 tests synthétiques).
Lancement : `python -m src.checks.d7_scheduler_order` → `results/d7_{summary.json,coverage,scheduler_effects,consistency,order_ranges,order_combos,order_drift,order_verdict,exogeneity,repetitions}`.
Lit **uniquement** des fichiers dérivés (`results/dataset_canonical.parquet`, version `268d524c117eb6de`, et `results/d6_reservations.csv`) : l'arbre brut n'est pas ouvert. Déterministe, sauf le test de permutation de la partie 4 (seed 0, 2 000 permutations). Aucun entraînement.
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée · **[P]** problème confirmé · **[Q]** question ouverte.

Périmètre : les 3 scripts ayant des fenêtres utilisables pour les 8 actions (sélection calculée, pas codée en dur) : a908e4cc (cluster 2), a53521b2 (cluster 3), c40f2fe7 (cluster 1, test). 655 réservations utilisables, dont **587** avec origine de temps-script acceptée (D6) : les 68 autres sont exclues des parties 1-4 (comptées en partie 5).
Convention : PF = sched 1, RR = sched 0 ; coût = `urllc_frac_viol` brut ; reward = `reward_embb_Mbps`. Les seuils (recouvrement 0,9 ; rapport d'ordre de grandeur < 10 ; |diff| > 2 SE) sont des **choix**, pas des résultats.

## 1. Toutes les réservations d'un script couvrent-elles le même segment ?
- **[V]** Non, au sens strict : intersection de tous les segments = 0 s pour les 3 scripts (`overlap_ratio` 0). Cause : des réservations tronquées ou démarrant tard (début jusqu'à 1 676 s, fin dès 236 s).
- **[V]** Hors ces réservations, oui : réservations hors « cœur » (début à > 10 s ou fin à > 60 s de la médiane), pour a535 / a908 / c40f : 40 sur 208, 39 sur 238, 24 sur 141 ; recouvrement du cœur 0,958 / 0,946 / 0,957. Médiane : début ≈ 71 s, fin ≈ 1 807-1 811 s ; 350 fenêtres couvertes par au moins 2 répétitions pour chaque comparaison ; pas de fenêtre manquante dans les segments (`median_fill` = 1,0).
- **[V]** Les fins médianes diffèrent légèrement entre schedulers (PF ≈ 1 797-1 806 s, RR ≈ 1 811 s) : ≈ 5-15 s, soit 1 à 3 fenêtres.
- **[H]** Les ≈ 18 % de réservations hors cœur ne sont pas expliquées (cause de la troncature non examinée). Les comparaisons des parties 2-4 se font sur les bins communs, donc ne dépendent pas de cette question.

## 2. PF − RR à slicing fixé, par script (`d7_scheduler_effects.csv`, `d7_consistency.csv`)
Différence sur les bins de temps-script communs (≈ 350 bins) ; SE naïve entre réservations **[H]** (traite les réservations comme indépendantes ; sous-estime l'incertitude d'après D6).

| slicing (PRB eMBB) | reward PF−RR (Mbps) a908 / a535 / c40f | coût PF−RR a908 / a535 / c40f |
|---|---|---|
| 1 (9)  | +0,23 / −0,24 / −0,24 | +0,180 / +0,109 / +0,042 |
| 2 (21) | −1,42 / −0,49 / −0,88 | +0,201 / +0,069 / +0,048 |
| 3 (30) | +0,45 / −2,76 / +0,11 | +0,163 / +0,109 / +0,107 |
| 4 (39) | −0,76 / −2,34 / −0,94 | +0,105 / +0,155 / +0,047 |

- **[V] Coût** : PF − RR est **positif dans les 12 couples (script, slicing)**, entre +0,04 et +0,20 ; le rapport max/min entre scripts est de 1,5 à 4,3 (même ordre de grandeur selon notre seuil) ; |diff| > 2 SE dans 11 couples sur 12 (3/3 aux slicings 1, 3, 4 ; 2/3 au slicing 2). Cet effet vaut 1,4 à 6,7 fois le budget 0,03.
- **[V] Reward** : le signe est négatif dans 9 couples sur 12 mais **non cohérent** : slicing 1 (signes mixtes, |diff| < 0,3, 0/3 distinguable de 0) et slicing 3 (+0,45 / −2,76 / +0,11, rapport 24). Cohérent seulement aux slicings 2 et 4 (négatif, rapport < 3,1) ; en moyenne sur les slicings : négatif pour les 3 scripts (−0,37 / −1,46 / −0,49 pour a908 / a535 / c40f), mais 0/3 distinguable de 0.
- **Réponse** : sens et ordre de grandeur cohérents entre les 3 scripts pour le **coût** ; **pas** pour le reward (effet petit devant le bruit, signe variable).
- **[H]** Ces différences mélangent l'effet du scheduler et celui du bloc d'exécution (partie 3).

## 3. Confusion avec l'ordre d'exécution (`d7_order_*.csv`)
- **[V]** Dans les 12 couples (script, slicing), les deux schedulers occupent des **blocs d'identifiants disjoints** : 1 seule bascule RR↔PF dans la suite triée, aucun recouvrement des plages. PF est avant RR pour a908 et a535, et en grande partie avant pour c40f2fe7 (plages PF 141 684-142 554, RR 142 630-142 786). Nombre de répétitions PF faible : 4 à 29.
- **[V]** Test demandé : on coupe chaque (scheduler, slicing) en moitié précoce / tardive d'identifiants, et on calcule PF − RR pour les 4 combinaisons. Le signe change selon la combinaison dans **1 couple sur 24 (script × slicing × métrique 3×4×2)** : c40f2fe7, slicing 3, reward (2 positives, 2 négatives). Le signe du coût ne change dans aucun couple (4/4 positifs partout).
- **[P] Cette stabilité ne lève pas la confusion.** Quelle que soit la moitié choisie, chaque comparaison oppose un bloc PF à un bloc RR séparés par 760 à 1 147 identifiants (médianes de moitiés) pour a908e4cc et a53521b2, 128 à 961 pour c40f2fe7 : elles sont toutes confondues avec le moment d'exécution. Le test montre seulement que la dérive *dans* un bloc n'inverse pas le signe, pas que le scheduler est identifié.
- **[V]** Ordre de grandeur de la dérive temporelle à action fixe (moitié tardive − précoce, `d7_order_drift.csv`) : côté RR, reward −0,13 à +1,33 Mbps, coût −0,03 à +0,06 ; côté PF, reward −2,35 à +0,30 Mbps, coût −0,15 à +0,20 (4 à 12 répétitions ; SE du coût 0,07 à 0,12 pour a908e4cc). Pour PF, la dérive dans le bloc est donc du **même ordre que l'effet scheduler** sur le coût pour a908e4cc (|dérive| 0,15 à 0,20 contre un effet de 0,10 à 0,20, avec une SE du même ordre) ; elle est faible pour RR.
- **[H]** Les identifiants sont supposés chronologiques (non vérifié sur les horodatages). **[Q]** Rien dans ce dataset ne permet de séparer scheduler et bloc : aucun script n'a RR et PF entrelacés.

## 4. nof_ue et débit reçu dépendent-ils de l'action, à script et bin fixés ? (`d7_exogeneity.csv`)
Méthode : y centré par bin de temps-script (bins couverts par ≥ 2 actions) ; une valeur par réservation (l'action est constante dans la réservation) ; F à un facteur (η² = part de variance inter-actions) ; p par permutation des étiquettes d'action entre réservations. Un test de Wald robuste par réservation avait été essayé et abandonné : il rejette trop souvent sous H0 (≈ 35 % de p < 0,05 par simulation).
Variables : `nof_ue` ; débit URLLC reçu = `n_pkts`/5 s **[H]** (paquets avec latence valide, 4 UE URLLC) ; débit eMBB = reward, en **contrôle positif** (dépend du split PRB par construction).

| subset | variable | η² (a908 / a535 / c40f) | p_perm |
|---|---|---|---|
| 8 actions | nof_ue | 0,18 / 0,11 / 0,12 | 0,0005 / 0,002 / 0,014 |
| 8 actions | URLLC rx pkt/s | 0,57 / 0,41 / 0,30 | ≤ 0,0005 |
| RR seul (4 slicings) | nof_ue | 0,014 / 0,002 / 0,055 | 0,48 / 0,96 / 0,25 |
| RR seul | URLLC rx pkt/s | 0,025 / 0,012 / 0,081 | 0,20 / 0,62 / 0,10 |
| PF seul (4 slicings) | nof_ue | 0,061 / 0,011 / 0,050 | 0,41 / 0,91 / 0,38 |
| PF seul | URLLC rx pkt/s | 0,126 / 0,029 / 0,051 | 0,11 / 0,68 / 0,36 |
| tous subsets | eMBB (contrôle) | 0,33 à 0,90 | ≤ 0,0005 |

- **[V]** Sur les 8 actions, `nof_ue` et le débit URLLC reçu dépendent de l'action (p ≤ 0,014), jusqu'à 16 % (nof_ue) et 42 % (URLLC) d'écart relatif à la moyenne du bin pour une action. Le contrôle positif est bien détecté.
- **[V]** À scheduler fixé (4 slicings), aucune dépendance détectée (p de 0,10 à 0,96, écarts ≤ 15 % pour PF, ≤ 6 % pour RR). Donc la dépendance sur les 8 actions vient du **changement de scheduler**, c'est-à-dire de RR vs PF **ou** du bloc d'exécution (partie 3) : non séparables.
- **[H]** L'absence de détection à scheduler fixé n'est pas une preuve d'indépendance : peu de puissance (PF : 4 à 29 répétitions), et l'échange des étiquettes suppose l'échangeabilité, que les blocs d'identifiants contredisent partiellement.
- **[Q]** Pourquoi le débit URLLC reçu (et nof_ue) diffère entre blocs PF et RR alors que le script émet la même charge (MGEN UDP périodique) : perte de paquets, UE détachés, ou état différent de la plateforme. Non examiné.

## 5. Répétitions par (slicing, scheduler) (`d7_repetitions.csv`; utilisables / origine acceptée)
| script | RR slicings 1-4 | PF slicings 1-4 |
|---|---|---|
| a908e4cc | 43/41, 50/49, 49/46, 55/53 | 18/17, 11/11, 13/13, 8/8 |
| a53521b2 | 43/39, 40/35, 44/40, 43/39 | 17/15, 15/13, 17/17, 12/10 |
| c40f2fe7 | 23/21, 18/17, 20/19, 19/19 | 18/10, 25/10, 25/23, 29/22 |

- **[V]** Déséquilibre RR/PF de 2 à 7 pour a908e4cc et a53521b2 (PF : 8 à 18 répétitions). c40f2fe7 (test) est équilibré (18 à 29 par cellule), mais 7 à 15 réservations PF (slicings 1, 2, 4) n'ont pas d'origine acceptée.
- **[P]** Ce sont des répétitions d'un même script : l'unité indépendante reste le script (voir D6) ; les SE par réservation des parties 2-3 sous-estiment l'incertitude.

## Hypothèses non vérifiées (récapitulatif)
1. **[H]** Identifiants de réservation = ordre chronologique. 2. **[H]** SE naïves (indépendance des réservations). 3. **[H]** Alignement temporel de D6 (horloges synchronisées, numérotation MGEN à partir de 1) ; 68 réservations utilisables exclues faute d'origine acceptée. 4. **[H]** `n_pkts` = débit URLLC reçu (paquets avec latence valide ; non comparé au débit émis). 5. **[H]** Échangeabilité des étiquettes pour le test de permutation. 6. **[H]** Seuils de décision (0,9 ; 10× ; 2 SE) = choix de l'analyste. 7. **[H]** Causes des réservations tronquées (≈ 18 %). 8. **[Q]** Scheduler vs bloc d'exécution non identifiable ; Lmax et budget 0,03 (voir `dataset_notes.md`).
