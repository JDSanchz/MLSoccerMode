import random
from playerCost import est_cost_eur
from utils import clamp
class Player:
    def __init__(self, name, pos, nation, age, rating, potential_plus):
        self.name = name
        self.pos = pos
        self.nation = nation
        self.age = age
        self.rating = rating
        self.potential = clamp(rating + potential_plus, 70, 95)
        self.injured_until = None
        self.retiring_notice = False
        self.potential_range = self._assign_potential_range()
        self.display_potential_range = False

    def value(self):
        return est_cost_eur(self.age, self.rating)
    
    def _assign_potential_range(self):
        """Assign a potential range bucket based on the player's potential."""
        if self.potential <= 72:
            return "60–72"
        elif self.potential <= 77:
            return "73–77"
        elif self.potential <= 82:
            return "78–82"
        elif self.potential <= 88:
            return "83–88"
        elif self.potential <= 92:
            return "89–92"
        else:
            return "93–95"


    def is_available_on(self, when):
        return self.injured_until is None or when > self.injured_until

    def season_progression(self):
        # Growth till 34: +1..+4 for youth, +1..+3 for others; decline after
        if self.age < 20:
            grow = random.randint(1, 5)
            self.rating = min(self.potential, self.rating + grow)
        elif self.age < 34:
            grow = random.randint(0, 4)
            self.rating = min(self.potential, self.rating + grow)
        else:
            drop = random.randint(0, 4)
            self.rating = max(50, self.rating - drop)

        # 25% chance to permanently reveal potential range if not already visible
        if not getattr(self, "display_potential_range", False) and random.random() < 0.25:
            self.display_potential_range = True

        self.age += 1
        self.potential_range = self._assign_potential_range()

    def apply_potential_boost(self, delta):
        old_pot = self.potential
        self.potential = clamp(self.potential + delta, 70, 95)
        self.potential_range = self._assign_potential_range()
        self.display_potential_range = True 
        return old_pot, self.potential
