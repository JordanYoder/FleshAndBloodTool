import sys
import os

# Ensure Card can be found even if this is called from subfolders
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from card import Card


class Deck:
    def __init__(self, name="New Deck", format_="CC"):
        self.name = name
        self.format = format_  # "CC" or "Blitz"
        self.cards = {}  # Structure: { "Card Name": {"obj": Card, "qty": int} }
        self.hero = None

    def set_hero(self, hero_card):
        """Sets the hero for the deck."""
        self.hero = hero_card

    def add_card(self, card_obj, quantity=1):
        """Adds a card or increments its quantity."""
        name = card_obj.name

        # Check if the card is a Hero type based on your JSON schema
        if "Hero" in card_obj.type_text or "Hero" in card_obj.types:
            self.set_hero(card_obj)
            return f"Hero set to {name}"

        if name in self.cards:
            self.cards[name]["qty"] += quantity
        else:
            self.cards[name] = {"obj": card_obj, "qty": quantity}
        return f"Added {quantity}x {name}"

    def validate_legality(self):
        """Checks format-specific FaB rules."""
        errors = []

        # 1. Hero Check
        if not self.hero:
            errors.append("No hero selected.")

        # 2. Total Count and Card Limits
        total_main_deck = sum(item["qty"] for item in self.cards.values())

        for name, data in self.cards.items():
            card = data["obj"]
            qty = data["qty"]

            # Format quantity limits
            limit = 3 if self.format == "CC" else 2
            if qty > limit:
                errors.append(f"{name}: Too many copies ({qty}/{limit}).")

            # Legality check using the method from Card class
            if not card.is_legal(self.format):
                errors.append(f"{name}: Not legal in {self.format}.")

        # 3. Deck Size Rules
        if self.format == "CC" and total_main_deck < 60:
            errors.append(f"CC Deck too small: {total_main_deck}/60 cards.")
        elif self.format == "Blitz" and total_main_deck != 40:
            errors.append(f"Blitz Deck must be exactly 40 cards (Current: {total_main_deck}).")

        return len(errors) == 0, errors