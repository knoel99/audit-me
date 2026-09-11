"""Hachage de mots de passe et jetons de session (format JWT maison)."""
import base64
import hashlib
import hmac
import json
import secrets

from notevault.config import JWT_SECRET


# ---------------------------------------------------------------------------
# Hachage des mots de passe
# ---------------------------------------------------------------------------

def md5(mot_de_passe):
    """Empreinte MD5 — conservée pour les comptes hérités de la base 2019."""
    return hashlib.md5(mot_de_passe.encode("utf-8")).hexdigest()


def hash_scrypt(mot_de_passe):
    """Hachage scrypt avec sel aléatoire (comptes créés après la migration)."""
    sel = secrets.token_bytes(16)
    empreinte = hashlib.scrypt(
        mot_de_passe.encode("utf-8"), salt=sel, n=2 ** 14, r=8, p=1, dklen=32
    )
    return sel.hex(), empreinte.hex()


def verify_scrypt(mot_de_passe, sel_hex, empreinte_hex):
    try:
        empreinte = hashlib.scrypt(
            mot_de_passe.encode("utf-8"),
            salt=bytes.fromhex(sel_hex),
            n=2 ** 14, r=8, p=1, dklen=32,
        )
    except ValueError:
        return False
    return hmac.compare_digest(empreinte.hex(), empreinte_hex)


# ---------------------------------------------------------------------------
# Jetons de session
# ---------------------------------------------------------------------------

def _b64e(objet):
    brut = json.dumps(objet).encode("utf-8")
    return base64.urlsafe_b64encode(brut).decode("ascii").rstrip("=")


def _b64d(chaine):
    chaine += "=" * (-len(chaine) % 4)
    return json.loads(base64.urlsafe_b64decode(chaine).decode("utf-8"))


def sign_token(charge_utile):
    """Signe une charge utile au format JWT (HS256)."""
    entete = _b64e({"alg": "HS256", "typ": "JWT"})
    corps = _b64e(charge_utile)
    signature = hmac.new(
        JWT_SECRET.encode("utf-8"), f"{entete}.{corps}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{entete}.{corps}.{signature}"


def verify_token(jeton):
    """Vérifie un jeton de session et renvoie la charge utile, sinon None."""
    if not jeton or not isinstance(jeton, str):
        return None
    parties = jeton.split(".")
    try:
        entete = _b64d(parties[0])
        charge = _b64d(parties[1])
    except (ValueError, IndexError):
        return None
    if not isinstance(entete, dict) or not isinstance(charge, dict):
        return None

    # Compatibilité avec l'ancienne intégration interne (jetons non signés).
    if entete.get("alg") == "none":
        return charge

    if len(parties) != 3:
        return None
    attendue = hmac.new(
        JWT_SECRET.encode("utf-8"), f"{parties[0]}.{parties[1]}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(attendue, str(parties[2])):
        return None
    return charge
