import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fab_cards.db")


class SQLiteSearch:
    def __init__(self):
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"Database not found at {DB_PATH}")
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def advanced_search(self, filters):
        # We ensure local_path is part of the selection
        query = "SELECT * FROM cards WHERE 1=1"
        params = []

        text_map = {'name': 'name', 'color': 'color', 'types': 'card_types',
                    'traits': 'traits', 'keywords': 'keywords', 'text': 'function_text'}

        for key, col in text_map.items():
            if filters.get(key):
                query += f" AND {col} LIKE ?"
                params.append(f"%{filters[key]}%")

        for s in ['pitch', 'cost', 'power', 'defense']:
            if filters.get(s):
                query += f" AND {s} = ?"
                params.append(filters[s])

        if filters.get('legal_cc'): query += " AND legal_cc = 1"
        if filters.get('legal_blitz'): query += " AND legal_blitz = 1"
        if filters.get('legal_silver_age'): query += " AND legal_silver_age = 1"

        return self.conn.execute(query, params).fetchall()