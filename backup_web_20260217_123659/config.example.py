"""
Configuration Template pour le bot
Les vraies valeurs viendront des variables d'environnement sur Render
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Tokens et IDs
BOT_TOKEN = os.getenv("BOT_TOKEN", "VOTRE_TOKEN_ICI")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
ROLE_ID = int(os.getenv("ROLE_ID", "0"))
VERIFY_CHANNEL_ID = int(os.getenv("VERIFY_CHANNEL_ID", "0"))
STAFF_CHANNEL_ID = int(os.getenv("STAFF_CHANNEL_ID", "0"))
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))

# URL du site (pour les liens)
SITE_URL = os.getenv("SITE_URL", "http://localhost:5000")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///verif.db")

# Sécurité
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")

# Paramètres
SESSION_EXPIRY_HOURS = 1  # Durée de validité des jetons
MAX_ATTEMPTS = 3          # Nombre max de tentatives

# Messages par défaut (personnalisables via commandes)
DEFAULT_WELCOME_TITLE = "🌟 Bienvenue sur le serveur !"
DEFAULT_WELCOME_DESCRIPTION = "Vérifie ton compte pour accéder à tous les salons"
DEFAULT_INSTRUCTIONS = "1️⃣ Clique sur le bouton\n2️⃣ Entre ton numéro\n3️⃣ Reçois un code\n4️⃣ Accès accordé"
DEFAULT_PRIVACY = "Ton numéro est supprimé après vérification"
DEFAULT_COLOR = 0x5865F2  # Bleu Discord
