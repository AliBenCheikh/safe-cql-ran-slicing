# Vérification du registre des affirmations

Produit par `src/checks/verifie_registre.py` (lecture seule ; aucun calcul nouveau ; ni `data/` ni `tests/` lus).
Règles de verdict : voir la docstring du script. Seules les lignes contenant au moins un nombre significatif sont listées.

Total : 145 lignes — OK 144, AMBIGU 1, ABSENT 0.

| ligne | repère | verdict | détail |
|---|---|---|---|
| 60 | D1-a | OK | sources : 5178c8d |
| 61 | D1-b | OK | sources : decision_memo |
| 62 | D1-c | OK | aucun nombre à vérifier |
| 63 | D2-a | OK | sources : decision_memo |
| 64 | D2-b | OK | sources : decision_memo, phase1_pipeline |
| 65 | D2-c | OK | sources : phase1_pipeline |
| 66 | D3-a | OK | sources : decision_memo, phase1_pipeline |
| 67 | D4-a | AMBIGU | trouvé(s) seulement par conversion % <-> fraction : 30,5, 32,8, 55,5, 55,6, 35,6, 42,3, 58,9, 61,1, 20,5 |
| 68 | D4-b | OK | sources : decision_memo |
| 69 | D4-c | OK | aucun nombre à vérifier |
| 70 | D4-d | OK | aucun nombre à vérifier |
| 71 | D5-a | OK | sources : decision_memo |
| 72 | D5-b | OK | sources : decision_memo |
| 73 | D5-c | OK | sources : decision_memo |
| 74 | D5-d | OK | sources : decision_memo |
| 80 | D6-a | OK | sources : 2ce8774 |
| 81 | D6-b | OK | sources : d6_shared_scripts |
| 82 | D6-c | OK | aucun nombre à vérifier |
| 83 | D6-d | OK | sources : d6_shared_scripts |
| 84 | D6-e | OK | sources : d6_shared_scripts |
| 85 | D6-f | OK | sources : d6_shared_scripts |
| 91 | D7-a | OK | sources : 5f4438e |
| 92 | D7-b | OK | sources : d7_scheduler_order |
| 93 | D7-c | OK | sources : d7_scheduler_order |
| 94 | D8-a | OK | sources : b9fcb92 |
| 95 | D8-b | OK | sources : d8_chronology |
| 96 | D8-c | OK | sources : d8_chronology |
| 97 | D8-d | OK | sources : d8_chronology |
| 103 | AU-a | OK | aucun nombre à vérifier |
| 104 | AU-b | OK | sources : audit_report |
| 105 | AU-c | OK | aucun nombre à vérifier |
| 106 | AU-d | OK | sources : audit_report, phase1_pipeline |
| 107 | AU-e | OK | aucun nombre à vérifier |
| 108 | AU-f | OK | sources : audit_report |
| 109 | AU-g | OK | sources : audit_report |
| 119 | - Train complet (clusters 2-3), seeds 0-4, 100 epochs, polit | OK | sources : e12_attente_pre_test |
| 120 | - Tables DM ajustées sur le train. Bootstrap par réservation | OK | sources : e12_attente_pre_test |
| 123 | - C'est la **seconde** lecture du test, pas une lecture aveu | OK | sources : phase2_baselines |
| 124 | - Seuls α = 0,1, la variante γ = 0 et la ventilation par scr | OK | sources : e12_attente_pre_test |
| 128 | Les trois scripts du test sont c40f2fe7 (177 réservations ut | OK | sources : results/e12/test_results.json |
| 130 | Légende des chiffres : coûts DM suivis de leur IC 95 % boots | OK | sources : phase2_baselines |
| 134 | E12-a | OK | sources : results/e12/test_results.json |
| 135 | E12-b | OK | sources : d6_shared_scripts, e12_rapport_final |
| 136 | E12-c | OK | sources : e12_rapport_final, results/e12/test_results.json |
| 137 | E12-d | OK | sources : e12_rapport_final |
| 138 | E12-e | OK | sources : e12_rapport_final, phase2_baselines, results/e12/test_results.json |
| 139 | E12-f | OK | sources : e12_rapport_final |
| 140 | E12-g | OK | sources : e12_rapport_final |
| 141 | E12-h | OK | sources : e12_rapport_final |
| 142 | E12-i | OK | sources : results/e12/test_results.json |
| 143 | E12-j | OK | sources : results/e12/test_results.json |
| 144 | E12-k | OK | aucun nombre à vérifier |
| 154 | - Budget d = 0,03. (e1_lp_diagnostic) | OK | sources : e1_lp_diagnostic |
| 158 | E1-a | OK | sources : 7ef80eb |
| 159 | E1-b | OK | sources : e1_lp_diagnostic |
| 160 | E1-c | OK | sources : e1_lp_diagnostic |
| 161 | E1-d | OK | sources : e1_lp_diagnostic |
| 162 | E1-e | OK | aucun nombre à vérifier |
| 163 | E2-a | OK | sources : 8f8a039, b2f9405 |
| 164 | E2-b | OK | sources : e2_safe_cql_diagnostic |
| 165 | E2-c | OK | sources : e2_safe_cql_diagnostic |
| 166 | E2-d | OK | sources : e2_safe_cql_diagnostic |
| 167 | E2-e | OK | sources : e2_safe_cql_diagnostic |
| 168 | E11-a | OK | sources : 3779a06, 7e9be78 |
| 169 | E11-b | OK | sources : e11_alpha_grid |
| 170 | E11-c | OK | sources : e11_alpha_grid |
| 171 | E11-d | OK | sources : e11_alpha_grid |
| 172 | E11-e | OK | sources : results/e11_summary.csv |
| 180 | TR-a | OK | sources : e1_lp_diagnostic |
| 181 | TR-b | OK | sources : ecb624d |
| 182 | TR-c | OK | sources : e2_safe_cql_diagnostic |
| 183 | TR-d | OK | sources : e1_lp_diagnostic |
| 184 | TR-e | OK | sources : e13a2_resultats, e13a_niveaux_charge |
| 185 | TR-f | OK | sources : e12_rapport_final |
| 199 | E13a-a | OK | sources : e13a_niveaux_charge |
| 200 | E13a-b | OK | sources : e13a_niveaux_charge |
| 201 | E13a2-a | OK | sources : 7652a34 |
| 202 | E13a2-b | OK | sources : e13a_niveaux_charge |
| 203 | E13a2-c | OK | sources : e13a2_resultats, e13a_niveaux_charge |
| 204 | E13a2-d | OK | sources : e13a2_resultats, e13a_niveaux_charge |
| 205 | E13a2-e | OK | sources : e13a2_resultats, e13a_niveaux_charge |
| 206 | E13a2-f | OK | sources : e13a2_resultats |
| 207 | R1W2-no | OK | aucun nombre à vérifier |
| 214 | - 12 réservations du **train** (aucune du test), colonnes d' | OK | sources : e13b_pas_echantillonnage |
| 220 | E13b-a | OK | sources : f77bff6 |
| 221 | E13b-b | OK | sources : e13b_pas_echantillonnage |
| 222 | E13b-c | OK | sources : e13b_pas_echantillonnage |
| 223 | E13b-d | OK | aucun nombre à vérifier |
| 224 | E13b-e | OK | aucun nombre à vérifier |
| 225 | E13b-f | OK | sources : phase1_pipeline |
| 226 | E13b-g | OK | sources : e13b_pas_echantillonnage |
| 233 | - 510 réservations du train ; protocole fixé avant lecture ( | OK | sources : 556bcf2 |
| 239 | E13d-a | OK | aucun nombre à vérifier |
| 240 | E13d-b | OK | sources : 41896a3 |
| 241 | E13d-c | OK | sources : e13d_filtre_latence |
| 242 | E13d-d | OK | sources : e13d_filtre_latence |
| 243 | E13d-e | OK | sources : e13d_filtre_latence |
| 244 | E13d-f | OK | sources : dataset_notes |
| 245 | E13d-g | OK | sources : e13d_filtre_latence |
| 246 | E13d-h | OK | sources : dataset_notes |
| 257 |   - D1 : aucune des 1 116 réservations ne change de config,  | OK | sources : decision_memo |
| 258 |   - D4 : l'état identifie l'action loguée (30-33 % avec les  | OK | sources : decision_memo |
| 259 |   - E2-d : avec α ≥ 0,5 la Q-net reproduit l'action loguée s | OK | sources : e2_safe_cql_diagnostic |
| 265 | - **À ne pas faire :** « Safe-CQL respecte le budget d = 0,0 | OK | sources : audit_report |
| 267 |   - E12-e : sur c40f2fe7, aucune politique n'est démontrée s | OK | sources : e12_rapport_final |
| 268 |   - E2-a : 0/60 runs convergent. | OK | sources : e2_safe_cql_diagnostic |
| 269 |   - E11-a : aucun α n'est faisable ; α = 0,1 est retenu par  | OK | sources : e11_alpha_grid |
| 272 | - **Formulation défendable :** « sur le script de test c40f2 | OK | sources : e12_rapport_final |
| 278 |   - E12-f : table-greedy a le meilleur reward DM (9,069 cont | OK | sources : e12_rapport_final |
| 279 |   - E11-e : la Q-net est moins bonne que le table-greedy tra | OK | sources : e11_alpha_grid |
| 282 |   - Réserve sur table-greedy : DM circulaire et couverture a | OK | sources : e12_rapport_final |
| 290 |   - TR-d : la contrainte respectée sur un script a été violé | OK | sources : e1_lp_diagnostic |
| 291 |   - D6-b : un script de test (90 %). | OK | sources : d6_shared_scripts |
| 292 |   - D5-b : 47-63 % des cellules ont un IC qui contient d. | OK | sources : decision_memo |
| 296 |   - E13d-d : 351/510 réservations seulement ont un coût ≤ d. | OK | sources : e13d_filtre_latence |
| 307 |   - E13b-c : le coût URLLC n'est pas résoluble à d en dessou | OK | sources : e13b_pas_echantillonnage |
| 310 | - **Formulation défendable :** boucle plus lente (type rApp  | OK | sources : e13b_pas_echantillonnage |
| 315 | à ne pas dire | OK | aucun nombre à vérifier |
| 317 | « Les résultats du notebook sont reproduits. » | OK | sources : audit_report |
| 318 | « Le scheduler PF cause plus de violations que RR. | OK | sources : d7_scheduler_order |
| 319 | « RR reste sûr à toutes les charges (typiquement < | OK | sources : audit_report, decision_memo |
| 320 | « Le nombre de niveaux de charge (3) est optimal o | OK | aucun nombre à vérifier |
| 321 | « Le filtre de latence n'a pas d'effet sur les rés | OK | sources : 41896a3, e13d_filtre_latence |
| 322 | « L'ordre Safe-CQL < CQL < IQL est robuste au filt | OK | sources : e13d_filtre_latence |
| 323 | « Généralise à un déploiement inconnu / à d'autres | OK | sources : d6_shared_scripts |
| 324 | « FQE confirme le classement. » | OK | aucun nombre à vérifier |
| 325 | « α = 0,1 est le meilleur hyperparamètre. » | OK | sources : e11_alpha_grid |
| 326 | « Le test est un jeu indépendant et aveugle. » | OK | aucun nombre à vérifier |
| 327 | « Le Q-learning a appris une dynamique qui ne dépe | OK | sources : decision_memo, e2_safe_cql_diagnostic |
| 328 | « Source du budget 0,03 et de Lmax = 20 ms : [vale | OK | sources : e1_lp_diagnostic |
| 329 | « Nouveauté algorithmique. » | OK | aucun nombre à vérifier |
| 337 | chiffre | OK | aucun nombre à vérifier |
| 339 | `pct_safe` par politique en E12 : présent dans `re | OK | aucun nombre à vérifier |
| 340 | λ finaux et statut de convergence des runs E12 | OK | aucun nombre à vérifier |
| 341 | Résultats d'une analyse de queue (`urllc_p99`) ou  | OK | aucun nombre à vérifier |
| 342 | Résultats complets de la phase 3 (100 epochs × 5 s | OK | sources : phase3_learning_curves |
| 343 | Rapport propre pour E13c | OK | aucun nombre à vérifier |
| 344 | Source de d = 0,03 et de Lmax | OK | sources : dataset_notes |
| 345 | Contenu d'un manuscrit révisé (corrections R3-W3,  | OK | sources : audit_report |
| 351 | - **Phase 1 contre notebook :** 224 193 lignes contre 225 31 | OK | sources : decision_memo, phase1_pipeline |
| 352 | - **D5 contre notebook :** (30, RR, charge basse) 0,142 cont | OK | sources : decision_memo |
| 353 | - **Phase 1 contre phase 0 :** ventilation des 101 réservati | OK | sources : phase1_pipeline |
| 358 | - **[Q]** Que valent les anomalies d'horodatage et le filtre | OK | sources : dataset_notes |
| 360 | - **[Q]** Le λ = 12,22 du notebook vient-il de la taille d'e | OK | sources : audit_report |
| 361 | - **[Q]** Le slicing 5 est-il « pas de slicing » ou « 50 PRB | OK | sources : decision_memo |
