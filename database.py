"""
Gestion de la base de données
"""
import sqlite3
from datetime import datetime
import os

def get_db():
    """Retourne une connexion à la base de données"""
    db_path = os.getenv('DATABASE_URL', 'verif.db').replace('sqlite:///', '')
    return sqlite3.connect(db_path)

def init_database():
    """Initialise la base de données"""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS verifications (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                phone TEXT,
                code TEXT,
                staff_id INTEGER,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON verifications(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_expires ON verifications(expires_at)')
        conn.commit()

def cleanup_expired():
    """Nettoie les entrées expirées"""
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM verifications WHERE expires_at < datetime('now')"
        )
        return cur.rowcount

if __name__ == "__main__":
    init_database()
    print("✅ Base de données initialisée")
