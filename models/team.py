from constants import *
from statistics import mean
from models.player import Player
import random
from utils import clamp
from randomName import random_name

def generate_rating_set(n, target_avg, spread=4.0):
    arr = [clamp(round(random.gauss(target_avg, spread)), 75, 89) for _ in range(n)]
    want = target_avg * n
    diff = round(want - sum(arr))
    step = 1 if diff > 0 else -1
    i = 0
    while diff != 0 and i < 20000:
        j = i % n
        new_val = clamp(arr[j] + step, 75, 89)
        if new_val != arr[j]:
            arr[j] = new_val
            diff -= step
        i += 1
    return arr


def suggest_bench_positions(formation, size):
    pools = {
        "4-3-3": ["GK", "CB", "LB", "RB", "CM", "CM", "LW", "RW", "ST"],
        "4-4-2": ["GK", "CB", "LB", "RB", "CDM", "CAM", "LW", "RW", "ST"],
        "3-5-2": ["GK", "CB", "CDM", "CAM", "LW", "RW", "ST"],
    }
    base = pools[formation]
    out = []
    i = 0
    while len(out) < size:
        out.append(base[i % len(base)])
        i += 1
    return out


class Team:
    def __init__(self, meta):
        self.name = meta["name"]
        self.avg_target = meta["avg"]
        self.budget = meta["budget"]
        self.objective = meta["objective"]
        self.formation = meta["formation"]
        self.stadium = meta["stadium"]
        self.origins = ORIGINS[self.name]
        self.starters = []
        self.bench = []
        self.reserves = []
        self.points = 0
        self.gf = 0
        self.ga = 0
        self.top3_streak = 0
        self.poach_protected = []

    def reset_season_stats(self):
        self.points = 0
        self.gf = 0
        self.ga = 0
        for p in self.all_players():
            p.injured_until = None
        self.cleanup_poach_protected()

    def all_players(self):
        return self.starters + self.bench + self.reserves

    def first_team(self):
        return self.starters + self.bench  # no reserves

    def avg_rating(self):
        roster = self.first_team()
        return round(mean(p.rating for p in roster), 1) if roster else self.avg_target

    def cleanup_poach_protected(self):
        roster = set(self.all_players())
        self.poach_protected = [p for p in self.poach_protected if p in roster]

    def protect_player(self, player):
        self.cleanup_poach_protected()
        if player in self.poach_protected:
            return True
        if len(self.poach_protected) >= 3:
            return False
        if player not in self.all_players():
            return False
        self.poach_protected.append(player)
        return True

    def unprotect_player(self, player):
        if player in self.poach_protected:
            self.poach_protected.remove(player)

    def generate_initial_squad(self):
        # Build XI positions from formation
        xi_positions = []
        for pos, c in FORMATIONS[self.formation].items():
            xi_positions += [pos] * c

        # Generate ratings for Starters + Bench, centered on team average
        total_needed = STARTERS + BENCH
        ratings = generate_rating_set(total_needed, self.avg_target)
        ratings.sort(reverse=True)  # best first

        # Starters = highest ratings
        for i, pos in enumerate(xi_positions):
            nation = random.choice(self.origins)
            self.starters.append(
                Player(
                    random_name(nation),
                    pos,
                    nation,
                    random.randint(18, 35),
                    ratings[i],
                    random.randint(1, 3),
                )
            )

        # Bench = next best ratings
        bench_positions = suggest_bench_positions(self.formation, BENCH)
        cursor = STARTERS
        for pos in bench_positions:
            nation = random.choice(self.origins)
            self.bench.append(
                Player(
                    random_name(nation),
                    pos,
                    nation,
                    random.randint(18, 35),
                    ratings[cursor],
                    random.randint(1, 3),
                )
            )
            cursor += 1

    # In class Team
    def pick_weighted_origin(self):
        arr = self.origins
        if not arr:
            return "Spain"  # fallback if needed
        if len(arr) == 1:
            return arr[0]
        first_w = 0.40
        rest_w = (1.0 - first_w) / (len(arr) - 1)
        weights = [first_w] + [rest_w] * (len(arr) - 1)
        return random.choices(arr, weights=weights, k=1)[0]

    def top_up_youth(self, is_user):
        def add_player(target_list, count):
            for _ in range(count):
                pos = random.choice(["GK", "CB", "LB", "RB", "CDM", "CAM", "CM", "ST", "LW", "RW"])
                nation = self.pick_weighted_origin()
                age = random.randint(YOUTH_AGE_MIN, YOUTH_AGE_MAX)
                ovr = random.randint(YOUTH_OVR_MIN, YOUTH_OVR_MAX)
                pot_min, pot_max = (YOUTH_POT_USER if is_user else YOUTH_POT_AI)
                potential_plus = random.randint(max(1, pot_min - ovr), max(1, pot_max - ovr))
                name = "❖ " + random_name(nation)  # youth tag here
                target_list.append(Player(name, pos, nation, age, ovr, potential_plus))

        if len(self.bench) < BENCH:
            add_player(self.bench, BENCH - len(self.bench))
        if len(self.reserves) < RESERVES:
            add_player(self.reserves, RESERVES - len(self.reserves))

    def weakest_positions(self):
        pool = self.starters + self.bench
        if not pool:
            return ["ST", "CB", "CM"]

        needs = []
        formation_positions = FORMATIONS.get(self.formation, {})

        for pos in formation_positions.keys():
            players = [p for p in pool if p.pos == pos]
            count = len(players)
            avg_rating = (sum(p.rating for p in players) / count) if count else 0

            # Prioritize positions with thin coverage first, then by low average rating
            if count == 0:
                coverage_priority = -2
            elif count == 1:
                coverage_priority = -1
            else:
                coverage_priority = 0

            needs.append((coverage_priority, avg_rating, pos))

        needs.sort(key=lambda item: (item[0], item[1]))
        weakest = [pos for _, _, pos in needs][:3]

        # Fallback: include other roster positions if formation list was short
        if len(weakest) < 3:
            remaining = [
                p.pos for p in pool
                if p.pos not in weakest
            ]
            for pos in remaining:
                if pos not in weakest:
                    weakest.append(pos)
                if len(weakest) == 3:
                    break

        return weakest

    def pay(self, amount):
        if amount > self.budget:
            return False
        self.budget -= amount
        return True

    def receive(self, amount):
        self.budget += amount
