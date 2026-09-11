#!/usr/bin/env python3
"""Reconstitue la phrase secrète du corrigé à partir de 5 fragments.

Les fragments suivent un partage de secret de Shamir sur GF(2^8)
(polynôme 0x11B, celui de l'AES), seuil 5 sur 5 : chaque octet du secret
est le terme constant d'un polynôme de degré 4, et le fragment n° i
contient f(i). La phrase secrète se retrouve par interpolation de
Lagrange en x = 0 — d'où la nécessité d'avoir les cinq fragments,
dans n'importe quel ordre.

Usage :
    python3 tools/reassembler.py "NV5:1:<hex>" "NV5:2:<hex>" ... "NV5:5:<hex>"
"""
import sys

POLY_Explication = "GF(2^8), polynôme 0x11B (identique au corps de l'AES)"


def gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x1B
        b >>= 1
    return p


def ginv(a):
    for b in range(1, 256):
        if gmul(a, b) == 1:
            return b
    raise ValueError("élément non inversible")


def lagrange_zero(points):
    """points : liste (x, y) ; renvoie f(0)."""
    resultat = 0
    for i, (xi, yi) in enumerate(points):
        terme = yi
        for j, (xj, _) in enumerate(points):
            if i == j:
                continue
            terme = gmul(terme, gmul(xj, ginv(xi ^ xj)))
        resultat ^= terme
    return resultat


def analyser_fragment(texte):
    texte = texte.strip()
    try:
        prefixe, numero, hexa = texte.split(":")
    except ValueError:
        raise SystemExit(f"fragment illisible (attendu NV5:<numéro>:<hex>) : {texte!r}")
    if prefixe != "NV5":
        raise SystemExit(f"préfixe inattendu dans {texte!r}")
    try:
        x = int(numero)
        y = bytes.fromhex(hexa)
    except ValueError:
        raise SystemExit(f"fragment illisible : {texte!r}")
    return x, y


def main():
    if len(sys.argv) != 6:
        raise SystemExit(__doc__)

    fragments = [analyser_fragment(a) for a in sys.argv[1:]]
    numeros = [x for x, _ in fragments]
    if len(set(numeros)) != 5:
        raise SystemExit(f"il faut les fragments n° 1 à 5, or reçus : {sorted(numeros)}")
    longueurs = {len(y) for _, y in fragments}
    if len(longueurs) != 1:
        raise SystemExit("fragments de longueurs différentes")

    secret = bytes(
        lagrange_zero([(x, y[i]) for x, y in fragments]) for i in range(longueurs.pop())
    )
    print("Fragments acceptés :", ", ".join(str(x) for x in sorted(numeros)))
    print("Corps utilisé      :", POLY_Explication)
    print()
    print("PHRASE SECRETE (hex) :", secret.hex())
    print()
    print("Déchiffrement du corrigé :")
    print("  openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \\")
    print("    -in solutions.enc -out SOLUTIONS.md -pass pass:" + secret.hex())


if __name__ == "__main__":
    main()
