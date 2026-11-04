# Synthèse du projet Safe-CQL RAN Slicing (état au 2026-11-04, branche `revision/18-synthese`)

## 0. Portée et règles de ce document

- Document de synthèse, **sans calcul nouveau**. Sources lues : `docs/` (rapports, `registre_affirmations.md`, `verification_registre.md`), `CLAUDE.md`, `reviews/reviewer_comments.md`, `paper/sections/02` à `05`.
- Non lus : `data/`, `results/e12/test_results.json`, `tests/`. Aucune évaluation lancée. Chaque nombre vient d'un rapport existant et porte son identifiant du registre. Quand il n'y en a pas, la source est un rapport nommé et c'est dit.
- `docs/etat_du_projet.md` : **non retrouvé** (il n'existe pas dans le dépôt).
- Statuts, comme dans le registre : **[V]** vérifié (script ou rapport), **[H]** hypothèse, **[Q]** question ouverte. « Non retrouvé » = aucune source dans les documents lus.
- Toutes les valeurs de coût et de reward de l'évaluation sont des estimations **DM** (lues dans des tables d'entraînement) ou **appariées** (observées sur les seules fenêtres où l'action choisie égale l'action loguée). Les sorties enregistrées du notebook (λ = 12,22, FQE, Table II) ne sont **pas** des résultats reproduits (NO-notebook, AU-f).
- Les chiffres du notebook repris ici le sont comme sorties enregistrées, jamais comme résultats.

---

## 1. Étapes du projet, dans l'ordre

Les phases 0 à 2 sont dans `main` (tête de `main` = `eb3aaef`). Les branches 03 à 18 ne le sont pas.
Les branches `revision/04-cmdp-lambda` et `revision/08-cmdp-gamma0` n'ont pas de travail propre : leur dernier commit est respectivement `36fd7e7` (notes dataset) et `b9fcb92` (D8). Les noms de branche ne correspondent donc pas toujours au contenu. Source : `git branch --contains`.

| Étape | Branche | Commit clé | Contenu et résultat principal | Rapport |
|---|---|---|---|---|
| Audit (lecture seule) | `revision/00-decision` | `fbe7a53` | Audit du PDF et du notebook (31 cellules). Trois tables de coût qui coexistent (AU-b), état à 12 dimensions contenant la récompense courante (AU-a), « Tabular OPE » non hors échantillon (AU-c), FQE incorrect (AU-e), « 2,25 × 10⁵ transitions d'entraînement » faux (AU-d), λ « près de 12,9 » contredit par la trace (AU-f). | `audit_report.md` |
| Phase 0 : D1 à D5 | `revision/00-decision` | `5178c8d` | D1 : 0/1 116 réservations changent de configuration (D1-a). D2 : horloge commune, mais fenêtres eMBB décalées par UE dans 532/1 101 réservations (D2-b). D3 : 46/706 réservations avec trous (D3-a). D4 : l'état laisse deviner l'action loguée (D4-a). D5 : IC par réservation 6 à 9 fois plus larges que par fenêtre (D5-a). Décision : option (A), sélection de configuration à un pas ; (B) contrôle séquentiel = travail futur. | `decision_memo.md` |
| Phase 1 : pipeline canonique | `revision/01-pipeline` | `1dba46b` | Origine `t0` commune, épisodes coupés aux trous (817), état à 10 dimensions, une seule table de coût à 3 bins. 706 réservations utilisables (D2-c), 224 193 lignes contre 225 313 dans le notebook, écart non attribué [Q]. | `phase1_pipeline.md` |
| Phase 2 : baselines et agents | `revision/02-baselines` | `eb3aaef` | always-RR, always-PF, best-fixed, table-greedy ; CQL, Safe-CQL, IQL ; première lecture du test (α = 0,5). Finding 3 : l'apport du RL sur une table « n'est pas soutenu ». | `phase2_baselines.md` |
| Phase 3 : courbes d'apprentissage | `revision/03-learning-curves` | `25af210` | Journalisation par epoch et mode `--curves-val`. **Seul un smoke test a été fait ; les runs complets 100 epochs × 5 seeds ne sont pas faits** (non retrouvé : aucun résultat). | `phase3_learning_curves.md` |
| D6 : scripts partagés | `revision/05-d6-scripts-partages` | `2ce8774` | 19 scripts, aucun partagé entre clusters (D6-a). Le test est de fait un script : c40f2fe7 pèse 177/196 réservations (D6-b). | `d6_shared_scripts.md` |
| D7 : effet scheduler, ordre | `revision/06-d7-ordre-scheduler` | `5f4438e` | PF − RR sur le coût positif dans 12 couples sur 12 (D7-a) ; PF et RR en blocs disjoints (D7-b). | `d7_scheduler_order.md` |
| D8 : chronologie | `revision/07-d8-ordre-chronologique` | `b9fcb92` | Ordre des identifiants = ordre chronologique (D8-a). Aucun des 17 couples n'a PF et RR entrelacés (D8-b). | `d8_chronology.md` |
| E1 : LP du CMDP à un pas | `revision/09-lp-diagnostic` | `7ef80eb` | Budget d = 0,03 faisable sur les tables (E1-a). λ* de table petit (E1-b), mal déterminé (E1-c). | `e1_lp_diagnostic.md` |
| E2 : diagnostic Safe-CQL par pli | `revision/10-safe-cql-g0` | `b2f9405` (code), `8f8a039` (rapport) | 0/60 runs convergés (E2-a). γ = 0 ne résout pas la dérive de λ (E2-c). | `e2_safe_cql_diagnostic.md` |
| E11 : grille d'α | `revision/11-alpha-grid` | `7e9be78` (gel), `3779a06`, `ecb624d` | Aucun α faisable (E11-a) ; α = 0,1 retenu par repli (E11-b). | `e11_alpha_grid.md` |
| E12 : lecture finale du test | `revision/12-test-final` | `2cf749e` (attente), `0387dbc` (gel), `0fa5787` (run), `c58d6e5` (rapport) | Seconde lecture du test, pas aveugle (E12-k, E12-l). Aucune politique démontrée sûre (E12-e). Tableau en §3.3. | `e12_attente_pre_test.md`, `e12_rapport_final.md` |
| E13a / E13a2 : niveaux de charge | `revision/13-bins-fenetre` | `ed677b6`, `fc32130` / `c699b57` (protocole), `7652a34` | Descriptif, train seul. Les IC du coût transféré contiennent d dans toutes les lignes (E13a2-c). Aucun nombre de niveaux n'est choisi ni recommandé. | `e13a_niveaux_charge.md`, `e13a2_protocole_entiers.md`, `e13a2_resultats.md` |
| E13b : pas d'échantillonnage | `revision/13-bins-fenetre` | `f77bff6`, `85e39ab` | Pas réel 0,25 s pour les flux KPM (E13b-a), 10 paquets/s par UE URLLC (E13b-c). **Aucune sensibilité à la fenêtre lancée** (E13b-e). | `e13b_pas_echantillonnage.md` |
| E13c : anomalies d'horodatage | `revision/13-bins-fenetre` | `15d2664` | 510 réservations du train ; test non lu. Pas de rapport propre : chiffres dans `dataset_notes.md`. | `dataset_notes.md` |
| E13d : filtre de latence | `revision/13-bins-fenetre` | `556bcf2` (protocole), `41896a3` | 840 paquets écartés sur 20 619 886 (E13d-b). Ordre Safe-CQL < CQL < IQL identique avec les bornes à α = 0,1 (E13d-e), **dans l'échantillon**. | `e13d_protocole_filtre_latence.md`, `e13d_filtre_latence.md` |
| Registre des affirmations | `revision/13-bins-fenetre` | `23d5536`, `e8ab6da` | 168 lignes vérifiées contre les rapports : OK 166, AMBIGU 2 (D4-a, COST-a), ABSENT 0. | `registre_affirmations.md`, `verification_registre.md` |
| Papier §02 « Data and audit » | `revision/14-section-data-audit` | `0347fa6`, `53ddea6` | Rédigée depuis le registre. | `paper/sections/02_data_audit.tex` |
| Papier §03 « Problem Formulation » | `revision/15-section-formulation` | `3f2dd49` | Bandit contextuel contraint (γ = 0), cadrage rApp, hypothèses A1 à A3. | `paper_03_formulation.md` |
| Papier §04 « Methods » | `revision/16-section-methods` | `d5d939f`, `db675c5` (BC retiré) | CQL, IQL, table-greedy, Safe-CQL, choix de α, diagnostic de λ. | `paper_04_methods.md` |
| Papier §05 « Evaluation Protocol » | `revision/17-section-evaluation` | `c66031f`, `6942b9b`, `8f64170` | DM et apparié, bootstrap par script, pré-enregistrement, garde (FREEZE-a). 0/15 runs Safe-CQL convergés en E12 (E12P-e). | `paper_05_evaluation.md`, `e12_convergence.md`, `e12_garde_limites_connues.md` |
| Synthèse | `revision/18-synthese` | (ce commit) | Ce document. | — |

**Sections du papier existantes :** 02, 03, 04, 05 uniquement. Introduction, travaux connexes, **section Résultats** (`sec:results`), conclusion : **non retrouvées**. Les renvois `sec:method` et `sec:results` sont pendants (`paper_03_formulation.md`, `paper_05_evaluation.md`).

---

## 2. Observations clés sur le dataset

### 2.1 Structure
- 1 116 réservations ; 706 utilisables (D1-a ; D2-c). Plateforme : 1 station de base, 50 PRB, 8 UE statiques (UE 1-4 eMBB, UE 5-8 URLLC), schedulers RR et PF (PLAT-a, lu dans le README, non recoupé par un script).
- 8 actions = 4 niveaux de PRB eMBB (9, 21, 30, 39) × {RR, PF} (PLAT-a). Le slicing 5 est exclu (D1-b).
- Entraînement : clusters 2-3 (510 réservations utilisables) ; test : cluster 1 (196) (phase1_pipeline ; pas d'identifiant propre).

### 2.2 Une configuration par réservation
- **[V]** La configuration ne change dans aucune des 1 116 réservations (0/1 116) (D1-a). Conséquence : aucune transition avec changement d'action ; Q(s, a ≠ a loguée) n'est identifiée que par des différences **entre** réservations (D1-c).
- **[V]** La charge varie dans une réservation, mais de façon scriptée (MGEN, changement toutes les 60 s) et exogène à l'action (D1-a).
- **[V]** L'état à 12 dimensions du notebook laisse deviner l'action loguée : 30,5-32,8 % de précision sur les 8 actions avec les lags seuls (base 12,4 %) (D4-a). Mesuré sur l'état à 12 dimensions ; **re-mesure sur l'état à 10 dimensions non faite** (D4-d [Q]).

### 2.3 Scripts comme unités indépendantes
- 19 scripts distincts, aucun partagé entre clusters, donc aucun entre train et test (D6-a).
- Le test est un script à 90 % : 177/196 réservations (D6-b). Le train tient sur 2 scripts : 478/510 (D6-b).
- Seuls 3 scripts couvrent les 8 actions : a908e4cc (cluster 2), a53521b2 (cluster 3), c40f2fe7 (cluster 1 = test) (D6-c).
- Unité indépendante de généralisation = le script : **[H] fortement soutenue**, non testée (D6-b, hypothèse A3 de la section 03).
- Le bruit entre répétitions d'un même script est du même ordre que le budget (D6-d).

### 2.4 Confusion scheduler / moment d'exécution
- **[V]** PF − RR sur le coût est positif dans 12 couples (script, slicing) sur 12, de +0,04 à +0,20 (D7-a). Sur le reward, le signe est variable (D7-a).
- **[V]** PF et RR occupent des blocs d'identifiants disjoints dans les 12 couples (D7-b). Aucun des 17 couples n'est entrelacé ; blocs à ≈ 8 jours pour 2 scripts, ≈ 13 h pour c40f2fe7 (D8-b).
- **[V]** Les paires PF/RR les plus proches gardent le signe (12/12, 12/12, 8/8) mais restent à ≈ 8-9 jours pour 2 scripts sur 3 : le contrôle **ne réfute pas** la confusion (D8-c).
- **[V]** La meilleure coupure unique du coût tombe à la bascule PF → RR pour les 3 scripts (D8-d).
- Conséquence : ne pas écrire « PF cause plus de violations » (NO-pfcause). Dire « associé à ».
- **[V]** `nof_ue` et le débit URLLC reçu dépendent de l'action sur les 8 actions (D7-c). À scheduler fixé, aucune dépendance détectée (D7-c, **[H]** : faible puissance). Le bin de charge n'est donc pas démontré exogène à l'action.

### 2.5 Échantillonnage et fenêtre
- Fenêtre de décision de 5 s (WIN-a). Pas réel des flux KPM : 0,25 s (E13b-a). Fenêtres de 1, 2 et 2,5 s possibles pour le reward, la radio et `nof_ue` ; 0,5 s et moins non (E13b-b).
- Coût URLLC : 10 paquets/s par UE, 2 à 3 UE actifs. Le critère « ≥ 34 paquets dans 99 % des fenêtres » est atteint à 5 s pour 7 réservations sur 12, à 2,5 s pour 4/12, à ≤ 1 s pour 0/12 (E13b-c).
- La plage 10 ms - 1 s n'est atteignable sur aucun des deux signaux (E13b-d).
- **Limite de portée** : 12 réservations du train, aucune du test (E13b). Aucune sensibilité à la fenêtre n'a été lancée (E13b-e).
- Horloge UE estimée, non validée : décalage médian 0,51 s, p5 −1,7 s, p95 +3,8 s, 124 fichiers au-delà de ±5 s (E13b-f, **[H]**).

### 2.6 Anomalies de données
- **Train seulement (510 réservations) ; le test n'est pas lu** (E13d-h [Q]) :
  - `Sent Time` : saut > 3 600 s dans 423/510 réservations, contre 8/510 pour `Received Time` (E13b-g) ; cause non établie [Q].
  - Au moins un des 4 fichiers `mgen.csv` URLLC est vide dans 353/510 réservations (E13d-f) ; raison non établie [Q].
  - Fichiers `bs/<IMSI>_metrics` : moins de 8 fichiers dans 112/510 réservations ; durée `ue_metrics`/`enb_metrics` hors de [0,9 ; 1,1] dans 37/510 (dataset_notes, E13c ; pas d'identifiant de registre).
- Filtre de latence : 840 paquets écartés sur 20 619 886 ; coût moyen 0,056338 (pipeline), 0,056332 / 0,056411 (bornes) (E13d-b, E13d-c).
- Trous de fenêtres : 46/706 réservations (D3-a). Slicing 5 : « pas de slicing » (309 réservations avec `slicing_enabled=0`) alors que le papier le présente comme « 50 PRB eMBB » : écart non expliqué (D1-b, [Q]).
- Cellules de coût : 47 à 63 % ont un IC contenant d = 0,03 (D5-b).
- Écart de comptage avec le notebook (224 193 contre 225 313 lignes) non attribué (D2-c [Q]). Cellule (30 PRB, RR, bas) : 0,142 ici contre 0,147 dans le notebook (D5-d [Q]).

---

## 3. Résultats d'entraînement

Tous les coûts ci-dessous sont **DM** ou **appariés**, jamais des mesures de système.

### 3.1 Diagnostic de λ (E1, E2, E12)
| Constat | Valeur | ID | Statut |
|---|---|---|---|
| Budget d = 0,03 faisable sur les tables A, B, TRAIN ; coût minimal 0,0211 / 0,0112 / 0,0182 | — | E1-a | [V] |
| λ* de table : 0 (A), 0,065 (B), 0,244 (TRAIN), contre 12,22 enregistré dans le notebook (non reproduit) | ≈ 50 fois plus petit | E1-b | [V] pour la table |
| λ* mal déterminé : IC de 0 à ≈ 1-3 ; contrainte active dans 36-74 % des rééchantillons | — | E1-c | [V] limite |
| La divergence de λ ne vient donc pas de la table de coût | — | E1-b | [V] |
| 0 run convergé sur 60 (6 variantes × 2 plis × 5 seeds) selon le critère gelé | 0/60 | E2-a | [V] |
| γ = 0,7, α = 0,5 : λ final 1,935 ± 0,045 (A) et 0,283 ± 0,011 (B) ; 300 epochs : 5,838 et 0,906, toujours en hausse | — | E2-b | [V] |
| γ = 0 ne résout pas la dérive : λ 3,112 (A), 0,595 (B) | — | E2-c | [V] |
| **E12 : 0 run convergé sur 15** Safe-CQL (3 configurations × 5 seeds) au critère d'E2 | 0/15 | E12P-e | [V] |
| E12, λ finaux : `safe_cql_a0.1` 0,1028 à 0,1272 ; `safe_cql_a0.5` 0,7497 à 0,9046 ; `safe_cql_a0.1_g0` 0,4398 à 0,4910 ; λ(99) > λ(79) dans les 15 runs | — | E12P-c | [V] |

- Limites : entraînement E2 sur un pli (≈ 73-80 k fenêtres), pas sur tout le train ; le λ = 12,22 du notebook n'est donc **pas reproduit**, et l'origine de cet écart reste [Q] (E2-b ; registre §9.3).
- La bande de coût du critère est peut-être trop étroite [Q] (E2-a). Le critère révisé d'E11 est descriptif (E11-d).
- Phrase défendable : le coût de Safe-CQL se rapproche de d, le multiplicateur ne se stabilise pas, et aucun run ne converge (NO-budget).

### 3.2 Choix de α (E11)
- Grille α ∈ {0 ; 0,02 ; 0,05 ; 0,1 ; 0,2 ; 0,5}, deux sens (A→B, B→A), seeds 0-4, 100 epochs : 60 runs terminés (GRID-a).
- **Aucun α faisable** : en B→A le coût de validation dépasse d pour tout α (0,0405 à 0,0504) (E11-a).
- α = 0,1 retenu **par le repli**, pas sur ses mérites. 0,05 / 0,1 / 0,2 sont à égalité en pratique (0,03470 / 0,03440 / 0,03464), écart entre seeds 0,0010 à 0,0021 (E11-b).
- Sens opposés : en A→B le coût baisse avec α, en B→A il monte ; moyenner les deux sens masque cette opposition (E11-c).
- La Q-net est en dessous d'un table-greedy transféré en reward : 8,056 contre 10,352 (A→B), 8,321 contre 11,370 (B→A) (E11-e). La phrase du rapport sur la plage de coûts des Q-nets en B→A ne coïncide pas avec son tableau : **[Q]**, bornes retirées du registre.
- Transfert : la politique LP construite sur A viole le budget sur B (0,052) ; construite sur B et lue dans A : 0,0300 (TR-a). « La sécurité ne se transfère pas » est vérifiée dans **un** sens seulement (TR-d).
- Les grilles d'α ont été fixées après E2 : pas une recherche aveugle (GRID-c).

### 3.3 E12 : table par script (lecture finale du test)

**Statut de la lecture.**
- C'est la **seconde** lecture du test, pas une lecture aveugle (E12-k, E12-l, NO-blind). La phase 2 l'avait déjà lu (α = 0,5, IQL, baselines).
- Nouveaux dans cette lecture : α = 0,1, γ = 0, la ventilation par script (E12-k).
- Les attentes (a) à (e) ont été écrites après la phase 2 et en connaissaient les résultats (E12-l).
- D6, D7 et D8 avaient examiné des résultats de c40f2fe7 (descriptif ; « aucun réglage » = **déclaration des auteurs**) (E12-m).
- Configurations, estimateurs, critères et garde figés avant (FREEZE-a, PREREG-a), tests d'étanchéité. Le gel ne rend pas la lecture aveugle.

**Lecture de la table.**
- Pour chaque politique : reward DM, coût DM [IC 95 % bootstrap par réservation, B = 2 000, conditionnel au script], coût apparié, couverture appariée.
- Source : `e12_rapport_final.md`. Lignes du registre : E12-a à E12-h.
- Les IC mesurent la dispersion des réservations dans le script, non celle entre scripts (BOOT-a).

**Script c40f2fe7 (177 réservations utilisables) :**

| Politique | Reward DM (Mbps) | Coût DM [IC 95 %] | Coût apparié | Couverture | ID |
|---|---|---|---|---|---|
| Safe-CQL α = 0,1 (principal) | 6,968 | 0,0315 [0,0290 ; 0,0344] | 0,0274 | 35,0 % | E12-a, E12-c |
| Safe-CQL α = 0,5 | 6,776 | 0,0305 [0,0272 ; 0,0342] | 0,0357 | 34,8 % | E12-a, E12-c |
| Safe-CQL α = 0,1, γ = 0 | 6,773 | 0,0286 [0,0253 ; 0,0325] | 0,0342 | 33,5 % | E12-i |
| CQL α = 0,1 | 7,117 | 0,0551 [0,0491 ; 0,0612] | 0,0415 | 36,0 % | E12-a |
| CQL α = 0,5 | 6,733 | 0,0548 [0,0486 ; 0,0609] | 0,0436 | 39,4 % | E12-a |
| IQL | 6,787 | 0,0582 [0,0516 ; 0,0649] | 0,0452 | 40,3 % | E12-a |
| always-RR | 7,027 | 0,0287 [0,0258 ; 0,0319] | 0,0216 | 45,3 % | E12-g |
| always-PF | 6,688 | 0,1294 [0,1188 ; 0,1400] | 0,0664 | 54,7 % | E12-g |
| best-fixed | 2,734 | 0,0140 [0,0125 ; 0,0156] | 0,0308 | 13,0 % | E12-h |
| table-greedy | 9,069 | 0,0217 [0,0204 ; 0,0230] | 0,0310 | 9,5 % | E12-f |

Toutes les valeurs du tableau sont recopiées de `e12_rapport_final.md`. La dernière colonne donne la ligne du registre qui les cite. La ligne γ = 0 n'est citée au registre qu'en différence avec γ = 0,7 (E12-i), non en valeurs absolues.

**Statut de chaque ligne.**
- **Safe-CQL a un coût DM plus bas que CQL et IQL à reward comparable** : DM 0,0305-0,0315 contre 0,055-0,058 (E12-a). Le reward des agents est proche : 6,73 à 7,12 (E12-d). Même ordre en apparié (E12-c).
- **Pas de séparation par IC en apparié** : les IC se recouvrent largement entre Safe-CQL et CQL/IQL (E12-c). L'ordre des moyennes est vérifié, pas une séparation par IC. En DM, les IC de Safe-CQL (borne haute 0,0344) et de CQL/IQL (borne basse 0,0486) ne se recouvrent pas sur c40f2fe7 (E12-a), mais ce DM est partiellement circulaire.
- **Aucune politique démontrée sûre** (critère gelé : borne haute des IC DM **et** apparié ≤ 0,03) : faux pour les 10 politiques (E12-e). En DM seules best-fixed et table-greedy passent ; en apparié, les 10 bornes hautes dépassent d (Safe-CQL α = 0,1 : 0,0379). Les IC appariés sont larges (couverture 9,5-54,7 %), donc cela tient en partie au manque d'information, sans prouver que les politiques sont dangereuses (E12-e).
- **Table-greedy** : meilleur reward DM (9,069), coût DM 0,0217, mais couverture appariée de 9,5 % et estimation DM la plus circulaire (E12-f, AU-c). Aucune supériorité du RL n'est démontrée (NO-rl). always-RR est au niveau de Safe-CQL (E12-g). always-RR et always-PF lisent l'action loguée : ce ne sont pas des politiques déployables (BASE-a).
- **Ablation γ = 0** (E12-i), compromis coût/reward :
  - Sur c40f2fe7 : coût −0,0029, reward −0,20 Mbps ; critère « amélioration nette » non satisfait, attente (d) tenue.
  - Sur l'ensemble : coût −0,0032, reward −0,22 Mbps ; critère satisfait, attente (d) fausse.
  - Marge mince (seuil ≈ 0,0032 pour un écart de 0,0029) ; critère arbitraire. Aucune conclusion de supériorité de γ = 0 ou de γ = 0,7.
- **Autres scripts du test** : 1dd38082 (10 réservations) et 3e1a4369 (9, `low_n`) ont des IC larges ; à ne pas utiliser pour des affirmations par script (E12-j). L'ensemble « pooled » est à 90 % un script (E12-b, D6-b).
- **Ce qui n'est pas démontré** : sécurité (NO-safe), respect du budget (NO-budget), supériorité du RL sur la table (NO-rl), généralisation à d'autres scripts (NO-general), test indépendant et aveugle (NO-blind).

---

## 4. Direction scientifique et cohérence

### 4.1 De « Safe-CQL résout le problème séquentiel » à « que permettent des traces statiques commerciales »
- Le manuscrit original posait un CMDP séquentiel, avec γ = 0,7 et un agent présenté comme xApp.
- L'audit a montré que les données ne le soutiennent pas :
  - aucune transition avec changement d'action (D1-a, D1-c) ;
  - l'état identifie l'action loguée (D4-a) ;
  - la Q-net reproduit l'action loguée sur 61-82 % des fenêtres selon α (E2-d), d'où NO-dyn ;
  - la sécurité ne se transfère pas entre scripts, au moins dans un sens (TR-d) ;
  - le scheduler est confondu avec le moment d'exécution (D7-b, D8-b).
- La question honnête devient : **que permettent ces traces statiques pour sélectionner une configuration sous contrainte de coût, et avec quel niveau de preuve ?** Le papier est un travail d'audit et de protocole d'évaluation autant qu'un travail d'algorithme (aucune nouveauté algorithmique revendiquée : NO-novelty, R3-W2).

### 4.2 Formulation à un pas
- La section 03 formule un **bandit contextuel contraint** : contexte x de 10 dimensions, 8 actions, récompense = débit eMBB, coût = fraction de paquets URLLC dont la latence dépasse 20 ms, budget moyen d = 0,03 (STATE-a, REW-a, COST-a). Relaxation lagrangienne (SAFE-a, SAFE-b).
- Pourquoi c'est cohérent : avec une configuration constante par réservation, aucune donnée ne contraint une valeur qui s'appuie sur les fenêtres successives (D1-a, D1-c). L'unité de décision est la configuration d'une réservation, évaluée au niveau réservation (NO-seq, formulation défendable).
- Hypothèses explicites, **non vérifiées** (section 03, `sec:assumptions`) :
  - (A1) le contexte est exogène à l'action : contredit en partie par D7-c ;
  - (A2) configuration « comme assignée » : contredite pour le scheduler (D7-b, D8-b) ;
  - (A3) le script est l'unité indépendante.

### 4.3 γ = 0,7 à l'entraînement, lecture à un pas, γ = 0 en ablation
- Le papier le dit : les agents principaux sont entraînés avec γ = 0,7 sur des fenêtres consécutives d'un épisode et utilisés comme **sélecteurs à un pas** (action = argmax de la Q-net, E12P-d). γ = 0, qui correspond à l'objectif à un pas, est une **ablation** `safe_cql_a0.1_g0` (E12P-b, E12-i).
- Ce choix a un coût de cohérence : l'objectif écrit est à un pas, l'agent principal est entraîné avec amorçage. `paper_03_formulation.md` le signale comme point à trancher : présenter γ = 0,7 comme variante d'entraînement de la même cible, ou refaire l'évaluation principale avec γ = 0 (ce qui serait une **troisième lecture du test**). **Non tranché.**
- Les données ne tranchent pas : γ = 0 ne résout pas la dérive de λ (E2-c) ; il baisse le coût et le reward à la fois, avec un résultat qui dépend de l'ensemble de scripts considéré (E12-i).

### 4.4 Cadrage rApp
- La section 03 cadre le sélecteur « dans le style d'un rApp du Non-RT RIC, plutôt que d'un xApp Near-RT » (`% REG: NO-nearrt`).
- Ce cadrage s'appuie sur la fenêtre de 5 s (WIN-a) et sur E13b-d. **La justification des échelles de temps O-RAN est une citation manquante** (`TODO-oran-timescales`), et `paper_03_formulation.md` (liste 2, n° 4) note que l'échelle de temps d'un rApp n'est dans aucun rapport.

### 4.5 Affirmations à NE PAS faire (registre §8)
NO-seq (contrôle séquentiel, Markov) · NO-budget (« respecte d », « λ converge près de 12,9 ») · NO-rl (« le RL fait mieux qu'une table ») · NO-safe (garantie) · NO-nearrt (xApp, 10 ms - 1 s, robustesse à la fenêtre) · NO-notebook · NO-pfcause · NO-rr · NO-bins · NO-filter · NO-order · NO-general · NO-fqe · NO-alpha · NO-blind · NO-dyn · NO-source · NO-bc · NO-novelty.

---

## 5. Remarques des reviewers

Statuts stricts : **traitée** / **partiellement traitée** / **ouverte**.
Aucune remarque n'est classée « traitée » : chacune laisse une limite, parfois la demande elle-même non exécutée.

| Remarque | Traitement | Où | Statut | Limites |
|---|---|---|---|---|
| **R1-W1** : l'état omet a_{t-1}, Markov violée | Reformulation en bandit contextuel à un pas (γ = 0) : pas d'hypothèse de Markov revendiquée (NO-seq). État à 10 dimensions, récompense et `urllc_p50` courants retirés (AU-a, STATE-a). Argument que a_{t-1} n'apporterait presque rien, car l'action est constante dans la réservation (D4-c). | `paper_03_formulation.md`, `paper/sections/03_formulation.tex` (§ Scope, hypothèses) ; `02_data_audit.tex` (D4) | **Partiellement traitée** | La demande du reviewer (a_{t-1} dans l'état + architecture récurrente) n'est **pas exécutée**. D4-c est un argument [H], non testé. L'état fuit toujours l'action loguée (D4-a) ; **D4-d : re-mesure sur 10 dimensions non faite [Q]**. Les agents sont entraînés avec γ = 0,7 (§4.3). |
| **R1-W2** : coût tabulaire à 3 bins, trop grossier pour la queue URLLC | IC par réservation sur les cellules de coût (D5-a, D5-b). Diagnostic LP (E1). Sensibilité descriptive au nombre de niveaux (E13a, E13a2), au filtre de latence (E13d), au pas d'échantillonnage (E13b). Les phrases de l'original sur la queue sont supprimées. | `decision_memo.md`, `e13a_niveaux_charge.md`, `e13a2_resultats.md`, `e13b_pas_echantillonnage.md`, `e13d_filtre_latence.md` ; `02_data_audit.tex`, `03_formulation.tex` | **Partiellement traitée** (limites documentées ; changement demandé non fait) | **Aucun critique continu ni mesure de queue** (`urllc_p99` est dans le parquet, aucun rapport : R1W2-no [Q]). La table à 3 bins reste le coût d'entraînement ; 47-63 % des cellules ont un IC contenant d (D5-b). E13a/E13a2 ne choisissent ni ne classent aucun nombre de niveaux ; IC du coût transféré contenant d partout (E13a2-c). 4-5 niveaux testés seulement en B→A (E13a2-a). E13d : train seulement, test non lu (E13d-h). |
| **R2-W1** : pas de 5 s, incompatible Near-RT | Cadrage rApp / Non-RT (§4.4). Mesure du pas réel des fichiers (E13b). Retrait des phrases sur le suivi de la dynamique. NO-nearrt. | `e13b_pas_echantillonnage.md` ; `03_formulation.tex`, `02_data_audit.tex` (§ fenêtre), `05_evaluation.tex` (limites) | **Partiellement traitée** | Le Near-RT est **écarté comme revendication, non réfuté ni testé** : la plage 10 ms - 1 s n'est atteignable sur aucun signal (E13b-d). **Aucune sensibilité à la fenêtre** (décision de l'auteur, E13b-e). Échantillon de 12 réservations du train (E13b). Citation O-RAN manquante (`TODO-oran-timescales`). Les échelles de temps O-RAN de la review ne sont pas vérifiées ici (E13b-d). |
| **R2-W2** : données statiques, configuration constante par réservation | Constat vérifié (D1-a), exposé en section 02 et en hypothèses A1 à A3 de la section 03. Sélection hors ligne de configuration, évaluée au niveau réservation. Protocole d'évaluation DM + apparié (EST-a, EST-b). | `decision_memo.md` ; `02_data_audit.tex` (§ configuration constante), `03_formulation.tex`, `05_evaluation.tex` | **Partiellement traitée** | La limite est **reconnue et le périmètre réduit**, non levée : pas de collecte avec changements de configuration (options B et C du mémo non faites). Scheduler non séparable du moment d'exécution (D7-b, D8-b) ; contexte non démontré exogène (D7-c). Séparer le scheduler du moment d'exécution par des relances entrelacées : [Q] (registre §9.3). |
| **R3-W1** : une seule baseline (BC) | Quatre baselines sans apprentissage (always-RR, always-PF, best-fixed, table-greedy) + CQL, IQL. BC **retiré** (BC-a). Évaluation par script avec IC (E12). | `phase2_baselines.md`, `e12_rapport_final.md` ; `04_methods.tex`, `05_evaluation.tex` | **Partiellement traitée** | La section Résultats n'est pas écrite. Un script de test (90 %) (D6-b). Pas d'IC sur la différence entre agents (E12-a). Table-greedy : DM circulaire, couverture 9,5 % (E12-f). Seconde lecture du test, non aveugle (E12-k). Pas de FQE ni d'estimateur à poids d'importance. Le BC du reviewer n'est plus dans le papier ; il est écarté par argument (BC-a), sans résultat. |
| **R3-W2** : nouveauté incrémentale | Aucune nouveauté algorithmique n'est revendiquée (NO-novelty). La portée est réduite et dite (NO-general). | `paper/sections/03_formulation.tex` (fin) ; registre §8 | **Ouverte** | Le mémo le dit : l'option (A) ne répond pas à R3-W2. Apport de fond = audit des données et protocole d'évaluation, à rédiger comme tel. Aucun rapport ne soutient une nouveauté. |
| **R3-W3** : rédaction, référence manquante, style | Sections 02 à 05 réécrites depuis le registre, chaque phrase marquée `% REG:` ou signalée comme non soutenue (listes 1 et 2 des rapports `paper_0X`). Coquilles corrigées dans la section 03 (liste 1, n° 14). Erreur « 2,25 × 10⁵ transitions » corrigée (AU-d). | `paper_03_formulation.md`, `paper_04_methods.md`, `paper_05_evaluation.md` | **Partiellement traitée** | Il reste **10 occurrences de citations `TODO-*`** (8 clés distinctes) dans les sections 02 à 04 (voir §6). La référence « [?] » de la Section II et la référence [15] ne sont pas corrigées : aucun manuscrit révisé complet n'existe (AU-g). Introduction, travaux connexes, résultats, conclusion : non retrouvés. La critique du style « rédigé par IA » n'a fait l'objet d'aucune analyse (non retrouvé). |

Pas d'identifiant de registre pour l'état d'avancement du papier complet ; il vient de `paper/sections/` (4 fichiers).

---

## 6. Points ouverts

1. **Références** : 10 occurrences de `\cite{TODO-…}` (8 clés distinctes) dans les sections 02 à 04. Voir la liste ci-dessous.
   - `TODO-oran-timescales` (sections 02 et 03), `TODO-budget-latency-source` (02 et 03), `TODO-lagrangian-relaxation` (03).
   - `TODO-dataset`, `TODO-mgen` (02) ; `TODO-cql`, `TODO-double-dqn`, `TODO-iql` (04).
   - Référence [15] (MGEN) et « [?] » de la Section II du PDF original : AU-g [Q].
   - Aucune citation n'est inventée dans ce dépôt (règle de `CLAUDE.md`).
2. **Source de d = 0,03 et de Lmax = 20 ms** : non documentée (`dataset_notes.md` : « à compléter » ; NO-source).
3. **Courbes d'apprentissage** : runs complets de la phase 3 non faits (seul un smoke test). Aucun résultat de courbe.
4. **Section Résultats** et sections amont/aval (introduction, travaux connexes, conclusion) : non écrites. Les renvois `sec:method` et `sec:results` sont pendants.
5. **Point à trancher sur γ** (§4.3) : γ = 0,7 comme variante d'entraînement, ou refaire l'évaluation principale avec γ = 0 (troisième lecture du test, NO-blind).
6. **Critique continue et mesure de queue URLLC** (R1-W2) : aucune analyse (R1W2-no).
7. **Sensibilité à la fenêtre** : non lancée (E13b-e). Les mesures de E13b portent sur 12 réservations du train.
8. **Test non lu pour les anomalies** (E13c, E13d) : l'effet du filtre de latence et des anomalies d'horodatage sur les 196 réservations du test est inconnu (E13d-h).
9. **Mesure de D4 sur l'état à 10 dimensions** (D4-d) : non faite.
10. **Incohérences et inconnues du registre §9** :
    - la phrase du rapport E11 sur la plage des coûts de Q-nets en B→A (E11-e) ;
    - l'écart 224 193 / 225 313 lignes (D2-c) ;
    - la cellule (30, RR, bas) 0,142 / 0,147 (D5-d) ;
    - slicing 5 « sans slicing » ou « 50 PRB eMBB » (D1-b) ;
    - cause des 1 120 lignes manquantes, du λ = 12,22 du notebook, des fichiers URLLC vides (E13d-f), des sauts de `Sent Time` (E13b-g).
11. **Relances entrelacées PF/RR** pour séparer le scheduler du moment d'exécution : nécessiterait de nouvelles données (registre §9.3).
12. **Lacunes de la garde E12** : `e12_garde_limites_connues.md` (tests/ non modifié).
13. **Écart de comptage du vérificateur** : `verification_registre.md` indique 166 OK / 2 AMBIGU / 0 ABSENT sur 168 lignes, alors que `paper_05_evaluation.md` citait 163 OK au moment de son écriture. Le fichier de vérification est le plus récent.

---

## 7. Réponse à la suggestion externe : xApp ou rApp ? Garder le CMDP ? Trois alternatives

**Sources utilisées pour cette section : NO-nearrt, E13b (a à g), D1 (a à c), D7 (a à c), D8 (a à d), E12 (a à m).**
Aucune ligne ou rapport ne traite de E2SM-KPM, E2SM-RC, de conformal risk control, de modèle causal structurel ni de bandit contextuel appris : **non retrouvé**. Toute affirmation sur ces sujets ci-dessous est un raisonnement à partir des constats de données, marqué [H].

**La suggestion externe est un énoncé non vérifié par ce dépôt.**
- Ses échelles de temps (« 10 à 100 ms » pour les xApp, « > 1 s » pour les rApp) ne sont dans aucun rapport. La review R2 donne 10 ms - 1 s pour le Near-RT ; le rapport E13b précise que cette lecture O-RAN « vient de la review, non vérifiée ici ».
- L'affirmation « un rApp est trop lent pour prévenir les violations de SLA URLLC » n'est ni testable ni testée avec ces données (voir A).

### A. xApp ou rApp ?

**Réponse : rApp (ou boucle lente), à titre de cadrage [H]. Un xApp ne peut pas être revendiqué.**

- **[V] Ce que les données permettent.**
  - La fenêtre de décision est de 5 s (WIN-a). La plage 10 ms - 1 s n'est atteignable avec ces fichiers sur aucun des deux signaux (E13b-d).
  - Les flux KPM sont échantillonnés à 0,25 s (E13b-a). Le coût URLLC exige ≥ 34 paquets par fenêtre dans 99 % des fenêtres : atteint à 5 s pour 7 réservations sur 12, pour 0 sur 12 à ≤ 1 s (E13b-c).
  - Aucune sensibilité à la fenêtre n'a été lancée (E13b-e).
  - La configuration est constante dans les 1 116 réservations (D1-a) : **il n'existe aucune boucle de contrôle observée à une échelle quelconque**, ni lente ni rapide (D1-c).
- **[H] Ce que le papier peut dire.**
  - Le sélecteur est cohérent avec une boucle lente (type rApp), parce qu'il choisit une configuration par contexte sur une fenêtre de 5 s, évaluée au niveau réservation (NO-seq). C'est une cohérence d'échelle, non un résultat.
  - La justification de l'échelle de temps d'un rApp est une **citation manquante** (`TODO-oran-timescales`).
- **Ce que nous ne pouvons pas affirmer.**
  - « Le rApp est suffisant pour tenir le SLA URLLC » : le coût est une **fraction moyenne de paquets** au-dessus de 20 ms sur une fenêtre de 5 s, avec un budget sur la moyenne (COST-a). Aucun résultat ne porte sur des violations plus rapides que la fenêtre.
  - « Le rApp est trop lent » : même absence de donnée, dans l'autre sens.
  - « Un xApp est inutile » ou « compatible avec E2SM-KPM / E2SM-RC » : non testé ; le mappage des 8 actions sur des services E2SM n'est dans aucun document (non retrouvé).
  - Que les actions (PRB et scheduler) imposent un xApp : le fait que les actions soient un partage de PRB et un scheduler est [V] (PLAT-a), mais la conséquence sur la couche d'hébergement n'est pas déductible de nos données.

### B. Garder le CMDP ?

**Réponse : abandonner la revendication séquentielle (CMDP/MDP), garder la contrainte. C'est déjà fait en section 03.**

- **[V]** Les données n'identifient aucune dynamique pilotée par l'action : aucune transition avec changement d'action (D1-a, D1-c), état informatif sur l'action loguée (D4-a), Q-net qui reproduit l'action loguée sur 61-82 % des fenêtres (E2-d, NO-dyn).
- **[V]** La section 03 pose déjà un bandit contextuel contraint (γ = 0) ; le « C » du CMDP reste dans l'objectif : budget de coût moyen d = 0,03, relaxation lagrangienne (SAFE-a).
- **[V]** Le mécanisme dual n'est pas satisfaisant empiriquement : 0/60 (E2-a), 0/15 (E12P-e), aucun α faisable (E11-a). Ce n'est pas une raison de passer à une autre méthode, mais une raison de ne pas écrire « respecte le budget » (NO-budget).
- **[H]** Une nuance : l'agent principal est entraîné avec γ = 0,7 (E12P-b) et lu comme sélecteur à un pas. Les données ne départagent pas γ = 0,7 et γ = 0 (E12-i : résultat dépendant de l'ensemble de scripts, marge mince ; E2-c). Point non tranché (§4.3, §6 n° 5).
- **Ne pas affirmer** : « sans violation de la propriété de Markov », « contrôle séquentiel », « apprend la dynamique ».

### C. Les trois alternatives proposées

| Alternative | Soutenue par nos données ? | [V] Ce que les données montrent | [H] Hypothèse | Ce que nous ne pouvons pas affirmer |
|---|---|---|---|---|
| **Bandits contextuels contraints** | **Oui comme formulation** ; le papier l'a déjà adoptée (section 03). | Pas de séquentialité identifiable (D1-a, D1-c). Une baseline sans apprentissage de ce type existe : table-greedy, choix par bin de charge sous contrainte de table (TG-a). Elle a le meilleur reward DM (9,069) et un coût DM de 0,0217 sur c40f2fe7 (E12-f), mais couverture appariée de 9,5 %. | Un bandit appris (au lieu de la Q-net) ferait au moins aussi bien : plausible, car la Q-net est en dessous du table-greedy transféré (E11-e) et les agents sont au niveau d'always-RR (E12-g). **Non testé** : aucun bandit contextuel appris n'est dans `src/`. | Que le bandit « résout » le problème : (A1) contexte exogène contredite en partie (D7-c), (A2) contredite pour le scheduler (D7-b, D8-b). Qu'il soit sûr : aucune politique démontrée sûre (E12-e). |
| **Conformal risk control** | **Non établi ; aucune analyse dans le dépôt.** | Constats de données [V] ; leur lecture comme obstacles est un raisonnement [H] : un script de test à 90 % (D6-b), donc pas de second script de test pour vérifier une calibration ; bruit entre répétitions du même ordre que d (D6-d) ; sécurité non transférée dans un sens (TR-d) ; le coût n'est observé que pour l'action loguée (couverture appariée 9,5-54,7 % : E12-e). | Une borne de risque conformale sur le coût moyen pourrait être calibrée **au sein d'un script**, sous l'hypothèse d'échangeabilité des réservations dans ce script. **Raisonnement, non testé.** | Une garantie de risque pour un script nouveau (échangeabilité entre scripts non soutenue : A3 de la section 03, TR-d). Toute valeur numérique (couverture, taille d'ensemble) : aucun résultat. Fausserait NO-safe si présenté comme garantie. |
| **Modèle causal structurel du scheduler** | **Non : les données ne séparent pas le scheduler du moment d'exécution.** | PF et RR en blocs disjoints dans 12/12 couples (D7-b), 17/17 non entrelacés (D8-b), blocs à ≈ 8 jours (2 scripts) ou ≈ 13 h (c40f2fe7). PF − RR sur le coût positif 12/12 (D7-a) mais paires proches encore à ≈ 8-9 jours (D8-c). Rupture du coût exactement à la bascule (D8-d). `nof_ue` et débit URLLC dépendent de l'action sur 8 actions (D7-c), non à scheduler fixé (faible puissance). | Une dérive lente produit aussi une coupure (D8-d, rapport SSE 1,08-1,18) : l'effet pourrait être en partie temporel. | Que PF cause plus de violations (NO-pfcause). Un effet causal du scheduler, sous quelque forme. L'identification nécessiterait des relances entrelacées PF/RR (registre §9.3 [Q]), qui n'existent pas. |

**Synthèse de la réponse.**
- *xApp ou rApp* : rApp / boucle lente [H] ; xApp non revendicable (E13b-d, D1-c).
- *CMDP* : abandonner la revendication séquentielle, garder la contrainte à un pas (déjà en section 03). La lacune de séquentialité de nos données est celle que le papier révisé a déjà prise en compte.
- *Alternatives* :
  - bandit contextuel contraint : soutenu comme cadre (déjà adopté), non comme preuve de performance ;
  - conformal risk control : non établi, aucune donnée, obstacles de calibration ;
  - modèle causal du scheduler : non soutenu, car les données ne séparent pas scheduler et moment d'exécution.
- **Ce que la review externe ne peut pas être utilisée pour affirmer** : un chiffre sur la violation de SLA à échelle de ms, une validation Near-RT, ou une garantie de risque.
