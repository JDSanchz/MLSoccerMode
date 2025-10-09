import random
from datetime import date, timedelta
from statistics import mean
import pandas as pd
from randomName import random_name
from constants import *
from retirement import season_end_retirements
from transfersAI import ai_transfers, champion_poach_user, trim_ai_reserves
from playerCost import est_cost_eur
from matchEngineSchedules import *
from transfersPlayer import trim_user_reserves
from prompts import prompt_int


def season_dates(year):
    """Return (TM_OPEN, TM_CLOSE, PROCESSING_DAY, SEASON_START, SEASON_END) for a given starting year."""
    tm_open = date(year, 6, 16)
    tm_close = date(year, 8, 13)
    processing = date(year, 8, 14)
    season_start = date(year, 8, 15)
    season_end = date(year+1, 6, 15)
    return tm_open, tm_close, processing, season_start, season_end


def yesno(msg):
    return input(msg).strip().lower().startswith("y")


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


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
        elif self.potential <= 79:
            return "73–79"
        elif self.potential <= 84:
            return "80–84"
        elif self.potential <= 90:
            return "85–90"
        else:
            return "90–95"

    def is_available_on(self, when):
        return self.injured_until is None or when > self.injured_until

    def season_progression(self):
        # Growth till 34: +1..+4 for youth, +1..+3 for others; decline after
        if self.age < 20:
            grow = random.randint(1, 4)
            self.rating = min(self.potential, self.rating + grow)
        elif self.age < 34:
            grow = random.randint(1, 3)
            self.rating = min(self.potential, self.rating + grow)
        else:
            drop = random.randint(0, 4)
            self.rating = max(50, self.rating - drop)

        # 25% chance to permanently reveal potential range if not already visible
        if not getattr(self, "display_potential_range", False) and random.random() < 0.25:
            self.display_potential_range = True

        self.age += 1




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

    def reset_season_stats(self):
        self.points = 0
        self.gf = 0
        self.ga = 0
        for p in self.all_players():
            p.injured_until = None

    def all_players(self):
        return self.starters + self.bench + self.reserves

    def first_team(self):
        return self.starters + self.bench  # no reserves

    def avg_rating(self):
        roster = self.first_team()
        return round(mean(p.rating for p in roster), 1) if roster else self.avg_target

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

        # Do not touch reserves

    # In class Team
    def pick_weighted_origin(self):
        arr = self.origins
        if not arr:
            return "Spain"  # fallback if needed
        if len(arr) == 1:
            return arr[0]
        first_w = 0.25
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
        pos_scores = {}
        pool = self.starters + self.bench
        if not pool:
            return ["ST", "CB", "CM"]
        sums, counts = {}, {}
        for p in pool:
            sums[p.pos] = sums.get(p.pos, 0) + p.rating
            counts[p.pos] = counts.get(p.pos, 0) + 1
        for pos in FORMATIONS[self.formation].keys():
            pos_scores[pos] = (sums.get(pos, 0) / counts.get(pos, 1)) if counts.get(pos) else 0
        order = sorted(pos_scores.items(), key=lambda kv: kv[1])  # lowest first
        return [k for k, _ in order][:3]

    def pay(self, amount):
        if amount > self.budget:
            return False
        self.budget -= amount
        return True

    def receive(self, amount):
        self.budget += amount


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
    }
    base = pools[formation]
    out = []
    i = 0
    while len(out) < size:
        out.append(base[i % len(base)])
        i += 1
    return out


def assign_season_injuries(team, season_start, season_end):
    n = random.randint(3, 5)
    for _ in range(n):
        who = random.choice(team.all_players())
        days = random.randint(20, 280)
        span = (season_end - season_start).days
        if span <= days:
            start_offset = 0
        else:
            start_offset = random.randint(0, span - days)
        when = season_start + timedelta(days=start_offset)
        who.injured_until = when + timedelta(days=days)
        # move to reserves if currently in XI/bench (display-only)
        if who in team.starters:
            team.starters.remove(who)
            team.reserves.append(who)
        elif who in team.bench:
            team.bench.remove(who)
            team.reserves.append(who)


def make_free_agent_pool(num=45):
    pool = []
    base_positions = ["GK", "CB", "LB", "RB", "CDM", "CAM", "CM", "ST", "LW", "RW"]

    # Generate pool of random players
    for _ in range(num):
        pos = random.choice(base_positions)
        nation = random.choice([n for arr in ORIGINS.values() for n in arr])
        name = random_name(nation)
        age = random.randint(16, 38)
        rating = random.randint(70, 86)

        pot = random.randint(79, 95)
        if pot <= rating:
            pot = min(95, rating + 1)  # ensure potential > rating, max 95

        potential_plus = pot - rating
        p = Player(name, pos, nation, age, rating, potential_plus)
        pool.append(p)

    # Ensure at least 2 Goalkeepers (GK)
    gks = [p for p in pool if p.pos == "GK"]
    while len(gks) < 2:
        nation = random.choice([n for arr in ORIGINS.values() for n in arr])
        name = random_name(nation)
        age = random.randint(16, 36)
        rating = random.randint(70, 85)
        pot = min(95, rating + random.randint(1, 5))
        p = Player(name, "GK", nation, age, rating, pot - rating)
        pool.append(p)
        gks.append(p)

    # Keep best 35 players by value (balanced between young and old)
    if len(pool) > 35:
        young = sorted(
            [p for p in pool if p.age <= 25],
            key=lambda x: x.value(),
            reverse=True
        )[:20]
        old = sorted(
            [p for p in pool if 26 <= p.age <= 38],
            key=lambda x: x.value(),
            reverse=True
        )[:15]
        pool = young + old

    return pool



def roster_capacity(team):
    return STARTERS + BENCH + RESERVES


def roster_count(team):
    return len(team.all_players())


def add_to_roster(team, player):
    # Prefer RESERVES → BENCH → STARTERS (new signings usually start low)
    if len(team.reserves) < RESERVES:
        team.reserves.append(player)
        return True
    if len(team.bench) < BENCH:
        team.bench.append(player)
        return True
    if len(team.starters) < STARTERS:
        team.starters.append(player)
        return True
    return False  # No space anywhere

def preseason_menu() -> int:
    print("\nWhat do you want to do?")
    print("  1) See Squad / End Contracts")
    print("  2) Transfer Hub")
    print("  3) Continue to next season")
    return prompt_int("Choice (1-3): ", 1, 3)


def show_player_list(label, players):
    print(f"\n{label}:")
    if not players:
        print("  (none)")
        return

    for i, p in enumerate(players, 1):
        flag = p.flag() if hasattr(p, "flag") else f"({p.nation})"
        pot_display = f"| Pot {p.potential_range:<7}" if getattr(p, "display_potential_range", False) else " " * 13

        print(
            f"  {i:>2}. "
            f"{p.pos:<3} "
            f"{p.rating:>2} OVR  "
            f"{p.name:<28} "
            f"{p.age:>2}y  "
            f"{pot_display}  "
            f"Value €{p.value():,}  {flag}"
        )

def end_contracts_flow(team: "Team"):
    """
    Let the user release players from Starters/Bench/Reserves.
    Uses the same 12% release fee logic as transfers.
    """
    while True:
        print("\n=== See Squad / End Contracts ===")
        show_player_list("Starters", team.starters)
        show_player_list("Bench", team.bench)
        show_player_list("Reserves", team.reserves)

        if not yesno("\nRelease someone? (y/n): "):
            break

        print("\nPick a list to release from:")
        print("  1) Starters")
        print("  2) Bench")
        print("  3) Reserves")
        lst_choice = prompt_int("List (1-3): ", 1, 3)

        pool = team.starters if lst_choice == 1 else team.bench if lst_choice == 2 else team.reserves
        if not pool:
            print("That list is empty.")
            continue

        show_player_list("Selected list", pool)
        idx = prompt_int(f"Release which (1..{len(pool)}): ", 1, len(pool)) - 1
        victim = pool[idx]
        fee = max(1, int(round(victim.value() * 0.12)))

        print(f"Releasing {victim.name} will cost €{fee:,}. Current budget €{team.budget:,}.")
        if yesno("Proceed? (y/n): "):
            if team.pay(fee):
                pool.pop(idx)
                print(f"Released {victim.name}. New budget €{team.budget:,}.")
            else:
                print("Insufficient funds to pay release fee.")
        # loop continues so they can release multiple or exit

import random

def user_transfers(team, free_agents):
    print(f"\nYour budget: €{team.budget:,}")
    print("Sign as many players as you want until you run out of money.")

    # Activate display_potential_range for 50% of all free agents
    half_count = max(1, int(len(free_agents) * 0.5))
    selected_for_display = set(random.sample(range(len(free_agents)), half_count))
    for i, p in enumerate(free_agents):
        p.display_potential_range = i in selected_for_display

    while free_agents:
        ans = input("Make a signing? (y/n): ").strip().lower()
        if ans != "y":
            break

        affordable = [p for p in free_agents if p.value() <= team.budget]
        if not affordable:
            print("No affordable free agents right now.")
            break

        affordable.sort(key=lambda x: x.value(), reverse=True)
        print("\nFree Agents (affordable options):")

        for i, p in enumerate(affordable, 1):
            flag = p.flag() if hasattr(p, "flag") else f"({p.nation})"
            pot_display = f"| Pot {getattr(p, 'potential_range', ''):<7}" if getattr(p, "display_potential_range", False) else " " * 13

            print(
                f"  {i:>2}. "
                f"{p.pos:<3} "
                f"{p.rating:>2} OVR  "
                f"{p.name:<28} "
                f"{p.age:>2}y  "
                f"{pot_display}  "
                f"Value €{p.value():,}  {flag}"
            )

        k = prompt_int(f"Sign which (1..{len(affordable)}): ", 1, len(affordable)) - 1
        signing = affordable[k]
        price = signing.value()

        if team.budget < price:
            print("Insufficient funds.")
            continue

        team.pay(price)
        free_agents.remove(signing)
        team.reserves.append(signing)
        organize_squad(team)
        trim_user_reserves(team)

        print(f"Signed {signing.name} ({signing.nation}) for €{price:,}. Added to Reserves.")
        print(f"Remaining budget: €{team.budget:,}")



def standings_table(teams):
    return sorted(teams, key=lambda t: (t.points, t.gf - t.ga, t.gf), reverse=True)
def apply_retirements(teams):
    print("\nApplying retirements")
    for t in teams:
        keep_starters, keep_bench, keep_res = [], [], []
        for lst, keep in [(t.starters, keep_starters), (t.bench, keep_bench), (t.reserves, keep_res)]:
            for p in lst:
                must_retire = (p.age >= 39) or p.retiring_notice  # your policy
                if not must_retire:
                    keep.append(p)
        t.starters, t.bench, t.reserves = keep_starters, keep_bench, keep_res

def process_rewards_penalties(table):
    if len(table) >= 1:
        table[0].receive(50)
    if len(table) >= 2:
        table[1].receive(40)
    if len(table) >= 3:
        table[2].receive(20)

    for pos, t in enumerate(table, start=1):
        if pos <= t.objective:
            t.receive(5)

    for pos, t in enumerate(table, start=1):
        if pos == t.objective + 1:
            t.budget = int(t.budget * 0.85)

    # Two random clubs from positions 3–10 get €40M each
    eligible = [t for i, t in enumerate(table, start=1) if 3 <= i <= 10]
    if len(eligible) >= 2:
        lucky_two = random.sample(eligible, 2)
        for lucky in lucky_two:
            lucky.receive(40)
            print(f"\nLucky Club: {lucky.name} receives €40M")



def next_season_base_budget(t):
    return max(30, int(t.budget * 0.97))


def manager_switch_option(user, table):
    bottom3 = table[-3:]
    print("\nBottom 3 teams (eligible to switch):")
    for i, t in enumerate(bottom3):
        print(f"  {i+1}. {t.name}  (Pts {t.points})")
    if yesno("Do you want to switch to one of them? (y/n): "):
        k = prompt_int("Pick (1..{}): ".format(len(bottom3)), 1, len(bottom3)) - 1
        print(f"You now manage {bottom3[k].name}.")
        return bottom3[k]
    return user

def organize_squad(team):
    # Build required starter slots from formation
    xi_positions = []
    for pos, c in FORMATIONS[team.formation].items():
        xi_positions += [pos] * c

    # Single sorted pool
    pool = team.all_players()[:]
    pool.sort(key=lambda p: p.rating, reverse=True)

    def take_best_pos(position):
        for i, p in enumerate(pool):
            if p.pos == position:
                return pool.pop(i)
        return None

    def take_best_any():
        return pool.pop(0) if pool else None

    # Fill starters (exact formation positions preferred)
    starters = []
    for pos in xi_positions:
        pick = take_best_pos(pos) or take_best_any()
        if pick:
            starters.append(pick)

    # Bench rule:
    bench = []

    # 1) Second GK (best remaining GK)
    bench_gk = take_best_pos("GK")
    if bench_gk:
        bench.append(bench_gk)

    # 2) Next best CB
    bench_cb = take_best_pos("CB")
    if bench_cb:
        bench.append(bench_cb)

    # 3) Fill remaining bench slots by best rating
    while len(bench) < BENCH and pool:
        bench.append(take_best_any())

    # Remaining = reserves
    reserves = pool

    # Commit with safety caps
    team.starters = starters[:STARTERS]
    team.bench = bench[:BENCH]
    team.reserves = reserves



# =========================
# MAIN FLOW (CONTINUOUS SEASONS)
# =========================
def main():
    random.seed(42)

    # Initialize teams & squads
    teams = [Team(m) for m in TEAMS_INIT]
    for t in teams:
        t.generate_initial_squad()

    # Pick user team
    print("Pick your team:")
    for i, t in enumerate(teams):
        print(f"  {i+1}. {t.name}  (Avg {t.avg_target}, Budget €{t.budget:,}, Obj {t.objective}, {t.formation})")
    me_idx = prompt_int("Choice: ", 1, len(teams)) - 1
    user = teams[me_idx]
    print(f"\nYou manage {user.name}.\n")

    year = INIT_YEAR
    prev_table = None

    while True:
        TM_OPEN, TM_CLOSE, PROCESSING_DAY, SEASON_START, SEASON_END = season_dates(year)
        print(f"\n================  SEASON {year}-{year+1}  ================")

        # Reset season stats
        for t in teams:
            t.reset_season_stats()

        # Top up youth (fill bench/reserve) at season start
        for t in teams:
            t.top_up_youth(is_user=(t is user))

        # ======= Preseason menu (user choice) =======
        while True:
            choice = preseason_menu()
            organize_squad(user)
            if choice == 1:
                # See Squad / End Contracts
                end_contracts_flow(user)
                organize_squad(user)
            elif choice == 2:
                print(f"\n--- Transfer Window: {TM_OPEN.isoformat()} to {TM_CLOSE.isoformat()} ---")
                fa = make_free_agent_pool(30)
                champion_poach_user(prev_table, user)
                # AI transfer order is random
                transfer_order = teams[:]  
                random.shuffle(transfer_order)
                user_transfers(user, fa)
                for t in transfer_order:
                    if t is user:
                        organize_squad(t)
                        continue
                    ai_transfers(t, fa)
                    organize_squad(t)
                    trim_ai_reserves(t)
                break

            elif choice == 3:
                champion_poach_user(prev_table, user, top_chance=0.20, bottom_chance=0, premium_rate=0.25)
                # Continue to next season with no changes
                for t in teams:
                    organize_squad(t)
                break  # proceed to injuries & season
        apply_retirements(teams)
        # Injuries for the season
        print("\nAssigning season injuries...")
        for t in teams:
            assign_season_injuries(t, SEASON_START, SEASON_END)
        print("Injuries assigned.\n")

        # Fixtures: each pair 4 times (2x home, 2x away)
        global _neutral_idx
        _neutral_idx = 0
        fixtures = build_home_and_away(teams)
        scheduled = assign_dates(fixtures, SEASON_START, SEASON_END)

        # Simulate season
        print(f"--- Season {SEASON_START} to {SEASON_END} ---\n")
        for when, (A, B, venue) in scheduled:
            simulate_match(A, B, venue, when)

        # Final table
        table = standings_table(teams)
        print("\n=== FINAL TABLE ===")
        print("Pos Team                Pts   GF  GA  GD   AvgRoster  Budget(€)")
        for i, t in enumerate(table, start=1):
            print(f"{i:>2}. {t.name:<18} {t.points:>3}  {t.gf:>3} {t.ga:>3} {t.gf-t.ga:>3}   {t.avg_rating():>9}  €{t.budget:,}")

        # End-of-season processing (rewards/penalties/lucky)
        process_rewards_penalties(table)

        # Retirement notices
        season_end_retirements(teams)

        # Player progression
        for t in teams:
            for p in t.all_players():
                p.season_progression()

        # Next-season base budgets (apply and print)
        print("\n=== NEXT SEASON BASE BUDGETS (APPLIED) ===")
        for t in teams:
            base = next_season_base_budget(t)
            t.budget = base
            print(f"{t.name:<18} -> Base Budget: €{t.budget:,}")

        # Manager switch option (to a bottom-3 side)
        user = manager_switch_option(user, table)

        prev_table = table[:]
        year += 1

        if not yesno("\nRun another season? (y/n): "):
            print("Thanks for playing!")
            break
if __name__ == "__main__":
    main()
