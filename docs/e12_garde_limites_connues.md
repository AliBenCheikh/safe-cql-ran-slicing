# Garde de `src/e12_final.py` : limites connues de la couverture par `tests/test_e12.py`

Constat de lecture (aucun test ni code modifié : `tests/` et `src/` sont gelés par l'empreinte et par `git_state`). Ce que les tests couvrent : empreinte épinglée, refus d'un arbre sale, refus d'une empreinte différente, entraînement sous une autre empreinte, verrou (seconde lecture refusée, relance après plantage), checkpoint manquant sans consommation du verrou, CLI sans contournement de la garde.

## Non couvert

1. `git_state()` réel n'est jamais exécuté (toujours simulé) : le filtre `git status --porcelain src tests <document d'attente>` n'est pas testé (fichier non suivi, fichier de tests modifié).
2. Le refus quand le document d'attente n'est pas commité (`ls-files`) n'est pas testé.
3. La branche `PINNED_SHA256 == "UNSET"` n'est pas isolée du cas « empreinte différente ».
4. Le chemin heureux de `guard()` (retour avec `fingerprint`) n'est pas testé.
5. Dans `acquire_lock`, la branche « statut ≠ `started` sans fichier de résultats » n'est pas isolée (le test de bout en bout a les deux conditions vraies).
6. `O_EXCL` n'est exercé que de façon incidente ; aucun test de création concurrente.
7. L'écart d'`EPOCHS` dans l'assertion « trained under other code » n'est pas testé.

## Vérifié (point 8 du constat précédent)

L'empreinte épinglée `PINNED_SHA256` de `src/e12_final.py` est identique à celle enregistrée au commit de gel `0387dbc` (`git show 0387dbc:src/e12_final.py`, ligne 70 ; même valeur dans `tests/test_e12.py` à ce commit et dans le résumé d'entraînement). La phrase de la section 05 (« the one recorded at the freeze commit ») est donc exacte.

## Statut

Limites connues, non corrigées par décision (les tests ne sont pas modifiés). Elles n'affectent pas un résultat déjà produit ; elles limitent seulement ce que la couverture de tests permet d'affirmer sur la garde.
