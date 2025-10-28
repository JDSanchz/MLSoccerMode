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
        self.user_manager_seasons = 0
        self.user_manager_objective_met = False

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
        # Build XI positions from formation, assign randomly so initial strengths vary
        xi_positions = []
        for pos, c in FORMATIONS[self.formation].items():
            xi_positions += [pos] * c
        random.shuffle(xi_positions)

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
                potential = ovr + potential_plus
                if potential > 91 and random.randint(1, 20) != 1:
                    potential = 91
                    potential_plus = max(1, potential - ovr)
                tag = "❖ "  # normal youth
                name = tag + random_name(nation)
                target_list.append(Player(name, pos, nation, age, ovr, potential_plus))

        if len(self.bench) < BENCH:
            add_player(self.bench, BENCH - len(self.bench))
        if len(self.reserves) < RESERVES:
            add_player(self.reserves, RESERVES - len(self.reserves))

    def weakest_positions(self, return_details=False):
        """
        Identify the soft spots in the XI. If a formation slot has no natural player,
        treat it as rating 0 so we surface true gaps (e.g., missing LB entirely).
        Also print a short diagnostic explaining why each returned position needs help.
        Set return_details=True to get the rich records used for prioritisation.
        """
        if not self.starters:
            print(f"{self.name}: weakest_positions fallback (no starters set) -> ST, CB, CM.")
            fallback = [
                {"pos": "ST", "avg": self.avg_target, "count": 0, "delta": 0},
                {"pos": "CB", "avg": self.avg_target, "count": 0, "delta": 0},
                {"pos": "CM", "avg": self.avg_target, "count": 0, "delta": 0},
            ]
            return fallback if return_details else [item["pos"] for item in fallback]

        formation = FORMATIONS.get(self.formation, {})
        if not formation:
            return ["ST", "CB", "CM"] if not return_details else []

        tracked_positions = {pos: [] for pos in formation.keys()}

        xi_slots = []
        for pos, count in formation.items():
            xi_slots.extend([pos] * count)

        for idx, slot in enumerate(xi_slots):
            player = self.starters[idx] if idx < len(self.starters) else None
            if player:
                tracked_positions[slot].append(player.rating)

        xi_avg = sum(p.rating for p in self.starters) / len(self.starters)
        scored = []
        for pos, ratings in tracked_positions.items():
            avg = sum(ratings) / len(ratings) if ratings else 0
            scored.append(
                {
                    "pos": pos,
                    "avg": avg,
                    "count": len(ratings),
                    "delta": xi_avg - avg,
                }
            )

        scored.sort(key=lambda item: item["avg"])
        weakest = scored[:3]

        for info in weakest:
            pos = info["pos"]
            if info["count"] == 0:
                reason = "no natural player for required formation slot."
            else:
                reason = (
                    f"avg starter rating {info['avg']:.1f} vs XI avg {xi_avg:.1f} "
                    f"({info['delta']:+.1f})."
                )
            print(f"{self.name}: need {pos} — {reason}")

        if return_details:
            return weakest
        return [item["pos"] for item in weakest]


    def pay(self, amount):
        if amount > self.budget:
            return False
        self.budget -= amount
        return True

    def receive(self, amount):
        self.budget += amount
