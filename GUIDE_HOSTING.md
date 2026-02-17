# GUIDE D'HÉBERGEMENT GRATUIT
# ============================

## OPTION 1: HÉBERGER SUR RENDER (GRATUIT ET FACILE)
----------------------------------------------------

### Pour le BOT Discord:
1. Crée un compte sur https://render.com
2. Clique sur "New +" → "Background Worker"
3. Connecte ton repository GitHub (ou uploade les fichiers)
4. Configuration:
   - Name: verification-bot
   - Environment: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: python bot.py
5. Ajoute les variables d'environnement:
   - BOT_TOKEN: ton_token
   - GUILD_ID: ton_id_serveur
   - ROLE_ID: ton_id_role
   - etc. (toutes les variables de config.py)

### Pour le SITE WEB:
1. Sur Render, "New +" → "Web Service"
2. Configuration:
   - Name: verification-site
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn webapp:app
3. Ajoute les mêmes variables d'environnement
4. Tu obtiendras une URL comme: https://ton-site.onrender.com
5. Mets cette URL dans config.SITE_URL et redémarre le bot

## OPTION 2: HÉBERGER SUR PYTHONANYWHERE (GRATUIT)
------------------------------------------------
https://www.pythonanywhere.com

1. Crée un compte gratuit
2. Ouvre une console Bash
3. Clone ton projet: git clone ton-repo
4. Pour le site web:
   - Va dans "Web" → "Add a new web app"
   - Choisi Flask et Python 3.x
   - Configure le chemin vers webapp.py
5. Pour le bot:
   - Va dans "Tasks" → "Always-on tasks"
   - Ajoute: python /home/tonuser/verif/bot.py

## OPTION 3: HÉBERGER SUR UN VPS GRATUIT (ORACLE CLOUD)
----------------------------------------------------
https://www.oracle.com/cloud/free/

1. Crée un compte (carte bancaire requise mais gratuit)
2. Crée une instance VM (Always Free tier)
3. Connecte-toi en SSH
4. Installe Python et les dépendances
5. Utilise screen ou tmux pour garder les processus en vie

## OPTION 4: UTILISER DISCOORD.PY AVEC REPL.IT
--------------------------------------------
https://replit.com

1. Crée un compte
2. Importe ton projet
3. Ajoute les secrets (variables d'environnement)
4. Le bot tourne 24/7 avec un pinger (UptimeRobot)

## FICHIERS NÉCESSAIRES POUR L'HÉBERGEMENT
----------------------------------------

### requirements.txt (déjà créé)
discord.py==2.3.2
flask==3.0.0
requests==2.31.0
aiohttp==3.9.1
gunicorn==21.2.0  # Pour Render
audioop-lts==0.0.3

### Procfile (pour Render)
web: gunicorn webapp:app
worker: python bot.py

### runtime.txt (optionnel)
python-3.11.0

## COMMANDES UTILES POUR LE SERVEUR
---------------------------------
# Démarrer le bot en arrière-plan
nohup python bot.py > bot.log 2>&1 &

# Démarrer le site
nohup python webapp.py > web.log 2>&1 &

# Voir les logs
tail -f bot.log
tail -f web.log

# Arrêter les processus
pkill -f bot.py
pkill -f webapp.py
