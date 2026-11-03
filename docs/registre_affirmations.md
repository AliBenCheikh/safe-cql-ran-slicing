# Registre des affirmations du papier réécrit

Pour chaque affirmation que le papier révisé pourrait faire : l'énoncé précis, son statut, sa source, ses limites, et la remarque de reviewer à laquelle elle répond. Une section finale liste les affirmations à **ne pas** faire.

## 0. Conventions

**Statuts.**
- **[V]** vérifié : par un script de `src/`, ou lu tel quel dans un rapport de `docs/`. Une *limite confirmée* (ce que les rapports appellent **[P]**) est notée « [V] limite ».
- **[H]** hypothèse : non vérifiée, ou vérifiée seulement en partie.
- **[Q]** question ouverte.

**Reviewers** (`reviews/reviewer_comments.md`).

| code | remarque |
|---|---|
| R1-W1 | l'état omet a_{t-1}, propriété de Markov violée |
| R1-W2 | coût tabulaire sur 3 bins de charge, trop grossier pour la queue URLLC |
| R2-W1 | pas de 5 s, incompatible avec Near-RT (10 ms – 1 s) |
| R2-W2 | données statiques : la config est constante pendant toute la réservation |
| R3-W1 | une seule baseline (BC) |
| R3-W2 | nouveauté incrémentale |
| R3-W3 | rédaction, référence manquante, style |
| — | point de l'audit hors reviewers |

**Provenance des chiffres.**
- Aucun chiffre n'est calculé ici : tous sont repris d'un rapport de `docs/`, avec le nom du rapport en source.
- Les chiffres qui ne se retrouvent dans aucun rapport sont listés en §9, et marqués **[non retrouvé]** dans le texte.
- Les chiffres du notebook (λ = 12,22, FQE, Table II) sont des **sorties enregistrées, non reproduites**.
- Ce registre n'a lu ni `data/`, ni `tests/`, ni `results/`. Il s'appuie sur les rapports, y compris `docs/e12_rapport_final.md` (sortie brute de la lecture finale du test, commit `c58d6e5`).

**Commits utiles.**

| étape | commits |
|---|---|
| audit | `fbe7a53` |
| phase 0 (D1-D5) | `5178c8d` |
| phase 1 | `1dba46b` |
| phase 2 | `eb3aaef` |
| D6 | `2ce8774` |
| D7 | `5f4438e` |
| D8 | `b9fcb92` |
| E1 | `7ef80eb` |
| E2 | `b2f9405` (code), `8f8a039` (rapport) |
| E11 | `7e9be78` (gel), `3779a06`, `ecb624d` |
| E12 | `2cf749e` (attente), `0387dbc` (gel), `0fa5787`, `c58d6e5` |
| E13a | `ed677b6`, `fc32130`, `8ee84f5` |
| E13a2 | `c699b57` (protocole), `e2e89b6` (run), `7652a34` |
| E13b | `f77bff6`, `6785e37`, `85e39ab` |
| E13c | `15d2664` |
| E13d | `556bcf2` (protocole), `5f16038` (run), `41896a3`, `ff850ac` |

---

## 1. Audit D1 à D8 (données et conception expérimentale)

### 1.1 Configuration, horloges, fenêtres, fuite d'action, cellules de coût (D1-D5, `decision_memo.md`)

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| D1-a | La configuration (PRB, scheduler, slicing, puissance) ne change dans aucune des 1 116 réservations (0/1 116) ; le contenu des fichiers concorde avec le chemin (0 désaccord). | [V] | decision_memo D1, `5178c8d` | Constat sur ce dataset. Il ne dit rien de ce que la plateforme permettrait. La charge varie dans une réservation (script MGEN, changement toutes les 60 s), mais de façon scriptée et exogène. | R2-W2, R1-W1 |
| D1-b | Le slicing 5 est « pas de slicing » (309 réservations avec `slicing_enabled=0`, `slice_prb=0`) et il est exclu des 8 actions. | [V] | decision_memo D1 | Le papier le présente comme « 50 PRB eMBB » : écart non expliqué, à demander aux auteurs du dataset. | — |
| D1-c | Il n'existe aucune transition avec changement d'action ; Q(s, a ≠ a_loguée) n'est identifiée que par des différences **entre** réservations. | [V] (conséquence de D1-a) | decision_memo, audit §2, `dataset_notes.md` | Le dataset ne permet pas d'identifier un contrôle séquentiel. Voir §8. | R2-W2, R1-W1 |
| D2-a | eNB, BS-UE et MGEN partagent une base de temps UTC. Décalage typique inférieur à 1 s (premier BS-UE moins premier eNB : médiane 0,49 s). | [V] | decision_memo D2 | Quelques valeurs aberrantes : 12/1 096 réservations avec écart > 5 s. L'horloge absolue des UE est **estimée** (`ue_metrics` n'a pas d'horloge absolue) : [H]. | R2-W1 |
| D2-b | Le notebook sommait des fenêtres eMBB décalées par UE : les premiers rows BS des UE diffèrent de plus de 5 s dans 532/1 101 réservations (48 %). Phase 1 impose une origine `t0` commune. | [V] | decision_memo D2 ; phase1_pipeline | La nouvelle fenêtre n'est pas validée de façon indépendante. Estimation de l'origine UE : décalage médian 0,51 s, p5 −1,7 s, p95 +3,8 s, 124 fichiers au-delà de ±5 s ([H], phase 1). | R2-W1 |
| D2-c | Le pipeline canonique redonne 706 réservations utilisables, comme le notebook, mais 224 193 lignes contre 225 313 (−1 120, soit 0,5 %). | [V] comptes ; [Q] cause | phase1_pipeline | Origine de l'écart (fenêtres avant `t0`, fenêtres sans eNB, nouvel alignement eMBB) non attribuée. | — |
| D3-a | 46/706 réservations (6,5 %) ont des trous de fenêtres (103 événements ; longueur médiane 11, max 204). Phase 1 les traite en épisodes séparés (817 épisodes). | [V] | decision_memo D3 ; phase1_pipeline | Cause probable des trous : fenêtres sans paquet URLLC ([H]). | — |
| D4-a | **L'état laisse deviner l'action loguée.** Avec les seuls lags : 30,5-32,8 % de précision sur les 8 actions (base 12,4 %), 55,5-55,6 % sur le niveau PRB (base 24,5 %). Avec les 12 variables : 35,6-42,3 % ; PRB 58,9-61,1 %. | [V] | decision_memo D4 | IC par bootstrap de réservations [0,25 ; 0,38] pour les lags. Mesuré sur l'état à 12 dimensions du notebook. Sur l'état à 10 dimensions de la phase 1 : seuls 20,5 % pour radio+charge et 71 % pour le scheduler (boosting) sont rapportés ; la re-mesure complète n'est pas faite. | R1-W1, R2-W2 |
| D4-b | Le scheduler est lisible à 71 % par un modèle non linéaire à partir de la radio courante et de la charge (linéaire : 55 %). | [V] | decision_memo D4 | Voir D4-a. | R2-W2 |
| D4-c | Ajouter a_{t-1} à l'état n'apporterait presque rien : l'action est constante dans la réservation, donc déjà devinable. | [H] (argument de l'audit, non testé par une expérience) | audit §6 R1-W1 ; decision_memo D4 | À ne présenter que comme argument, pas comme résultat. | R1-W1 |
| D4-d | Re-vérification de la fuite sur l'état à 10 dimensions de la phase 1 (lags uniquement). | [Q] non faite | phase1 « Next » ; phase2 finding 6 | Aucun rapport ne la contient. | R1-W1 |
| D5-a | Les cellules de coût (action × bin de charge) sont bien dotées en fenêtres mais pauvres en réservations. Les IC par réservation sont 6 à 9 fois plus larges que les IC naïfs par fenêtre (largeur médiane 0,044-0,059 contre 0,006-0,010). | [V] limite | decision_memo D5 | Bootstrap par réservation, B = 2 000, seed 0. | R1-W2 |
| D5-b | Entre 47 % et 63 % des cellules ont un IC qui contient le budget 0,03 (15/24 en train à 3 bins ; 18/32 à 4 bins). | [V] limite | decision_memo D5 | Selon le sous-ensemble et le nombre de bins. | R1-W2 |
| D5-c | La charge est presque une covariable de réservation, et elle est partiellement confondue avec l'action et le cluster (`nof_ue` moyen 4,58 / 5,80 / 5,34 pour cl1 / cl2 / cl3). | [V] | decision_memo D5 | — | R1-W2 |
| D5-d | Cellule (30 PRB, RR, charge basse) : 0,142 [0,005 ; 0,227] ici, 0,147 dans le notebook. | [Q] | decision_memo D5 | Convention de bords des bins probable, non vérifiée. | R1-W2 |

### 1.2 Scripts de trafic partagés (D6, `d6_shared_scripts.md`)

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| D6-a | 19 scripts distincts, aucun partagé entre clusters, donc aucun entre train et test. | [V] | D6 §1, `2ce8774` | — | R2-W2 |
| D6-b | Le test est de fait **un seul script** : c40f2fe7 pèse 177/196 réservations utilisables (90 %). Le train tient sur 2 scripts : 478/510 (94 %). | [V] limite | D6 §4 | Le nombre de réservations n'est pas l'effectif effectif pour la généralisation. Unité indépendante ≈ le script : [H] fortement soutenue. | R3-W2 (portée), R2-W2 |
| D6-c | Seuls 3 scripts couvrent les 8 actions avec réservations utilisables : a908e4cc (cluster 2), a53521b2 (cluster 3), c40f2fe7 (cluster 1 = test). | [V] | D6 §1 ; dataset_notes | Les 8 autres scripts ont 1 à 5 configurations sur 8. | R2-W2 |
| D6-d | Le bruit entre répétitions d'un même script est du même ordre que le budget : sd du coût moyen par réservation 0,002 à 0,22 pour des moyennes de 0,002 à 0,23. | [V] | D6 §2 | Trois scripts dominants. | R1-W2 |
| D6-e | Le `t0` du pipeline est déjà aligné sur le temps du script à environ 1 s (fenêtre 0 à 71,2 s, premier ON à 70 s) ; réaligner ne change pas les différences entre actions (écart absolu médian 0,001 Mbps ; 0,000 sur le coût). | [V] | D6 §3 | 621 réservations avec origine acceptée. 85 rejetées (75 avec un seul flux URLLC, 10 avec flux discordants). L'alignement repose sur des hypothèses ([H]). | R2-W1 |
| D6-f | Le trafic émis est en boucle ouverte : les 3 705 lignes `ON` des 19 scripts sont `UDP … PERIODIC`. | [V] code ; [H] que le débit émis soit identique entre réservations | D6 « Hypothèses » | Que `nof_ue` et le débit reçu ne dépendent pas de l'action est **non vérifié** (voir D7-c). | R2-W2 |

### 1.3 Effet scheduler et ordre d'exécution (D7, `d7_scheduler_order.md` ; D8, `d8_chronology.md`)

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| D7-a | À slicing fixé, PF − RR sur le **coût** est positif dans les 12 couples (script, slicing), de +0,04 à +0,20 (1,4 à 6,7 fois le budget). Sur le **reward**, le signe est variable (négatif dans 9 couples sur 12) et aucun effet n'est distinguable de 0. | [V] | D7 §2, `5f4438e` | SE naïves entre réservations ([H], sous-estiment l'incertitude). Le coût PF − RR mélange le scheduler et le bloc d'exécution (D7-b). | R2-W2 |
| D7-b | Dans les 12 couples, PF et RR occupent des blocs d'identifiants disjoints (une seule bascule). Le scheduler n'est donc pas séparable du moment d'exécution. | [V] | D7 §3 ; D8 §3 | Le test moitié précoce/tardive ne change le signe que dans 1 cas sur 24 (reward). Cela ne lève pas la confusion. La dérive du coût PF dans le bloc est du même ordre que l'effet scheduler pour a908e4cc. | R2-W2 |
| D7-c | Sur les 8 actions, `nof_ue` et le débit URLLC reçu dépendent de l'action (p ≤ 0,014 ; η² 0,11-0,18 et 0,30-0,57). À scheduler fixé, aucune dépendance détectée (p 0,10-0,96). | [V] pour l'effet sur 8 actions ; [H] pour l'absence à scheduler fixé (faible puissance, PF 4-29 répétitions) | D7 §4 | Le bin de charge n'est donc pas démontré exogène à l'action, ce qui concerne directement le DM (parts de bins `p_b`). | R1-W2, R2-W2 |
| D8-a | L'ordre des identifiants est l'ordre chronologique (Spearman 1,000 ; 5 inversions de ≤ 17 min). | [V] | D8 §2, `b9fcb92` | `time` supposé en epoch ms UTC fiable ([H]). | — |
| D8-b | Aucun des 17 couples (script, slicing) n'a PF et RR entrelacés. Pour a908e4cc et a53521b2, les blocs sont à ≈ 8 jours d'écart ; pour c40f2fe7 (test), à ≈ 13 h (PF ≈ 10 j, RR ≈ 1,5 j). | [V] | D8 §3 | Cause du délai non documentée ([Q]). | R2-W2 |
| D8-c | Sur les paires PF/RR les plus proches, le coût PF − RR garde son signe (12/12, 12/12, 8/8 cellules à 100/50/25 % des paires) et son ordre de grandeur. | [V] | D8 §4 | Pour 2 scripts sur 3, les « paires proches » sont encore à ≈ 8-9 jours. Seul c40f2fe7 a des paires proches (16-24 h). Ce contrôle ne réfute pas la confusion. | R2-W2 |
| D8-d | La meilleure coupure unique du coût tombe exactement à la bascule PF → RR pour les 3 scripts. Aucune coupure significative à l'intérieur d'un bloc. | [V] | D8 §5 | Une dérive lente produit aussi une coupure (rapport SSE tendance/marche 1,08-1,18) : [H]. | R2-W2 |

### 1.4 Constats de l'audit initial (`audit_report.md`)

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| AU-a | Le notebook mettait la récompense de la fenêtre courante (`reward_embb_Mbps`) et `urllc_p50` dans l'état. Phase 1 retire ces deux colonnes courantes et ne garde que leurs lags (10 dimensions). | [V] code | audit §3 ; phase1_pipeline | D4 montre que retirer ces colonnes ne supprime pas la fuite de l'action. | R1-W1 |
| AU-b | Le notebook entraînait Safe-CQL sur une table de coût à 3 bins mais évaluait le « Tabular OPE » sur une table à 4 bins ; 3 tables de coût coexistent. Le pipeline canonique en a une (3 bins `[0 ; 3,5 ; 5,5 ; 8,1]`, repli sous 20 fenêtres). | [V] code | audit §4 ; phase1_pipeline | Le repli à 20 fenêtres n'a jamais été déclenché en phase 1. | R1-W2 |
| AU-c | Le « Tabular OPE » n'est pas une évaluation hors échantillon (tables ajustées sur le train). | [V] code | audit §4 ; phase2 finding 3 | Pour table-greedy et Safe-CQL, l'estimateur DM est en partie circulaire. | R3-W1 |
| AU-d | « 2,25 × 10⁵ transitions d'entraînement » est faux : le train a 163 960 transitions (notebook) ou 162 490 (pipeline canonique) ; 225 313 inclut le test. | [V] | audit §7.3 ; phase1_pipeline | — | R3-W3 |
| AU-e | Le FQE du notebook ne fait pas l'amorçage avec la politique évaluée (action d'amorçage tirée du réseau FQE lui-même ; unités différentes ; pas de réseau cible). Aucune correction n'a été faite dans `src/`. | [V] code notebook ; correction **non faite** | audit §5 | Les chiffres FQE du papier ne peuvent pas être repris. Aucun FQE ni OPE à poids d'importance dans `src/` (phase 2 « Limits »). | — |
| AU-f | Le λ « converge près de 12,9 » est contredit par la trace enregistrée (λ = 12,22 à l'epoch 99, toujours croissant, coût 0,032 > 0,03). | [V] sortie enregistrée, **non reproduite** | audit §4 | Voir §3 pour les diagnostics par script. | — |
| AU-g | La référence [15] (outils de test de réseau smart grid) pour MGEN, et la référence « [?] » en Sec. II, n'ont pas été corrigées. | [Q] | audit §6 R3-W3 | Aucun manuscrit révisé n'existe dans ce dépôt. | R3-W3 |

---

## 2. Évaluation E12 par script (lecture finale du test)

**Procédure.** `docs/e12_attente_pre_test.md` ; gel `0387dbc` ; rapport `c58d6e5` ; sortie brute dans `docs/e12_rapport_final.md`.

Procédure [V] :
- Configurations figées avant la lecture : `safe_cql_a0.1` (principal), `cql_a0.1`, `safe_cql_a0.5`, `cql_a0.5`, `safe_cql_a0.1_g0`, `iql`, plus 4 baselines.
- Train complet (clusters 2-3), seeds 0-4, 100 epochs, politique = dernière epoch, aucune convergence exigée.
- Tables DM ajustées sur le train. Bootstrap par réservation dans chaque script, B = 2 000, seed 0.

Statut du test :
- C'est la **seconde** lecture du test, pas une lecture aveugle. La phase 2 avait déjà lu le test avec CQL/Safe-CQL à α = 0,5, IQL et les baselines.
- Seuls α = 0,1, la variante γ = 0 et la ventilation par script sont nouveaux.
- Les attentes (a) à (e) n'étaient donc pas aveugles.
- Les scripts D6-D8 avaient aussi examiné c40f2fe7 (descriptif, sans réglage).

Les trois scripts du test sont c40f2fe7 (177 réservations utilisables), 1dd38082 et 3e1a4369. Les deux derniers se partagent les 19 autres réservations (196 − 177, **dérivé**). Leurs effectifs exacts ne sont dans aucun rapport lu : **[non retrouvé]**.

Légende des chiffres : coûts DM suivis de leur IC 95 % bootstrap [bas ; haut]. « Appariée » = estimateur matched, couverture entre parenthèses.

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| E12-a | **Coût DM, c40f2fe7.** Safe-CQL α = 0,1 : 0,0315 [0,0290 ; 0,0344]. Safe-CQL α = 0,5 : 0,0305 [0,0272 ; 0,0342]. CQL α = 0,1 : 0,0551 [0,0491 ; 0,0612]. CQL α = 0,5 : 0,0548. IQL : 0,0582 [0,0516 ; 0,0649]. | [V] | e12_rapport_final | DM sur tables d'entraînement. Le coût de Safe-CQL est en partie circulaire (il est construit sur la même table). Pas d'IC sur la différence appariée (CIs non apparié, mesure la dispersion des réservations, pas celle des scripts). Seed std non retrouvé. Convention des IC pour les lignes RL = moyenne des bornes par seed (phase 2), supposée identique en E12 : [H]. | R3-W1, R3-W2 |
| E12-b | **Coût DM, ensemble du test (« pooled »).** Safe-CQL 0,0310 [0,0288 ; 0,0335] (α = 0,1) et 0,0295 [0,0266 ; 0,0327] (α = 0,5). CQL 0,0536 / 0,0533. IQL 0,0569 [0,0512 ; 0,0630]. | [V] | e12_rapport_final ; phase2 (même 0,0295 pour α = 0,5) | « Pooled » ≈ 90 % un seul script. À ne pas lire comme un résultat sur plusieurs scripts. | R3-W1 |
| E12-c | **Ordre des coûts, estimateur apparié.** c40f2fe7 : Safe-CQL 0,0274 (α = 0,1) / 0,0357 (α = 0,5) ; CQL 0,0415 / 0,0436 ; IQL 0,0452. Couvertures 33,5-40,3 % (< 50 % pour tous les agents). Même ordre que le DM. | [V] | e12_rapport_final (attente (c) vérifiée) | Couverture partielle : le sous-ensemble dépend de la politique. IC des coûts appariés : **[non retrouvé]**. | R3-W1 |
| E12-d | **Reward DM, c40f2fe7.** Les agents sont proches : 6,73 à 7,12 Mbps (Safe-CQL α = 0,1 : 6,968 ; CQL α = 0,1 : 7,117 ; IQL : 6,787). | [V] | e12_rapport_final (attente (a)) | Le seuil « proche » (≤ 10 %) est arbitraire et fixé avant. | R3-W1 |
| E12-e | **Aucune politique n'est démontrée sûre sur c40f2fe7.** La borne haute de l'IC 95 % dépasse d = 0,03 pour Safe-CQL (0,0344 / 0,0342 / 0,0325 selon la variante) ; pour always-RR (0,0319) ; et le coût apparié de table-greedy (0,0310) dépasse d. Le critère gelé « démontrée sûre » est faux pour les 10 politiques. | [V] | e12_rapport_final (attente (e)) | Critère : borne haute ≤ d à la fois en DM et en apparié. | R3-W1 |
| E12-f | **Table-greedy, c40f2fe7 :** reward DM 9,069, coût DM 0,0217 [0,0204 ; 0,0230], coût apparié 0,0310, couverture appariée 9,5 %. Il est au-dessus des agents en reward DM. | [V] chiffres ; [H] interprétation | e12_rapport_final ; phase2 finding 3 | Chiffre le plus circulaire (table du train, DM). Couverture appariée de 9,5 % seulement. Voir §8. | R3-W1 |
| E12-g | **always-RR, c40f2fe7 :** reward DM 7,027, coût DM 0,0287 [0,0258 ; 0,0319], coût apparié 0,0216. Il est au niveau de Safe-CQL α = 0,1 (6,968 ; 0,0315). **always-PF :** 6,688 ; 0,1294 [0,1188 ; 0,1400]. | [V] | e12_rapport_final | Ces baselines lisent l'action loguée : conserver le niveau PRB loggé et fixer le scheduler. Ce ne sont pas des politiques déployables. | R3-W1 |
| E12-h | **best-fixed :** reward 2,734, coût DM 0,0140, couverture 13,0 % (c40f2fe7). | [V] | e12_rapport_final ; phase2 finding 4 | Infaisable en validation en phase 2 (plus bas coût 0,0315 > d) : repli sur l'action de plus bas coût. | R3-W1 |
| E12-i | **Ablation γ = 0 :** sur c40f2fe7 pas d'amélioration nette (coût −0,0029, reward −0,195 Mbps par rapport à γ = 0,7). Sur l'ensemble, le critère « amélioration nette » est **satisfait** (coût −0,0032, reward −0,224). L'attente (d) est donc fausse sur l'ensemble. | [V] selon le critère gelé | e12_rapport_final (« holds »: false) | Le critère (2 écarts-types entre seeds) est arbitraire. Écarts-types entre seeds **[non retrouvé]**. On rapporte tel quel, sans réécrire l'attente. | — |
| E12-j | **Autres scripts du test.** Les coûts de 1dd38082 et 3e1a4369 sont rapportés mais très dispersés (ex. always-RR sur 3e1a4369 : 0,0241 [0,0108 ; 0,0374]). Table-greedy y a 1,2 % de couverture appariée sur 3e1a4369. | [V] chiffres ; [H] que les effectifs soient très faibles | e12_rapport_final | Effectifs en réservations : **[non retrouvé]**. À ne pas utiliser pour des affirmations par script. | R3-W2 |
| E12-k | **Statut de la lecture :** seconde lecture ; configurations, critères et seuils figés avant ; tout point faux est rapporté tel quel. | [V] | e12_attente_pre_test ; commits `2cf749e`, `0387dbc`, `0fa5787` | Les agrégats du test vus en E1 (parts de bins, nombre d'actions) sont consignés. | — |

---

## 3. Diagnostic de λ (E1, E2, E11)

**Portée commune.**
- Train seul, scripts A = a908e4cc et B = a53521b2.
- Toutes les valeurs sont **lues dans des tables** (estimateur DM), pas mesurées.
- Le test n'est pas lu (`test_split_read: false`).
- Budget d = 0,03.

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| E1-a | Le budget d = 0,03 est faisable sur les trois tables (A, B, TRAIN). Coût minimal atteignable : 0,0211 / 0,0112 / 0,0182. | [V] | e1_lp_diagnostic, `7ef80eb` | Bootstrap : faisabilité 97,9 % (A), 100 % (B), 100 % (TRAIN). Le coût minimal de A dépasse d dans 2,1 % des rééchantillons. | R1-W2 |
| E1-b | Le multiplicateur optimal de la table est petit : λ* = 0 (A), 0,065 (B), 0,244 (TRAIN), contre 12,22 enregistré dans le notebook (≈ 50 fois plus). Avec un argmax sur la table, tout λ ≥ 0,245 donne un coût ≤ 0,0297. | [V] pour la table ; le 12,22 est **non reproduit** | e1_lp_diagnostic | La divergence de λ ne vient donc pas de la table de coût. | — |
| E1-c | λ* est mal déterminé : IC de 0 à environ 1-3 (A, B) ; contrainte active dans 36-74 % des rééchantillons. Une valeur ponctuelle de λ* ne doit pas être présentée comme précise. | [V] limite | e1_lp_diagnostic | IC conditionnels à un script ; les réservations d'un script ne sont pas indépendantes. | R1-W2 |
| E1-d | Randomiser un seul bin ne rapporte que 0,1 % de reward (table) : un argmax déterministe est presque aussi bon que le LP. Le coût d'un argmax déterministe peut atteindre 0,0286 (B) et 0,0297 (TRAIN), juste sous d. | [V] | e1_lp_diagnostic | « Aucun λ ne donne exactement 0,03 » est vrai, mais l'écart (≤ 0,0014) n'explique pas λ = 12. | — |
| E1-e | Les récompenses LP sont biaisées à la hausse (malédiction du gagnant sur cellules bruitées à 2-6 réservations). | [H] | e1_lp_diagnostic, limite 2 | Le bootstrap le montre en partie, ne le corrige pas. | R1-W2 |
| E2-a | Aucun des 60 runs (6 variantes × 2 plis × 5 seeds) ne satisfait le critère de convergence gelé ; la condition « coût dans la bande [0,9 d ; d] » est satisfaite 0 fois sur 60. | [V] | e2_safe_cql_diagnostic, `b2f9405`/`8f8a039` | Critère figé avant le run. La bande est peut-être trop étroite par rapport au bruit epoch à epoch : [Q]. | — |
| E2-b | Avec la configuration actuelle (γ = 0,7, α = 0,5, 100 epochs), λ final = 1,935 ± 0,045 (A) et 0,283 ± 0,011 (B) ; coût greedy 0,0358 (A) et 0,0311 (B). En 300 epochs : λ = 5,838 (A), 0,906 (B), toujours en hausse. | [V] | e2 | Entraînement sur **un pli** (≈ 73-80 k fenêtres), pas sur tout le train : le λ = 12,22 du notebook n'est pas reproduit. | — |
| E2-c | γ = 0 ne résout pas la dérive de λ : λ final 3,112 (A), 0,595 (B), coût greedy 0,0403 (A), 0,0320 (B). | [V] | e2 | La conclusion « γ = 0 est la cause » n'est donc **pas** soutenue (voir aussi E12-i). | — |
| E2-d | Avec α ≥ 0,5, la Q-net reproduit l'action loguée sur 64-82 % des fenêtres du pli ; cette part baisse avec α (α = 0,1 : 61-63 % ; α = 0 : 20-32 %). | [V] chiffres ; [H] que ce soit le conservatisme CQL qui ramène vers l'action loguée | e2 | Le terme α change aussi l'échelle des Q : pas de test causal. Les actions loguées sont prédictibles (D4). | R2-W2 |
| E2-e | Les variantes α = 0,1 et α = 0 donnent des coûts greedy plus proches de d (A : 0,0314 / 0,0303 ; B : 0,0306 / 0,0309) avec un λ plus petit. | [V] | e2 | Valeurs de diagnostic, non réglées. En échantillon : tables et fenêtres du pli d'entraînement. | — |
| E11-a | **Aucun α n'est faisable.** Pour tout α de la grille, le coût de validation moyen dépasse d dans le sens B→A (0,0405 à 0,0504). Statut enregistré : `infeasible: no configuration is feasible`. | [V] | e11_alpha_grid, `7e9be78`/`3779a06` | Deux scripts seulement ; 60/60 runs terminés ; 0/60 convergés selon le critère E2. | R3-W1 |
| E11-b | α = 0,1 est retenu **par le repli**, pas sur ses mérites. α = 0,05, 0,1 et 0,2 sont à égalité en pratique (coût de validation moyen 0,03470 / 0,03440 / 0,03464), l'écart entre seeds étant de 0,0010 à 0,0021. | [V] | e11_alpha_grid | Règle de sélection gelée avant la grille. | — |
| E11-c | Les deux sens évoluent en sens opposé avec α : en A→B le coût baisse (0,0329 → 0,0227 à α = 0,2) et passe sous d dès α = 0,02 ; en B→A il monte (0,0405 → 0,0504). Le reward de validation baisse dans les deux sens (9,12 → 7,86 ; 10,06 → 7,90). | [V] | e11_alpha_grid | Moyenner les deux sens (règle de repli) masque cette opposition. | — |
| E11-d | Critère de convergence révisé (E11) : R1 (pente de λ) échoue partout ; le nombre de runs convergés égale le nombre de runs passant R1. À α bas en B→A, 5/5 passent ; à α = 0,2 et 0,5 : 0/5. | [V] | e11_alpha_grid | `BAND_TOL` = 0,0025 est calibrée sur les 60 runs d'E2 : critère à lire comme **descriptif**. | — |
| E11-e | Le reward de validation de la Q-net est inférieur à celui d'un table-greedy transféré : A→B 8,056 contre 10,352 ; B→A 8,321 contre 11,370 (α = 0,1). En B→A, la Q-net est moins bonne sur les deux axes (coût 0,0454 contre 0,0303). | [V] | e11_alpha_grid | Le texte du rapport écrit « Q-nets 0,040 à 0,047 » alors que le tableau va jusqu'à 0,0504 (α = 0,5) : écart à clarifier avant citation. | R3-W1 |

---

## 4. Transfert entre scripts

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| TR-a | La politique LP optimale construite sur A (`7-7-6`) viole le budget lue dans les tables de B : coût 0,052 contre 0,030, reward 10,35. Construite sur B et lue dans A : 0,0300 (LP) ou 0,0303 (meilleur déterministe). | [V] | e1_lp_diagnostic ; e11 (« table-greedy transféré ») | Valeurs de table (DM), 2 scripts, IC conditionnels. | R2-W2 |
| TR-b | Le table-greedy transféré dépasse d en A→B (0,0520). En B→A il est à 0,0303, soit 1 % de d : « viole d » n'y est **pas établi**. | [V] en A→B ; [H] en B→A | e11 (correctif `ecb624d`) | Intervalle sur 0,0303 : non calculé en E11 ; voir TR-e. | — |
| TR-c | Entraînée sur B, la Q-net a un coût greedy ≈ 0,031 sur les tables de B mais 0,050-0,062 lu dans les tables de A. Entraînée sur A, le coût lu dans B (0,023-0,031) est plus bas que le coût greedy propre. | [V] | e2 (coûts croisés) | Avec 2 scripts, on ne sépare pas « propriété de la paire » et « propriété générale ». | R2-W2 |
| TR-d | « La sécurité ne se transfère pas entre scripts » : vérifiée dans **un** sens (A→B, 0,052 / 0,0520), pas dans l'autre (B→A, 0,030). | [V] sens A→B ; [H] pour la généralité | e1 ; e11 | Formulation sûre : « sur deux scripts, la contrainte respectée sur les tables d'un script a été violée sur l'autre dans un sens et respectée à 1 % près dans l'autre ». | R2-W2 |
| TR-e | Le coût transféré (table-greedy, DM) a un IC 95 % de [0,0147 ; 0,0523] en B→A (3 niveaux actuels, 0,0303) et [0,0146 ; 0,0830] en A→B (0,0520) ; la part de réplicats ≤ d est de 0,53 (B→A) et 0,30 (A→B). | [V] | e13a2_resultats | Conditionnel aux deux scripts, réservations supposées échangeables ; ne mesure pas la variabilité entre scripts. E13a donne des valeurs très proches pour la même ligne (flux aléatoire différent : [0,0147 ; 0,0821], 0,32 et [0,0149 ; 0,0522], 0,56). | — |
| TR-f | L'attente E12 « ni Safe-CQL ni table-greedy ne respectent d dans les deux sens » est **plus forte** que ce qu'E11 établit pour table-greedy. Sur le test, table-greedy a un coût DM de 0,0217 (c40f2fe7) mais un coût apparié de 0,0310 (couverture 9,5 %). | [V] pour la formulation des attentes ; [H] pour table-greedy sur le test | e12_attente_pre_test ; e12_rapport_final | Les deux estimateurs divergent pour table-greedy ; aucun IC apparié retrouvé. | — |

---

## 5. E13a et E13a2 : niveaux de charge (R1-W2)

**Statut.**
- Analyses descriptives, train seul, 2 scripts, DM, `test_split_read: false`.
- Aucun nombre de niveaux n'est choisi, classé ni recommandé.
- La configuration principale du papier (3 niveaux, fenêtre de 5 s) reste celle qui a été figée.
- Aucune troisième lecture du test n'est motivée.

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| E13a-a | `nof_ue` est entier pour 98,3 % (A) et 98,0 % (B) des fenêtres. L'hypothèse de départ « continu » était fausse. | [V] | e13a_niveaux_charge, `ed677b6` | — | R1-W2 |
| E13a-b | Dans A, les quantiles de 20 à 80 % valent tous 6,0 : k = 2, 3, 4, 5 donnent **2 niveaux** en A→B (même partition). En B→A : k = 2 → 2 niveaux ; k = 3, 4 → 3 ; k = 5 → 4. La question « 4 ou 5 niveaux ? » n'est donc pas traitée par E13a. | [V] limite | e13a | Les différences entre les lignes A→B k2…k5 sont du bruit Monte-Carlo. | R1-W2 |
| E13a2-a | Avec des arêtes entières (protocole gelé `c699b57`, exécution unique `e2e89b6`), A atteint 3 niveaux au plus (k = 3, 4, 5 identiques) et B 4 niveaux ; `int_each` donne 7 niveaux (A) et 8 (B). Garde de reproduction : PASS (0,0520 / 0,0303). | [V] | e13a2_resultats, `7652a34` | 4-5 niveaux ne sont testés qu'en B→A (4 niveaux). Les arêtes diffèrent entre sens. | R1-W2 |
| E13a2-b | Coût transféré selon le jeu d'arêtes : A→B de 0,0448 à 0,0520 (6 jeux) ; B→A de 0,0303 à 0,0357. En E13a (jeux à quantiles) : A→B de 0,0256 à 0,0520 ; B→A de 0,0295 à 0,0357. | [V] | e13a ; e13a2_resultats | Valeurs de table. | R1-W2 |
| E13a2-c | **Les IC bootstrap du coût transféré contiennent d dans toutes les lignes** (10 en E13a, 12 en E13a2), largeur 0,034-0,068. Aucun écart entre jeux n'est distinguable du bruit ; aucun classement n'en est tiré. | [V] | e13a ; e13a2_resultats | Conditionnel aux scripts ; arêtes et `r_scale` fixés dans le bootstrap. | R1-W2 |
| E13a2-d | Deux partitions à 2 niveaux donnent des coûts très différents en A→B : arête 6,0 → 0,0256 (E13a) ; arête 5,0 → 0,0463 (E13a2). Le résultat dépend du placement des arêtes, et pas de façon monotone avec k. | [V] (comparaison des deux rapports) | e13a ; e13a2_resultats | Non testé comme hypothèse : constat de deux lignes. | R1-W2 |
| E13a2-e | Part des cellules (action × niveau) dont l'IC contient d : 0,38-0,67 (E13a) et 0,52-0,67 (E13a2). Avec `int_each`, 9 cellules sources sans IC en A→B et 17 cellules de validation sans IC en B→A. | [V] | e13a ; e13a2_resultats | Dénominateurs 16 à 64. | R1-W2 |
| E13a2-f | En B→A `int_each`, table-greedy choisit l'action 0 au niveau 0 sur une cellule de 3 réservations (487 fenêtres, coût 0,00035). | [V] chiffres ; [H] que ce coût soit fiable | e13a2_resultats | Illustration du risque d'un cut fin. | R1-W2 |
| R1W2-no | Un critique continu (non binné) répondant à la remarque R1-W2, et une mesure de queue (`urllc_p99` est dans le parquet) : **aucune analyse ni rapport n'existe**. | [Q] non fait | e13a « Limites » 5 ; audit §6 | Ne pas annoncer de résultat sur la queue. | R1-W2 |

---

## 6. E13b : échantillonnage réel et limites de fenêtre (R2-W1)

**Portée.**
- 12 réservations du **train** (aucune du test), colonnes d'horodatage seulement, aucune valeur de KPM ni latence lue.
- Échantillon choisi par rang chronologique dans chaque cellule (cluster 2/3 × scheduler).
- La première exécution (`eab6758`) poolait par erreur les fichiers eMBB ; corrigée (`66d6cd3`) avant interprétation ; seuls les résultats corrigés sont rapportés.

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| E13b-a | Le pas réel des flux KPM est **0,25 s** (4 Hz) : `enb_metrics` 12/12, `ue_metrics` 96/96 fichiers. Une fenêtre de 5 s contient ≈ 20 échantillons. | [V] | e13b_pas_echantillonnage, `f77bff6` | 12 réservations : représentativité non garantie ([H]). | R2-W1 |
| E13b-b | Pour le reward, la radio et `nof_ue`, des fenêtres de 1, 2 et 2,5 s sont possibles (≥ 3 échantillons dans ≥ 99 % des fenêtres) ; 0,5 s et en dessous ne le sont pas. | [V] | e13b | Seuil « ≥ 3 échantillons » : choix de l'analyste. | R2-W1 |
| E13b-c | Pour le coût URLLC (10 paquets/s par UE, 2 à 3 UE actifs), le critère « ≥ 34 paquets dans 99 % des fenêtres » est atteint à 5 s pour 7 réservations sur 12, à 2,5 s pour 4/12, à 2 s pour 3/12, à ≤ 1 s pour 0/12. | [V] | e13b | Le seuil de 34 paquets est un choix (1/34 < d). Même à 5 s, 5 réservations sur 12 n'atteignent pas le critère (résolution jusqu'à 1/50). | R2-W1, R1-W2 |
| E13b-d | La plage Near-RT (10 ms à 1 s) n'est atteignable avec ces fichiers sur aucun des deux signaux. | [V] pour l'échantillonnage ; la lecture O-RAN vient de la review, non vérifiée ici | e13b | À dire comme limite de données mesurée, pas comme réponse sur le fond Near-RT. | R2-W1 |
| E13b-e | **Aucune sensibilité à la fenêtre n'a été lancée** (décision de l'auteur) : 5 s est la seule fenêtre évaluée. | [V] | e13b « Décision » | Ne rien affirmer sur la robustesse à la fenêtre. | R2-W1 |
| E13b-f | L'alignement d'horloge UE (p5 −1,7 s, p95 +3,8 s, 124 fichiers au-delà de ±5 s) borne en pratique les fenêtres plus fines que quelques secondes. | [H] (valeurs de phase 1, non re-mesurées en E13b) | phase1 ; e13b | Estimation non validée de façon indépendante. | R2-W1 |
| E13b-g | `Sent Time` (mgen) a des sauts énormes (écart max de 31 507 s sur les paquets poolés des 12 réservations) ; le pipeline utilise `Received Time` pour le fenêtrage (écart max 2,34 s). | [V] | e13b ; dataset_notes (E13c : 423/510 réservations avec saut > 3 600 s sur `Sent Time`, 8/510 sur `Received Time`) | Cause non examinée [Q]. Le test n'a pas été lu pour E13c. | R2-W1 |

---

## 7. E13d : filtre de latence sur le coût URLLC (train seul)

**Portée.**
- 510 réservations du train ; protocole fixé avant lecture (`556bcf2`) ; exécution `5f16038`.
- Le test n'est pas lu. Aucun entraînement : inférence sur les checkpoints E12.
- Gardes G1 (coûts par fenêtre recalculés) et G2 (table de coût) : écart maximal **0** [V].

| id | énoncé précis | statut | source | limites | reviewer |
|---|---|---|---|---|---|
| E13d-a | Le pipeline garde les paquets avec `0 ≤ lat < 20 000 ms` et calcule la violation (`lat > 20 ms`) sur les gardés seulement. Les paquets écartés ne sont ni au numérateur ni au dénominateur. | [V] code | e13d_protocole, e13d_filtre_latence | — | R1-W2 |
| E13d-b | Sur 20 619 886 paquets lus (train), **840** sont écartés (latence ≥ 20 000 ms), 0 latence négative, 0 non finie. 448/510 réservations ont ≥ 1 paquet écarté (maximum 4 par réservation) ; 62 n'en ont aucun. | [V] | e13d_filtre_latence, `41896a3` | 271 paquets écartés tombent hors des fenêtres canoniques ; 5 fenêtres n'existent que par des paquets écartés (comptés à part). | R1-W2 |
| E13d-c | Coût moyen sur les fenêtres du train : pipeline 0,056338 ; borne basse (écartés = non-violations) 0,056332 ; borne haute (écartés = violations) 0,056411. Écart maximal des tables de coût : 6,0·10⁻⁵ (bas), 2,85·10⁻⁴ (haut). | [V] | e13d_filtre_latence | Moyenne des fenêtres, pas des réservations. Les bornes ne couvrent pas les 5 fenêtres perdues. | R1-W2 |
| E13d-d | Réservations avec coût ≤ d : 351/510 pour le pipeline et pour la borne haute. Réservations avec borne basse > d : 159/510. | [V] | e13d_filtre_latence | — | R1-W2 |
| E13d-e | **Ordre Safe-CQL < CQL < IQL à α = 0,1 :** identique avec le coût du pipeline et avec chaque borne, sur tout le train et sur chaque script (ex. 0,0300 / 0,0514 / 0,0524). **À α = 0,5 :** Safe-CQL (0,0326) reste sous CQL et IQL, mais CQL (0,0525) et IQL (0,0524) sont indiscernables ; la condition stricte « CQL < IQL » ne tient dans aucun des trois cas. | [V] | e13d_filtre_latence ; dataset_notes | **Dans l'échantillon** (tables et politiques sur les mêmes fenêtres). Sans intervalle. Ne dit rien sur l'ordre mesuré en E12. | R3-W1 |
| E13d-f | Les fichiers `mgen` URLLC vides ne sont pas des « paquets écartés » : au moins un des 4 fichiers URLLC est vide dans 353/510 réservations (E13c) ; ces UE n'entrent pas du tout dans le coût. | [V] code et comptes | dataset_notes (E13c) ; e13d « Limites » 3 | Raison (UE non attaché ? panne ?) non établie [Q]. | R1-W2 |
| E13d-g | Les 840 paquets écartés pourraient être les lignes à `Sent Time` aberrant vues en E13c. | [H] | e13d « Limites » 4 | Lignes non appariées. | — |
| E13d-h | Effet du filtre sur le test : **inconnu**. | [Q] | e13d « Portée » | Les 196 réservations du test n'ont pas été lues en E13c ni en E13d. | R1-W2 |

---

## 8. Affirmations à NE PAS faire

Pour chacune : ce que le papier ne doit pas dire, pourquoi, et ce qu'on peut dire à la place.

### 8.1 Contrôle séquentiel
- **À ne pas faire :** « l'agent contrôle le slicing de façon séquentielle », « la politique apprend la dynamique », « Q(s, a) capte l'effet d'une décision sur l'état suivant », « sans violation de la propriété de Markov ».
- **Pourquoi :**
  - D1 : aucune des 1 116 réservations ne change de config, donc aucune transition avec changement d'action n'existe (D1-a, D1-c).
  - D4 : l'état identifie l'action loguée (30-33 % avec les lags seuls, contre 12,4 %).
  - E2-d : avec α ≥ 0,5 la Q-net reproduit l'action loguée sur 64-82 % des fenêtres.
  - Aucun rapport ne contient d'expérience avec action variable ; l'option (B) du mémo de décision est une collecte de données future.
- **Formulation défendable :** sélection hors ligne de configuration par contexte (option (A) du mémo), évaluée au niveau réservation ; contrôle séquentiel = travail futur.
- **Reviewers :** R1-W1, R2-W2.

### 8.2 Respect du budget
- **À ne pas faire :** « Safe-CQL respecte le budget d = 0,03 », « le coût se stabilise sur le budget », « λ converge près de 12,9 », « le coût est contraint par construction ».
- **Pourquoi :**
  - E12-e : sur c40f2fe7, aucune politique n'est démontrée sûre. La borne haute de l'IC DM de Safe-CQL est 0,0325-0,0344, au-dessus de d.
  - E2-a : 0/60 runs convergent.
  - E11-a : aucun α n'est faisable ; α = 0,1 est retenu par le repli.
  - AU-f : le λ enregistré du notebook est toujours croissant, avec un coût > d.
  - E1-c : λ* n'est pas précisément déterminé.
- **Formulation défendable :** « sur le script de test c40f2fe7, le coût DM de Safe-CQL est de 0,0305-0,0315, plus bas que CQL/IQL (0,055-0,058), avec un intervalle dont la borne haute dépasse 0,03 ; aucune garantie ». Dire que les coûts sont lus dans des tables du train.
- **Reviewers :** R1-W2, R3-W1.

### 8.3 Supériorité du RL sur une table
- **À ne pas faire :** « le RL fait mieux qu'une table de lookup », « les agents surpassent les baselines », « le RL apporte un gain par rapport à une règle simple ».
- **Pourquoi :**
  - E12-f : table-greedy a le meilleur reward DM (9,069 contre 6,7-7,1) sur c40f2fe7, avec un coût DM plus bas (0,0217).
  - E11-e : la Q-net est moins bonne que le table-greedy transféré en reward (8,06 contre 10,35 ; 8,32 contre 11,37).
  - E12-g : always-RR atteint presque la même chose que Safe-CQL.
  - Phase 2 : l'apport du RL « n'est pas soutenu » par cette évaluation.
  - Réserve sur table-greedy : DM circulaire et couverture appariée de 9,5 % ; mais cette réserve va aussi contre le RL, pas en sa faveur.
- **Formulation défendable :** « Safe-CQL a un coût plus bas que CQL et IQL à reward comparable ; une table construite sur les mêmes cellules fait au moins aussi bien selon l'estimateur DM ».
- **Reviewers :** R3-W1, R3-W2.

### 8.4 Garantie de sécurité
- **À ne pas faire :** « garantie », « sûr », « safe » au sens de garantie probabiliste, « contrainte satisfaite », « violation SLA contrôlée à tout niveau de charge ».
- **Pourquoi :**
  - E12-e : critère « démontrée sûre » faux pour les 10 politiques.
  - TR-d : la contrainte respectée sur un script a été violée sur l'autre dans un sens (0,052).
  - D6-b : un script de test (90 %).
  - D5-b : 47-63 % des cellules ont un IC qui contient d.
  - D6-d : bruit entre répétitions du même ordre que d.
  - D7-c : le bin de charge n'est pas démontré exogène à l'action.
  - E13a2-c : les IC du coût transféré contiennent d pour toutes les partitions.
  - E13d-d : 351/510 réservations seulement ont un coût ≤ d.
  - Phase 2 : le DM de Safe-CQL est en partie circulaire.
  - Attente E12 : si un coût sur le test est ≤ d, ce ne sera pas présenté comme une garantie.
- **Formulation défendable :** « réduit le coût estimé » ; « un budget de coût moyen par fenêtre est utilisé comme contrainte d'entraînement » ; ne pas employer « safe » comme propriété démontrée.
- **Reviewers :** R1-W2.

### 8.5 Validation Near-RT
- **À ne pas faire :** « xApp Near-RT », « compatible avec les boucles 10 ms - 1 s de l'O-RAN », « validé en Near-RT », « robuste à la taille de fenêtre ».
- **Pourquoi :**
  - La fenêtre de décision est de 5 s.
  - E13b-d : les fichiers ne permettent la plage 10 ms - 1 s pour aucun des deux signaux.
  - E13b-c : le coût URLLC n'est pas résoluble à d en dessous de 5 s (34 paquets dans 99 % des fenêtres : 7/12 à 5 s, 0/12 à ≤ 1 s).
  - E13b-e : aucune sensibilité à la fenêtre n'a été lancée.
  - D1-c : aucune transition avec changement d'action, donc aucune boucle de contrôle à valider.
- **Formulation défendable :** boucle plus lente (type rApp / Non-RT RIC), à justifier ; ou limite de données mesurée (pas d'échantillonnage 0,25 s, 10 paquets/s par UE). Le rapport E13b précise de dire « limites de données mesurées, pas réponse à la plage Near-RT ».
- **Reviewers :** R2-W1.

### 8.6 Autres affirmations à ne pas faire

| à ne pas dire | pourquoi | source |
|---|---|---|
| « Les résultats du notebook sont reproduits. » | Ils ne le sont pas ; le λ = 12,22 n'est pas reproduit (E2, entraînement sur un pli). | audit ; E2-b |
| « Le scheduler PF cause plus de violations que RR. » (sens causal) | Scheduler et moment d'exécution ne sont pas séparables (PF et RR en blocs disjoints, ≈ 8 j d'écart pour 2 scripts sur 3). Dire plutôt « dans ce dataset, PF est associé à un coût plus élevé dans 12 couples sur 12 ». | D7-b, D8-b, D8-c |
| « RR reste sûr à toutes les charges (typiquement < 6 %). » | Le notebook montre 0,147 en (30 PRB, RR) à charge basse ; IC [0,005 ; 0,227] au train. | audit §7.3 ; D5-d |
| « Le nombre de niveaux de charge (3) est optimal ou justifié. » | E13a/E13a2 ne choisissent ni ne classent aucun jeu ; 4-5 niveaux ne sont testés qu'en B→A. | E13a-b ; E13a2-a |
| « Le filtre de latence n'a pas d'effet sur les résultats. » | Mesuré sur le **train** seulement (840 paquets sur 20,6 M, écart entre borne haute et pipeline ≈ 7·10⁻⁵ sur la moyenne des fenêtres) ; test non lu. | E13d-b, E13d-h |
| « L'ordre Safe-CQL < CQL < IQL est robuste au filtre. » | Vrai dans l'échantillon (train), pour α = 0,1 ; CQL < IQL ne tient pas à α = 0,5. | E13d-e |
| « Généralise à un déploiement inconnu / à d'autres scripts. » | Un script de test (90 %), deux de validation, trois en tout avec 8 actions. | D6-b, D6-c, E12-j |
| « FQE confirme le classement. » | Le FQE du notebook est incorrect (AU-e) ; aucun FQE corrigé dans `src/`. | audit §5 |
| « α = 0,1 est le meilleur hyperparamètre. » | Retenu par repli ; 0,05 et 0,2 à égalité en pratique ; aucun α faisable. | E11-a, E11-b |
| « Le test est un jeu indépendant et aveugle. » | Seconde lecture ; phase 2 l'avait déjà lu ; les attentes n'étaient pas aveugles. | E12-k |
| « Le Q-learning a appris une dynamique qui ne dépend pas de l'action loguée. » | La Q-net reproduit l'action loguée sur 61-82 % (E2-d) ; l'état la devine (D4-a). | D4-a, E2-d |
| « Source du budget 0,03 et de Lmax = 20 ms : [valeur de référence]. » | Source non documentée dans `dataset_notes.md` (« à compléter »). | E1 limite 5 |
| « Nouveauté algorithmique. » | Aucun rapport ne soutient une nouveauté ; le papier le dit lui-même. | audit §6 R3-W2 |

---

## 9. Chiffres non retrouvés, incohérences repérées, questions ouvertes

### 9.1 Chiffres non retrouvés dans les rapports lus

| chiffre | où on l'attendrait | effet |
|---|---|---|
| Écarts-types entre seeds des politiques RL en E12 | `e12_rapport_final.md` (la sortie brute n'en contient pas) | E12-a, E12-i : critère « 2 écarts-types » non vérifiable ici |
| IC des coûts et rewards **appariés** en E12 | idem | E12-c, E12-e, E12-f |
| `pct_safe` par politique en E12 | idem (phase 2 le donne pour α = 0,5 : Safe-CQL 76,6 ± 2,4 %, CQL 27,7 ± 3,6 %, IQL 23,2 ± 1,5 %) | non repris pour E12 |
| λ finaux et statut de convergence des runs E12 | idem | E12 ne l'exige pas |
| Effectifs en réservations des scripts 1dd38082 et 3e1a4369 (test) | `e12_rapport_final.md` | seule la borne « ≤ 19 réservations au total » est dérivable |
| Convention des IC des lignes RL en E12 | idem (phase 2 : moyenne des bornes par seed) | supposée identique : [H] |
| Résultats d'une analyse de queue (`urllc_p99`) ou d'un critique continu | aucun rapport | R1-W2 non couvert |
| Résultats complets de la phase 3 (100 epochs × 5 seeds, courbes) | `phase3_learning_curves.md` | seul un smoke test est mentionné (« pas des résultats ») |
| Rapport propre pour E13c | seul `dataset_notes.md` (E13c) | chiffres repris de là, scripts `src/e13c_anomalies.py` |
| Source de d = 0,03 et de Lmax | `dataset_notes.md` : « à compléter » | question ouverte |
| Contenu d'un manuscrit révisé (corrections R3-W3, référence [15]) | n'existe pas dans ce dépôt | AU-g |

### 9.2 Incohérences repérées entre rapports (à clarifier avant citation)

- **E11 :** le texte écrit « Q-nets 0,040 à 0,047 » pour B→A, mais le tableau va de 0,0405 à 0,0504 (E11-e).
- **E13a et E13a2 :** la même ligne `edges3_current` a des IC légèrement différents selon le rapport, car le flux aléatoire diffère (TR-e).
- **Phase 1 contre notebook :** 224 193 lignes contre 225 313 ; cause non attribuée (D2-c).
- **D5 contre notebook :** (30, RR, charge basse) 0,142 contre 0,147 (D5-d).
- **Phase 1 contre phase 0 :** ventilation des 101 réservations écartées (79 / 15 / 7 contre 95 / 6) ; seul l'ordre des contrôles diffère.
- **`dataset_notes.md` :** la phrase sur le slicing 5 a été corrigée par D6 (commits `3d501a6`, `40caf81`).

### 9.3 Questions ouvertes transversales

- **[Q]** Que valent les anomalies d'horodatage et le filtre de latence sur les 196 réservations du test ?
- **[Q]** Le moment d'exécution peut-il être séparé du scheduler (relance de réservations entrelacées) ?
- **[Q]** Le λ = 12,22 du notebook vient-il de la taille d'entraînement (tout le train) ou d'autre chose ?
- **[Q]** Le slicing 5 est-il « pas de slicing » ou « 50 PRB eMBB » ?
