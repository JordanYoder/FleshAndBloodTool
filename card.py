class Card:
    def __init__(self, data: dict):
        self.name = data.get("name")
        self.color = data.get("color", "N/A")
        self.pitch = data.get("pitch")
        self.cost = data.get("cost")
        self.power = data.get("power")
        self.defense = data.get("defense")
        self.types = data.get("types", [])
        self.type_text = data.get("type_text", "")
        self.traits = data.get("traits", [])
        self.keywords = data.get("card_keywords", [])
        self.text = data.get("functional_text", "")

        # Extract the image URL from the first printing in the list
        printings = data.get("printings", [])
        if isinstance(printings, list) and len(printings) > 0:
            self.image_url = printings[0].get("image_url")
        else:
            self.image_url = None

        self.legalities = {
            "CC": data.get("cc_legal", False),
            "Blitz": data.get("blitz_legal", False),
            "Silver Age": data.get("silver_age_legal", False)
        }

    def is_legal(self, format_name):
        return self.legalities.get(format_name, False)