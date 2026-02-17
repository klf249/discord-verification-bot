import sqlite3
from datetime import datetime

def get_db():
    return sqlite3.connect('verif.db')

def init_database():
    """Crée la table si elle n'existe pas"""
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
        conn.commit()

if __name__ == "__main__":
    init_database()
    print("✅ Base de données créée avec succès!")