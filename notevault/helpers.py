"""Boîte à outils HTTP : requêtes, réponses, échappement HTML."""
import json
from html import escape
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

from notevault.config import MAX_BODY


def esc(valeur):
    """Échappe une valeur pour un affichage HTML sûr (contexte texte/attribut)."""
    return escape(str(valeur), quote=True)


class PayloadTooLarge(Exception):
    pass


class Request:
    """Requête entrante, remplie par le serveur puis passée aux routes."""

    def __init__(self, method, path, query, headers, client_ip):
        self.method = method
        self.path = path
        self.query = query          # dict str -> str (première valeur)
        self.headers = headers
        self.client_ip = client_ip
        self.form = {}              # corps urlencoded
        self.json = None            # corps JSON (dict) le cas échéant
        self.user = None            # rempli par le middleware d'authentification
        self._raw_body = b""

    def read_body(self, rfile):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise PayloadTooLarge()
        if length:
            self._raw_body = rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type and self._raw_body:
            try:
                self.json = json.loads(self._raw_body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self.json = None
        elif "application/x-www-form-urlencoded" in content_type and self._raw_body:
            try:
                parsed = parse_qs(self._raw_body.decode("utf-8"), keep_blank_values=True)
                self.form = {cle: valeurs[0] for cle, valeurs in parsed.items()}
            except UnicodeDecodeError:
                self.form = {}

    @property
    def cookies(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            pass
        return {cle: morsel.value for cle, morsel in cookie.items()}


class Response:
    def __init__(self, status=200, body="", content_type="text/html; charset=utf-8", headers=None):
        self.status = status
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.content_type = content_type
        self.headers = headers or {}

    @classmethod
    def html(cls, contenu, status=200, headers=None):
        return cls(status=status, body=contenu, headers=headers)

    @classmethod
    def text(cls, contenu, status=200, headers=None):
        return cls(status=status, body=contenu, content_type="text/plain; charset=utf-8", headers=headers)

    @classmethod
    def json(cls, donnees, status=200, headers=None):
        corps = json.dumps(donnees, ensure_ascii=False, indent=2)
        return cls(status=status, body=corps, content_type="application/json; charset=utf-8", headers=headers)

    @classmethod
    def redirect(cls, location):
        return cls(status=302, body="", headers={"Location": location})

    def set_cookie(self, nom, valeur, max_age=None, expire=False):
        morceau = f"{nom}={valeur}; Path=/; HttpOnly; SameSite=Lax"
        if expire:
            morceau += "; Max-Age=0"
        elif max_age:
            morceau += f"; Max-Age={max_age}"
        self.headers["Set-Cookie"] = morceau
        return self
