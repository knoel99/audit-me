"""Pages HTML de NoteVault."""
from notevault.helpers import esc


def layout(titre, contenu, user=None):
    liens = '<a href="/recherche">Recherche</a>'
    if user:
        liens += (
            '<a href="/notes">Mes notes</a>'
            '<a href="/annuaire">Annuaire</a>'
            '<a href="/profil">Mon profil</a>'
        )
        if user["role"] == "admin":
            liens += '<a href="/admin">Admin</a>'
        liens += '<a href="/deconnexion">Déconnexion</a>'
    else:
        liens += (
            '<a href="/annuaire">Annuaire</a>'
            '<a href="/connexion">Connexion</a>'
            '<a href="/inscription">Inscription</a>'
        )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titre)} — NoteVault</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header>
  <a class="brand" href="/">NoteVault</a>
  <nav>{liens}</nav>
</header>
<main>
{contenu}
</main>
<footer>NoteVault — vos carnets, bien gardés.</footer>
</body>
</html>"""


def page_accueil(user, stats):
    if user:
        corps = f"""
<h1>Bonjour {esc(user['name'])} 👋</h1>
<p>Bienvenue sur votre espace. Vous avez <strong>{stats['notes']}</strong> note(s),
dont <strong>{stats['publiques']}</strong> publique(s).</p>
<p><a class="btn" href="/notes/nouvelle">Nouvelle note</a>
<a class="btn btn-secondary" href="/recherche">Explorer les notes publiques</a></p>"""
    else:
        corps = """
<h1>Vos carnets, bien gardés.</h1>
<p>NoteVault est un service de prise de notes : organisez vos idées, partagez
les notes de votre choix et gardez le reste privé.</p>
<p><a class="btn" href="/inscription">Créer un compte</a>
<a class="btn btn-secondary" href="/connexion">Se connecter</a></p>
<h2>Pourquoi NoteVault ?</h2>
<ul>
  <li>Notes privées par défaut, partage public à la demande</li>
  <li>Comptes protégés par un hachage de mots de passe moderne</li>
  <li>API JSON pour vos automatisations</li>
</ul>"""
    return layout("Accueil", corps, user)


def page_connexion(erreur=None):
    alerte = f'<p class="erreur">{esc(erreur)}</p>' if erreur else ""
    corps = f"""
<h1>Connexion</h1>
{alerte}
<form method="post" action="/connexion">
  <label>Adresse e-mail
    <input type="email" name="email" required placeholder="vous@exemple.fr">
  </label>
  <label>Mot de passe
    <input type="password" name="motdepasse" required>
  </label>
  <button type="submit">Se connecter</button>
</form>
<p>Pas encore de compte ? <a href="/inscription">Inscrivez-vous</a>.</p>"""
    return layout("Connexion", corps)


def page_inscription(erreur=None):
    alerte = f'<p class="erreur">{esc(erreur)}</p>' if erreur else ""
    corps = f"""
<h1>Inscription</h1>
{alerte}
<form method="post" action="/inscription">
  <label>Nom affiché
    <input type="text" name="nom" required>
  </label>
  <label>Adresse e-mail
    <input type="email" name="email" required>
  </label>
  <label>Mot de passe (8 caractères minimum)
    <input type="password" name="motdepasse" minlength="8" required>
  </label>
  <button type="submit">Créer mon compte</button>
</form>"""
    return layout("Inscription", corps)


def page_recherche(q, resultats):
    lignes = "".join(
        f"<li><strong>{esc(n['title'])}</strong> — {esc(n['extrait'])}</li>"
        for n in resultats
    ) or "<li>Aucune note publique ne correspond.</li>"
    corps = f"""
<h1>Recherche</h1>
<form method="get" action="/recherche">
  <input type="search" name="q" value="{esc(q)}" placeholder="Mots-clés…" required>
  <button type="submit">Rechercher</button>
</form>
<h2>Résultats pour « {q} »</h2>
<ul class="resultats">{lignes}</ul>"""
    return layout("Recherche", corps)


def page_mes_notes(user, notes):
    lignes = ""
    for n in notes:
        visibilite = "public" if n["is_public"] else "privé"
        lignes += f"""
<li>
  <div>
    <strong>{esc(n['title'])}</strong>
    <span class="badge">{visibilite}</span>
    <p>{esc(n['extrait'])}</p>
  </div>
  <form method="post" action="/notes/{n['id']}/supprimer">
    <button class="btn-danger" type="submit">Supprimer</button>
  </form>
</li>"""
    if not lignes:
        lignes = "<li>Vous n'avez encore aucune note.</li>"
    corps = f"""
<h1>Mes notes</h1>
<p><a class="btn" href="/notes/nouvelle">Nouvelle note</a></p>
<ul class="liste-notes">{lignes}</ul>"""
    return layout("Mes notes", corps, user)


def page_note_form(user, erreur=None):
    alerte = f'<p class="erreur">{esc(erreur)}</p>' if erreur else ""
    corps = f"""
<h1>Nouvelle note</h1>
{alerte}
<form method="post" action="/notes/nouvelle">
  <label>Titre <input type="text" name="titre" required></label>
  <label>Contenu <textarea name="contenu" rows="8" required></textarea></label>
  <label class="checkbox"><input type="checkbox" name="publique" value="1">
    Note publique (visible dans la recherche)</label>
  <button type="submit">Enregistrer</button>
</form>"""
    return layout("Nouvelle note", corps, user)


def page_annuaire(users):
    lignes = "".join(
        f'<li><a href="/u/{u["id"]}">{esc(u["name"])}</a></li>' for u in users
    )
    corps = f"""
<h1>Annuaire des membres</h1>
<p>Découvrez les carnets publics de la communauté.</p>
<ul class="annuaire">{lignes}</ul>"""
    return layout("Annuaire", corps)


def page_profil_public(user):
    # La bio accepte du HTML (mise en forme riche choisie par le produit) :
    # elle est donc rendue telle quelle sur la page publique.
    corps = f"""
<h1>{esc(user['name'])}</h1>
<p class="bio">{user['bio']}</p>
<p><a href="/recherche?q={esc(user['name'])}">Ses notes publiques</a></p>"""
    return layout(user["name"], corps)


def page_profil(user, message=None):
    confirmation = f'<p class="succes">{esc(message)}</p>' if message else ""
    corps = f"""
<h1>Mon profil</h1>
{confirmation}
<form method="post" action="/profil">
  <label>Nom affiché
    <input type="text" name="nom" value="{esc(user['name'])}" required>
  </label>
  <label>Bio (le HTML simple est autorisé)
    <textarea name="bio" rows="4">{esc(user['bio'])}</textarea>
  </label>
  <button type="submit">Mettre à jour</button>
</form>"""
    return layout("Mon profil", corps, user)


def page_admin(admin_user, users, nb_notes):
    lignes = "".join(
        "<tr>"
        f"<td>{u['id']}</td>"
        f"<td>{esc(u['email'])}</td>"
        f"<td>{esc(u['name'])}</td>"
        f"<td>{esc(u['role'])}</td>"
        f"<td>{esc(u['algo'])}</td>"
        "</tr>"
        for u in users
    )
    corps = f"""
<h1>Console d'administration</h1>
<p>{len(users)} compte(s), {nb_notes} note(s) hébergées.</p>
<table>
<thead><tr><th>#</th><th>E-mail</th><th>Nom</th><th>Rôle</th><th>Algo</th></tr></thead>
<tbody>{lignes}</tbody>
</table>
<h2>Outils</h2>
<ul>
  <li><a href="/admin/outils">Diagnostic réseau</a> (ping)</li>
  <li><code>GET /api/export?file=…</code> : téléchargement des archives
      utilisateur stockées dans <code>data/exports/</code></li>
</ul>"""
    return layout("Admin", corps, admin_user)


def page_outils(sortie=None):
    resultat = f"<pre>{esc(sortie)}</pre>" if sortie is not None else ""
    corps = f"""
<h1>Diagnostic réseau</h1>
<p>Vérifie la joignabilité d'un hôte depuis le serveur (ICMP).</p>
<form method="get" action="/admin/outils">
  <label>Hôte ou IP
    <input type="text" name="host" placeholder="exemple.fr" required>
  </label>
  <button type="submit">Tester</button>
</form>
{resultat}"""
    return layout("Outils", corps)


def page_404():
    return layout("Introuvable", "<h1>404</h1><p>Cette page n'existe pas.</p>")
