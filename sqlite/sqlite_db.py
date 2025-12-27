import sqlite3
import json
import sys
import os
import requests
import time

# Ensure we can import card.py from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from card import Card

# Path Configuration
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
DB_PATH = os.path.join(DATA_DIR, "fab_cards.db")
JSON_PATH = os.path.join(DATA_DIR, "card.json")


def create_tables(conn):
    conn.execute("DROP TABLE IF EXISTS cards")
    conn.execute("""
    CREATE TABLE cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, color TEXT, pitch INTEGER, cost TEXT,
        power TEXT, defense TEXT, card_types TEXT, traits TEXT,
        keywords TEXT, function_text TEXT,
        legal_cc INTEGER, legal_blitz INTEGER, legal_silver_age INTEGER,
        image_url TEXT,
        local_path TEXT  -- Column to store the filename on your computer
    )
    """)
    conn.execute("CREATE INDEX idx_name ON cards(name)")


def populate_database():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    with open(JSON_PATH, encoding='utf-8') as f:
        raw_data = json.load(f)

    print("Building database...")
    for entry in raw_data:
        c = Card(entry)

        # Create a safe filename (e.g., "Tectonic Rift.png")
        safe_name = "".join([x if x.isalnum() or x in " -_" else "_" for x in c.name])
        local_filename = f"{safe_name}_{c.pitch or 0}.png"

        conn.execute("""
        INSERT INTO cards (
            name, color, pitch, cost, power, defense,
            card_types, traits, keywords, function_text,
            legal_cc, legal_blitz, legal_silver_age, image_url, local_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c.name, c.color, c.pitch, c.cost, c.power, c.defense,
            ", ".join(c.types), ", ".join(c.traits), ", ".join(c.keywords),
            c.text, int(c.is_legal("CC")), int(c.is_legal("Blitz")),
            int(c.is_legal("Silver Age")), c.image_url, local_filename
        ))

    conn.commit()
    conn.close()
    print("Database built.")


def download_all_images():
    """Iterates through the DB and downloads missing images to data/images/"""
    if not os.path.exists(IMAGES_DIR): os.makedirs(IMAGES_DIR)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cards = conn.execute("SELECT name, image_url, local_path FROM cards WHERE image_url IS NOT NULL").fetchall()

    print(f"Checking {len(cards)} images...")
    for i, row in enumerate(cards):
        dest_path = os.path.join(IMAGES_DIR, row['local_path'])

        if os.path.exists(dest_path): continue  # Skip if already downloaded

        try:
            print(f"[{i + 1}/{len(cards)}] Downloading: {row['name']}...", end="\r")
            r = requests.get(row['image_url'], timeout=10)
            if r.status_code == 200:
                with open(dest_path, 'wb') as f:
                    f.write(r.content)
            time.sleep(0.1)  # Be polite to the server
        except Exception as e:
            print(f"\nFailed {row['name']}: {e}")

    conn.close()
    print("\nAll downloads finished.")


if __name__ == "__main__":
    populate_database()
    # Uncomment the line below to download everything for offline use:
    #download_all_images()
    #download_all_images()