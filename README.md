# 🤖 Bot de Vérification Discord (partie bot)

Ce dossier contient le bot Discord du système de vérification par téléphone.

## Installation locale

1. Copier `.env.example` vers `.env` et modifier avec vos tokens.
2. Copier `config.example.py` vers `config.py` (si vous n'utilisez pas les variables d'env).
3. Installer les dépendances : `pip install -r requirements.txt`
4. Initialiser la BDD : `python database.py`
5. Lancer le bot : `python bot/main.py`

## Commandes disponibles

- `!setup` : Crée un embed de vérification avec bouton.
- `!code` : Liste les demandes en attente.
- `!code <jeton> <code>` : Associe un code à une demande.
- `!stats` : Affiche les statistiques.
- `!clean` : Supprime les jetons expirés.

## Déploiement sur Render

Le fichier `render.yaml` est fourni. Connectez votre dépôt GitHub à Render et utilisez le blueprint.
