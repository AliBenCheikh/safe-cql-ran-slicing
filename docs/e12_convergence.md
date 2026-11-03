# Convergence de λ dans les 15 runs Safe-CQL d'E12 (critère d'E2)

Produit par `src/checks/convergence_e12.py` (lecture seule ; ni `data/`, ni `tests/`, ni `results/e12/test_results.json` lus). Sources : `results/e12/checkpoints/*.pt` (`lambda_history`) et la méta de `results/e12/train_summary.json`.

Critère : celui d'E2 (`convergence`, importé sans modification) sur les 20 dernières époques : (1) étendue de λ < 0.02 ; (2) λ > 0 et 0.9 d ≤ coût greedy ≤ d partout, ou λ = 0 et coût ≤ d ; (3) l'IC à 95 % de la pente de λ contient 0. d = 0.03.
Le coût greedy est lu sur la table de coût d'entraînement et les fenêtres d'entraînement : c'est une quantité dans l'échantillon.

Commit d'entraînement : `0fa578751dca90ddfeb6bccd20786bb191bb556d` ; empreinte `c88c288ea41dd1cb05b9a66b1574e4180bf6a2d562e37c9bb42198d74536d854` ; époques 100.

**Résultat : 0 run(s) convergé(s) sur 15.**

| config | seed | époques | λ fin | coût greedy fin | étendue de λ | (1) | (2) | (3) | converge |
|---|---|---|---|---|---|---|---|---|---|
| safe_cql_a0.1 | 0 | 100 | 0.1191 | 0.0296 | 0.0255 | False | False | False | False |
| safe_cql_a0.1 | 1 | 100 | 0.1212 | 0.0294 | 0.0203 | False | False | False | False |
| safe_cql_a0.1 | 2 | 100 | 0.1272 | 0.0302 | 0.0176 | True | False | False | False |
| safe_cql_a0.1 | 3 | 100 | 0.1203 | 0.0300 | 0.0196 | True | False | False | False |
| safe_cql_a0.1 | 4 | 100 | 0.1028 | 0.0306 | 0.0132 | True | False | False | False |
| safe_cql_a0.5 | 0 | 100 | 0.8187 | 0.0326 | 0.1754 | False | False | False | False |
| safe_cql_a0.5 | 1 | 100 | 0.7497 | 0.0323 | 0.1544 | False | False | False | False |
| safe_cql_a0.5 | 2 | 100 | 0.8293 | 0.0326 | 0.1703 | False | False | False | False |
| safe_cql_a0.5 | 3 | 100 | 0.9046 | 0.0326 | 0.1734 | False | False | False | False |
| safe_cql_a0.5 | 4 | 100 | 0.8361 | 0.0329 | 0.1794 | False | False | False | False |
| safe_cql_a0.1_g0 | 0 | 100 | 0.4415 | 0.0324 | 0.1321 | False | False | False | False |
| safe_cql_a0.1_g0 | 1 | 100 | 0.4910 | 0.0320 | 0.1258 | False | False | False | False |
| safe_cql_a0.1_g0 | 2 | 100 | 0.4398 | 0.0318 | 0.1187 | False | False | False | False |
| safe_cql_a0.1_g0 | 3 | 100 | 0.4830 | 0.0323 | 0.1362 | False | False | False | False |
| safe_cql_a0.1_g0 | 4 | 100 | 0.4805 | 0.0323 | 0.1347 | False | False | False | False |
