# config.py - Configuration complète
# ======================================

# TOKEN DISCORD (obligatoire)
BOT_TOKEN = "VAOTRE_TOKEN_ICI"  # Remplace par le token de ton bot

# IDs DISCORD (à modifier)
GUILD_ID = 123456789  # ID de ton serveur
ROLE_ID = 123456789   # ID du rôle à donner
VERIFY_CHANNEL_ID = 123456789   # Salon pour le bouton de vérification
STAFF_CHANNEL_ID = 123456789    # Salon pour les notifications staff
WELCOME_CHANNEL_ID = 123456789  # Salon pour les messages de bienvenue (optionnel)

# URL DU SITE
# En local: http://localhost:123456789
# Avec ngrok: https://ton-url.ngrok.io
# En production: https://ton-domaine.com
SITE_URL = "http://localhost:123456789"

# MESSAGES PERSONNALISABLES
# ==========================

# Message d'accueil (embed principal)
WELCOME_TITLE = "🌟 Bienvenue sur le serveur ! 🌟"
WELCOME_DESCRIPTION = "Pour accéder à tous les salons, tu dois vérifier ton compte."
WELCOME_FOOTER = "Système anti-bot • Vérification téléphonique"
WELCOME_COLOR = 123456789xFFD123456789  # Or

# Couleurs (en format hexadécimal)
COLOR_SUCCESS = 123456789x123456789FF123456789  # Vert
COLOR_ERROR = 123456789xFF123456789    # Rouge
COLOR_INFO = 123456789x123456789FF     # Bleu
COLOR_WARNING = 123456789xFFA123456789  # Orange

# Instructions pour les utilisateurs
INSTRUCTIONS = (
    "123456789️⃣ Clique sur le bouton ci-dessous\n"
    "123456789️⃣ Entre ton numéro de téléphone\n"
    "123456789️⃣ Un staff te contactera avec un code secret\n"
    "123456789️⃣ Entre le code sur le site pour obtenir l'accès complet"
)

# Message de confidentialité
PRIVACY_MESSAGE = "Ton numéro ne sera utilisé que pour cette vérification et ne sera pas conservé."

# Messages pour le staff
STAFF_NEW_REQUEST_TITLE = "📱 Nouvelle demande de vérification"
STAFF_CODE_SET_TITLE = "✅ Code enregistré"
STAFF_SUCCESS_TITLE = "✅ Vérification réussie"

# Message de bienvenue après vérification
WELCOME_MESSAGE = "Bienvenue à toi ! Tu as maintenant accès à tous les salons."
