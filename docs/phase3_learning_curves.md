# Étape 03 — historique par epoch et courbes d'apprentissage

## Ce qui est loggé (fait vérifié dans le code)
Pour chaque agent, une entrée par epoch dans `hist` (liste de dicts), stockée dans le checkpoint et dans
`results/evaluation_results.json` sous `rl.<agent>.extras[seed]["history"]` :

| agent | clés |
|---|---|
| CQL, Safe-CQL | `epoch, loss, bellman, cons, q_logged, q_max, greedy_cost_train` (+ `lambda` pour Safe-CQL) |
| IQL | `epoch, loss_v, loss_q, loss_pi, q_logged, q_max, greedy_cost_train` |

- Pertes : moyenne pondérée sur les mini-batches de l'epoch (comme avant).
- `q_logged`, `q_max`, `greedy_cost_train` : calculés en fin d'epoch sur tout le train (forward seul, sans RNG ;
  `src.agents.cql.epoch_stats`). `greedy_cost_train` = moyenne de `cost_hat[a_greedy, load_bin]` (argmax Q ; IQL : argmax π).
- `lambda` (Safe-CQL) = valeur utilisée *pendant* l'epoch ; `lam_hist` garde la valeur après mise à jour.
- La logique d'entraînement, les hyperparamètres et les seeds ne sont pas modifiés ; le test
  `test_monitor_does_not_change_training` vérifie que les poids finaux sont identiques avec/sans monitor.

## Mode `--curves-val` (diagnostic uniquement)
`python -m src.evaluate --curves-val` → `results/learning_curves_val.json` (`meta.diagnostic_only = true`).
- Ne garde que `split == "train"` ; sub-train 80 % / validation 20 % par réservation (`split_val`, seed 0).
- Tables de récompense et de coût (et colonne `cost_hat` d'entraînement) refit sur sub-train seul.
- Chaque epoch : `dm_reward_mean`, `dm_cost_mean` via `evaluate_policy` sur la validation, + stats train ci-dessus.
- Le test n'est pas utilisé pour le monitoring ; ce fichier n'alimente pas le tableau de résultats.

## Vérifié / non vérifié
- Vérifié : 35 tests verts ; smoke test 2 epochs, seed 0 sur le vrai dataset (~13 s par mode) : historiques de 2 entrées pour les trois agents, JSON des courbes bien formé. Ces sorties de smoke test ne sont **pas** des résultats.
- Non fait : runs complets (100 epochs × 5 seeds). Non-régression des métriques finales vs `evaluation_results_v1.json` à vérifier après le run complet.
- Surcoût de temps de la passe train par epoch : non mesuré.
- Les DM de validation sont des estimations par tables, pas des retours mesurés.
