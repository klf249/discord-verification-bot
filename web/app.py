"""
Application Flask pour le site de vérification
"""
from flask import Flask, render_template, request, jsonify
import psycopg2
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
    DATABASE_URL = os.getenv('DATABASE_URL')
    BOT_API_URL = os.getenv('BOT_API_URL', 'http://localhost:5001')
    
    def get_db():
        if not DATABASE_URL:
            raise Exception("❌ DATABASE_URL non définie")
        return psycopg2.connect(DATABASE_URL)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'

@app.route('/')
def index():
    return render_template('index.html', site_url=SITE_URL)

@app.route('/verify/<token>')
def verify_page(token):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, expires_at FROM verifications WHERE token = %s AND phone IS NULL",
                (token,)
            )
            row = cur.fetchone()
    
    if not row:
        return render_template('error.html', message="Lien invalide ou déjà utilisé")
    
    expires = row[1]  # datetime object
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
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM verifications WHERE token = %s AND phone IS NULL",
                (token,)
            )
            row = cur.fetchone()
            
            if not row:
                return render_template('error.html', message="Token invalide")
            
            user_id = row[0]
            
            cur.execute(
                "UPDATE verifications SET phone = %s WHERE token = %s",
                (phone, token)
            )
        conn.commit()
    
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
        with conn.cursor() as cur:
            cur.execute(
                "SELECT code FROM verifications WHERE token = %s AND code IS NOT NULL",
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
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, code FROM verifications WHERE token = %s",
                (token,)
            )
            row = cur.fetchone()
            
            if not row:
                return render_template('error.html', message="Token invalide")
            
            user_id, expected_code = row
            
            if expected_code != code:
                return render_template('error.html', message="Code incorrect")
            
            cur.execute("DELETE FROM verifications WHERE token = %s", (token,))
        conn.commit()
    
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