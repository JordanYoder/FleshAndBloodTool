from sqlite.search_sqlite import SQLiteSearch


def print_table(rows):
    """Prints a list of SQLite Row objects in a clean, tabulated format."""
    if not rows:
        print("No records found in the database.")
        return

    # Column headers and formatting setup
    # <30 means left-aligned with a width of 30 characters
    headers = ["Name", "Type", "Pitch", "Class", "Cost", "Power", "Def"]
    row_format = "{:<30} {:<12} {:<6} {:<15} {:<5} {:<6} {:<4}"

    print("-" * 85)
    print(row_format.format(*headers))
    print("-" * 85)

    for r in rows:
        # Truncate long names to keep the table aligned
        name = (r["name"][:27] + "..") if len(r["name"]) > 27 else r["name"]

        # Handle None values for cleaner display
        card_type = r["card_type"] or "-"
        pitch = r["pitch"] if r["pitch"] is not None else "-"
        cls = r["class"] or "-"
        cost = r["cost"] if r["cost"] is not None else "-"
        power = r["power"] if r["power"] is not None else "-"
        defense = r["defense"] if r["defense"] is not None else "-"

        print(row_format.format(
            name, card_type, pitch, cls, cost, power, defense
        ))
    print("-" * 85)


def main():
    search = SQLiteSearch()

    # Query the first 5 records directly from the database using the LIMIT clause
    # SQLite uses LIMIT to constrain the number of rows returned
    query = "SELECT * FROM cards LIMIT 5"
    results = search.conn.execute(query).fetchall()

    print(f"\n--- Displaying the first {len(results)} records found ---\n")
    print_table(results)


if __name__ == "__main__":
    main()