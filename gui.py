import os
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from io import BytesIO
from PIL import Image, ImageTk
from sqlite.search_sqlite import SQLiteSearch
from deck import Deck
from card import Card


class FabGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Flesh and Blood - Generic Card Tool")
        self.root.geometry("1400x850")  # Widened to fit the image
        self.current_deck = Deck(format_="CC")
        self.setup_deck_ui()

        try:
            self.search_engine = SQLiteSearch()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect: {e}")
            self.root.destroy()
            return

        # UI State Variables
        self.vars = {
            'name': tk.StringVar(), 'color': tk.StringVar(), 'pitch': tk.StringVar(),
            'cost': tk.StringVar(), 'power': tk.StringVar(), 'defense': tk.StringVar(),
            'types': tk.StringVar(), 'traits': tk.StringVar(), 'keywords': tk.StringVar(),
            'text': tk.StringVar(),
            'legal_cc': tk.BooleanVar(), 'legal_blitz': tk.BooleanVar(), 'legal_silver_age': tk.BooleanVar()
        }

        self.setup_ui()
        self.perform_search()

    def setup_deck_ui(self):
        """Replaces Listbox with a Treeview for better quantity tracking."""
        deck_frame = ttk.LabelFrame(self.root, text="Current Deck", padding=10)
        deck_frame.pack(side="right", fill="both", padx=10)

        # Create Treeview with Name and Qty columns
        cols = ("name", "qty")
        self.deck_tree = ttk.Treeview(deck_frame, columns=cols, show="headings", height=20)

        self.deck_tree.heading("name", text="Card Name")
        self.deck_tree.column("name", width=200)

        self.deck_tree.heading("qty", text="Qty")
        self.deck_tree.column("qty", width=50, anchor="center")

        self.deck_tree.pack(pady=5, fill="both", expand=True)

        # Buttons
        ttk.Button(deck_frame, text="Add Selected to Deck", command=self.add_to_deck).pack(fill="x")
        ttk.Button(deck_frame, text="Remove Selected", command=self.remove_from_deck).pack(fill="x", pady=2)
        ttk.Button(deck_frame, text="Check Legality", command=self.check_deck).pack(fill="x", pady=5)

    def add_to_deck(self):
        selected_ids = self.tree.selection()
        if not selected_ids:
            return

        for item_id in selected_ids:
            card_name = self.tree.item(item_id)['values'][0]

            # Fetch the full Card object for the deck logic
            card_obj = self.get_card_object_by_name(card_name)
            if card_obj:
                # 1. Update the Logic (Deck Object)
                self.current_deck.add_card(card_obj)

                # 2. Update the UI (Deck Treeview)
                self.refresh_deck_display()

    def refresh_deck_display(self):
        """Clears and repopulates the deck treeview based on the Deck object."""
        # Clear current UI rows
        for item in self.deck_tree.get_children():
            self.deck_tree.delete(item)

        # Add Hero at the top if set
        if self.current_deck.hero:
            self.deck_tree.insert("", "end", values=(f"⭐ {self.current_deck.hero.name}", 1), tags=('hero',))

        # Add all other cards
        for name, data in self.current_deck.cards.items():
            self.deck_tree.insert("", "end", values=(name, data['qty']))

    def get_card_object_by_name(self, name):
        """Helper to fetch a full Card object from the database for the Deck logic."""
        res = self.search_engine.conn.execute(
            "SELECT * FROM cards WHERE name = ?", (name,)
        ).fetchone()

        if res:
            # Convert the SQLite Row back into the dictionary format your Card class expects
            return Card(dict(res))
        return None

    def check_deck(self):
        is_legal, errors = self.current_deck.validate_legality()
        if is_legal:
            messagebox.showinfo("Legality Check", "Deck is LEGAL!")
        else:
            error_msg = "\n".join(errors)
            messagebox.showwarning("Legality Check", f"Deck is ILLEGAL:\n\n{error_msg}")

    def setup_ui(self):
        # --- Left Side: Filters and Table ---
        left_main = ttk.Frame(self.root)
        left_main.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        filter_frame = ttk.LabelFrame(left_main, text="Search Criteria", padding=10)
        filter_frame.pack(fill="x")

        # Row Helper
        def add_filter(r, c, lbl, var, w=15):
            ttk.Label(filter_frame, text=lbl).grid(row=r, column=c * 2, sticky="e", padx=2)
            ttk.Entry(filter_frame, textvariable=self.vars[var], width=w).grid(row=r, column=c * 2 + 1, padx=5, pady=2)

        add_filter(0, 0, "Name:", "name", 25)
        add_filter(0, 1, "Color:", "color")
        add_filter(0, 2, "Pitch:", "pitch")
        add_filter(1, 0, "Types:", "types", 25)
        add_filter(1, 1, "Traits:", "traits")
        add_filter(1, 2, "Keywords:", "keywords")

        btn_f = ttk.Frame(filter_frame)
        btn_f.grid(row=2, column=0, columnspan=6, pady=10, sticky="w")
        ttk.Checkbutton(btn_f, text="CC", variable=self.vars['legal_cc']).pack(side="left", padx=5)
        ttk.Checkbutton(btn_f, text="Blitz", variable=self.vars['legal_blitz']).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Search", command=self.perform_search).pack(side="left", padx=20)

        # Table
        cols = ("name", "color", "pitch", "cost", "power", "defense")
        self.tree = ttk.Treeview(left_main, columns=cols, show="headings", height=25)
        for c in cols:
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=80, anchor="center")
        self.tree.column("name", width=200, anchor="w")
        self.tree.pack(fill="both", expand=True)

        # Bind Selection Event
        self.tree.bind("<<TreeviewSelect>>", self.on_card_select)

        # --- Right Side: Image Preview ---
        self.preview_frame = ttk.LabelFrame(self.root, text="Card Preview", padding=10)
        self.preview_frame.pack(side="right", fill="y", padx=10, pady=10)

        self.img_label = ttk.Label(self.preview_frame, text="Select a card to load image")
        self.img_label.pack(expand=True)

    def remove_from_deck(self):
        selected = self.deck_tree.selection()
        if not selected:
            return

        for item_id in selected:
            card_name = self.deck_tree.item(item_id)['values'][0]
            # Clean hero tag if present
            clean_name = card_name.replace("⭐ ", "")

            # Update Logic: Decrement quantity or remove
            if clean_name in self.current_deck.cards:
                self.current_deck.cards[clean_name]['qty'] -= 1
                if self.current_deck.cards[clean_name]['qty'] <= 0:
                    del self.current_deck.cards[clean_name]
            elif self.current_deck.hero and clean_name == self.current_deck.hero.name:
                self.current_deck.hero = None

        self.refresh_deck_display()

    def on_card_select(self, event):
        """Triggered when a user clicks a row in the table."""
        selected = self.tree.selection()
        if not selected: return

        # Get the name of the selected card from the first column of the treeview
        card_name = self.tree.item(selected[0])['values'][0]

        # Query DB for BOTH the image URL and the local filename
        res = self.search_engine.conn.execute(
            "SELECT image_url, local_path FROM cards WHERE name = ?", (card_name,)
        ).fetchone()

        if res:
            # Pass both required arguments to display_image
            self.display_image(res['image_url'], res['local_path'])
        else:
            self.img_label.config(image='', text="No data found for this card")

    def display_image(self, url, local_filename):
        """Checks local storage first, then falls back to URL."""
        # Define where the local image should be
        local_dir = os.path.join(os.path.dirname(__file__), "data", "images")
        local_path = os.path.join(local_dir, local_filename) if local_filename else None

        try:
            if local_path and os.path.exists(local_path):
                # Load from hard drive (Fast)
                img = Image.open(local_path)
            elif url:
                # Fallback to internet (Slow)
                response = requests.get(url, timeout=5)
                img = Image.open(BytesIO(response.content))
            else:
                raise Exception("No image available")

            img.thumbnail((350, 500))
            photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=photo, text="")
            self.img_label.image = photo
        except Exception as e:
            self.img_label.config(image='', text="Image not available")

    def perform_search(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        filters = {k: v.get() for k, v in self.vars.items() if v.get() not in ["", False]}

        results = self.search_engine.advanced_search(filters)
        for r in results:
            self.tree.insert("", "end", values=(
                r["name"], r["color"], r["pitch"], r["cost"], r["power"], r["defense"]
            ))


if __name__ == "__main__":
    root = tk.Tk()
    app = FabGui(root)
    root.mainloop()