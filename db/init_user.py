import sqlite3
import os

def create_user_db():
    db_path = os.path.join("db", "cocktail.db")

    # Stelle sicher, dass der Ordner existiert
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Datenbank und Tabelle erstellen
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benutzername TEXT NOT NULL,
                userscore INTEGER NOT NULL
            )
        ''')
        conn.commit()
        print(f"Datenbank erstellt unter: {db_path}")

if __name__ == "__main__":
    create_user_db()