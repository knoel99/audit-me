"""Configuration de NoteVault."""

PORT = 8000

# Secret de signature des jetons de session.
# TODO: déplacer dans une variable d'environnement avant la mise en prod.
JWT_SECRET = "notevault-secret-2024"

# Compte support pour les démos internes de l'équipe.
# ATTENTION: à supprimer avant la mise en production.
SUPPORT_EMAIL = "support@notevault.fr"
SUPPORT_PASSWORD = "Supp0rt!2024"

# Taille maximale des corps de requête acceptés (octets).
MAX_BODY = 100_000

# Limitation du taux de tentatives de connexion (échecs).
LOGIN_WINDOW_SECONDS = 300
LOGIN_MAX_FAILURES = 5
