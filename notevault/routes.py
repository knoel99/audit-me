"""Routes de NoteVault (pages web + API JSON)."""
import os
import re
import sqlite3
import subprocess
import time

from notevault import views
from notevault.auth import md5, hash_scrypt, sign_token, verify_scrypt, verify_token
from notevault.config import LOGIN_MAX_FAILURES, LOGIN_WINDOW_SECONDS
from notevault.db import EXPORTS_DIR, connexion
from notevault.helpers import Response, esc

# ---------------------------------------------------------------------------


def _utilisateur_courant(req):
    """Charge l'utilisateur correspondant au jeton de session (relecture en
    base à chaque requête pour toujours utiliser des données à jour)."""
    jeton = req.cookies.get("session")
    charge = verify_token(jeton)
    if not charge:
        return None
    try:
        sous = int(charge.get("sub", 0))
    except (TypeError, ValueError):
        return None
    conn = connexion()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (sous,)).fetchone()
    conn.close()
    return user


def _redirection_connexion(req):
    if req.path.startswith("/api/"):
        return Response.json({"erreur": "authentification requise"}, status=401)
    return Response.redirect("/connexion")


def _page_protegee(req):
    """Barrière d'authentification pour les pages HTML."""
    if req.user is None:
        return _redirection_connexion(req)
    return None


# ---------------------------------------------------------------------------
# Accueil, pages publiques
# ---------------------------------------------------------------------------

def accueil(req):
    user = req.user
    stats = {"notes": 0, "publiques": 0}
    if user:
        conn = connexion()
        ligne = conn.execute(
            "SELECT COUNT(*) AS n,"
            " SUM(CASE WHEN is_public = 1 THEN 1 ELSE 0 END) AS p"
            " FROM notes WHERE user_id = ?",
            (user["id"],),
        ).fetchone()
        stats = {"notes": ligne["n"], "publiques": ligne["p"] or 0}
        conn.close()
    return Response.html(views.page_accueil(user, stats))


def annuaire(req):
    conn = connexion()
    users = conn.execute(
        "SELECT id, name FROM users ORDER BY name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return Response.html(views.page_annuaire(users, req.user))


def profil_public(req, identifiant):
    conn = connexion()
    user = conn.execute(
        "SELECT id, name, bio FROM users WHERE id = ?", (identifiant,)
    ).fetchone()
    conn.close()
    if not user:
        return Response.html(views.page_404(), status=404)
    return Response.html(views.page_profil_public(user, req.user))


def recherche(req):
    q = req.query.get("q", "")
    resultats = []
    if q:
        conn = connexion()
        lignes = conn.execute(
            "SELECT id, title, substr(content, 1, 140) AS extrait FROM notes"
            " WHERE is_public = 1 AND (title LIKE ? OR content LIKE ?)"
            " ORDER BY id DESC LIMIT 20",
            (f"%{q}%", f"%{q}%"),
        ).fetchall()
        conn.close()
        resultats = lignes
    return Response.html(views.page_recherche(q, resultats, req.user))


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

_echecs_connexion = {}  # ip -> liste des horodatages d'échec


def _enregistrer_echec(ip):
    maintenant = time.time()
    fenetre = _echecs_connexion.setdefault(ip, [])
    fenetre[:] = [t for t in fenetre if maintenant - t < LOGIN_WINDOW_SECONDS]
    fenetre.append(maintenant)


def _trop_de_tentatives(ip):
    maintenant = time.time()
    fenetre = [t for t in _echecs_connexion.get(ip, []) if maintenant - t < LOGIN_WINDOW_SECONDS]
    return len(fenetre) >= LOGIN_MAX_FAILURES


def formulaire_connexion(req):
    return Response.html(views.page_connexion())


def connexion_post(req):
    email = (req.form.get("email") or "").strip()
    mot_de_passe = req.form.get("motdepasse") or ""

    if _trop_de_tentatives(req.client_ip):
        return Response.html(views.page_connexion(
            "Trop de tentatives. Réessayez dans quelques minutes."), status=429)

    conn = connexion()
    user = None

    # 1) Comptes hérités de la base 2019 : vérification MD5 conservée
    #    telle quelle pour ne pas casser les clients historiques.
    sql = ("SELECT * FROM users WHERE email = '%s' AND password_hash = '%s'"
           " LIMIT 1" % (email, md5(mot_de_passe)))
    try:
        user = conn.execute(sql).fetchone()
    except sqlite3.Error as err:
        conn.close()
        return Response.html(views.page_connexion(
            "Erreur interne : %s" % err), status=500)

    # 2) Comptes modernes : scrypt + sel, requête paramétrée.
    if user is None:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        if user is not None and user["algo"] == "scrypt":
            if not verify_scrypt(mot_de_passe, user["salt"] or "", user["password_hash"]):
                user = None
        else:
            user = None
    conn.close()

    if user is None:
        _enregistrer_echec(req.client_ip)
        return Response.html(views.page_connexion("Identifiants invalides."),
                             status=401)

    jeton = sign_token({"sub": user["id"], "email": user["email"]})
    rep = Response.redirect("/")
    rep.set_cookie("session", jeton, max_age=86400)
    return rep


def formulaire_inscription(req):
    return Response.html(views.page_inscription())


def inscription_post(req):
    nom = (req.form.get("nom") or "").strip()
    email = (req.form.get("email") or "").strip().lower()
    mot_de_passe = req.form.get("motdepasse") or ""

    if not nom or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return Response.html(views.page_inscription("Nom ou e-mail invalide."), status=400)
    if len(mot_de_passe) < 8:
        return Response.html(views.page_inscription(
            "Le mot de passe doit contenir au moins 8 caractères."), status=400)

    conn = connexion()
    existe = conn.execute(
        "SELECT 1 FROM users WHERE email = ?", (email,)
    ).fetchone()
    if existe:
        conn.close()
        return Response.html(views.page_inscription("Cet e-mail est déjà utilisé."), status=400)

    sel_hex, empreinte = hash_scrypt(mot_de_passe)
    curseur = conn.execute(
        "INSERT INTO users (email, name, password_hash, salt, algo, role, bio)"
        " VALUES (?, ?, ?, ?, 'scrypt', 'user', '')",
        (email, nom, empreinte, sel_hex),
    )
    identifiant = curseur.lastrowid
    conn.commit()
    conn.close()

    jeton = sign_token({"sub": identifiant, "email": email})
    rep = Response.redirect("/")
    rep.set_cookie("session", jeton, max_age=86400)
    return rep


def deconnexion(req):
    rep = Response.redirect("/")
    rep.set_cookie("session", "", expire=True)
    return rep


# ---------------------------------------------------------------------------
# Notes (interface web)
# ---------------------------------------------------------------------------

def mes_notes(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    conn = connexion()
    notes = conn.execute(
        "SELECT id, title, is_public, substr(content, 1, 120) AS extrait"
        " FROM notes WHERE user_id = ? ORDER BY id DESC",
        (req.user["id"],),
    ).fetchall()
    conn.close()
    return Response.html(views.page_mes_notes(req.user, notes))


def formulaire_note(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    return Response.html(views.page_note_form(req.user))


def creer_note(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    titre = (req.form.get("titre") or "").strip()
    contenu = (req.form.get("contenu") or "").strip()
    if not titre or not contenu:
        return Response.html(views.page_note_form(req.user, "Titre et contenu obligatoires."), status=400)
    conn = connexion()
    conn.execute(
        "INSERT INTO notes (user_id, title, content, is_public) VALUES (?, ?, ?, ?)",
        (req.user["id"], titre, contenu, 1 if req.form.get("publique") else 0),
    )
    conn.commit()
    conn.close()
    return Response.redirect("/notes")


def supprimer_note(req, identifiant):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    conn = connexion()
    conn.execute(
        "DELETE FROM notes WHERE id = ? AND user_id = ?",
        (identifiant, req.user["id"]),
    )
    conn.commit()
    conn.close()
    return Response.redirect("/notes")


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------

def formulaire_profil(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    return Response.html(views.page_profil(req.user))


def profil_post(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    nom = (req.form.get("nom") or "").strip()
    bio = req.form.get("bio") or ""
    if not nom:
        return Response.html(views.page_profil(req.user, "Le nom est obligatoire."), status=400)
    conn = connexion()
    conn.execute(
        "UPDATE users SET name = ?, bio = ? WHERE id = ?",
        (nom, bio, req.user["id"]),
    )
    conn.commit()
    conn.close()
    return Response.redirect("/profil?ok=1")


def profil_avec_message(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    message = "Profil mis à jour." if req.query.get("ok") else None
    return Response.html(views.page_profil(req.user, message))


# ---------------------------------------------------------------------------
# Administration
# ---------------------------------------------------------------------------

def _exiger_admin(req):
    if req.user is None:
        return _redirection_connexion(req)
    if req.user["role"] != "admin":
        return Response.json({"erreur": "réservé aux administrateurs"}, status=403) \
            if req.path.startswith("/api/") else Response.text("Accès refusé.", status=403)
    return None


def console_admin(req):
    barriere = _exiger_admin(req)
    if barriere:
        return barriere
    conn = connexion()
    users = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    nb_notes = conn.execute("SELECT COUNT(*) AS n FROM notes").fetchone()["n"]
    conn.close()
    return Response.html(views.page_admin(req.user, users, nb_notes))


def outils_admin(req):
    barriere = _exiger_admin(req)
    if barriere:
        return barriere
    sortie = None
    hote = req.query.get("host", "").strip()
    if hote:
        # Diagnostic ICMP de l'hôte demandé.
        sortie = subprocess.getoutput("ping -c 1 -W 2 %s" % hote)
    return Response.html(views.page_outils(req.user, sortie))


# ---------------------------------------------------------------------------
# API JSON
# ---------------------------------------------------------------------------

def api_sante(req):
    return Response.json({"status": "ok", "service": "notevault", "version": "1.0.0"})


def api_moi(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    u = req.user
    return Response.json({
        "id": u["id"], "email": u["email"], "name": u["name"],
        "role": u["role"], "bio": u["bio"],
    })


CHAMPS_PROFIL = ["name", "bio", "role"]  # champs du schéma users modifiables


def api_profil_put(req):
    """Mise à jour générique : applique les champs fournis dans le corps."""
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    corps = req.json
    if not isinstance(corps, dict):
        return Response.json({"erreur": "corps JSON requis"}, status=400)
    maj = {champ: corps[champ] for champ in CHAMPS_PROFIL if champ in corps}
    if not maj:
        return Response.json({"erreur": "aucun champ reconnu"}, status=400)
    clause = ", ".join("%s = ?" % champ for champ in maj)
    conn = connexion()
    conn.execute(
        "UPDATE users SET %s WHERE id = ?" % clause,
        (*maj.values(), req.user["id"]),
    )
    conn.commit()
    conn.close()
    return Response.json({"message": "profil mis à jour", "champs": list(maj)})


def api_notes_liste(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    conn = connexion()
    notes = conn.execute(
        "SELECT id, title, is_public, created_at FROM notes"
        " WHERE user_id = ? ORDER BY id DESC",
        (req.user["id"],),
    ).fetchall()
    conn.close()
    return Response.json({"notes": [dict(n) for n in notes]})


def api_notes_creation(req):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    corps = req.json or {}
    titre = str(corps.get("title") or "").strip()
    contenu = str(corps.get("content") or "").strip()
    if not titre or not contenu:
        return Response.json({"erreur": "title et content requis"}, status=400)
    conn = connexion()
    curseur = conn.execute(
        "INSERT INTO notes (user_id, title, content, is_public) VALUES (?, ?, ?, ?)",
        (req.user["id"], titre, contenu, 1 if corps.get("is_public") else 0),
    )
    conn.commit()
    identifiant = curseur.lastrowid
    conn.close()
    return Response.json({"id": identifiant, "message": "note créée"}, status=201)


def api_note_detail(req, identifiant):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    conn = connexion()
    note = conn.execute(
        "SELECT id, user_id, title, content, is_public, created_at"
        " FROM notes WHERE id = ?",
        (identifiant,),
    ).fetchone()
    conn.close()
    if not note:
        return Response.json({"erreur": "note inconnue"}, status=404)
    return Response.json({"note": dict(note)})


def api_note_suppression(req, identifiant):
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    conn = connexion()
    note = conn.execute("SELECT * FROM notes WHERE id = ?", (identifiant,)).fetchone()
    if not note:
        conn.close()
        return Response.json({"erreur": "note inconnue"}, status=404)
    conn.execute("DELETE FROM notes WHERE id = ?", (identifiant,))
    conn.commit()
    conn.close()
    return Response.json({"message": "note supprimée"})


def api_export(req):
    """Télécharge un fichier d'archive depuis le dossier des exports."""
    barriere = _page_protegee(req)
    if barriere:
        return barriere
    fichier = req.query.get("file", "")
    if not fichier:
        return Response.json({"erreur": "paramètre file requis"}, status=400)
    cible = os.path.join(EXPORTS_DIR, fichier)
    try:
        with open(cible, "r", encoding="utf-8", errors="replace") as f:
            contenu = f.read()
    except FileNotFoundError:
        return Response.json({"erreur": "archive inconnue"}, status=404)
    except OSError:
        return Response.json({"erreur": "lecture impossible"}, status=400)
    return Response.text(contenu)


# ---------------------------------------------------------------------------
# Table de routage : (méthode, regex, gestionnaire, garde)
# ---------------------------------------------------------------------------

ROUTES = [
    ("GET", re.compile(r"^/$"), accueil, "public"),
    ("GET", re.compile(r"^/style\.css$"), None, "static"),  # géré par app.py
    ("GET", re.compile(r"^/annuaire$"), annuaire, "public"),
    ("GET", re.compile(r"^/recherche$"), recherche, "public"),
    ("GET", re.compile(r"^/u/(?P<identifiant>\d+)$"), profil_public, "public"),
    ("GET", re.compile(r"^/connexion$"), formulaire_connexion, "public"),
    ("POST", re.compile(r"^/connexion$"), connexion_post, "public"),
    ("GET", re.compile(r"^/inscription$"), formulaire_inscription, "public"),
    ("POST", re.compile(r"^/inscription$"), inscription_post, "public"),
    ("GET", re.compile(r"^/deconnexion$"), deconnexion, "public"),
    ("GET", re.compile(r"^/notes$"), mes_notes, "user"),
    ("GET", re.compile(r"^/notes/nouvelle$"), formulaire_note, "user"),
    ("POST", re.compile(r"^/notes/nouvelle$"), creer_note, "user"),
    ("POST", re.compile(r"^/notes/(?P<identifiant>\d+)/supprimer$"), supprimer_note, "user"),
    ("GET", re.compile(r"^/profil$"), profil_avec_message, "user"),
    ("POST", re.compile(r"^/profil$"), profil_post, "user"),
    ("GET", re.compile(r"^/admin$"), console_admin, "admin"),
    ("GET", re.compile(r"^/admin/outils$"), outils_admin, "admin"),
    ("GET", re.compile(r"^/api/health$"), api_sante, "public"),
    ("GET", re.compile(r"^/api/me$"), api_moi, "user"),
    ("PUT", re.compile(r"^/api/profile$"), api_profil_put, "user"),
    ("GET", re.compile(r"^/api/notes$"), api_notes_liste, "user"),
    ("POST", re.compile(r"^/api/notes$"), api_notes_creation, "user"),
    ("GET", re.compile(r"^/api/notes/(?P<identifiant>\d+)$"), api_note_detail, "user"),
    ("DELETE", re.compile(r"^/api/notes/(?P<identifiant>\d+)$"), api_note_suppression, "user"),
    ("GET", re.compile(r"^/api/export$"), api_export, "user"),
]
