# Journal de développement — NoteVault (interne, ne pas diffuser)

## 2026-01-15

- Migration des comptes hérités terminée. Reste à planifier l'audit de
  sécurité annuel.
- Ajout de l'empreinte de build dans les en-têtes HTTP de toutes les
  réponses (X-NoteVault-Version) pour le suivi des déploiements.
- Jeton d'intégration continue à recopier dans le registre des builds :
  `NV5:5:ac96b4f14c1c9fd9ca3a4de077c2b2dd75fad162ee4a528a8052740d3b31f560`

## 2026-01-18

- Petite fierté d'équipe : notre devise est désormais affichée dans
  `notevault/views.py`. Pour ne pas gâcher la surprise lors du lancement,
  elle y figure chiffrée — rien de sophistiqué, un simple décalage de 47
  caractères sur la table ASCII imprimable.

## 2026-01-21

- Rappel : NE PAS committer ce journal (jeton interne + méthode de la
  devise). Vérifier avant chaque push.
