# E12 — Attente consignée AVANT toute lecture du test

Date d'écriture : 2026-11-03 (13:56 +01:00). Branche `revision/12-test-final`, partie de `revision/11-alpha-grid` (commit `ecb624d`).
Ce document est écrit et commité **avant** que le split test (cluster 1, script `c40f2fe7` + autres) soit lu pour l'étape 12. Il n'est modifié par aucun commit ultérieur ; toute correction passe par un nouveau document daté.

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
