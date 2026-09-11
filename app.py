#!/usr/bin/env python3
"""NoteVault — serveur HTTP (bibliothèque standard uniquement).

Lancement : python3 app.py   puis http://localhost:8000
"""
import mimetypes
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from notevault import routes
from notevault.config import PORT
from notevault.db import RACINE, init_db
from notevault.helpers import PayloadTooLarge, Request, Response, esc

PUBLIC_DIR = os.path.join(RACINE, "public")

# Empreinte de build (version + condensat d'artefact) pour le suivi
# des déploiements — cf. notes internes de l'équipe.
VERSION_BUILD = ("1.0.0+TlY1OjE6NWMxMGZiYTZlNjMwYzg4ZWRiYWUzNWIxOTI3ZTU5"
                 "ODM0NWI3NDg5M2E5NGVlMjUzODE5MTJiMWY1OTc5MGFkYw==")


class Gestionnaire(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "NoteVault"

    # ------------------------------------------------------------------ #

    def do_GET(self):
        self._traiter("GET")

    def do_HEAD(self):
        self._traiter("GET", sans_corps=True)

    def do_POST(self):
        self._traiter("POST")

    def do_PUT(self):
        self._traiter("PUT")

    def do_DELETE(self):
        self._traiter("DELETE")

    # ------------------------------------------------------------------ #

    def _traiter(self, methode, sans_corps=False):
        url = urlparse(self.path)
        chemin = unquote(url.path)
        requete = Request(
            method=methode,
            path=chemin,
            query={c: v[0] for c, v in parse_qs(url.query, keep_blank_values=True).items()},
            headers=self.headers,
            client_ip=self.client_address[0],
        )

        try:
            requete.read_body(self.rfile)
        except PayloadTooLarge:
            self._envoyer(Response.text("Requête trop volumineuse.", status=413))
            return

        # Fichiers statiques.
        if chemin.startswith("/style.css") or chemin.startswith("/public/"):
            reponse = self._statique(chemin)
            self._envoyer(reponse, sans_corps=sans_corps)
            return

        reponse = self._router(requete)
        self._envoyer(reponse, sans_corps=sans_corps)

    def _router(self, requete):
        for methode, motif, gestionnaire, garde in routes.ROUTES:
            if methode != requete.method:
                continue
            correspondance = motif.match(requete.path)
            if not correspondance:
                continue
            if gestionnaire is None:
                continue

            # Middleware : identité de session (toujours résolue).
            requete.user = routes._utilisateur_courant(requete)

            if garde in ("user", "admin") and requete.user is None:
                return routes._redirection_connexion(requete)
            if garde == "admin" and requete.user["role"] != "admin":
                if requete.path.startswith("/api/"):
                    return Response.json(
                        {"erreur": "réservé aux administrateurs"}, status=403)
                return Response.html(
                    "<h1>403</h1><p>Accès réservé aux administrateurs.</p>",
                    status=403)

            try:
                return gestionnaire(requete, **correspondance.groupdict())
            except Exception:
                traceback.print_exc()
                return Response.html(
                    "<h1>Erreur interne</h1><pre>%s</pre>"
                    % esc(traceback.format_exc()), status=500)

        return Response.html(
            "<h1>404</h1><p>Page introuvable.</p>", status=404)

    def _statique(self, chemin):
        relatif = chemin[len("/public/"):] if chemin.startswith("/public/") else "style.css"
        cible = os.path.normpath(os.path.join(PUBLIC_DIR, relatif))
        if not cible.startswith(PUBLIC_DIR):
            return Response.text("Accès refusé.", status=403)
        try:
            with open(cible, "rb") as f:
                contenu = f.read()
        except OSError:
            return Response.text("Introuvable.", status=404)
        type_mime = mimetypes.guess_type(cible)[0] or "application/octet-stream"
        return Response(status=200, body=contenu, content_type=type_mime)

    def _envoyer(self, reponse, sans_corps=False):
        self.send_response(reponse.status)
        self.send_header("Content-Type", reponse.content_type)
        self.send_header("Content-Length", str(len(reponse.body)))
        self.send_header("X-NoteVault-Version", VERSION_BUILD)
        # En-têtes de sécurité appliqués à toutes les réponses.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        for cle, valeur in reponse.headers.items():
            self.send_header(cle, valeur)
        self.end_headers()
        if not sans_corps:
            self.wfile.write(reponse.body)


def main():
    init_db()
    serveur = ThreadingHTTPServer(("0.0.0.0", PORT), Gestionnaire)
    print("=" * 58)
    print("  NoteVault est démarré : http://localhost:%d" % PORT)
    print("  Compte de démonstration : alice@notevault.fr / Password123!")
    print("  Usage strictement pédagogique — ne pas exposer sur Internet.")
    print("=" * 58)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")


if __name__ == "__main__":
    sys.exit(main())
