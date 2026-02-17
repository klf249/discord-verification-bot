from flask import Flask, render_template, request
import sqlite3
import requests
from datetime import datetime
import config

app = Flask(__name__)

def get_db():
    return sqlite3.connect('verif.db')

@app.route('/')
def index():
    return "✅ Serveur web opérationnel!"

@app.route('/verify/<token>')
def verify_form(token):
    with get_db() as conn:
        cur = conn.execute(
            'SELECT user_id, expires_at FROM verifications WHERE token = ? AND phone IS NULL',
            (token,)
        )
        row = cur.fetchone()
    
    if not row:
        return render_template('error.html', message="Lien invalide ou déjà utilisé.")
    
    expires = datetime.fromisoformat(row[1])
    if datetime.utcnow() > expires:
        return render_template('error.html', message="Ce lien a expiré.")
    
    return render_template('phone_form.html', token=token)

@app.route('/submit-phone', methods=['POST'])
def submit_phone():
    token = request.form['token']
    phone = request.form['phone']
    
    with get_db() as conn:
        cur = conn.execute(
            'UPDATE verifications SET phone = ? WHERE token = ? AND phone IS NULL',
            (phone, token)
        )
        if cur.rowcount == 0:
            return render_template('error.html', message="Erreur: jeton invalide.")
        
        cur = conn.execute('SELECT user_id FROM verifications WHERE token = ?', (token,))
        user_id = cur.fetchone()[0]
    
    try:
        requests.post('http://localhost:5001/phone_submitted', json={
            'token': token,
            'phone': phone,
            'user_id': user_id
        }, timeout=1)
    except:
        pass
    
    return render_template('phone_submitted.html', token=token)

@app.route('/enter-code/<token>')
def code_form(token):
    with get_db() as conn:
        cur = conn.execute(
            'SELECT code FROM verifications WHERE token = ? AND code IS NOT NULL',
            (token,)
        )
        row = cur.fetchone()
    
    if not row:
        return render_template('waiting.html', token=token)
    
    return render_template('code_form.html', token=token)

@app.route('/submit-code', methods=['POST'])
def submit_code():
    token = request.form['token']
    user_code = request.form['code']
    
    with get_db() as conn:
        cur = conn.execute(
            'SELECT user_id, code FROM verifications WHERE token = ?',
            (token,)
        )
        row = cur.fetchone()
        
        if not row:
            return render_template('error.html', message="Jeton invalide.")
        
        user_id, expected_code = row
        
        if expected_code != user_code:
            return render_template('error.html', message="Code incorrect.")
        
        conn.execute('DELETE FROM verifications WHERE token = ?', (token,))
    
    try:
        requests.post('http://localhost:5001/grant_role', json={'user_id': user_id})
    except:
        pass
    
    return render_template('success.html')

if __name__ == '__main__':
    app.run(port=5000, debug=True)
