# Étape 19 : section 06 « Results » (`paper/sections/06_results.tex`)

Remplace VI-B à VI-D, la Table II, la Fig. 2 et la Fig. 3 du PDF original (non modifié). Aucun nombre ne vient d'ailleurs que des rapports de `docs/` et du registre ; `data/` et `results/e12/test_results.json` ne sont pas lus ; aucune évaluation ni entraînement n'est lancé. Les deux tableaux recopient `docs/e12_rapport_final.md` (testé par `tests/test_paper_06_results.py`). Le LaTeX n'a pas été compilé (pas de `pdflatex` dans l'environnement). `matplotlib` a été installé dans `.venv` pour la figure.

## Historiques par epoch disponibles

| essai | chemin | colonnes | seeds | epochs |
|---|---|---|---|---|
| E2 | `results/e2_runs.json` (`runs`, 60 entrées) | `lambda_hist`, `greedy_cost_hist` (+ `fold`, `variant`) | 0-4 | 100 ; 300 pour `current_300ep` |
| E11 | `results/e11_runs.json` (`runs`, 60 entrées) | `lambda_hist`, `greedy_cost_hist` (+ `direction`, `alpha`) | 0-4 | 100 |
| E12 | `results/e12/checkpoints/<config>_seed<k>.pt`, clé `lambda_history` (15 Safe-CQL) | `epoch`, `lambda` (après mise à jour), `greedy_cost` | 0-4 | 100 |
| E12 | mêmes `.pt`, clé `history` (30 modèles) | `epoch, loss, bellman, cons, q_logged, q_max, greedy_cost_train` (+ `lambda` pour Safe-CQL ; IQL : `loss_v, loss_q, loss_pi`) | 0-4 | 100 |
| phase 3 | `results/learning_curves_val.json` | courbes `cql`, `safe_cql`, `iql` par seed ; **validation (DM sur 20 % du train)** | 0-4 | non vérifié | 

`learning_curves_val.json` n'est pas utilisé : il contient des DM de validation, pas seulement des données d'entraînement. La figure (`src/figures/courbes_apprentissage.py` → `paper/figures/courbes_apprentissage.pdf`, PDF vectoriel) trace λ et le coût greedy d'entraînement des 15 runs Safe-CQL d'E12 (moyenne sur 5 seeds, bande min-max). E2 et E11 existent mais ne sont pas tracés (choix : la figure suit les modèles évalués).

## Liste 1 : phrases de l'original supprimées ou changées

| # | original | sort | raison |
|---|---|---|---|
| 1 | VI-B/VI-C : texte et Table II (« 25–47 % », « 1–2 % ») | supprimé ; remplacé par les tableaux 1 et 2 (DM + apparié + IC + couverture, par script) | sorties du notebook non reproduites (NO-notebook) ; E12-a à E12-h |
| 2 | Fig. 2 (convergence) et Fig. 3 (« λ climbs monotonically while the tabular cost is driven onto the 3 % budget ») | remplacé par la figure d'entraînement E12 ; « driven onto the budget » supprimé | AU-f, E2-a, E12P-e, NO-budget |
| 3 | « λ converge près de 12,9 » (si repris en VI-D) | non repris | AU-f ; E1-b |
| 4 | Affirmations de supériorité du RL ou de respect du budget (agrégé) | remplacées par « coût estimé plus bas que CQL/IQL à reward comparable » ; table-greedy au moins aussi bon | NO-rl, NO-budget, E12-f |
| 5 | Résultats agrégés sur le test comme « un cluster inédit » | remplacés par résultats par script, « pooled » = 90 % un script | D6-b, E12-b |
| 6 | Choix de α sans règle | remplacé par E11 (aucun α faisable, repli) | E11-a, E11-b |

Je n'ai pas relu VI-B à VI-D dans le PDF pour cette liste : les lignes 1 à 6 viennent du rapport d'audit et des descriptions de la section 05 ; à confirmer contre le PDF.

## Liste 2 : phrases que le registre ne soutient pas suffisamment

| # | phrase | ce qui manque |
|---|---|---|
| 1 | Tableaux 1-2 : rewards, coûts DM et appariés des 10 politiques sur les 3 scripts + pooled | seules les lignes E12-a à E12-h, E12-j en citent une partie ; le reste est dans `e12_rapport_final.md` (sortie brute, pas dans le registre) |
| 2 | « Matched upper bound » des 10 politiques | E12-c et E12-e les donnent pour les 10 ; non revérifié dans `test_results.json` (non lu) |
| 3 | « possible windup of the dual update, which integrates a constraint violation that the policy does not remove » | aucune ligne ne parle de windup ; c'est une hypothèse (SAFE-b décrit la mise à jour, E12P-c la montée de λ au-dessus de d) ; non testée |
| 4 | « The direction of the transfer result is the same for every partition tested » | E13a2-b donne des plages (A→B 0,0448-0,0520 > d ; B→A 0,0303-0,0357) ; « même direction » est une lecture ; et les IC contiennent d (E13a2-c) |
| 5 | « the diagnostic runs at α = 0.5 also show a larger λ with γ = 0 » | E2-c : λ 3,112 / 0,595 contre 1,935 / 0,283 pour `current` (α = 0,5) ; comparaison faite dans E2, pas dans le registre en une ligne |
| 6 | « above the values at γ = 0.7 and α = 0.1 » | E12P-c : 0,4398-0,4910 contre 0,1028-0,1272 ; comparaison écrite par moi à partir de deux valeurs du registre |
| 7 | « five learned agents lie between 6.73 and 7.12 Mbps » | E12-d : plage pour « les agents », sans dire explicitement 5 ou 6 (le γ = 0 est à 6,773, dans la plage) |
| 8 | « matched coverages of 33.5 % to 40.3 % for the agents, below 50 % » | E12-c : « 33,5-40,3 % » ; ok mais E12-e donne 9,5-54,7 % pour les 10 politiques |
| 9 | « The failure of the criterion is also a lack of information » | E12-e dit « manque de puissance » ; aucune analyse de puissance (la section 05 a retiré ce mot) |
| 10 | « Safe-CQL … lower estimated cost than CQL and IQL at a comparable reward » | E12-a, E12-d ; intervalles non comparés (pas d'IC sur la différence) |
| 11 | « Always-PF has a higher cost than always-RR » (sens associatif) | E12-g donne 0,1294 contre 0,0287 sur c40f2fe7 ; D7-b/NO-pfcause pour la réserve |
| 12 | E13a2 : « 10 with quantile edges, 12 with integer edges », « widths 0.034-0.068 » | E13a2-c ; la largeur est donnée pour l'ensemble |
| 13 | « Between 52 % and 67 % of the cells … with integer edges » | E13a2-e : la part est 0,52-0,67 ; « of the cells » = dénominateurs 16-64 |
