# Artefacts d'entraînement E12 : r_scale, configurations enregistrées, λ finaux

Produit par `src/checks/lit_artefacts_entrainement.py` (lecture seule ; valeurs recopiées, aucun calcul ; ni `data/`, ni `tests/`, ni `results/e12/test_results.json` lus). Sources : `results/e12/train_summary.json` et `results/e12/checkpoints/*.pt`.

## Provenance

- Commit de l'entraînement : `0fa578751dca90ddfeb6bccd20786bb191bb556d` (arbre propre : True).
- Empreinte gelée : `c88c288ea41dd1cb05b9a66b1574e4180bf6a2d562e37c9bb42198d74536d854`.
- Version du dataset : `268d524c117eb6de`.
- Époques : 100 ; seeds : [0, 1, 2, 3, 4].
- `test_split_read` : False.

## r_scale

Valeurs distinctes sur les 30 checkpoints : 4.0757787775968035.
C'est l'écart-type du reward d'entraînement (`train_cql`, `train_iql`), le même pour tous les agents.

## Configurations enregistrées dans les checkpoints (seed 0)

| nom | cfg enregistrée |
|---|---|
| cql_a0.1 | {'hidden': 256, 'gamma': 0.7, 'alpha': 0.1, 'epochs': 100, 'batch': 1024, 'lr': 0.0003, 'tau': 0.005} |
| cql_a0.5 | {'hidden': 256, 'gamma': 0.7, 'alpha': 0.5, 'epochs': 100, 'batch': 1024, 'lr': 0.0003, 'tau': 0.005} |
| iql | {'hidden': 256, 'gamma': 0.7, 'expectile': 0.7, 'beta': 3.0, 'epochs': 100, 'batch': 1024, 'lr': 0.0003, 'tau': 0.005, 'w_max': 100.0} |
| safe_cql_a0.1 | {'hidden': 256, 'gamma': 0.7, 'alpha': 0.1, 'epochs': 100, 'batch': 1024, 'lr': 0.0003, 'tau': 0.005, 'budget': 0.03, 'eta': 0.1} |
| safe_cql_a0.1_g0 | {'hidden': 256, 'gamma': 0.0, 'alpha': 0.1, 'epochs': 100, 'batch': 1024, 'lr': 0.0003, 'tau': 0.005, 'budget': 0.03, 'eta': 0.1} |
| safe_cql_a0.5 | {'hidden': 256, 'gamma': 0.7, 'alpha': 0.5, 'epochs': 100, 'batch': 1024, 'lr': 0.0003, 'tau': 0.005, 'budget': 0.03, 'eta': 0.1} |

## Safe-CQL : λ et coût greedy d'entraînement

`λ fin` = `final_lambda` de `train_summary.json` (valeur après la dernière mise à jour, époque 99). `coût greedy` = `greedy_cost_train` de la dernière époque (table de coût d'entraînement, fenêtres d'entraînement). `λ[79]` et `λ[99]` = `lambda_history` du checkpoint (valeur après la mise à jour des époques 79 et 99).

| config | seed | λ fin | coût greedy | λ[79] | λ[99] |
|---|---|---|---|---|---|
| safe_cql_a0.1 | 0 | 0.1191 | 0.0296 | 0.0955 | 0.1191 |
| safe_cql_a0.1 | 1 | 0.1212 | 0.0294 | 0.1036 | 0.1212 |
| safe_cql_a0.1 | 2 | 0.1272 | 0.0302 | 0.1052 | 0.1272 |
| safe_cql_a0.1 | 3 | 0.1203 | 0.0300 | 0.1027 | 0.1203 |
| safe_cql_a0.1 | 4 | 0.1028 | 0.0306 | 0.0888 | 0.1028 |
| safe_cql_a0.5 | 0 | 0.8187 | 0.0326 | 0.6351 | 0.8187 |
| safe_cql_a0.5 | 1 | 0.7497 | 0.0323 | 0.5872 | 0.7497 |
| safe_cql_a0.5 | 2 | 0.8293 | 0.0326 | 0.6489 | 0.8293 |
| safe_cql_a0.5 | 3 | 0.9046 | 0.0326 | 0.7228 | 0.9046 |
| safe_cql_a0.5 | 4 | 0.8361 | 0.0329 | 0.6458 | 0.8361 |
| safe_cql_a0.1_g0 | 0 | 0.4415 | 0.0324 | 0.3036 | 0.4415 |
| safe_cql_a0.1_g0 | 1 | 0.4910 | 0.0320 | 0.3592 | 0.4910 |
| safe_cql_a0.1_g0 | 2 | 0.4398 | 0.0318 | 0.3153 | 0.4398 |
| safe_cql_a0.1_g0 | 3 | 0.4830 | 0.0323 | 0.3411 | 0.4830 |
| safe_cql_a0.1_g0 | 4 | 0.4805 | 0.0323 | 0.3387 | 0.4805 |

## Agents sans multiplicateur : coût greedy d'entraînement à la dernière époque

| config | seed | coût greedy |
|---|---|---|
| cql_a0.1 | 0 | 0.0518 |
| cql_a0.1 | 1 | 0.0483 |
| cql_a0.1 | 2 | 0.0511 |
| cql_a0.1 | 3 | 0.0525 |
| cql_a0.1 | 4 | 0.0532 |
| cql_a0.5 | 0 | 0.0525 |
| cql_a0.5 | 1 | 0.0515 |
| cql_a0.5 | 2 | 0.0527 |
| cql_a0.5 | 3 | 0.0531 |
| cql_a0.5 | 4 | 0.0527 |
| iql | 0 | 0.0523 |
| iql | 1 | 0.0528 |
| iql | 2 | 0.0523 |
| iql | 3 | 0.0521 |
| iql | 4 | 0.0522 |
