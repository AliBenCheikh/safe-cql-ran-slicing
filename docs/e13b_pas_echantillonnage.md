# E13b — Pas d'échantillonnage réel des fichiers bruts (R2-W1) — branche `revision/13-bins-fenetre`

Code : `src/e13b_sampling_check.py`. Tests : `tests/test_e13b.py`. Sortie : `results/e13b_sampling.json`, liste `results/e13b_sample.csv` (gitignorés ; `--make-sample` la régénère à l'identique).
Tags : **[V]** vérifié sur les fichiers lus · **[H]** hypothèse non vérifiée · **[P]** problème constaté · **[Q]** question ouverte.

## Statut
- **Lecture seule, colonnes d'horodatage uniquement** (`usecols`), 12 réservations de **train** (aucune du test) : `enb_metrics.csv` (`time`), `bs/<IMSI>_metrics.csv` (`Timestamp`), `ue_metrics.csv` (`time`), `mgen.csv` (`Sent Time`, `Received Time`). Aucune valeur de KPM ni latence lue [V].
- **Aucune sensibilité à la fenêtre n'a été lancée** (en attente de ton accord). La fenêtre gelée du papier reste 5 s.
- **Échantillon :** par (cluster 2/3 × scheduler), la première, celle du rang médian (indice n//2) et la dernière par date de début (`start_utc` de D8), parmi les réservations utilisables du train. Ce sont des rangs chronologiques dans la cellule, pas le milieu calendaire. Liste : 142792, 142949, 143109 (c2, sched 0) ; 141887, 142021, 142151 (c2, sched 1) ; 143121, 143279, 143401 (c3, sched 0) ; 142162, 142330, 142462 (c3, sched 1).
- **Critères fixés avant la lecture** (docstring du script) : flux KPM « possible » à la fenêtre w si ≥ 99 % des fenêtres contiennent ≥ 3 échantillons ; flux mgen URLLC « possible » si ≥ 99 % des fenêtres contiennent ≥ 34 paquets (1/34 < d = 0,03). Fenêtres : 0,1 ; 0,25 ; 0,5 ; 1 ; 2 ; 2,5 ; 5 ; 10 s. Le seuil de 34 paquets est un choix de ma part, pas une valeur du dataset.
- **Transparence :** la première exécution (commit `eab6758`) poolait par erreur les 8 fichiers `mgen.csv`, eMBB compris. J'ai vu ses résultats, constaté le défaut (le coût porte sur les 4 UE URLLC), corrigé (commit `66d6cd3`) et relancé. Seuls les résultats corrigés sont rapportés ; le critère n'a pas été modifié.

## Pas d'échantillonnage réel

| flux | pas médian | régularité | fenêtres « possibles » (réservations sur 12) |
|---|---|---|---|
| `enb_metrics` (`nof_ue`) | **0,25 s (4 Hz)** dans 12/12 | ≥ 99,8 % des pas à ±10 % de la médiane ; aucun pas > 2× la médiane ; pas max 0,466 s | ≥ 1 s : 12/12 ; ≤ 0,5 s : 0/12 |
| `ue_metrics` (radio, débit eMBB) | **0,249 s** dans 96/96 fichiers | 100 % à ±10 % ; pas max 0,25 s | ≥ 1 s : 12/12 ; ≤ 0,5 s : 0/12 |
| `bs/<IMSI>_metrics` (`Timestamp`) | 0,25 s (médiane des fichiers) | **irrégulier** : pas max jusqu'à 1 319,5 s, durées de 1,25 s à 1 773 s, 4 à 8 fichiers par réservation | 1 s et 5 s : 1/12 (voir [P]) |
| `mgen.csv`, `Received Time`, UE URLLC | **0,1 s par UE** (10 paquets/s), 2 à 3 UE sur 4 avec des paquets | pas max pooled 2,34 s | 10 s : 12/12 ; **5 s : 7/12** ; 2,5 s : 4/12 ; 2 s : 3/12 ; ≤ 1 s : 0/12 |

- **[V]** Le pas réel des flux KPM est **0,25 s, non 1 s** : une fenêtre de 5 s contient ~20 échantillons de `nof_ue` et de radio.
- **[V]** Fenêtres plus fines que 5 s possibles **pour le reward, la radio et `nof_ue`** : 1 s, 2 s et 2,5 s (≥ 3 échantillons). 0,5 s (2 échantillons), 0,25 s (1 échantillon) et 0,1 s ne satisfont pas le critère.
- **[V]** Pour le **coût URLLC**, le débit de paquets (~30/s au plus, pooled) rend les fenêtres < 5 s trop pauvres : la médiane est de 50 à 150 paquets par fenêtre de 5 s (150 pour 5 réservations sur 12, 100 pour 3, et 142, 98, 84, 50 pour les autres). Avec ≤ 30 paquets par seconde, une fraction de violations de 0,03 n'est pas résoluble à 1 s.
- **[P]** Même à 5 s, 5 réservations sur 12 n'atteignent pas 99 % de fenêtres à ≥ 34 paquets (la part va de 0,979 à 0,989 pour elles) : la granularité du coût dans la fenêtre gelée est déjà grossière pour ces réservations (résolution 1/50 pour la plus pauvre). Je n'en tire aucune conséquence sur les résultats déjà produits.

## Ce que cela implique pour R2-W1 (descriptif)
- Le dataset permet, au mieux, des fenêtres de 1 à 2,5 s pour le reward et l'état, et pas en dessous de 5 s pour un coût URLLC à la résolution de d. **La plage Near-RT de 10 ms à 1 s n'est atteignable avec ces fichiers sur aucun des deux signaux** [V sur l'échantillonnage ; l'interprétation O-RAN vient de la review, non vérifiée].
- **[H, d'après docs/phase1_pipeline.md, non re-mesuré ici]** L'horloge UE est estimée : décalage médian 0,51 s, p5 −1,7 s, p95 +3,8 s, 124 fichiers au-delà de ±5 s. Des fenêtres de moins de ~4 s ne seraient donc pas fiablement alignées entre le reward eMBB et le coût/`nof_ue`, même si l'échantillonnage le permet.
- **[V, dataset_notes]** Aucune transition avec changement d'action : une fenêtre plus fine change l'unité du reward et du coût, pas la contrôlabilité.

## Problèmes et questions ouvertes
- **[P]** `Sent Time` (mgen) : écart maximal de 31 507 s entre paquets pooled ; les fenêtres calculées dessus sont majoritairement vides (le critère échoue pour presque toutes les réservations). La cause n'est pas examinée (lignes aberrantes ?). Le pipeline utilise `Received Time`, dont l'écart max pooled est 2,34 s [V].
- **[P]** Fichiers `bs/<IMSI>_metrics` très irréguliers (trous de plusieurs minutes, fichiers de 6 lignes pour 142330 ; 4 à 7 fichiers dans 2 réservations). Ils ne servent qu'à l'alignement (`Timestamp` de la première ligne) ; l'effet sur l'alignement n'est pas étudié.
- **[Q]** Rapport durée `ue_metrics` / durée `enb` : 0,96 à 0,98 pour 10 réservations sur 12 (ce qui soutient l'unité ms supposée), mais 1,41 et 1,13 pour les deux autres, non expliqués.
- **[Q]** Un des quatre fichiers `mgen.csv` URLLC est vide (ou deux) : s'agit-il d'UE non attachés ? Non étudié.
- **[H]** 12 réservations ne garantissent pas la représentativité (autres slicings, début/fin de campagne seulement couverts par rang).
- **[Q]** Lancer ou non une sensibilité à la fenêtre (1, 2, 2,5 s sur le reward, sans coût) : à décider ; non lancée.
