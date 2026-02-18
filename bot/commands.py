"""
Commandes du bot Discord
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
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database import get_db, cleanup_expired

# ===== CONFIGURATION DEPUIS VARIABLES D'ENVIRONNEMENT =====
SITE_URL = os.getenv('SITE_URL', 'https://verification-site-pkos.onrender.com')
ROLE_ID = int(os.getenv('ROLE_ID', '0'))
SESSION_EXPIRY_HOURS = int(os.getenv('SESSION_EXPIRY_HOURS', '1'))
DEFAULT_WELCOME_TITLE = os.getenv('DEFAULT_WELCOME_TITLE', '🌟 Bienvenue sur le serveur !')
DEFAULT_WELCOME_DESCRIPTION = os.getenv('DEFAULT_WELCOME_DESCRIPTION', 'Vérifie ton compte pour accéder à tous les salons')
DEFAULT_INSTRUCTIONS = os.getenv('DEFAULT_INSTRUCTIONS', '1️⃣ Clique sur le bouton\n2️⃣ Entre ton numéro\n3️⃣ Reçois un code\n4️⃣ Accès accordé')
DEFAULT_PRIVACY = os.getenv('DEFAULT_PRIVACY', 'Ton numéro est supprimé après vérification')
DEFAULT_COLOR = int(os.getenv('DEFAULT_COLOR', '0x5865F2'), 16)

logger = logging.getLogger(__name__)

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
        """Crée un embed personnalisé étape par étape (interactif)"""
        
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
            instructions = msg.content.replace(",", "\n")
            
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
                color = int(color_input[1:], 16)
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

    # === COMMANDE CODE ===
    @bot.command(name="code")
    @commands.has_permissions(administrator=True)
    async def code_command(ctx, token: str = None, code: str = None):
        cleanup_expired()
        if not token:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT token, user_id, phone, expires_at FROM verifications WHERE phone IS NOT NULL AND code IS NULL ORDER BY expires_at DESC"
                    )
                    pending = cur.fetchall()
            if not pending:
                await ctx.send(embed=discord.Embed(title="📋 Aucune demande en attente", color=0xFFA500))
                return
            embed = discord.Embed(title=f"📋 Demandes en attente ({len(pending)})", color=0x3498db)
            for p in pending[:5]:
                expires = p[3]
                if isinstance(expires, str):
                    expires = datetime.fromisoformat(expires)
                minutes = int((expires - datetime.utcnow()).total_seconds() / 60)
                embed.add_field(
                    name=f"Jeton: {p[0][:8]}...",
                    value=f"👤 <@{p[1]}>\n📞 {p[2]}\n⏰ Expire dans {minutes} min\n📝 `!code {p[0]} CODE`",
                    inline=False
                )
            await ctx.send(embed=embed)
            return

        if not code:
            await ctx.send("❌ Utilisation: `!code <jeton> <code>`")
            return

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE verifications SET code = %s, staff_id = %s WHERE token = %s AND code IS NULL",
                    (code, ctx.author.id, token)
                )
                if cur.rowcount == 0:
                    await ctx.send("❌ Jeton invalide ou déjà utilisé")
                    return
                cur.execute(
                    "SELECT user_id, phone FROM verifications WHERE token = %s",
                    (token,)
                )
                row = cur.fetchone()
                if not row:
                    await ctx.send("❌ Erreur : jeton introuvable après mise à jour")
                    return
                user_id, phone = row
            conn.commit()

        # Embed de confirmation pour le staff – le code est affiché clairement
        embed = discord.Embed(
            title="✅ Code généré – À envoyer par SMS",
            color=0x00FF00,
            description=f"**Code** : `{code}`\n**Téléphone** : `{phone}`\n**Utilisateur** : <@{user_id}>"
        )
        embed.add_field(name="🔗 Lien pour l'utilisateur", value=f"{SITE_URL}/enter/{token}", inline=False)
        embed.set_footer(text="Envoie ce code manuellement par SMS à l'utilisateur.")
        await ctx.send(embed=embed)

    # === COMMANDE STATS ===
    @bot.command(name="stats")
    @commands.has_permissions(administrator=True)
    async def stats_command(ctx):
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM verifications")
                total = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM verifications WHERE phone IS NOT NULL AND code IS NULL")
                pending = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM verifications WHERE code IS NOT NULL")
                validated = cur.fetchone()[0]
        embed = discord.Embed(title="📊 Statistiques", color=0x3498db)
        embed.add_field(name="Total", value=str(total))
        embed.add_field(name="En attente", value=str(pending))
        embed.add_field(name="Validés", value=str(validated))
        await ctx.send(embed=embed)

    # === COMMANDE CLEAN ===
    @bot.command(name="clean")
    @commands.has_permissions(administrator=True)
    async def clean_command(ctx):
        cleaned = cleanup_expired()
        await ctx.send(f"🧹 {cleaned} jetons expirés supprimés")

    return bot

def setup_views(bot):
    bot.add_view(VerifyView())