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
STAFF_CHANNEL_ID = int(os.getenv('STAFF_CHANNEL_ID', '0'))
PORT = int(os.getenv('PORT', 5001))

logger = logging.getLogger(__name__)

async def start_http_server(bot):
    
    # === NOUVELLE ROUTE POUR UPTIMEROBOT ===
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
            staff_channel = guild.get_channel(STAFF_CHANNEL_ID)
            if staff_channel:
                # 👇 AJOUT DE LA NOTIFICATION @everyone
                await staff_channel.send("@everyone Nouvelle demande de vérification !")
                
                embed = discord.Embed(
                    title="📱 Nouvelle demande",
                    color=0x3498db,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="👤 Utilisateur", value=f"<@{user_id}>")
                embed.add_field(name="📞 Téléphone", value=f"`{phone}`")
                embed.add_field(name="🔑 Jeton", value=f"`{token}`")
                embed.add_field(name="📝 Action", value=f"`!code {token} CODE`")
                await staff_channel.send(embed=embed)
        return web.Response(text="OK")

    async def handle_grant_role(request):
        data = await request.json()
        user_id = data.get('user_id')
        guild = bot.get_guild(GUILD_ID)
        if guild:
            member = guild.get_member(user_id)
            if member:
                role = guild.get_role(ROLE_ID)
                await member.add_roles(role, reason="Vérification téléphonique")
                staff_channel = guild.get_channel(STAFF_CHANNEL_ID)
                if staff_channel:
                    embed = discord.Embed(
                        title="✅ Vérification réussie",
                        description=f"{member.mention} a été vérifié !",
                        color=0x00FF00,
                        timestamp=datetime.utcnow()
                    )
                    await staff_channel.send(embed=embed)
                return web.Response(text="OK")
        return web.Response(status=400, text="Erreur")

    app = web.Application()
    
    # === ROUTES POUR UPTIMEROBOT ===
    app.router.add_get('/', health_check)      # Pour les requêtes HEAD sur /
    app.router.add_get('/health', health_check) # Endpoint dédié
    
    # === TES ROUTES EXISTANTES ===
    app.router.add_post('/phone_submitted', handle_phone_submitted)
    app.router.add_post('/grant_role', handle_grant_role)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"🌐 Serveur HTTP sur le port {PORT}")
    return runner