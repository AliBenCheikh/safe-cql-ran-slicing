# Vérification du registre des affirmations

Produit par `src/checks/verifie_registre.py` (lecture seule ; aucun calcul nouveau ; ni `data/` ni `tests/` lus).
Règles de verdict : voir la docstring du script. Seules les lignes contenant au moins un nombre significatif sont listées.

Total : 155 lignes — OK 153, AMBIGU 2, ABSENT 0.

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
| 115 | WIN-a | OK | aucun nombre à vérifier |
| 116 | COST-a | AMBIGU | aucune source résolvable |
| 117 | PLAT-a | OK | sources : dataset_notes |
| 127 | - Train complet (clusters 2-3), seeds 0-4, 100 epochs, polit | OK | sources : e12_attente_pre_test |
| 128 | - Tables DM ajustées sur le train. Bootstrap par réservation | OK | sources : e12_attente_pre_test |
| 131 | - C'est la **seconde** lecture du test, pas une lecture aveu | OK | sources : phase2_baselines |
| 132 | - Seuls α = 0,1, la variante γ = 0 et la ventilation par scr | OK | sources : e12_attente_pre_test |
| 136 | Les trois scripts du test sont c40f2fe7 (177 réservations ut | OK | sources : results/e12/test_results.json |
| 138 | Légende des chiffres : coûts DM suivis de leur IC 95 % boots | OK | sources : phase2_baselines |
| 142 | E12-a | OK | sources : results/e12/test_results.json |
| 143 | E12-b | OK | sources : d6_shared_scripts, e12_rapport_final |
| 144 | E12-c | OK | sources : e12_rapport_final, results/e12/test_results.json |
| 145 | E12-d | OK | sources : e12_rapport_final |
| 146 | E12-e | OK | sources : e12_rapport_final, phase2_baselines, results/e12/test_results.json |
| 147 | E12-f | OK | sources : e12_rapport_final |
| 148 | E12-g | OK | sources : e12_rapport_final |
| 149 | E12-h | OK | sources : e12_rapport_final |
| 150 | E12-i | OK | sources : results/e12/test_results.json |
| 151 | E12-j | OK | sources : results/e12/test_results.json |
| 152 | E12-k | OK | aucun nombre à vérifier |
| 162 | - Budget d = 0,03. (e1_lp_diagnostic) | OK | sources : e1_lp_diagnostic |
| 166 | E1-a | OK | sources : 7ef80eb |
| 167 | E1-b | OK | sources : e1_lp_diagnostic |
| 168 | E1-c | OK | sources : e1_lp_diagnostic |
| 169 | E1-d | OK | sources : e1_lp_diagnostic |
| 170 | E1-e | OK | aucun nombre à vérifier |
| 171 | E2-a | OK | sources : 8f8a039, b2f9405 |
| 172 | E2-b | OK | sources : e2_safe_cql_diagnostic |
| 173 | E2-c | OK | sources : e2_safe_cql_diagnostic |
| 174 | E2-d | OK | sources : e2_safe_cql_diagnostic |
| 175 | E2-e | OK | sources : e2_safe_cql_diagnostic |
| 176 | E11-a | OK | sources : 3779a06, 7e9be78 |
| 177 | E11-b | OK | sources : e11_alpha_grid |
| 178 | E11-c | OK | sources : e11_alpha_grid |
| 179 | E11-d | OK | sources : e11_alpha_grid |
| 180 | E11-e | OK | sources : results/e11_summary.csv |
| 188 | TR-a | OK | sources : e1_lp_diagnostic |
| 189 | TR-b | OK | sources : ecb624d |
| 190 | TR-c | OK | sources : e2_safe_cql_diagnostic |
| 191 | TR-d | OK | sources : e1_lp_diagnostic |
| 192 | TR-e | OK | sources : e13a2_resultats, e13a_niveaux_charge |
| 193 | TR-f | OK | sources : e12_rapport_final |
| 207 | E13a-a | OK | sources : e13a_niveaux_charge |
| 208 | E13a-b | OK | sources : e13a_niveaux_charge |
| 209 | E13a2-a | OK | sources : 7652a34 |
| 210 | E13a2-b | OK | sources : e13a_niveaux_charge |
| 211 | E13a2-c | OK | sources : e13a2_resultats, e13a_niveaux_charge |
| 212 | E13a2-d | OK | sources : e13a2_resultats, e13a_niveaux_charge |
| 213 | E13a2-e | OK | sources : e13a2_resultats, e13a_niveaux_charge |
| 214 | E13a2-f | OK | sources : e13a2_resultats |
| 215 | R1W2-no | OK | aucun nombre à vérifier |
| 222 | - 12 réservations du **train** (aucune du test), colonnes d' | OK | sources : e13b_pas_echantillonnage |
| 228 | E13b-a | OK | sources : f77bff6 |
| 229 | E13b-b | OK | sources : e13b_pas_echantillonnage |
| 230 | E13b-c | OK | sources : e13b_pas_echantillonnage |
| 231 | E13b-d | OK | aucun nombre à vérifier |
| 232 | E13b-e | OK | aucun nombre à vérifier |
| 233 | E13b-f | OK | sources : phase1_pipeline |
| 234 | E13b-g | OK | sources : e13b_pas_echantillonnage |
| 241 | - 510 réservations du train ; protocole fixé avant lecture ( | OK | sources : 556bcf2 |
| 247 | E13d-a | OK | aucun nombre à vérifier |
| 248 | E13d-b | OK | sources : 41896a3 |
| 249 | E13d-c | OK | sources : e13d_filtre_latence |
| 250 | E13d-d | OK | sources : e13d_filtre_latence |
| 251 | E13d-e | OK | sources : e13d_filtre_latence |
| 252 | E13d-f | OK | sources : dataset_notes |
| 253 | E13d-g | OK | sources : e13d_filtre_latence |
| 254 | E13d-h | OK | sources : dataset_notes |
| 265 |   - D1 : aucune des 1 116 réservations ne change de config,  | OK | sources : decision_memo |
| 266 |   - D4 : l'état identifie l'action loguée (30-33 % avec les  | OK | sources : decision_memo |
| 267 |   - E2-d : avec α ≥ 0,5 la Q-net reproduit l'action loguée s | OK | sources : e2_safe_cql_diagnostic |
| 273 | - **À ne pas faire :** « Safe-CQL respecte le budget d = 0,0 | OK | sources : audit_report |
| 275 |   - E12-e : sur c40f2fe7, aucune politique n'est démontrée s | OK | sources : e12_rapport_final |
| 276 |   - E2-a : 0/60 runs convergent. | OK | sources : e2_safe_cql_diagnostic |
| 277 |   - E11-a : aucun α n'est faisable ; α = 0,1 est retenu par  | OK | sources : e11_alpha_grid |
| 280 | - **Formulation défendable :** « sur le script de test c40f2 | OK | sources : e12_rapport_final |
| 286 |   - E12-f : table-greedy a le meilleur reward DM (9,069 cont | OK | sources : e12_rapport_final |
| 287 |   - E11-e : la Q-net est moins bonne que le table-greedy tra | OK | sources : e11_alpha_grid |
| 290 |   - Réserve sur table-greedy : DM circulaire et couverture a | OK | sources : e12_rapport_final |
| 298 |   - TR-d : la contrainte respectée sur un script a été violé | OK | sources : e1_lp_diagnostic |
| 299 |   - D6-b : un script de test (90 %). | OK | sources : d6_shared_scripts |
| 300 |   - D5-b : 47-63 % des cellules ont un IC qui contient d. | OK | sources : decision_memo |
| 304 |   - E13d-d : 351/510 réservations seulement ont un coût ≤ d. | OK | sources : e13d_filtre_latence |
| 315 |   - E13b-c : le coût URLLC n'est pas résoluble à d en dessou | OK | sources : e13b_pas_echantillonnage |
| 318 | - **Formulation défendable :** boucle plus lente (type rApp  | OK | sources : e13b_pas_echantillonnage |
| 345 | chiffre | OK | aucun nombre à vérifier |
| 347 | `pct_safe` par politique en E12 : présent dans `re | OK | aucun nombre à vérifier |
| 348 | λ finaux des runs E12 | OK | aucun nombre à vérifier |
| 349 | Résultats d'une analyse de queue (`urllc_p99`) ou  | OK | aucun nombre à vérifier |
| 350 | Résultats complets de la phase 3 (100 epochs × 5 s | OK | sources : phase3_learning_curves |
| 351 | Rapport propre pour E13c | OK | aucun nombre à vérifier |
| 352 | Source de d = 0,03 et de Lmax | OK | sources : dataset_notes |
| 353 | Contenu d'un manuscrit révisé (corrections R3-W3,  | OK | sources : audit_report |
| 359 | - **Phase 1 contre notebook :** 224 193 lignes contre 225 31 | OK | sources : decision_memo, phase1_pipeline |
| 360 | - **D5 contre notebook :** (30, RR, charge basse) 0,142 cont | OK | sources : decision_memo |
| 361 | - **Phase 1 contre phase 0 :** ventilation des 101 réservati | OK | sources : phase1_pipeline |
| 366 | - **[Q]** Que valent les anomalies d'horodatage et le filtre | OK | sources : dataset_notes |
| 368 | - **[Q]** Le λ = 12,22 du notebook vient-il de la taille d'e | OK | sources : audit_report |
| 369 | - **[Q]** Le slicing 5 est-il « pas de slicing » ou « 50 PRB | OK | sources : decision_memo |
| 385 | STATE-a | OK | aucun nombre à vérifier |
| 386 | REW-a | OK | aucun nombre à vérifier |
| 387 | REC-a | OK | aucun nombre à vérifier |
| 388 | SCALE-a | OK | aucun nombre à vérifier |
| 389 | SCALE-b | OK | sources : e12_artefacts_entrainement |
| 395 | ARCH-a | OK | sources : phase2_baselines |
| 396 | OPT-a | OK | sources : phase2_baselines |
| 397 | CQL-a | OK | aucun nombre à vérifier |
| 398 | IQL-a | OK | sources : phase2_baselines |
| 399 | SAFE-a | OK | sources : e2_safe_cql_diagnostic |
| 400 | SAFE-b | OK | sources : e2_safe_cql_diagnostic |
| 406 | TG-a | OK | aucun nombre à vérifier |
| 407 | BASE-a | OK | sources : phase2_baselines |
| 408 | BC-a | OK | sources : audit_report |
| 414 | E12P-a | OK | sources : e12_attente_pre_test |
| 415 | E12P-b | OK | sources : e12_attente_pre_test |
| 416 | E12P-c | OK | sources : e12_artefacts_entrainement |
| 417 | E12P-d | OK | aucun nombre à vérifier |
| 423 | GRID-a | OK | sources : e11_alpha_grid |
| 424 | GRID-b | OK | sources : e11_alpha_grid |
| 425 | GRID-c | OK | sources : e11_alpha_grid |
