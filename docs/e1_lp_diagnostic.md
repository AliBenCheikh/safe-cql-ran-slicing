# E1 — Diagnostic par programmation linéaire du CMDP à une étape (branche `revision/09-lp-diagnostic`)

Code : `src/lp_diagnostic.py`. Tests : `tests/test_e1.py` (10 tests synthétiques).
Lancement : `python -m src.lp_diagnostic` → `results/e1_{summary.json,cells.csv,det_policies.csv,lagrangian_curve.csv,boot.csv}`.
Entrées : `results/dataset_canonical.parquet` (version `268d524c117eb6de`, split **train** uniquement, filtré à la lecture) et `results/d6_reservations.csv` (réservation → md5 du script). Aucune donnée brute, aucun entraînement. Déterministe (seed 0, bootstrap B = 1 000).
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée · **[P]** problème confirmé · **[Q]** question ouverte.

## Ce que ce diagnostic est, et n'est pas
- **Un diagnostic, pas une performance.** Le LP utilise **les mêmes tables** (récompense `R[a,b]`, coût `C[a,b]`, mêmes règles de repli que `fit_cost_table` / `reward_table`) et les mêmes parts de bins `p_b` que l'estimateur DM de `src.evaluate.evaluate_policy`. Un reward « LP » est donc une valeur *selon les tables*, la borne supérieure des politiques qui ne voient que le bin de charge ; ce n'est pas un retour mesuré. [V] test unitaire : les tables du script égalent celles du pipeline.
- Trois jeux de tables : script A = a908e4cc (cluster 2, 247 réservations), script B = a53521b2 (cluster 3, 231), et TRAIN = tout le split train (510 réservations ; c'est la table que voient les agents du notebook). A et B sont les plis de validation par script ; TRAIN sert de référence.
- Le coût est la moyenne par fenêtre (`urllc_frac_viol`), comme dans le DM. Le LP ne contraint pas la part de réservations sûres (`dm_pct_safe`), qui est une autre métrique.
- Le test (c40f2fe7) n'est pas utilisé. Voir la note de transparence en fin de document.

## Résultats (d = 0,03 ; budget non modifié)

| table | LP faisable | coût minimal atteignable | reward LP | coût LP | budget actif | randomisation | λ* (échelle agent) | μ* (Mbps / unité de coût) |
|---|---|---|---|---|---|---|---|---|
| A (a908e4cc) | oui | 0,0211 | 11,70 | 0,0215 | **non** | aucune | **0** | 0 |
| B (a53521b2) | oui | 0,0112 | 10,78 | 0,0300 | oui | 1 bin | 0,065 | 9,47 |
| TRAIN | oui | 0,0182 | 11,28 | 0,0300 | oui | 1 bin | 0,244 | 33,2 |

- **[V] d = 0,03 est faisable sur les trois tables**, avec une marge : le coût minimal est 0,011 à 0,021. Aucun pli n'est infaisable.
- **[V] Sur A, la contrainte n'est pas active** : l'optimum sans contrainte (politique `7-7-6`, une action par bin 0/1/2) coûte déjà 0,0215 ; λ* = 0.
- **[V] λ\*** est converti en échelle de l'agent par `λ = μ·d / r_scale` (cible `r/r_scale − λ(c/d − 1)`), avec `r_scale` = écart-type du reward de la table concernée (4,08 pour TRAIN). Le dual est unique ici (pente gauche = pente droite, au 1e-9 près).
- **[V] Comparaison avec la référence enregistrée.** L'audit note λ = 12,22 à l'epoch 99 et un coût greedy train ≈ 0,032–0,033 (valeurs lues dans le notebook, **non reproduites**). Sur la table TRAIN, λ* = 0,244, soit ≈ 50 fois moins, et **toute valeur λ ≥ 0,245 donne, avec un argmax sur la table, un coût ≤ 0,0297** (courbe `e1_lagrangian_curve.csv`) ; à λ = 12 l'argmax de la table coûte 0,0182 (politique `0-0-6`).
- **[H, non vérifiée]** Donc l'échec à atteindre d avec λ = 12 ne vient pas de la table : une Q-net qui suivrait l'argmax de la table aurait un coût ≤ d depuis λ ≈ 0,25. Explications possibles, à tester à l'étape 10 : le conservatisme CQL (α = 0,5) ramène l'argmax vers l'action loguée ; l'amorçage de Bellman (γ = 0,7) ; la généralisation de la Q-net sur l'état continu, où l'action loguée est prédictible par le script (D4). Rien dans ce rapport ne tranche entre elles.
- Pour mémoire, la politique de comportement (actions loguées) vaut, selon les tables, coût 0,056 / reward 7,74 (TRAIN), coût 0,068 / 8,16 (A), coût 0,047 / 7,11 (B).

## Meilleur déterministe (512 = 8³ politiques par bin) contre LP
| table | politiques déterministes faisables | meilleur déterministe | reward | coût | écart au LP |
|---|---|---|---|---|---|
| A | 34 | `7-7-6` | 11,7029 | 0,0215 | 0 (le LP est déterministe) |
| B | 177 | `6-4-6` | 10,7653 | 0,0286 | 0,0130 (0,12 %) |
| TRAIN | 80 | `2-7-6` | 11,2663 | 0,0297 | 0,0114 (0,10 %) |

- **[V]** Randomiser un seul bin ne rapporte que 0,1 % de reward selon les tables : la politique déterministe est presque aussi bonne que le LP.
- **[V]** Le coût de la meilleure politique déterministe est juste sous d (0,0286 pour B, 0,0297 pour TRAIN). Sur la table, un argmax **peut** donc se placer près de d ; la courbe argmax en fonction de λ a un saut de coût de 0,0350 → 0,0297 à λ ≈ 0,24 (TRAIN) et de 0,0529 → 0,0286 à λ ≈ 0,07 (B). **L'hypothèse « un argmax déterministe ne peut pas atteindre d » est vraie au sens strict (aucun λ ne donne exactement 0,03) mais l'écart est petit (≤ 0,0014 sous d) ; ce n'est pas, à lui seul, une explication plausible de λ = 12.**
- Le LP randomisé est donné **comme référence** ; la politique argmax reste l'algorithme principal.

## Variante softmax (étiquetée variante, non principale)
Politique softmax sur le score `r/r_scale − λ(c/d − 1)`, température τ ∈ {0,05 ; 0,1 ; 0,2} (choix de l'analyste, **non réglé**), λ = plus petit λ qui donne un coût ≤ d.

| table | τ = 0,05 | τ = 0,1 | τ = 0,2 |
|---|---|---|---|
| A : λ / reward / coût | 0 / 11,69 / 0,0228 | 0,0098 / 11,63 / 0,0300 | 0,075 / 11,53 / 0,0300 |
| B | 0,093 / 10,76 / 0,0300 | 0,103 / 10,71 / 0,0300 | 0,127 / 10,49 / 0,0300 |
| TRAIN | 0,303 / 11,27 / 0,0300 | 0,304 / 11,23 / 0,0300 | 0,290 / 11,05 / 0,0300 |

- **[V]** La softmax atteint exactement d (coût continu en λ), au prix d'un peu de reward quand τ grandit. Ce sont des valeurs de table, pas des performances.

## Robustesse : bootstrap des réservations à l'intérieur de chaque script (B = 1 000)
Les tables sont rééchantillonnées par réservation dans le script (les fenêtres d'une réservation sont dépendantes), puis le LP est résolu. IC 2,5 / 50 / 97,5 %.

| table | LP faisable | coût minimal | reward LP | λ* | budget actif |
|---|---|---|---|---|---|
| A | 97,9 % | 0,0082 / 0,0187 / 0,0295 | 10,79 / 11,64 / 11,93 | 0 / 0 / 2,90 | 36 % |
| B | 100 % | 0,0017 / 0,0068 / 0,0149 | 10,11 / 10,94 / 11,74 | 0 / 0,048 / 0,82 | 74 % |
| TRAIN | 100 % | 0,0097 / 0,0160 / 0,0227 | 10,74 / 11,34 / 11,84 | 0 / 0,060 / 0,93 | 61 % |

- **[V]** Le coût minimal de A dépasse d dans 2,1 % des rééchantillons ; la faisabilité n'est donc pas certaine à l'intérieur de A.
- **[P]** λ\* est mal déterminé : l'IC de A et B va de 0 à ≈ 1–3, et la contrainte n'est active que dans 36–74 % des rééchantillons. Une valeur ponctuelle de λ* ne doit pas être présentée comme précise.
- **[P]** Ces intervalles sont **conditionnels à un script**. Les réservations d'un script ne sont pas indépendantes (D6) et chaque cellule (action × bin) vient de 2 à 55 réservations : ils sous-estiment l'incertitude. Ils ne mesurent pas la généralisation à un autre script.

## Transfert entre scripts (toujours en DM, donc toujours un diagnostic)
Politique construite avec les tables d'un script, évaluée avec les tables et les parts de bins de l'autre.

| de → vers | politique | reward | coût | oracle LP du script cible |
|---|---|---|---|---|
| A → B | LP(A) = `7-7-6` | 10,35 | **0,052** (> d) | 10,78 / 0,0300 |
| B → A | LP(B) | 11,39 | 0,0300 | 11,70 / 0,0215 |
| B → A | meilleur déterministe de B (`6-4-6`) | 11,37 | 0,0303 (> d de 0,0003) | |

- **[V]** La politique optimale de A, qui n'a pas besoin de la contrainte, viole le budget de façon nette sous les tables de B (0,052 contre 0,030). La politique de B respecte à peu près le budget sous A.
- **[P]** Les deux scripts n'ont pas les mêmes tables : un résultat « contrainte respectée » dépend du script sur lequel on la mesure. Avec 2 scripts, on ne peut pas estimer la variabilité entre scripts.
- **[H]** Les parts de bins `p_b` sont supposées indépendantes de l'action (trafic en boucle ouverte). D7 a montré que `nof_ue` dépend du scheduler ; le bin de charge n'est donc peut-être pas exogène. Ici `p_b` vient de toutes les fenêtres du script (mélange des 8 actions), pas d'une charge indépendante de l'action.

## Limites et hypothèses non vérifiées
1. **[H]** Les tables viennent d'actions loguées par script : chaque cellule mélange un slicing, un scheduler et un bloc temporel (D8 : scheduler non séparable du moment d'exécution). Le « coût de PF » ou « de RR » dans une cellule contient cette confusion.
2. **[H]** `R` et `C` d'une cellule peu couverte (2 à 6 réservations) sont bruités ; 1 cellule de A utilise le repli par action (< 20 fenêtres). Le LP exploite ce bruit : il choisit le maximum d'estimations bruitées, donc le reward LP est biaisé à la hausse (malédiction du gagnant). Le bootstrap le montre en partie mais ne le corrige pas.
3. **[H]** `r_scale` pour convertir μ* en λ* : écart-type de la table du pli (celui de l'entraînement dans `train_cql`). Le λ de l'agent peut être différent si l'état de l'agent est normalisé autrement.
4. **[H]** Le LP ne voit que le bin de charge (3 bins). Une politique qui exploite l'état continu (rsrp, mcs, lags) peut faire mieux ou pire ; ce diagnostic ne le dit pas.
5. **[Q]** Lmax et la source de d = 0,03 ne sont pas documentés (à compléter par l'utilisatrice ou l'utilisateur dans `dataset_notes.md` ; je ne les ai pas renseignés). `meta.json` contient `sla_ms = 20` comme paramètre du pipeline, mais ce n'est pas la source du budget.
6. **[Q]** Pourquoi la Q-net garde un coût greedy ≈ 0,033 alors que la table donne ≤ 0,03 pour λ ≥ 0,25 : à tester à l'étape 10 (voir ci-dessus).

## Note de transparence
Pendant l'exploration, une commande d'inspection a affiché les parts de bins et le nombre d'actions du script de test c40f2fe7 (agrégats du parquet, split test). Ces valeurs n'ont servi ni au code ni au rapport ni à un choix ; mais la règle « le test n'est lu qu'une fois à la fin » est donc entamée pour ces deux agrégats. À garder en tête pour l'étape 12.

## Suite (étape 10)
Les tables ne contiennent pas l'explication de λ = 12. L'étape 10 devra d'abord reproduire, **en entraînement, sur les plis A/B**, le comportement (λ, coût greedy) de Safe-CQL actuel et le comparer à la table (λ* ≈ 0,07–0,24), puis seulement tester γ = 0. Aucun entraînement n'a été lancé ici.
