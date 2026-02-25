"""
Gestion de la base de données (PostgreSQL)
"""

import os
import psycopg2
from datetime import datetime

def get_db():
    """Retourne une connexion PostgreSQL"""
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("❌ DATABASE_URL non définie dans les variables d'environnement")
    return psycopg2.connect(DATABASE_URL)

def init_database():
    """Initialise la base de données"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS verifications (
                    token TEXT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    phone TEXT,
                    code TEXT,
                    staff_id BIGINT,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    staff_message_id BIGINT
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON verifications(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_expires ON verifications(expires_at)")
        conn.commit()

def cleanup_expired():
    """Nettoie les entrées expirées"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM verifications WHERE expires_at < NOW()")
            deleted = cur.rowcount
        conn.commit()
        return deleted

if __name__ == "__main__":
    init_database()
    print("✅ Base de données PostgreSQL initialisée")
# PostgreSQL version