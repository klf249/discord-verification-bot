#!/usr/bin/env python
"""
Bot Discord - Point d'entrée principal
Utilise les variables d'environnement directement (pour Render)
"""
import discord
from discord.ext import commands
import os
import sys
import logging
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

# ===== CONFIGURATION DEPUIS LES VARIABLES D'ENVIRONNEMENT =====
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', '0'))
ROLE_ID = int(os.getenv('ROLE_ID', '0'))
VERIFY_CHANNEL_ID = int(os.getenv('VERIFY_CHANNEL_ID', '0'))
STAFF_CHANNEL_ID = int(os.getenv('STAFF_CHANNEL_ID', '0'))
SITE_URL = os.getenv('SITE_URL', 'http://localhost:5000')
BOT_API_URL = os.getenv('BOT_API_URL', 'http://localhost:5001')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///verif.db')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-me')

# Vérification que le token est présent
if not BOT_TOKEN:
    print("❌ ERREUR: BOT_TOKEN non défini dans les variables d'environnement")
    print("   Vérifie que tu as bien ajouté les variables sur Render")
    sys.exit(1)

# ===== IMPORTS (après configuration) =====
from database import init_database
from bot.commands import setup_commands
from bot.views import setup_views
from bot.utils import start_http_server

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class VerificationBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.guild_id = GUILD_ID
        self.http_server = None

    async def setup_hook(self):
        logger.info("🚀 Configuration du bot...")
        init_database()
        await setup_commands(self)
        setup_views(self)
        self.http_server = await start_http_server(self)
        logger.info("✅ Bot configuré avec succès!")

    async def on_ready(self):
        logger.info(f"✅ Bot connecté en tant que {self.user}")
        guild = self.get_guild(self.guild_id)
        if guild:
            logger.info(f"📝 Serveur: {guild.name}")
        else:
            logger.warning(f"⚠️ Serveur avec ID {self.guild_id} non trouvé")
        logger.info("🚀 Bot prêt!")

def main():
    try:
        bot = VerificationBot()
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        logger.error("❌ Token invalide - Vérifie BOT_TOKEN")
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()