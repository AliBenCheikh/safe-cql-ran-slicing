# Notes sur le dataset (Open RAN Commercial Traffic Twinning)

Source : Bonati et al., "Twinning Commercial Network Traces on Experimental Open RAN Platforms", ACM WiNTECH 2024.
Chemin des données (lecture seule) : /home/AliBen/data/safe-cql/dataset-kpm

## Montage expérimental (README du dataset)
- 1 station de base, bande de 10 MHz = 50 PRB, 2 slices.
- 8 UE statiques : UE 1-4 = eMBB (slice 0), UE 5-8 = URLLC (slice 1).
- Schedulers : policy 0 = Round-robin (RR), policy 2 = Proportionally fair (PF).
- Trafic jumelé à partir d'un dataset public LTE de 3 stations à Madrid (816, 1835, 2650 MHz).
- Slicings (PRB eMBB / URLLC) : 1 = 9/41, 2 = 21/29, 3 = 30/20, 4 = 39/11, 5 = 50/0.
- Structure : cluster_<1-3>/slicing_<1-5>/scheduling_<0|2>/RESERVATION-<id>/{bs,ue_<IMSI>}.
- Fichiers côté bs : <IMSI>_metrics.csv (KPM PHY/MAC par UE), enb_metrics.csv (débits agrégés), mgen-script-scope.mgn (script de trafic), enb.log.
- Fichiers côté UE : mgen.csv (KPM applicatifs), ue_metrics.csv, ue.log.

## Définitions utilisées dans le projet
- Reward : débit eMBB (Mbps) par fenêtre de 5 s.
- Coût : fraction de paquets URLLC dont la latence dépasse Lmax = à compléter (ms).
- Budget d = 0,03 : source de l'exigence = à compléter.

## Faits établis par les contrôles
- La configuration est constante dans chaque réservation (0/1116 changent).
- Actions : 4 niveaux de PRB eMBB (9/21/30/39) x {RR, PF} = 8 actions.
- Train : clusters 2-3 ; test : cluster 1.
- 706 réservations utilisables sur 1 116.

## Scripts de trafic partagés (md5 de bs/mgen-script-scope.mg*)
- Les scripts sont massivement partagés entre réservations. Les 6 plus fréquents : 275, 270, 187, 120, 115, 60 réservations.
- Les scripts dominants sont dans un seul cluster, avec 4 slicings x 2 schedulers (un script : 1 slicing x 2 schedulers ; un autre : 2 slicings x 2 schedulers).
- Les scripts de 120, 115 et 60 réservations sont presque tous en slicing 5 (aucune réservation utilisable). Seuls 3 scripts sont utilisables avec 4 slicings x 2 schedulers : a908e4cc (cluster 2), a53521b2 (cluster 3), c40f2fe7 (cluster 1 = test).
- Même script ne garantit pas la même charge observée (début de réservation, nof_ue, radio).
- Exogénéité du trafic (boucle ouverte) : supposée, non vérifiée (protocole de transport MGEN non précisé dans le README).

## Ce que le dataset ne permet pas
- Aucune transition avec changement d'action : pas de contrôle séquentiel identifiable.

## Résultats de D6 (docs/d6_shared_scripts.md)
- 19 scripts distincts, aucun partagé entre clusters.
- Test (cluster 1) : 196 réservations dont 90 % sur un seul script (c40f2fe7). Train : 8 scripts, 94 % des réservations sur 2 scripts.
- Les intervalles par réservation sous-estiment l'incertitude : l'unité indépendante est le script.
- Les schedulers ont tourné par blocs dans le temps (PF puis RR, ordre supposé chronologique d'après les identifiants) : effet scheduler potentiellement confondu avec le moment d'exécution.
- Trafic MGEN en UDP périodique (boucle ouverte) ; indépendance de nof_ue et du débit reçu vis-à-vis de l'action : non vérifiée.

## Résultats de D6 (docs/d6_shared_scripts.md)
- 19 scripts distincts, aucun partagé entre clusters.
- Test (cluster 1) : 196 réservations dont 90 % sur un seul script (c40f2fe7). Train : 8 scripts, 94 % des réservations sur 2 scripts.
- Les intervalles par réservation sous-estiment l'incertitude : l'unité indépendante est le script.
- Les schedulers ont tourné par blocs dans le temps (PF puis RR, ordre supposé chronologique d'après les identifiants) : effet scheduler potentiellement confondu avec le moment d'exécution.
- Trafic MGEN en UDP périodique (boucle ouverte) ; indépendance de nof_ue et du débit reçu vis-à-vis de l'action : non vérifiée.
