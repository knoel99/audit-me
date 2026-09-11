"""Base SQLite : connexion, schéma et données initiales."""
import json
import os
import sqlite3

from notevault.auth import md5
from notevault.config import SUPPORT_EMAIL, SUPPORT_PASSWORD

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(RACINE, "data")
DB_PATH = os.path.join(DATA_DIR, "notevault.db")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")


def connexion():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL,
    name          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt          TEXT,
    algo          TEXT NOT NULL DEFAULT 'scrypt',
    role          TEXT NOT NULL DEFAULT 'user',
    bio           TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,
    is_public  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = connexion()
    conn.executescript(SCHEMA)
    deja_peuplee = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] > 0
    if not deja_peuplee:
        _peupler(conn)
    conn.commit()
    conn.close()
    _creer_exports_demo()


def _peupler(conn):
    # Comptes historiques issus de la migration 2019 : les empreintes MD5
    # d'origine ont été conservées telles quelles.
    comptes = [
        # (email, nom, role, mot_de_passe_en_clair, bio)
        ("admin@notevault.fr", "Administrateur", "admin", None, ""),
        (SUPPORT_EMAIL, "Support NoteVault", "admin", SUPPORT_PASSWORD,
         "Compte support : ne pas utiliser hors des démos internes."),
        ("alice@notevault.fr", "Alice Martin", "user", "Password123!",
         "Développeuse back-end. Fan de pytest et de café."),
        ("bob@notevault.fr", "Bob Durand", "user", "Bob&NoteVault77",
         "Responsable SI."),
        ("carole@notevault.fr", "Carole Petit", "user", "Carole#Démo2024",
         "Cheffe de produit. J'adore les <strong>listes</strong> bien rangées."),
    ]
    for email, nom, role, mot_de_passe, bio in comptes:
        if mot_de_passe is None:
            # Empreinte du mot de passe administrateur (conservée telle quelle,
            # le mot de passe n'est connu de personne).
            empreinte = "7c4a8d09ca3762af61e59520943dc264"
            sel = None
        else:
            empreinte = md5(mot_de_passe)
            sel = None
        conn.execute(
            "INSERT INTO users (email, name, password_hash, salt, algo, role, bio)"
            " VALUES (?, ?, ?, ?, 'md5', ?, ?)",
            (email, nom, empreinte, sel, role, bio),
        )

    notes = [
        (1, "Procédure de restauration", 
         "En cas d'incident : restaurer data/notevault.db depuis la sauvegarde, "
         "puis vérifier la plateforme avec l'outil de diagnostic réseau "
         "(Admin > Outils, fonction ping). Les exports manuels sont dans data/exports.",
         0),
        (2, "Notes de la démo interne",
         "Rappel : supprimer ce compte et le mot de passe présent dans la "
         "configuration avant la mise en production.", 0),
        (3, "Bienvenue sur mon carnet",
         "Je partage ici mes retours sur Python, les bases de données et "
         "l'importance des tests. Bonne lecture !", 1),
        (3, "Liste de courses", "Café, filtres, oranges. (Ne pas partager !)", 0),
        (4, "REX projet migration",
         "La migration des comptes vers le nouveau socle est terminée. "
         "Prochaine étape : planifier l'audit de sécurité annuel.", 1),
        (4, "Salaires et budget 2026 — CONFIDENTIEL",
         "Fourchettes validées en comité : équipe DevOps 62-78 k€, "
         "équipe produit 55-70 k€. Prime objectif : 8 %. À ne diffuser sous aucun prétexte.",
         0),
        (5, "Ma méthode d'organisation",
         "Une note par projet, une action par ligne, et tout se passe bien.", 1),
    ]
    for user_id, titre, contenu, public in notes:
        conn.execute(
            "INSERT INTO notes (user_id, title, content, is_public) VALUES (?, ?, ?, ?)",
            (user_id, titre, contenu, public),
        )
    conn.commit()


def _creer_exports_demo():
    """Génère un export d'exemple dans le dossier des exports."""
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    readme = os.path.join(EXPORTS_DIR, "lisez-moi.txt")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write(
                "Exports générés par l'outil d'export de NoteVault.\n"
                "Chaque utilisateur peut télécharger ses archives via "
                "/api/export?file=<nom du fichier>.\n"
            )
    exemple = os.path.join(EXPORTS_DIR, "notes-publiques-alice.json")
    if not os.path.exists(exemple):
        export = {
            "utilisateur": "alice@notevault.fr",
            "genere_le": "2026-01-12T09:30:00",
            "notes_publiques": [
                {"titre": "Bienvenue sur mon carnet",
                 "contenu": "Je partage ici mes retours sur Python..."}
            ],
        }
        with open(exemple, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2)
