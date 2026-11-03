# Étape 18 : section 05 « Evaluation Protocol » (`paper/sections/05_evaluation.tex`)

Réécriture de V-E (OPE) et VI-A (protocole) du PDF original. Le PDF et le notebook ne sont pas modifiés. Les sections 03 et 04 sont référencées (`sec:formulation`, `sec:assumptions`, `sec:methods`, `sec:alpha`, `sec:lambda_diag`), non répétées. Les résultats iront dans une autre section (`sec:results` reste un renvoi pendant).
Registre : section 11 ajoutée (EST-a, EST-b, EST-c, BOOT-a, GRP-a, PREREG-a, FREEZE-a, CRIT-a, CONV-a, FOLD-a). Test : `tests/test_paper_05_evaluation.py` (identifiants existants, phrases sans `% REG:`, constantes du texte présentes dans `src/e12_final.py`). Vérificateur : 163 OK, 0 ABSENT, 2 AMBIGU (D4-a, COST-a, préexistants).

## Liste 1 : phrases de l'original supprimées ou changées

| # | original | sort | raison |
|---|---|---|---|
| 1 | VI-A : « All agents are trained on clusters 2 and 3 and evaluated on the held-out cluster 1, measuring generalization to one unseen deployment cluster » | changé : « le test est un script (90 %), évaluation conditionnelle à ce script » | NO-general ; D6-b, D6-c ; R2-W2 |
| 2 | VI-A : « Features are normalized using training-split statistics only » | déplacé en section 04 | SCALE-a |
| 3 | VI-A : « BC and CQL are each trained with five random seeds and Safe-CQL with two; we report mean and standard deviation across seeds » | changé : 5 seeds pour toutes les configurations d'E12, écart-type avec ddof = 1 rapporté à part | E12P-a, BOOT-a ; audit (2 seeds, ddof = 0) |
| 4 | VI-A : « Reward is eMBB throughput (Mbps) and cost the URLLC violation rate against Lmax = 20 ms » | déplacé en section 03 | REW-a, COST-a |
| 5 | VI-A : « Training convergence is shown in Fig. 2, and the multiplier and constraint dynamics of the safe agent in Fig. 3: λ climbs monotonically while the tabular cost is driven onto the 3% budget » | supprimé | sorties enregistrées du notebook (NO-notebook) ; AU-f ; E2-a (0/60 convergés) ; NO-budget |
| 6 | V-E : « An offline policy cannot be run on the live network, so evaluation is off-policy; we use two primary estimators and one independent check and rely on their agreement » | changé : deux estimateurs, pas de « vérification indépendante », pas d'« accord » comme garantie | AU-e, NO-fqe |
| 7 | V-E : « The matching estimator averages the true measured reward and cost on held-out transitions where the policy's action equals the logged one (unbiased but limited to matched coverage ≈ 40%) » | changé : « sans biais » supprimé ; confusion avec le bloc d'exécution, sous-ensemble dépendant de la politique, estimateur non défini si aucune fenêtre appariée ; « ≈ 40 % » supprimé | EST-b, E12-c, D8-b |
| 8 | V-E : « Tabular OPE reads the empirical (action, load-bin) reward and cost of the chosen action in every test state, covering the full distribution and producing the headline numbers of Table II » | renommé « direct method », « headline numbers » supprimé, circularité dite | EST-a, AU-c, E12-f |
| 9 | V-E : « Fitted Q Evaluation (FQE), structurally independent… guards against a shared bias… we use it to confirm the agent ranking » | supprimé ; la section dit qu'aucun FQE ni OPE à poids d'importance n'est utilisé | AU-e : FQE du notebook incorrect ; NO-fqe |
| 10 | V-E : « Since the configuration is fixed within each logged episode, none of the estimators observes a mid-episode action switch, so all are proxies for—not substitutes for—online evaluation » | gardé (reformulé) | D1-a, D1-c |
| 11 | Table II et le texte de VI-C (« 25–47% », « 1–2% ») | non repris (autre section) | AU, NO-notebook |
| 12 | Aucun intervalle, aucun pré-enregistrement ni gel dans l'original | ajouts : bootstrap B = 2 000 par script, pré-enregistrement, empreinte, verrou | R3-W1, R1-W2 |

## Liste 2 : phrases de la section 05 que le registre ne suffit pas à soutenir

| # | phrase (section 05) | ce qui manque | support actuel |
|---|---|---|---|
| 1 | « The first reading … its results were known to us » | E12-k dit « seconde lecture » ; « résultats connus de l'auteur et de l'assistant » est dans le rapport d'attente | `e12_attente_pre_test.md` §1 |
| 2 | « several of [the expectations] restate results of the first reading » | idem ; la ligne E12-k n'énonce pas que les attentes (a) à (e) reprennent la phase 2 | `e12_attente_pre_test.md` §1 et §3 |
| 3 | « the descriptive analyses of the scheduler order and of the execution blocks had examined the main test script without tuning anything » | seul un paragraphe d'introduction du registre (§2), non une ligne, et l'addendum de l'attente | registre §2 (introduction), `e12_attente_pre_test.md` (addendum D6-D8) |
| 4 | « Two aggregates of the test script… had also been displayed during an earlier diagnostic » | E12-k : « agrégats vus en E1 consignés » ; le détail (parts de bins, nombre d'actions) est dans l'attente | `e12_attente_pre_test.md` (« Transparence ») |
| 5 | (remplacée, étape a) « We therefore never use the test to choose a configuration, a hyperparameter or a rule » → « α was selected on validation folds, not on the test script, and the other hyperparameters … were fixed by us and not tuned » | α : E11 (validation, test non lu). Autres hyperparamètres : « choix de l'analyste, non réglés » (OPT-a, IQL-a). La formule « all hyperparameters … selected on validation folds » est contredite par OPT-a/IQL-a et n'a pas été retenue. Non vérifié pour la phase 2 et le notebook (BC-a) | E12-k, E11-b, OPT-a, IQL-a |
| 6 | « We use both and look for agreement of their ordering, and we do not average them » | choix de méthode d'auteur, pas un fait | E12-c (ordre vérifié sur c40f2fe7) |
| 7 | « Both estimators are computed per reservation as ratios of sums, so that every window weighs equally within a resampled sample » | « chaque fenêtre pèse autant » est une conséquence arithmétique de EST-c, pas écrite dans le registre | EST-c |
| 8 | « the matched subset depends on the policy » | E12-c limites : « le sous-ensemble dépend de la politique » | E12-c |
| 9 | « the matched intervals overlap widely » | E12-c dit « se recouvrent largement entre Safe-CQL et CQL/IQL » ; la généralisation à tous les groupes n'est pas vérifiée | E12-c |
| 10 | « a script with fewer than ten test reservations is flagged… and its intervals are not interpreted » | le signalement est dans GRP-a ; « non interprétés » vient de E12-j (« à ne pas utiliser pour des affirmations par script ») | GRP-a, E12-j |
| 11 | (remplacée, étape a) « the evaluation lacks power » → « the upper bound of every matched interval exceeds d = 0.03 (E12-e), so no policy is demonstrated safe » | E12-e : les 10 bornes hautes appariées dépassent d ; aucune analyse de puissance n'existe, d'où le retrait de l'expression | E12-e |
| 12 | « These thresholds are arbitrary » | E12-i : le critère de 2 écarts-types est arbitraire ; la généralisation aux seuils de 10 % et 50 % vient du rapport d'attente | E12-i, `e12_attente_pre_test.md` §3 |
| 13 | « The test split is not read for these folds » | E11-a dit `test_split_read: false` dans E11 ; E2 le dit aussi | E11-a, FOLD-a |
| 14 | « The validation tables are fitted on the validation fold itself » | FOLD-a l'énonce ; la conséquence sur l'interprétation n'est pas testée | FOLD-a |
| 15 | « The scheduler is associated with a higher cost in 12 of 12 pairs » | D7-a : le chiffre 12/12 est sur les couples (script, slicing) d'entraînement et de test, SE naïves | D7-a, D7-b |
| 16 | « A table built on the same cells has a higher DM reward and a lower DM cost than the learned agents on the main test script » | E12-f/E12-a donnent les chiffres ; « plus bas que Safe-CQL » : 0,0217 contre 0,0305-0,0315, intervalles non comparés | E12-a, E12-f |
| 17 | « The code that reads the test refuses to run unless… » (cinq conditions) | FREEZE-a est une lecture du code, non d'un test d'intégration ; la garde est testée dans `tests/test_e12.py` (non lu) | FREEZE-a |
| 18 | « the matched estimator … does not read the tables » | vrai dans `_res_sums` ; mais la fonction `evaluate_once` calcule aussi les tables DM sur la même frame | EST-b |
| 19 | « the training tables transfer across scripts… checked in one direction only » | TR-d concerne les tables de coût pour table-greedy, pas toutes les tables | TR-a, TR-d |

## Points ouverts pour la suite

- Renvois pendants : `sec:results`.
- Référence : aucune nouvelle `\cite` dans cette section.
- Les trois assumptions A1 à A3 sont reprises de la section 03 (`sec:assumptions`) ; A1 et A2 y sont déjà dites non vérifiées.
