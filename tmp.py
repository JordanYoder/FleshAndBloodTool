import sqlite3

conn = sqlite3.connect("data/fab_cards.db")
cursor = conn.cursor()

cursor.execute("SELECT DISTINCT class FROM cards LIMIT 20")
for row in cursor.fetchall():
    print(row)

conn.close()