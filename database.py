import json
from card import Card


class CardDatabase:
    def __init__(self, path="data/card.json"):
        self.cards = self._load_cards(path)

    def _load_cards(self, path):
        with open(path, encoding="utf-8") as f:
            raw_cards = json.load(f)

        cards = []
        for entry in raw_cards:
            try:
                cards.append(Card(entry))
            except Exception as e:
                print(f"Failed to load card: {entry.get('name')} → {e}")

        return cards
