#!/usr/bin/env python
"""
Bot Discord - Point d'entrée principal
"""
import discord
from discord.ext import commands
import os
import sys
import logging
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from config import BOT_TOKEN, GUILD_ID
    from database import init_database
    from bot.commands import setup_commands
    from bot.views import setup_views
    from bot.utils import start_http_server
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("Assure-toi d'avoir copié config.example.py vers config.py")
    sys.exit(1)

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
        logger.error("❌ Token invalide")
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
