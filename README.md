<div align="center">

# 🔐 Discord Verification Bot

**Un bot Discord en Python pour gérer un parcours de vérification par téléphone.**

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-Bot-5865F2?logo=discord&logoColor=white)
![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)
![Security](https://img.shields.io/badge/Security-Secrets%20protected-success)

</div>

## ✨ Présentation

Ce projet fournit la partie bot d’un système de vérification Discord. Il permet de créer un panneau de vérification, suivre les demandes, associer des codes et consulter des statistiques.

## 🚀 Fonctionnalités

- panneau de vérification avec bouton interactif ;
- suivi des demandes en attente ;
- association d’un code à une demande ;
- statistiques de vérification ;
- nettoyage des jetons expirés ;
- base de données locale ;
- déploiement simplifié sur Render.

## ⚡ Installation

```bash
git clone https://github.com/klf249/discord-verification-bot.git
cd discord-verification-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python database.py
python bot/main.py
```

Sous Windows, activez l’environnement avec :

```powershell
.venv\Scripts\activate
```

## 🤖 Commandes

| Commande | Description |
|---|---|
| `!setup` | Crée le panneau de vérification |
| `!code` | Affiche les demandes en attente |
| `!code <jeton> <code>` | Associe un code à une demande |
| `!stats` | Affiche les statistiques |
| `!clean` | Supprime les jetons expirés |

## ☁️ Déploiement

Le fichier `render.yaml` permet de déployer le projet avec un Blueprint Render. Configurez les variables d’environnement dans l’interface Render et ne publiez jamais vos secrets dans le dépôt.

## 🔒 Sécurité

Consultez [`SECURITY.md`](SECURITY.md) avant de signaler une vulnérabilité. Les tokens Discord, clés API, numéros de téléphone et codes de vérification ne doivent jamais apparaître dans une issue publique.

## 🤝 Contribution

Les contributions sont bienvenues. Consultez [`CONTRIBUTING.md`](CONTRIBUTING.md) avant d’ouvrir une Pull Request.

---

<div align="center">
Maintenu par <a href="https://github.com/klf249">Walker</a>.
</div>
