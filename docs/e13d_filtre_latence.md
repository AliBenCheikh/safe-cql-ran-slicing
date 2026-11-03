# E13d — Effet du filtre de latence sur le coût URLLC (train seul) — chiffres tels quels

Protocole : `docs/e13d_protocole_filtre_latence.md` (commit `556bcf2`, fixé avant lecture). Code : `src/e13d_latency_filter.py` (commit d'exécution `5f16038`, arbre propre). Sorties : `results/e13d_{reservations.csv,summary.json}`, journal `results/e13d.log` (gitignorés).
Portée : 510 réservations utilisables du **train** ; test non lu (`test_split_read: false`), aucun entraînement (`trained_anything: false`, inférence sur les checkpoints existants). Dataset `268d524c117eb6de`.
Tags : **[V]** vérifié par le script · **[H]** hypothèse non vérifiée.

Les chiffres ci-dessous sont donnés sans interprétation.

## Le filtre (code exact de `build_dataset._urllc_stream`)
```python
m = _read(os.path.join(d, "mgen.csv"), ",", usecols=["Received Time", "Sent Time"])
if m is None:
    continue
m["lat"] = (m["Received Time"] - m["Sent Time"]) * 1000.0
m = m[(m["lat"] >= 0) & (m["lat"] < 20000)]
...
urllc_frac_viol=lambda s: (s > SLA_MS).mean()        # SLA_MS = 20.0
```
- Latences négatives : écartées par `lat >= 0` (ni corrigées, ni comptées en violation ou non-violation). Latence NaN : écartée de la même façon. Latences ≥ 20 000 ms : écartées. Un paquet écarté n'est ni au numérateur ni au dénominateur de `urllc_frac_viol`.
- Dans le script d'analyse, la même condition est appliquée à l'identique (test `test_classify_matches_pipeline_filter`).

## Gardes de reproduction [V]
- G1 : écart maximal entre le coût par fenêtre recalculé sur les paquets gardés et `urllc_frac_viol` du parquet : **0** (toutes les fenêtres canoniques du train).
- G2 : écart maximal entre la table de coût refaite depuis le parquet et `results/cost_table.csv` : **0**.

## Paquets (somme sur les 510 réservations) [V]
| mesure | valeur |
|---|---|
| paquets lus (4 fichiers URLLC) | 20 619 886 |
| gardés | 20 619 046 |
| écartés, latence ≥ 20 000 ms | **840** |
| écartés, latence négative | **0** |
| écartés, latence non finie | **0** |
| écartés dont `Received Time` non finie | 0 |
| écartés affectés à une fenêtre hors des fenêtres canoniques | 271 (dont 0 avec `win < 0`) |
| fenêtres qui n'existent que par des paquets écartés (perdues) | 5 |

Distribution par réservation (min · Q1 · médiane · Q3 · max) :
| mesure | min | Q1 | médiane | Q3 | max |
|---|---|---|---|---|---|
| part de latences négatives | 0 | 0 | 0 | 0 | 0 |
| part ≥ 20 000 ms | 0 | 2,1·10⁻⁵ | 3,9·10⁻⁵ | 5,8·10⁻⁵ | 6,29·10⁻⁴ |
| part écartée totale | 0 | 2,1·10⁻⁵ | 3,9·10⁻⁵ | 5,8·10⁻⁵ | 6,29·10⁻⁴ |
| part en violation (> 20 ms) parmi les gardés | 0 | 6,2·10⁻⁴ | 2,90·10⁻³ | 5,32·10⁻² | 0,621 |

- 448 réservations sur 510 ont au moins un paquet écarté ; 62 n'en ont aucun. Le maximum est de 4 paquets écartés par réservation. 5 réservations ont une fenêtre perdue.
- Les bornes n'incluent pas : les 271 paquets hors fenêtres canoniques, les 5 fenêtres perdues ; elles sont calculées sur les 163 065 fenêtres canoniques du train.

## Deux bornes du coût et écart au budget d = 0,03 [V]
Borne basse : écartés = non-violations ; borne haute : écartés = violations (formules du protocole).

**Moyenne sur l'ensemble des fenêtres de train :**
| | coût | coût − d |
|---|---|---|
| pipeline (gardés seuls) | 0,056338 | +0,026338 |
| borne basse | 0,056332 | +0,026332 |
| borne haute | 0,056411 | +0,026411 |

**Par réservation (min · Q1 · médiane · Q3 · max) :**
| mesure | min | Q1 | médiane | Q3 | max |
|---|---|---|---|---|---|
| coût pipeline | 0 | 0,000712 | 0,003055 | 0,062842 | 0,801335 |
| borne basse | 0 | 0,000712 | 0,003055 | 0,062840 | 0,801335 |
| borne haute | 0 | 0,000765 | 0,003149 | 0,062849 | 0,801335 |
| borne basse − d | −0,030000 | −0,029288 | −0,026945 | +0,032840 | +0,771335 |
| borne haute − d | −0,030000 | −0,029235 | −0,026851 | +0,032849 | +0,771335 |

- Réservations dont le coût est ≤ d : pipeline **351/510** ; borne haute **351/510**. Réservations dont la borne basse est > d : **159/510**.
- Écart maximal borne haute − borne basse sur une réservation : 0,005245 ; médiane 3,5·10⁻⁵.

**Tables de coût (action × `load_bin`) :** écart maximal absolu `lo` − `orig` : 6,0·10⁻⁵ ; `hi` − `orig` : 2,85·10⁻⁴ (même règle de repli à 20 fenêtres).

## Ordre Safe-CQL < CQL < IQL avec les bornes (train, dans l'échantillon, checkpoints E12) [V]
DM = moyenne sur les fenêtres de `C[a, load_bin]` ; moyenne ± écart-type sur 5 seeds ; « ordre » = comparaison stricte des moyennes. Triplet α = 0,1 : (`safe_cql_a0.1`, `cql_a0.1`, `iql`) ; triplet α = 0,5 : (`safe_cql_a0.5`, `cql_a0.5`, `iql`).

| triplet | découpe | table | Safe-CQL | CQL | IQL | ordre tient |
|---|---|---|---|---|---|---|
| α = 0,1 | tout le train | orig | 0,0300 ± 0,0005 | 0,0514 ± 0,0019 | 0,0524 ± 0,0003 | oui |
| α = 0,1 | tout le train | lo | 0,0300 ± 0,0005 | 0,0514 ± 0,0019 | 0,0523 ± 0,0003 | oui |
| α = 0,1 | tout le train | hi | 0,0300 ± 0,0005 | 0,0515 ± 0,0019 | 0,0524 ± 0,0003 | oui |
| α = 0,1 | script A | orig / lo / hi | 0,0311 / 0,0311 / 0,0312 | 0,0524 / 0,0523 / 0,0524 | 0,0530 / 0,0530 / 0,0531 | oui / oui / oui |
| α = 0,1 | script B | orig / lo / hi | 0,0296 / 0,0296 / 0,0297 | 0,0528 / 0,0528 / 0,0529 | 0,0547 / 0,0547 / 0,0548 | oui / oui / oui |
| α = 0,5 | tout le train | orig | 0,0326 ± 0,0002 | 0,0525 ± 0,0006 | 0,0524 ± 0,0003 | **non** |
| α = 0,5 | tout le train | lo | 0,0326 ± 0,0002 | 0,0525 ± 0,0006 | 0,0523 ± 0,0003 | **non** |
| α = 0,5 | tout le train | hi | 0,0327 ± 0,0002 | 0,0526 ± 0,0006 | 0,0524 ± 0,0003 | **non** |
| α = 0,5 | script A | orig / lo / hi | 0,0352 / 0,0352 / 0,0352 | 0,0533 / 0,0533 / 0,0534 | 0,0530 / 0,0530 / 0,0531 | non / non / non |
| α = 0,5 | script B | orig / lo / hi | 0,0313 / 0,0312 / 0,0313 | 0,0548 / 0,0548 / 0,0549 | 0,0547 / 0,0547 / 0,0548 | non / non / non |

Les 18 comparaisons (2 triplets × 3 découpes × 3 tables) donnent le même résultat pour `orig`, `lo` et `hi` dans chaque cas. Les écarts-types complets sont dans `results/e13d_summary.json`.

## Limites [V sauf mention]
1. L'évaluation de l'ordre est **dans l'échantillon** (tables ajustées sur les mêmes fenêtres que celles vues à l'entraînement) ; elle ne dit rien sur l'ordre mesuré sur le test en E12. Aucun intervalle n'est calculé.
2. Les bornes ne couvrent que les paquets affectables à une fenêtre canonique ; les 271 paquets hors fenêtres canoniques et les 5 fenêtres perdues sont comptés à part.
3. Le filtre ne voit que ce qui est lu dans les quatre fichiers URLLC : les fichiers `mgen` vides (69 % des réservations en ont au moins un, E13c) ou illisibles ne sont pas des paquets écartés, ils n'entrent pas du tout (paquets jamais lus).
4. **[H non vérifiée]** Les 840 paquets écartés (≥ 20 000 ms) pourraient être les lignes à `Sent Time` aberrant vues en E13c (423 réservations avec un saut de plus de 3 600 s ; 448 réservations avec au moins un paquet écarté). Je n'ai pas apparié les lignes.
