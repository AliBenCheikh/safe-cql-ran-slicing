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

## Liste 1 : phrases de l'original (Safe_CQL.pdf, VI-B à VI-D, Fig. 2 et Fig. 3) supprimées ou changées

Relu dans le PDF (non modifié) ; une ligne par affirmation. « Supprimé » = pas de phrase correspondante dans la section 06.

| # | original | sort | raison |
|---|---|---|---|
| 1 | VI-B : « The gain comes not from allocating fewer PRBs to eMBB but from changing the scheduler preference—exactly the lever the audit identified » | supprimé | lecture causale ; scheduler et bloc d'exécution non séparables (D7-b, D8-b, NO-pfcause) ; aucune analyse du comportement des politiques dans le registre |
| 2 | VI-B : « BC retains substantial mass on the high-cost PF configurations (shaded), reproducing the unsafe logged decisions » | supprimé | BC non inclus (BC-a, NO-bc) ; chiffres du notebook non reproduits |
| 3 | VI-B : « unconstrained CQL shifts somewhat toward RR but still selects PF in a non-negligible fraction of states » | supprimé | aucune répartition des actions des agents dans les rapports ; E2-d dit seulement que la Q-net reproduit l'action loguée sur 61-82 % des fenêtres du pli |
| 4 | VI-B : « the safe agent suppresses PF while preserving RR allocations across PRB levels—concentrating, e.g., on (21, RR) and higher-PRB RR configurations » | supprimé | même raison ; [Q] non vérifié dans `src/` |
| 5 | VI-B : « The constraint thus manifests as a learned, load-aware avoidance of proportional-fair scheduling, directly consistent with the cost structure of Fig. 1 » | supprimé | NO-dyn, NO-pfcause ; le bin de charge n'est pas démontré exogène à l'action (D7-c) |
| 6 | VI-C : « both agree on the safety ranking » | changé : « l'ordre des moyennes est le même ; les IC appariés se recouvrent » | E12-c |
| 7 | VI-C : « BC and unconstrained CQL incur the highest violation rates (≈ 4.0–4.1 % under matching, 4.9–5.7 % under tabular OPE) » | supprimé ; nouveaux chiffres dans les tableaux 1 et 2 | sorties du notebook, non reproduites (NO-notebook) ; BC non inclus |
| 8 | VI-C : « the safe agent reaches 3.0 % under both—a ≈ 25 % reduction under matching and ≈ 39–47 % under tabular OPE » | supprimé | E12-a, E12-e : coût DM de Safe-CQL 0,0305-0,0315, borne haute au-dessus de d ; aucune politique démontrée sûre ; NO-budget, NO-safe |
| 9 | VI-C : « FQE, evaluated independently, confirms the direction: its discounted cost value falls from 0.088 (CQL) to 0.076 (Safe-CQL) » | supprimé | FQE du notebook incorrect (AU-e, NO-fqe) |
| 10 | VI-C : « This lower cost is a direct consequence of the learned policy of Sec. VI-B: the safe agent replaces PF with RR at medium-to-high load—the cells carrying 19–27 % violation rates in Fig. 1 » | supprimé | causal ; points 3-4 ; les taux de 19-27 % ne sont retrouvés dans aucun rapport ; confusion scheduler/bloc (D7-b) |
| 11 | VI-C : « the PRB split (which the audit showed does not move URLLC latency) is left free to maximize throughput » | supprimé | aucune ligne du registre ne l'établit (D7-c : `nof_ue` et le débit URLLC dépendent de l'action sur les 8 actions) |
| 12 | VI-C : « The throughput price is therefore small: ≈ 98 % under matching and ≈ 99 % under tabular OPE » | changé : reward DM des agents proches (E12-d), sans pourcentage | E12-d ; chiffres du notebook non reproduits |
| 13 | VI-C : « Across seeds the safe agent is stable, with standard deviations below 0.05 Mbps on throughput and 0.001 on cost » | supprimé ; écarts-types entre seeds donnés seulement pour l'ablation γ | 2 seeds dans l'original contre 5 (E12P-a) ; E12-i |
| 14 | VI-C : « In short, Safe-CQL reduces URLLC violations by 25–47 % while sacrificing only 1–2 % of eMBB throughput » | supprimé | points 8 et 12 ; NO-safe, NO-rl |
| 15 | VI-D : « unconstrained CQL is not by itself safe: … violate the SLA at nearly the BC rate, and only the explicit constraint drives violations to the budget » | changé : coût DM de CQL plus haut que celui de Safe-CQL (E12-a) ; « drives violations to the budget » supprimé | E12-a, E12-e, NO-budget |
| 16 | VI-D : « safety is nearly free because PF is not throughput-superior to RR … the safe agent avoids a dominated action, so 1–2 % of throughput buys a 25–47 % violation reduction » | supprimé | D7-a : signe du reward variable, aucun effet distinguable de 0, mais confusion avec le bloc (D7-b) ; « gratuit » non soutenu ; points 8 et 12 |
| 17 | VI-D : « achieved with no online interaction … the decisive property for O-RAN, as it removes unsafe exploration on a production network while respecting the URLLC SLA » | supprimé ; remplacé par la liste « What the results do not show » | « respecting the SLA » contredit par E12-e ; NO-safe, NO-seq, NO-nearrt |
| 18 | Fig. 2 : « Training convergence and validation for BC, CQL, and Safe-CQL » (sorties du notebook) | supprimée ; remplacée par la Fig. 1 révisée (E12, E2) | NO-notebook ; BC-a |
| 19 | Fig. 3 : « λ converges near 12.9 (a) as the tabular training cost settles onto the d = 0.03 budget (b) » | supprimée ; remplacée par la Fig. 1 révisée, dont la légende dit que λ ne converge pas | AU-f, E2-a, E12P-e, NO-budget |
| 20 | Table II (BC, CQL, CQL-safe ; matching et tabular OPE, ± sur 2 seeds) | supprimée ; remplacée par les tableaux 1 et 2 | NO-notebook ; BC-a ; E12-a à E12-h |

Hors du périmètre demandé (non traité ici) : la section VII (conclusion : « safety cost so little », « 25–47 % ») et la phrase de la section V sur λ « converges near 12.9±0.6 », qui relève de la section 04 révisée.

## Liste 2 : phrases que le registre ne soutient pas suffisamment

| # | phrase | ce qui manque |
|---|---|---|
| 1 | Tableaux 1-2 : rewards, coûts DM et appariés des 10 politiques sur les 3 scripts + pooled | couverts par TAB-a et TAB-b (recopiés de `e12_rapport_final.md`) ; les valeurs ne sont pas dans le registre, seulement la provenance |
| 2 | « Matched upper bound » des 10 politiques | E12-c et E12-e les donnent pour les 10 ; non revérifié dans `test_results.json` (non lu) |
| 3 | « One untested hypothesis is a windup of the dual update, which would integrate a violation that the policy does not remove » | LAM-d [H] ; reste une hypothèse non testée, présentée comme telle après l'observation (LAM-c) |
| 4 | « The direction of the transfer result is the same for every partition tested » | E13a2-b donne des plages (A→B 0,0448-0,0520 > d ; B→A 0,0303-0,0357) ; « même direction » est une lecture ; et les IC contiennent d (E13a2-c) |
| 5 | « the diagnostic runs at α = 0.5 also show a larger λ with γ = 0 » | couvert par LAM-b |
| 6 | « above the values at γ = 0.7 and α = 0.1 » | couvert par LAM-a ; comparaison de plages, sans test |
| 7 | « five learned agents lie between 6.73 and 7.12 Mbps » | E12-d : plage pour « les agents », sans dire explicitement 5 ou 6 (le γ = 0 est à 6,773, dans la plage) |
| 8 | « matched coverages of 33.5 % to 40.3 % for the agents, below 50 % » | E12-c : « 33,5-40,3 % » ; ok mais E12-e donne 9,5-54,7 % pour les 10 politiques |
| 9 | « The failure of the criterion is also a lack of information » | E12-e dit « manque de puissance » ; aucune analyse de puissance (la section 05 a retiré ce mot) |
| 10 | « Safe-CQL … lower estimated cost than CQL and IQL at a comparable reward » | E12-a, E12-d ; intervalles non comparés (pas d'IC sur la différence) |
| 11 | « Always-PF has a higher cost than always-RR » (sens associatif) | E12-g donne 0,1294 contre 0,0287 sur c40f2fe7 ; D7-b/NO-pfcause pour la réserve |
| 12 | E13a2 : « 10 with quantile edges, 12 with integer edges », « widths 0.034-0.068 » | E13a2-c ; la largeur est donnée pour l'ensemble |
| 13 | « Between 52 % and 67 % of the cells … with integer edges » | E13a2-e : la part est 0,52-0,67 ; « of the cells » = dénominateurs 16-64 |

## Ajouts de l'étape 19 bis

- Observation d'abord (E2, 300 epochs : λ monte, coût greedy d'entraînement au même niveau qu'à 100 epochs, LAM-c), puis une phrase « windup » marquée hypothèse non testée (LAM-d). « Au même niveau » est une lecture de valeurs voisines, sans test ([H] dans LAM-c).
- Figure : 3 panneaux ; le troisième trace λ des runs `current_300ep` d'E2 (plis A et B, moyenne sur 5 seeds, bande min-max). Le coût d'E2 n'est pas tracé. Légende : coûts dans l'échantillon, λ ne converge pas.
- Registre : section 12 (TAB-a, TAB-b, LAM-a à LAM-d). Vérificateur : 172 OK, 0 ABSENT, 2 AMBIGU (D4-a, COST-a, préexistants).
- `paper/main.tex`, `paper/refs.bib` (8 entrées vides `TODO-…`), `paper/README.md`. Labels ajoutés dans les sections : `sec:audit` (02), `sec:method` (04), `sec:eval` (05) ; `sec:results` (06) et `sec:leakage` (02) existaient. Seul `sec:method` était pendant (renvoi de la section 03) ; plus aucun renvoi pendant.
