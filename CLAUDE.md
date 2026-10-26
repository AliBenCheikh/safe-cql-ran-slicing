# Règles du projet — Safe-CQL RAN Slicing

## Phase en cours : AUDIT en lecture seule

- Ne modifier ni le notebook, ni le manuscrit, ni les données.
- Ne lancer aucun entraînement ni job GPU.
- Ne pas lire les données brutes (dataset ~10 Go sur Google Drive) sauf demande explicite.
- Distinguer explicitement : fait vérifié dans le code / hypothèse à vérifier sur les données / problème confirmé / question ouverte.
- Ne jamais présenter les sorties enregistrées dans le notebook comme des résultats reproduits.
- Ne pas inventer de citations, de résultats ni de garanties.

## Fichiers du projet
- Safe_CQL.pdf : manuscrit original, ne pas modifier
- Safe-CQL-Notebook.ipynb : notebook original, ne pas modifier
- reviews/reviewer_comments.md : rapports des trois reviewers, ne pas modifier
- CLAUDE.md : ce fichier

## Dataset
- Emplacement : Google Drive
- Taille approximative : ~10 Go
- Ne pas copier dans ce dépôt

## Phase 2 : RÉVISION (par étapes)
- Une branche git par étape (revision/NN-nom). Jamais de travail direct sur main.
- Le notebook original et le PDF original ne sont jamais modifiés. Le nouveau code va dans src/.
- Les scripts d'analyse de données sont en lecture seule sur les données (data/ est dans .gitignore).
- Tout chiffre du papier révisé doit venir d'un script reproductible de src/, avec seed et version du dataset.
- Chaque étape se termine par : tests dans tests/, un court rapport dans docs/, un commit.
- Ne jamais inventer de résultats ni de citations.
