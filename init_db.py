import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = "database.db"

def init_db():
    """Create database and tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        department TEXT NOT NULL,
        password TEXT NOT NULL
    )
    """)

    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    
    admin_password = generate_password_hash("uspvoting1122")
    cursor.execute("""
    INSERT OR IGNORE INTO admin (username, password)
    VALUES (?, ?)
    """, ("uspmultan", admin_password))

    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        department TEXT NOT NULL,
        image TEXT,
        votes INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        candidate_id INTEGER,
        voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_datetime TEXT
    )
    """)


    cursor.execute("""
    INSERT INTO settings (id, result_datetime)
        SELECT 1, NULL
        WHERE NOT EXISTS (SELECT 1 FROM settings WHERE id = 1)
    """)


    conn.commit()
    conn.close()
    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
