# E13d — Protocole : effet du filtre de latence sur le coût URLLC — FIXÉ AVANT TOUTE LECTURE

Commit de protocole, écrit avant que le moindre paquet ne soit relu pour cette question. Portée : **les 510 réservations utilisables du train** (clusters 2-3, `split == "train"`) ; le test n'est pas lu, ni ses résultats enregistrés (`results/e12/test_results.json` n'est pas ouvert). Colonnes lues : `Received Time`, `Sent Time` des quatre `mgen.csv` URLLC, plus ce que `_enb_stream` lit pour `t0`.

## Le filtre, code exact (`src/build_dataset.py`, `_urllc_stream`, lignes 205-231)
```python
m = _read(os.path.join(d, "mgen.csv"), ",", usecols=["Received Time", "Sent Time"])
if m is None:
    continue
m["lat"] = (m["Received Time"] - m["Sent Time"]) * 1000.0
m = m[(m["lat"] >= 0) & (m["lat"] < 20000)]
...
urllc_frac_viol=lambda s: (s > SLA_MS).mean()        # SLA_MS = 20.0 (ms), build_dataset.py:35
```
- **Latences négatives** : `lat >= 0` les **écarte** (elles ne sont ni corrigées ni comptées comme violation ou non-violation). Une latence **NaN** (temps non numérique) échoue aussi les deux comparaisons : elle est écartée sans trace.
- **Latences ≥ 20 000 ms** : écartées de la même façon.
- `_read` renvoie `None` (fichier ignoré) si le fichier est vide, illisible ou n'a qu'une colonne.
- Violation : `lat > 20 ms` (Lmax = 20 ms dans le code), sur les paquets **gardés** seulement ; fenêtre = `floor((t_abs − t0)/5 s)`, `win ≥ 0`, `t_abs` dérivé de `Received Time` (jour de `t0`, fuseau déduit du minimum des temps **gardés**, repli de minuit).
- Un paquet écarté n'est donc ni au numérateur ni au dénominateur de `urllc_frac_viol`. Une fenêtre où tous les paquets sont écartés disparaît (`dropna` du pipeline).

## Mesures par réservation (une ligne par réservation, plus le détail par fenêtre)
1. `n_packets` : lignes lues dans les fichiers URLLC lisibles.
2. `n_neg` (lat < 0), `n_big` (lat ≥ 20 000 ms), `n_nan` (lat non finie), `n_kept` ; parts `n_neg/n_packets`, `n_big/n_packets`, part écartée totale `(n_neg+n_big+n_nan)/n_packets`.
3. Part en violation parmi les gardés : `mean(lat > 20)`, comptée sur les paquets gardés (c'est ce que voit le pipeline).
4. Coût du pipeline de la réservation = moyenne sur ses fenêtres canoniques de `urllc_frac_viol` (doit égaler le parquet).

## Deux bornes du coût (fenêtres canoniques du parquet uniquement)
Pour une fenêtre w de la réservation : `k_w` = paquets gardés, `v_w` = gardés avec lat > 20 ms, `e_w` = paquets écartés (neg + big) **affectés à w par leur `Received Time`** avec la transformation temporelle du pipeline (mêmes `day0`, `tz_h`, repli de minuit, calculés sur les paquets gardés).
- **Borne basse** (écartés = non-violations) : `lo_w = v_w / (k_w + e_w)`.
- **Borne haute** (écartés = violations) : `hi_w = (v_w + e_w) / (k_w + e_w)`.
- Coût d'une réservation = moyenne de `lo_w` (resp. `hi_w`) sur ses fenêtres canoniques. Pour chaque borne, **écart au budget** : `borne − d`, d = 0,03, par réservation (min, quartiles, médiane, max ; nombre de réservations avec `hi ≤ d`, avec `lo > d`) et sur l'ensemble du train.
- Hors périmètre des bornes, **comptés à part** : paquets écartés dont la fenêtre est hors des fenêtres canoniques (fenêtre absente, `win < 0`), nombre de fenêtres qui n'existent que par des paquets écartés (fenêtres perdues), paquets à `Received Time` non finie (non affectables).
- Les bornes ne couvrent donc pas les fenêtres perdues ; leur nombre est rapporté pour que ce manque soit visible.

## Gardes de reproduction (avant toute autre sortie ; arrêt si échec)
- G1 : pour chaque réservation, le coût par fenêtre recalculé sur les paquets gardés égale `urllc_frac_viol` du parquet (tolérance 1e-9) sur toutes les fenêtres canoniques.
- G2 : la table de coût (action × `load_bin`, repli < 20 fenêtres) refaite depuis le parquet train égale `results/cost_table.csv`.

## Ordre Safe-CQL < CQL < IQL avec les bornes (politiques déjà entraînées, train seul)
- Politiques : checkpoints existants `results/e12/checkpoints/*_seed{0..4}.pt` (entraînés sur le train, aucun entraînement relancé). Actions greedy sur **toutes les fenêtres de train** ; aucun appel à `evaluate_once`, aucun accès au test.
- Estimateur : DM = moyenne sur les fenêtres de `C[a, load_bin]` (moyenne des fenêtres, pas des réservations), avec trois tables de coût : `orig` (celle du pipeline), `lo`, `hi` (même construction, même repli à 20 fenêtres, appliquée à `lo_w`, `hi_w`).
- Triplets testés : (`safe_cql_a0.1`, `cql_a0.1`, `iql`) et (`safe_cql_a0.5`, `cql_a0.5`, `iql`). Pour chaque table : moyenne et écart-type sur les 5 seeds, écart `coût − d`, et le **booléen** « Safe-CQL < CQL < IQL » sur les moyennes de seeds (comparaison stricte). Découpes : tout le train, script A (`a908e4cc`), script B (`a53521b2`).
- **Limite fixée d'avance :** l'évaluation est **dans l'échantillon** (les tables sont ajustées sur ces mêmes fenêtres et les politiques les ont vues à l'entraînement) ; elle ne dit rien sur l'ordre mesuré sur le test en E12. Aucun intervalle n'est calculé.

## Rapport des chiffres
Les chiffres sont donnés tels quels, sans interprétation, dans `docs/e13d_filtre_latence.md`. Pas de seuil de décision fixé.
