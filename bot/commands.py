"""
Commandes du bot Discord (version minimale: uniquement !setup / !setup_default)
"""
import discord
from discord.ext import commands
from discord.ui import Button, View
import secrets
from datetime import datetime, timedelta
import logging
import os
import sys
import asyncio
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database import get_db  # utilisé pour insérer le token

# ===== CONFIGURATION DEPUIS VARIABLES D'ENVIRONNEMENT =====
SITE_URL = os.getenv('SITE_URL', 'https://verification-site-pkos.onrender.com')
SESSION_EXPIRY_HOURS = int(os.getenv('SESSION_EXPIRY_HOURS', '1'))
DEFAULT_WELCOME_TITLE = os.getenv('DEFAULT_WELCOME_TITLE', '🌟 Bienvenue sur le serveur !')
DEFAULT_WELCOME_DESCRIPTION = os.getenv('DEFAULT_WELCOME_DESCRIPTION', 'Vérifie ton compte pour accéder à tous les salons')
DEFAULT_INSTRUCTIONS = os.getenv('DEFAULT_INSTRUCTIONS', '1️⃣ Clique sur le bouton\n2️⃣ Entre ton numéro\n3️⃣ Reçois un code\n4️⃣ Accès accordé')
DEFAULT_PRIVACY = os.getenv('DEFAULT_PRIVACY', 'Ton numéro est supprimé après vérification')
DEFAULT_COLOR = int(os.getenv('DEFAULT_COLOR', '0x5865F2'), 16)

logger = logging.getLogger(__name__)

# Verrou pour éviter les doubles exécutions de commandes interactives
user_locks = defaultdict(asyncio.Lock)

class VerifyButton(Button):
    def __init__(self):
        super().__init__(
            label="🔐 Vérifier mon compte",
            style=discord.ButtonStyle.primary,
            custom_id="persistent_verify_button"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        logger.info(f"SITE_URL utilisé pour ce lien : {SITE_URL}")

        token = secrets.token_urlsafe(16)
        expires = datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)

        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO verifications (token, user_id, expires_at) VALUES (%s, %s, %s)",
                        (token, interaction.user.id, expires)
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion du token {token}: {e}")
            await interaction.followup.send(
                "❌ Une erreur technique est survenue. Veuillez réessayer.",
                ephemeral=True
            )
            return

        link = f"{SITE_URL}/verify/{token}"
        embed = discord.Embed(
            title="📱 Vérification téléphonique",
            description="Clique sur le bouton ci-dessous pour commencer",
            color=0x5865F2
        )
        embed.add_field(name="⏰ Expiration", value=f"Ce lien expire dans {SESSION_EXPIRY_HOURS} heure")
        embed.add_field(name="🔗 Lien direct", value=f"[Clique ici pour vérifier]({link})", inline=False)

        view = View()
        view.add_item(Button(label="✅ Commencer la vérification", url=link, style=discord.ButtonStyle.link))
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())

async def setup_commands(bot):
    # === COMMANDE INTERACTIVE POUR PERSONNALISER L'EMBED ===
    @bot.command(name="setup", aliases=["config"])
    @commands.has_permissions(administrator=True)
    async def setup_interactive(ctx):
        # Verrou pour éviter les doubles exécutions
        async with user_locks[ctx.author.id]:
            await ctx.send("📝 **Quel titre veux-tu pour l'embed ?**")
            await ctx.send("Exemple: `🌟 Bienvenue sur mon serveur 18+ !`")
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                msg = await bot.wait_for('message', timeout=60.0, check=check)
                title = msg.content
                
                await ctx.send("📝 **Quelle description ?**")
                await ctx.send("Exemple: `Pour accéder à tous les salons, vérifie ton compte`")
                msg = await bot.wait_for('message', timeout=60.0, check=check)
                description = msg.content
                
                await ctx.send("Exemple: `1️⃣ Clique sur le bouton, 2️⃣ Entre ton numéro, 3️⃣ Reçois un code, 4️⃣ Accès accordé`")
                await ctx.send("📝 **Instructions ?** (sépare les étapes par des virgules ou \\n)")
                msg = await bot.wait_for('message', timeout=60.0, check=check)
                instructions = msg.content.replace(",", "\\n")
                
                await ctx.send("📝 **Message de confidentialité ?**")
                await ctx.send("Exemple: `Ton numéro est supprimé après vérification`")
                msg = await bot.wait_for('message', timeout=60.0, check=check)
                privacy = msg.content
                
                await ctx.send("🎨 **Couleur ?** (rouge, vert, bleu, jaune, violet, orange, rose, ou code hex comme #FF5733)")
                await ctx.send("Tape `default` pour la couleur par défaut (bleu Discord)")
                msg = await bot.wait_for('message', timeout=60.0, check=check)
                
                color_input = msg.content.lower()
                color_map = {
                    "rouge": 0xFF0000, "vert": 0x00FF00, "bleu": 0x0000FF,
                    "jaune": 0xFFFF00, "violet": 0x800080, "orange": 0xFFA500,
                    "rose": 0xFF69B4, "default": 0x5865F2
                }
                if color_input in color_map:
                    color = color_map[color_input]
                elif color_input.startswith("#"):
                    try:
                        color = int(color_input[1:], 16)
                    except Exception:
                        color = 0x5865F2
                        await ctx.send("⚠️ Couleur non reconnue, j'utilise le bleu Discord")
                else:
                    color = 0x5865F2
                    await ctx.send("⚠️ Couleur non reconnue, j'utilise le bleu Discord")
                
                await ctx.send("👣 **Texte du footer ?** (optionnel, tape `non` pour passer)")
                msg = await bot.wait_for('message', timeout=60.0, check=check)
                footer = msg.content if msg.content.lower() != "non" else "Clique sur le bouton ci-dessous"
                
                embed = discord.Embed(title=title, description=description, color=color)
                embed.add_field(name="📋 Instructions", value=instructions, inline=False)
                embed.add_field(name="🔒 Confidentialité", value=privacy, inline=False)
                embed.set_footer(text=footer)
                
                await ctx.send("✅ **Voici ton embed personnalisé :**")
                await ctx.send(embed=embed, view=VerifyView())
                await ctx.message.delete()
                logger.info(f"✅ Embed personnalisé créé par {ctx.author}")
                
            except asyncio.TimeoutError:
                await ctx.send("⏰ **Temps écoulé !** Recommence la commande.")

    # === COMMANDE RAPIDE AVEC LES VALEURS PAR DÉFAUT ===
    @bot.command(name="setup_default")
    @commands.has_permissions(administrator=True)
    async def setup_default(ctx):
        embed = discord.Embed(
            title=DEFAULT_WELCOME_TITLE,
            description=DEFAULT_WELCOME_DESCRIPTION,
            color=DEFAULT_COLOR
        )
        embed.add_field(name="📋 Instructions", value=DEFAULT_INSTRUCTIONS, inline=False)
        embed.add_field(name="🔒 Confidentialité", value=DEFAULT_PRIVACY, inline=False)
        embed.set_footer(text="Clique sur le bouton ci-dessous")
        await ctx.send(embed=embed, view=VerifyView())
        await ctx.message.delete()
        logger.info(f"✅ Embed par défaut créé par {ctx.author}")

    # NOTE : pas d'autres commandes staff (comme !code, !stats, !clean)
    return bot

def setup_views(bot):
    bot.add_view(VerifyView())