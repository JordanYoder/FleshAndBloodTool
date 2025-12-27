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


if __name__ == "__main__":
    root = tk.Tk()
    app = FabGui(root)
    root.mainloop()