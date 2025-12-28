import os
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from io import BytesIO
from PIL import Image, ImageTk
from sqlite.search_sqlite import SQLiteSearch
from deck import Deck
from card import Card
import ctypes
import re
from tkinter import filedialog

# Fix taskbar icon for Windows
try:
    myappid = 'unofficalfab.jordany.fab_action_point.01'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


class FabGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Flesh & Blood: AP")
        self.root.geometry("1400x850")
        self.current_deck = Deck(format_="CC")

        # --- SET WINDOW ICON ---
        icon_path = os.path.join(os.path.dirname(__file__), "data", "images", "icons", "fab_ap.png")
        if os.path.exists(icon_path):
            try:
                img_icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, img_icon)
                self.root.tk_icon = img_icon
            except Exception as e:
                print(f"Could not load window icon: {e}")

        try:
            self.search_engine = SQLiteSearch()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect: {e}")
            self.root.destroy()
            return

        self.vars = {
            'name': tk.StringVar(), 'color': tk.StringVar(), 'pitch': tk.StringVar(),
            'cost': tk.StringVar(), 'power': tk.StringVar(), 'defense': tk.StringVar(),
            'types': tk.StringVar(), 'traits': tk.StringVar(), 'keywords': tk.StringVar(),
            'text': tk.StringVar(),
            'legal_cc': tk.BooleanVar(), 'legal_blitz': tk.BooleanVar(), 'legal_silver_age': tk.BooleanVar()
        }

        self.setup_ui()
        self.perform_search()

    def add_to_deck(self):
        selected_ids = self.tree.selection()
        if not selected_ids: return
        for item_id in selected_ids:
            card_name = self.tree.item(item_id)['values'][0]
            card_obj = self.get_card_object_by_name(card_name)
            if card_obj:
                self.current_deck.add_card(card_obj)
                self.refresh_deck_display()

    def refresh_deck_display(self):
        for item in self.deck_tree.get_children():
            self.deck_tree.delete(item)
        total_qty = 0
        if self.current_deck.hero:
            # Using standard star to avoid encoding errors
            self.deck_tree.insert("", "end", values=(f"* {self.current_deck.hero.name}", 1))

        sorted_cards = sorted(self.current_deck.cards.items())
        for name, data in sorted_cards:
            self.deck_tree.insert("", "end", values=(name, data['qty']))
            total_qty += data['qty']

        format_name = self.current_deck.format
        self.count_label.config(text=f"Total Cards: {total_qty} | Format: {format_name}")
        if (format_name == "CC" and total_qty >= 60) or (format_name == "Blitz" and total_qty == 40):
            self.count_label.config(foreground="green")
        else:
            self.count_label.config(foreground="black")

    def get_card_object_by_name(self, name):
        res = self.search_engine.conn.execute("SELECT * FROM cards WHERE name = ?", (name,)).fetchone()
        return Card(dict(res)) if res else None

    def check_deck(self):
        is_legal, errors = self.current_deck.validate_legality()
        if is_legal:
            messagebox.showinfo("Legality Check", "Deck is LEGAL!")
        else:
            messagebox.showwarning("Legality Check", f"Deck is ILLEGAL:\n\n" + "\n".join(errors))

    def setup_ui(self):
        # Left Side
        left_main = ttk.Frame(self.root)
        left_main.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        filter_frame = ttk.LabelFrame(left_main, text="Search Criteria", padding=10)
        filter_frame.pack(fill="x", pady=(0, 10))

        def add_filter(r, c, lbl, var_name, width=15):
            ttk.Label(filter_frame, text=lbl).grid(row=r, column=c * 2, sticky="e", padx=2)
            entry = ttk.Entry(filter_frame, textvariable=self.vars[var_name], width=width)
            entry.grid(row=r, column=c * 2 + 1, padx=5, pady=2)

            # BIND ENTER KEY:
            # This ensures pressing Enter in ANY box triggers the search
            entry.bind("<Return>", lambda e: self.perform_search())

        # Now all filters created with this function will support the Enter key
        add_filter(0, 0, "Name:", "name", 25)
        add_filter(0, 1, "Color:", "color")
        add_filter(0, 2, "Pitch:", "pitch")
        add_filter(1, 0, "Types:", "types", 25)
        add_filter(1, 1, "Traits:", "traits")
        add_filter(1, 2, "Keywords:", "keywords")

        options_f = ttk.Frame(filter_frame)
        options_f.grid(row=2, column=0, columnspan=6, pady=10, sticky="w")
        ttk.Checkbutton(options_f, text="CC Legal", variable=self.vars['legal_cc']).pack(side="left", padx=5)
        ttk.Checkbutton(options_f, text="Blitz Legal", variable=self.vars['legal_blitz']).pack(side="left", padx=5)
        ttk.Button(options_f, text="Search", command=self.perform_search).pack(side="left", padx=20)

        # Result Table (ONLY CREATED ONCE)
        cols = ("name", "color", "pitch", "cost", "power", "defense")
        self.tree = ttk.Treeview(left_main, columns=cols, show="headings", height=25)
        for c in cols:
            self.tree.heading(c, text=c.title(), command=lambda _c=c: self.sort_column(self.tree, _c, False))
            self.tree.column(c, width=80, anchor="center")
        self.tree.column("name", width=200, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_card_select)
        self.tree.bind("<Double-1>", self.on_search_double_click)

        # Middle Side
        self.preview_frame = ttk.LabelFrame(self.root, text="Card Art", padding=10)
        self.preview_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.img_label = ttk.Label(self.preview_frame, text="Select a card to view art")
        self.img_label.pack(expand=True)

        # Right Side
        deck_frame = ttk.LabelFrame(self.root, text="Current Deck", padding=10)
        deck_frame.pack(side="right", fill="both", padx=10, pady=10)

        self.deck_tree = ttk.Treeview(deck_frame, columns=("name", "qty"), show="headings", height=20)
        self.deck_tree.heading("name", text="Card Name",
                               command=lambda: self.sort_column(self.deck_tree, "name", False))
        self.deck_tree.column("name", width=180)
        self.deck_tree.heading("qty", text="Qty", command=lambda: self.sort_column(self.deck_tree, "qty", False))
        self.deck_tree.column("qty", width=40, anchor="center")
        self.deck_tree.pack(pady=5, fill="both", expand=True)

        self.deck_tree.bind("<Delete>", lambda e: self.remove_from_deck())
        self.deck_tree.bind("<BackSpace>", lambda e: self.remove_from_deck())
        self.deck_tree.bind("<Double-1>", self.on_deck_double_click)

        # --- Inside setup_ui, under the Deck Building Sidebar section ---
        button_container = ttk.Frame(deck_frame)
        button_container.pack(fill="x", pady=5)

        # --- Inside setup_ui, under the Deck Building Sidebar section ---
        btn_f = ttk.Frame(deck_frame)
        btn_f.pack(fill="x", pady=5)

        ttk.Button(btn_f, text="📂 Load", command=self.load_deck).pack(side="left", expand=True, fill="x", padx=1)
        ttk.Button(btn_f, text="💾 Save", command=self.save_deck).pack(side="left", expand=True, fill="x", padx=1)
        ttk.Button(btn_f, text="📋 Paste", command=self.open_import_window).pack(side="left", expand=True, fill="x",
                                                                                padx=1)
        ttk.Button(deck_frame, text="🗑️ Clear Deck", command=self.clear_deck).pack(fill="x", pady=2)

        self.count_label = ttk.Label(deck_frame, text="Total Cards: 0 | Format: CC", font=("Arial", 10, "bold"))
        self.count_label.pack(pady=5)

        ttk.Button(deck_frame, text="Add Selected", command=self.add_to_deck).pack(fill="x")
        ttk.Button(deck_frame, text="Remove Selected", command=self.remove_from_deck).pack(fill="x", pady=2)
        ttk.Button(deck_frame, text="Validate Legality", command=self.check_deck).pack(fill="x", pady=5)

    def sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        try:
            l.sort(key=lambda t: float(t[0] if t[0] != "" else -1), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
        tv.heading(col, command=lambda: self.sort_column(tv, col, not reverse))

    def on_search_double_click(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell":
            self.add_to_deck()

    def on_deck_double_click(self, event):
        if self.deck_tree.identify_region(event.x, event.y) == "cell":
            self.remove_from_deck()

    def remove_from_deck(self, event=None):
        selected = self.deck_tree.selection()
        if not selected: return
        selected_index = self.deck_tree.index(selected[0])
        card_name = self.deck_tree.item(selected[0])['values'][0]
        # Match the icon used in refresh_deck_display
        clean_name = card_name.replace("* ", "")

        if clean_name in self.current_deck.cards:
            self.current_deck.cards[clean_name]['qty'] -= 1
            if self.current_deck.cards[clean_name]['qty'] <= 0:
                del self.current_deck.cards[clean_name]
        elif self.current_deck.hero and clean_name == self.current_deck.hero.name:
            self.current_deck.hero = None

        self.refresh_deck_display()
        children = self.deck_tree.get_children()
        if children:
            new_index = min(selected_index, len(children) - 1)
            target_id = children[new_index]
            self.deck_tree.selection_set(target_id)
            self.deck_tree.focus(target_id)

    def on_card_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        card_name = self.tree.item(selected[0])['values'][0]
        res = self.search_engine.conn.execute("SELECT image_url, local_path FROM cards WHERE name = ?",
                                              (card_name,)).fetchone()
        if res:
            self.display_image(res['image_url'], res['local_path'])

    def display_image(self, url, local_filename):
        local_path = os.path.join(os.path.dirname(__file__), "data", "images",
                                  local_filename) if local_filename else None
        try:
            if local_path and os.path.exists(local_path):
                img = Image.open(local_path)
            elif url:
                img = Image.open(BytesIO(requests.get(url, timeout=5).content))
            else:
                return
            img.thumbnail((350, 500))
            photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=photo, text="")
            self.img_label.image = photo
        except Exception:
            self.img_label.config(image='', text="Image not available")

    def perform_search(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        filters = {k: v.get() for k, v in self.vars.items() if v.get() not in ["", False]}
        try:
            results = self.search_engine.advanced_search(filters)
            for r in results:
                self.tree.insert("", "end",
                                 values=(r["name"], r["color"], r["pitch"], r["cost"], r["power"], r["defense"]))
            children = self.tree.get_children()
            if children:
                self.tree.selection_set(children[0])
                self.on_card_select(None)
        except Exception as e:
            messagebox.showerror("Search Error", str(e))

    def open_import_window(self):
        """Opens a pop-up window for pasting a deck list."""
        import_win = tk.Toplevel(self.root)
        import_win.title("Paste Deck List")
        import_win.geometry("400x500")

        ttk.Label(import_win, text="Paste list below (e.g., 3x Wounded Bull):", padding=10).pack()

        # Text area for pasting
        text_area = tk.Text(import_win, wrap="none", height=20)
        text_area.pack(padx=10, pady=5, fill="both", expand=True)

        # Import Button
        btn = ttk.Button(import_win, text="Import into Deck",
                         command=lambda: self.process_pasted_text(text_area.get("1.0", tk.END), import_win))
        btn.pack(pady=10)

    import re

    def process_pasted_text(self, raw_text, window):
        """Parses Fabrary exports and captures the deck name."""
        lines = raw_text.split('\n')
        added_count = 0
        missing_cards = []

        # 1. Reset current deck
        self.current_deck.cards = {}
        self.current_deck.hero = None
        self.current_deck.name = "New Deck"  # Default if no name found

        for line in lines:
            line = line.strip()
            if not line or "Made with" in line or "See the full" in line:
                continue

            # NEW: Capture Deck Name from the paste
            if line.startswith("Name:"):
                self.current_deck.name = line.replace("Name:", "").strip()
                continue

            # Handle Hero
            if line.startswith("Hero:"):
                hero_name = line.replace("Hero:", "").strip()
                hero_obj = self.get_card_object_by_name(hero_name)
                if hero_obj:
                    self.current_deck.set_hero(hero_obj)
                continue

            # Regex to find: [Quantity]x [Card Name] ([Color])
            # Example: "2x Autumn's Touch (red)" -> Groups: "2", "Autumn's Touch"
            match = re.match(r'^(\d+)x?\s+([^(]+)', line)

            if match:
                qty = int(match.group(1))
                # .strip() removes trailing spaces before the parentheses
                name = match.group(2).strip()

                # Use your existing helper to find the card object
                card_obj = self.get_card_object_by_name(name)
                if card_obj:
                    for _ in range(qty):
                        self.current_deck.add_card(card_obj)
                    added_count += qty
                else:
                    missing_cards.append(name)

        self.refresh_deck_display()
        # Only destroy the window if it was provided (for the paste pop-up)
        if window:
            window.destroy()

        if missing_cards:
            messagebox.showwarning("Import Summary",
                                   f"Imported {added_count} cards.\n\nCould not find in DB:\n" +
                                   "\n".join(set(missing_cards)))
        else:
            messagebox.showinfo("Success", f"Successfully imported {added_count} cards!")

    def clear_deck(self):
        """Wipes all cards and the hero from the current deck."""
        # Optional: Ask for confirmation so users don't accidentally delete their work
        if messagebox.askyesno("Clear Deck", "Are you sure you want to delete all cards in this deck?"):
            # 1. Reset the Logic
            self.current_deck.cards = {}
            self.current_deck.hero = None

            # 2. Update the UI
            self.refresh_deck_display()
            print("Deck cleared.")

    from tkinter import filedialog
    import os

    def save_deck(self):
        """
        Saves the deck directly to data/save_data/saved_decks
        using a sanitized version of the deck name.
        """
        if not self.current_deck.cards and not self.current_deck.hero:
            messagebox.showwarning("Save Error", "Your deck is empty!")
            return

        # 1. Setup the Path
        base_path = os.path.dirname(__file__)
        save_dir = os.path.join(base_path, "data", "save_data", "saved_decks")
        os.makedirs(save_dir, exist_ok=True)

        # 2. Sanitize the filename
        # This turns "Calling: Hong Kong 1st" into "Calling Hong Kong 1st"
        safe_name = self.sanitize_filename(self.current_deck.name)
        file_path = os.path.join(save_dir, f"{safe_name}.txt")

        # 3. Write Data
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Name: {self.current_deck.name}\n")
                f.write(f"Hero: {self.current_deck.hero.name if self.current_deck.hero else 'No Hero'}\n")
                f.write(f"Format: {self.current_deck.format}\n\n")

                f.write("Deck cards\n")
                for name, data in sorted(self.current_deck.cards.items()):
                    # Detect pitch for color tags
                    pitch = getattr(data['obj'], 'pitch', None)
                    tag = {1: " (red)", 2: " (yellow)", 3: " (blue)"}.get(pitch, "")
                    f.write(f"{data['qty']}x {name}{tag}\n")

            # Visual feedback without a dialog: update the status label or console
            print(f"Deck saved to: {file_path}")
            messagebox.showinfo("Saved", f"Deck saved as '{safe_name}.txt'")

        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save file: {e}")

    def sanitize_filename(self, filename):
        """Removes characters that are illegal in file names."""
        # Strip out characters like < > : " / \ | ? *
        return re.sub(r'[<>:"/\\|?*]', '', filename).strip()

    def load_deck(self):
        """Loads a saved deck file and populates the current deck list."""
        # 1. Path to your saved decks
        base_path = os.path.dirname(__file__)
        save_dir = os.path.join(base_path, "data", "save_data", "saved_decks")

        # 2. Open the file dialog
        file_path = filedialog.askopenfilename(
            initialdir=save_dir,
            title="Load Saved Deck",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            # 3. Read the content
            with open(file_path, "r", encoding="utf-8") as f:
                deck_content = f.read()

            # 4. Use your existing parser to fill the deck
            self.process_pasted_text(deck_content, window=None)

            messagebox.showinfo("Loaded", f"Successfully loaded: {os.path.basename(file_path)}")

        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load file: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FabGui(root)
    root.mainloop()