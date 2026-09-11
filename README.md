# Audit Me — NoteVault

**NoteVault** est un service de prise de notes : comptes utilisateurs, notes
privées ou publiques, annuaire des membres, recherche, console
d'administration et API JSON.

C'est aussi un **exercice d'audit de sécurité** : l'application contient
**10 failles**, de difficulté croissante (niveau 1 à 5), ainsi que de **vraies
bonnes pratiques de sécurité** qu'il faut aussi savoir repérer et distinguer
des faiblesses.

> ⚠️ Application volontairement vulnérable, à usage **strictement
> pédagogique**. Ne l'exposez pas sur Internet, ne réutilisez aucun des mots
> de passe présents dans ce dépôt.

## Lancement

Aucune dépendance externe : Python 3.10+ et sa bibliothèque standard
suffisent.

```bash
python3 app.py
```

Puis ouvrir <http://localhost:8000>. La base SQLite est créée et initialisée
automatiquement dans `data/` au premier démarrage.

## Compte de démonstration

| Compte | Mot de passe |
|---|---|
| `alice@notevault.fr` | `Password123!` |

D'autres comptes existent (leur trouver l'accès fait partie de l'exercice).

## Votre mission

Trouver les **10 failles** de l'application, **déclarer chacune en issue**,
puis les **corriger en pull request**. Le code source est fourni :
l'audit combine donc **lecture du code** et **tests dynamiques** de l'API et
des pages. Chaque faille est exploitable de façon observable (pas de
faille « théorique »).

Barème suggéré : une faille de niveau N rapporte N points (total : 30 points)
si elle est **trouvée, déclarée correctement en issue et corrigée en PR
fusionnée**. Les bonus éventuels rapportent 1 point chacun, dans la limite
de 5.

| # | Niveau | Domaine d'indice |
|---|:---:|---|
| 1 | ★☆☆☆☆ | Secrets et configuration |
| 2 | ★☆☆☆☆ | Protection des données sensibles |
| 3 | ★★☆☆☆ | Comportement côté client |
| 4 | ★★☆☆☆ | Interactions avec la base de données |
| 5 | ★★★☆☆ | Comportement côté client |
| 6 | ★★★☆☆ | Logique d'accès aux données |
| 7 | ★★★★☆ | Logique d'accès aux données |
| 8 | ★★★★☆ | Sessions et jetons |
| 9 | ★★★★★ | Manipulation de fichiers |
| 10 | ★★★★★ | Interactions avec le système |

### Méthode conseillée

1. Cartographier l'application : pages, formulaires, points d'entrée d'API
   (regarder la table de routage en fin de `notevault/routes.py`).
2. Lire `notevault/config.py`, `notevault/auth.py` et `notevault/db.py` :
   le contexte (migrations, comptes « hérités ») raconte une histoire.
3. Tester chaque hypothèse avec des requêtes réelles (`curl` ou navigateur).
4. Pour chaque faille trouvée : décrire l'impact **concret** (ce qu'un
   attaquant obtient) et la correction à apporter.
5. Bonus : repérer les **bonnes pratiques** déjà en place (il y en a), et
   les petites faiblesses supplémentaires qui ne comptent pas dans les 10.

### Restitution attendue : issues puis pull requests

L'audit se conclut sur GitHub — c'est la restitution qui est notée, pas
seulement la découverte.

**1. Déclarer chaque faille en issue.** Pour chaque faille confirmée, ouvrez
une issue avec le modèle « Signalement de faille » proposé automatiquement :

- titre au format `[Faille Niveau X] brève description`
  (ex. `[Faille Niveau 2] Injection SQL à la connexion`) ;
- renseignez : emplacement (fichier/fonction), étapes de reproduction
  (commandes `curl` ou étapes navigateur), impact concret, correction
  proposée, CWE si vous la connaissez ;
- une faille = une issue ; les bonus sont déclarés de la même façon ;
- ajoutez le label `faille` et le label de niveau (`niveau-1` à `niveau-5`,
  ou `bonus`).

**2. Corriger chaque faille en pull request.**

- une branche par faille, créée depuis `master` :
  `fix/faille-N-description` (ex. `fix/faille-4-injection-sql`) ;
- une PR par issue, qui la référence avec `Fixes #N` ;
- la PR décrit la correction, prouve que l'exploitation de l'issue échoue
  désormais et que le comportement légitime est préservé ;
- **attention** : votre correctif ne doit corriger **que** la faille de
  l'issue — pas les autres (elles valent des points pour le reste de
  l'exercice) ;
- les PR sont revues puis fusionnées par le responsable du dépôt.

> ⚠️ Les issues sont publiques : elles révèlent des éléments de solution aux
> autres participants. Cherchez d'abord, déclarez ensuite.

## Déverrouiller le corrigé (l'épreuve finale)

Le corrigé est publié, mais **chiffré** : [`solutions.enc`](solutions.enc)
(AES-256-CBC, dérivation PBKDF2, 600 000 itérations). La phrase secrète
(64 caractères hexadécimaux) a été découpée avec le **partage de secret de
Shamir** sur GF(2⁸) : **5 fragments, seuil 5** — il faut les cinq pour la
reconstituer, dans n'importe quel ordre, avec
[`tools/reassembler.py`](tools/reassembler.py).

Chaque fragment est caché dans le projet et réclame un **domaine de
compétence différent** :

| Fragment | Domaine requis |
|:---:|---|
| 1 | Protocole HTTP (inspection des réponses du serveur) et encodages |
| 2 | Cryptographie classique |
| 3 | Stéganographie (image) |
| 4 | Analyse de fichiers : encodages exotiques et Unicode |
| 5 | Forensique : l'historique Git ne perd rien |

Repères : chaque fragment se présente sous la forme `NV5:<numéro>:<hex>`.
L'un d'eux n'existe que dans l'historique du dépôt ; un autre ne se voit
qu'en interrogeant le serveur ; les trois derniers sont dans des fichiers
que vous avez déjà sous les yeux.

Une fois la phrase reconstituée :

```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -in solutions.enc -out SOLUTIONS.md -pass pass:<phrase>
```

## Corrigé

Le corrigé détaillé (emplacement, exploitation, impact, correction) est
publié **chiffré** dans [`solutions.enc`](solutions.enc) — voir la section
« Déverrouiller le corrigé » ci-dessus.

## Structure du dépôt

```
app.py                  Serveur HTTP (stdlib)
notevault/config.py     Configuration de l'application
notevault/db.py         SQLite : schéma et données initiales
notevault/auth.py       Mots de passe et jetons de session
notevault/routes.py     Routes (pages web + API JSON)
notevault/views.py      Gabarits HTML
notevault/helpers.py    Requêtes/réponses, échappement
public/                 Feuille de style, logo
tools/reassembler.py    Reconstitution de la phrase secrète (Shamir)
solutions.enc           Corrigé chiffré (AES-256-CBC + PBKDF2)
data/                   Base et exports (créés au runtime)
```
