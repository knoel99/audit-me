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

Trouver les **10 failles** de l'application. Le code source est fourni :
l'audit combine donc **lecture du code** et **tests dynamiques** de l'API et
des pages. Chaque faille est exploitable de façon observable (pas de
faille « théorique »).

Barème suggéré : une faille de niveau N rapporte N points (total : 30 points).
Les bonus éventuels rapportent 1 point chacun, dans la limite de 5.

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

## Corrigé

Le corrigé détaillé (emplacement, exploitation, impact, correction) se
trouve dans [`SOLUTIONS.md`](SOLUTIONS.md) — **spoiler** : ne l'ouvrez que
après avoir cherché.

## Structure du dépôt

```
app.py                  Serveur HTTP (stdlib)
notevault/config.py     Configuration de l'application
notevault/db.py         SQLite : schéma et données initiales
notevault/auth.py       Mots de passe et jetons de session
notevault/routes.py     Routes (pages web + API JSON)
notevault/views.py      Gabarits HTML
notevault/helpers.py    Requêtes/réponses, échappement
public/style.css        Feuille de style
data/                   Base et exports (créés au runtime)
```
