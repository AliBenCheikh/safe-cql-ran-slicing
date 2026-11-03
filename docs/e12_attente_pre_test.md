# E12 — Attente consignée AVANT toute lecture du test

Date d'écriture : 2026-11-03 (13:56 +01:00). Branche `revision/12-test-final`, partie de `revision/11-alpha-grid` (commit `ecb624d`).
Ce document est écrit et commité **avant** que le split test (cluster 1, script `c40f2fe7` + autres) soit lu pour l'étape 12. Document en ajout seulement : les sections ultérieures sont datées, le texte déjà commité n'est pas réécrit (l'historique git fait foi).

## Attente (formulée par l'auteur du projet, reprise telle quelle)

> « Nous ne prévoyons pas de garantie de respect du budget sur le script test : la sécurité ne se transfère pas entre scripts (E11), et ni Safe-CQL ni table-greedy ne respectent d dans les deux sens. »

Statut : **attente, pas un résultat**. Elle s'appuie sur E11 (validation sur des plis de train, estimateur DM), où :
- aucune valeur d'α n'est faisable pour Safe-CQL (coût de validation moyen > d = 0,03 en B→A pour tout α : 0,0405 à 0,0504) [V, E11] ;
- le table-greedy transféré dépasse d en A→B (0,0520) ; en B→A il est à 0,0303, soit à 1 % de d, ce qui est dans le bruit possible des tables : « ne respecte pas d » n'y est **pas établi** [H, E11, ligne corrigée au commit `ecb624d`].
La phrase « dans les deux sens » est donc, pour table-greedy, une attente plus forte que ce qu'E11 a montré. Elle est consignée comme telle, et sera confrontée au test sans être réécrite.

Conséquence d'interprétation fixée d'avance : si un ou plusieurs coûts sur le test sont ≤ d, cela ne sera **pas** présenté comme une garantie de sécurité (un script, un estimateur DM sur tables d'entraînement, aucune validation de transfert).

## Transparence : agrégats du script test déjà vus

Lors d'E1 (voir `docs/e1_lp_diagnostic.md`, note de transparence), une commande d'inspection a affiché deux agrégats du script de test `c40f2fe7` :
1. les **parts de bins de charge** ;
2. le **nombre d'actions**.

Ces valeurs n'ont servi ni au code, ni à un rapport, ni à un choix (configuration, hyperparamètre, règle). La règle « le test n'est lu qu'une fois, à la fin » est donc entamée pour ces deux agrégats seulement. Rien d'autre du split test n'a été lu à ma connaissance de cette session.

---

# Addendum du 2026-11-03 (14:00 +01:00), avant le gel — correction, configurations, attentes

## 1. Correction : ceci est une lecture finale, la SECONDE lecture du test

La section « Transparence » ci-dessus est **incomplète** : elle ne mentionne que les deux agrégats vus en E1. Le split test a déjà été lu en **phase 2** (`src/evaluate.py`, Safe-CQL/CQL α = 0,5, γ = 0,7, IQL, baselines), et ses résultats sont connus de l'auteur et de l'assistant. L'étape 12 n'est donc **pas** une lecture unique ni aveugle ; c'est la **lecture finale (seconde lecture)**. Conséquences :
- le test ne peut pas servir à choisir quoi que ce soit : tout est fixé avant (commit de gel) ;
- les attentes ci-dessous ne sont **pas aveugles** : (a) à (e) reprennent des résultats de phase 2 ;
- la nouveauté réelle de cette lecture est : α = 0,1, CQL α = 0,1, l'ablation γ = 0, la ventilation par script, et les intervalles par script.

## 2. Configurations figées d'avance

| nom | agent | α | γ | rôle |
|---|---|---|---|---|
| `safe_cql_a0.1` | Safe-CQL | 0,1 | 0,7 | **principal** (α par le repli d'E11 ; quasi-ex æquo avec α = 0,05 et 0,2 : coût de validation moyen 0,03440 / 0,03470 / 0,03464) |
| `cql_a0.1` | CQL | 0,1 | 0,7 | comparaison à α égal |
| `safe_cql_a0.5` | Safe-CQL | 0,5 | 0,7 | continuité avec la phase 2 |
| `cql_a0.5` | CQL | 0,5 | 0,7 | continuité avec la phase 2 |
| `safe_cql_a0.1_g0` | Safe-CQL | 0,1 | **0** | ablation γ |
| `iql` | IQL | – | 0,7 | tel quel (`IQL_CFG`) |

Baselines : always-RR, always-PF, best-fixed, table-greedy (définitions de `src/baselines.py`, inchangées).
Entraînement : tout le train (clusters 2–3), seeds 0–4, 100 epochs, politique = dernière epoch (pas de choix de checkpoint). Aucune convergence n'est exigée (0/60 en E2 et E11) ; ce point sera dit dans le rapport. Tables DM : reward/coût du train. Bootstrap : B = 2000, seed 0, par réservation à l'intérieur de chaque script.

## 3. Attentes consignées (non aveugles)

Évaluées mécaniquement par `check_expectations` (gelée), sur `c40f2fe7` et, pour continuité, sur l'ensemble du test.
- **(a)** Reward DM : table-greedy au-dessus de tous les agents ; Safe-CQL, CQL et IQL proches (écart max ≤ 10 % de leur moyenne).
- **(b)** Coût DM : Safe-CQL plus bas que CQL et IQL (aux deux α), mais avec un intervalle à 95 % dont la borne haute reste ≥ d.
- **(c)** Matched : même ordre des coûts ; couverture partielle (< 50 % pour tous les agents).
- **(d)** γ = 0 sans amélioration nette (« nette » := coût DM plus bas de plus de 2 écarts-types entre seeds, ou reward plus haut de plus de 2 écarts-types à coût non supérieur).
- **(e)** Aucune politique démontrée sûre sur `c40f2fe7` (« démontrée sûre » := borne haute de l'IC 95 % ≤ d à la fois en DM et en matched).
- **(f)** Tout point faux sera rapporté tel quel, sans réécriture de l'attente ni du critère.

Les seuils (10 %, 50 %, 2 écarts-types) sont arbitraires ; ils sont fixés ici et dans le code avant le gel.

---

# Addendum du 2026-11-03, avant `--evaluate` — analyses D6, D7, D8 sur le script `c40f2fe7`

D6, D7 et D8 ont examiné des résultats du script test `c40f2fe7` (effet PF contre RR, blocs d'exécution, coûts par réservation). Ces analyses étaient descriptives et n'ont servi à régler aucun paramètre.

Cet addendum s'ajoute aux sections précédentes, qui ne sont pas modifiées. Il complète la section « Transparence » : le script principal `c40f2fe7` a donc été examiné, avant cette lecture finale, par ces trois analyses en plus des lectures déjà consignées.
