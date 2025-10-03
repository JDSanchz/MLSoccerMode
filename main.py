import random
from datetime import date, timedelta
from statistics import mean
import pandas as pd
from randomName import random_name
from constants import *
from retirement import season_end_retirements
from transfersAI import ai_transfers
from playerCost import est_cost_eur



# =========================
# UTILITIES
# =========================
def season_dates(year):
    """Return (TM_OPEN, TM_CLOSE, PROCESSING_DAY, SEASON_START, SEASON_END) for a given starting year."""
    tm_open = date(year, 6, 16)
    tm_close = date(year, 8, 13)
    processing = date(year, 8, 14)
    season_start = date(year, 8, 15)
    season_end = date(year+1, 6, 15)
    return tm_open, tm_close, processing, season_start, season_end


def prompt_int(msg, lo, hi):
    while True:
        try:
            v = int(input(msg))
            if lo <= v <= hi:
                return v
        except Exception:
            pass
        print(f"Enter a number between {lo} and {hi}.")


def yesno(msg):
    return input(msg).strip().lower().startswith("y")


def spread_pick(dates, k):
    """Evenly pick k entries across date list."""
    n = len(dates)
    if k <= 1:
        return [dates[0]] if k == 1 else []
    out = []
    for i in range(k):
        idx = int(round(i * (n - 1) / (k - 1)))
        out.append(dates[idx])
    return out


def frisa_dates(start, end):
    d = start
    while d <= end:
        if d.weekday() in (4, 5):  # Fri, Sat
            yield d
        d += timedelta(days=1)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# =========================
# DOMAIN OBJECTS
# =========================
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

    def value(self):
        return est_cost_eur(self.age, self.rating)

    def is_available_on(self, when):
        return self.injured_until is None or when > self.injured_until

    def season_progression(self):
        # Growth till 34: +1..+3 not exceeding potential; decline after
        if self.age < 34:
            grow = random.randint(1, 3)
            self.rating = min(self.potential, self.rating + grow)
        else:
            drop = random.randint(0, 4)
            self.rating = max(50, self.rating - drop)
        self.age += 1
        # No contracts — only retirement logic applies elsewhere


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
            p.retiring_notice = False

    def all_players(self):
        return self.starters + self.bench + self.reserves

    def avg_rating(self):
        roster = self.all_players()
        return round(mean([p.rating for p in roster]), 1) if roster else self.avg_target

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

    def top_up_youth(self, is_user):
        def add_player(target_list, count):
            for _ in range(count):
                pos = random.choice(["GK", "CB", "LB", "RB", "CDM", "CAM", "CM", "ST", "LW", "RW"])
                nation = random.choice(self.origins)
                age = random.randint(YOUTH_AGE_MIN, YOUTH_AGE_MAX)
                ovr = random.randint(YOUTH_OVR_MIN, YOUTH_OVR_MAX)
                pot_min, pot_max = (YOUTH_POT_USER if is_user else YOUTH_POT_AI)
                potential_plus = random.randint(max(1, pot_min - ovr), max(1, pot_max - ovr))
                target_list.append(Player(random_name(nation), pos, nation, age, ovr, potential_plus))

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


# =========================
# SQUAD GENERATION HELPERS
# =========================
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


# =========================
# MATCH ENGINE
# =========================
def match_probabilities(rA, rB, venue):
    if venue == "homeA":
        rA += 1.5
        rB -= 1.5
    elif venue == "homeB":
        rB += 1.5
        rA -= 1.5
    gap = rA - rB
    p_draw = 0.25 if abs(gap) <= 2 else 0.15

    def sigmoid(x):
        return 1 / (1 + pow(2.71828, -x))

    pA = sigmoid(gap / 6) * (1 - p_draw)
    pB = (1 - p_draw) - pA
    return pA, p_draw, pB


def result_score(a_wins):
    if a_wins is True:
        gA = random.choice([1, 2, 2, 3, 3, 4])
        gB = random.choice([0, 0, 1, 1, 2])
        if gB >= gA:
            gB = max(0, gA - 1)
    elif a_wins is False:
        gB = random.choice([1, 2, 2, 3, 3, 4])
        gA = random.choice([0, 0, 1, 1, 2])
        if gA >= gB:
            gA = max(0, gB - 1)
    else:
        g = random.choice([0, 1, 1, 2, 2])
        return g, g
    return gA, gB


_neutral_idx = 0


def simulate_match(teamA, teamB, venue, when):
    rA = teamA.avg_rating()
    rB = teamB.avg_rating()
    pA, pD, pB = match_probabilities(rA, rB, venue)
    roll = random.random()
    if roll < pA:
        gA, gB = result_score(True)
        teamA.points += 3
    elif roll < pA + pD:
        gA, gB = result_score(None)
        teamA.points += 1
        teamB.points += 1
    else:
        gA, gB = result_score(False)
        teamB.points += 3
    teamA.gf += gA
    teamA.ga += gB
    teamB.gf += gB
    teamB.ga += gA

    # Only HOME/AWAY now
    label = "HOME" if venue == "homeA" else "AWAY"
    venue_name = teamA.stadium if venue == "homeA" else teamB.stadium
    print(f"{when.isoformat()} [{label}] {teamA.name} {gA}-{gB} {teamB.name} @ {venue_name}")


# =========================
# SCHEDULING
# =========================
def all_pairs(teams):
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            yield teams[i], teams[j]


def build_four_meetings(teams):
    fixtures = []
    for A, B in all_pairs(teams):
        fixtures.extend([
            (A, B, "homeA"), (A, B, "homeA"),
            (A, B, "homeB"), (A, B, "homeB"),
        ])
    return fixtures


def assign_dates(fixtures, season_start, season_end):
    all_weekend = list(frisa_dates(season_start, season_end))
    if len(all_weekend) < len(fixtures):
        raise RuntimeError("Not enough Fri/Sat dates to host all matches.")
    picked = spread_pick(all_weekend, len(fixtures))
    scheduled = list(zip(picked, fixtures))
    scheduled.sort(key=lambda x: x[0])
    return scheduled


# =========================
# INJURIES / RETIREMENTS
# =========================
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

# =========================
# TRANSFER MARKET
# =========================
def make_free_agent_pool(num=35):
    pool = []
    base_positions = ["GK", "CB", "LB", "RB", "CDM", "CAM", "CM", "ST", "LW", "RW"]
    for _ in range(num):
        pos = random.choice(base_positions)
        nation = random.choice([n for arr in ORIGINS.values() for n in arr])
        name = random_name(nation)
        age = random.randint(16, 38)
        rating = random.randint(70, 86)

        pot = random.randint(79, 95)
        if pot <= rating:
            pot = min(95, rating + 1)  # ensure potential > rating, max 95

        potential_plus = pot - rating  # >= 1
        p = Player(name, pos, nation, age, rating, potential_plus)
        pool.append(p)

    if len(pool) > 35:
        young = sorted([p for p in pool if p.age <= 25], key=lambda x: x.rating, reverse=True)[:20]
        old = sorted([p for p in pool if 26 <= p.age <= 38], key=lambda x: x.rating, reverse=True)[:15]
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


def user_transfers(team, free_agents):
    print(f"\nYour budget: €{team.budget:,}")
    print("Sign as many as you want. If your roster is full, you must release a Bench or Reserve first (release fee = 12% of value).")

    while free_agents:
        ans = input("Make a signing? (y/n): ").strip().lower()
        if ans != "y":
            break

        # If roster full, force a release from Bench/Reserves to free a slot
        if roster_count(team) >= roster_capacity(team):
            candidates = team.bench + team.reserves   # starters are protected
            if not candidates:
                print("Roster is full and you have no Bench/Reserves to release.")
                continue

            # Lowest 10 by market value
            lowest = sorted(candidates, key=lambda x: x.value())[:min(10, len(candidates))]
            print("Roster full. Choose a Bench/Reserve to release (lowest by value):")
            for i, p in enumerate(lowest):
                print(f"  {i+1}. {p.pos} {p.name} {p.rating} OVR  Age {p.age}  Value €{p.value():,}")
            k = prompt_int(f"Release which (1..{len(lowest)}): ", 1, len(lowest)) - 1
            victim = lowest[k]
            fee = int(victim.value() * 0.12)
            if team.pay(fee):
                if victim in team.bench:
                    team.bench.remove(victim)
                elif victim in team.reserves:
                    team.reserves.remove(victim)
                print(f"Released {victim.name} (fee €{fee:,}).")
            else:
                print("Insufficient funds to pay release fee.")
                continue

        # Proceed to shortlist and signing (unchanged)
        affordable = [p for p in free_agents if p.value() <= team.budget]
        if not affordable:
            print("No affordable free agents right now.")
            break

        shortlisted = sorted(affordable, key=lambda x: x.rating, reverse=True)[:12]
        print("\nFree Agents (top affordable):")
        for i, p in enumerate(shortlisted):
            print(f"  {i+1:>2}. {p.pos:<3} {p.name:<22} {p.rating} OVR  {p.age}y  Value €{p.value():,}")
        k = prompt_int(f"Sign which (1..{len(shortlisted)}): ", 1, len(shortlisted)) - 1
        signing = shortlisted[k]
        price = signing.value()

        if not team.pay(price):
            print("Insufficient funds.")
            continue

        free_agents.remove(signing)
        if add_to_roster(team, signing):
            print(f"Signed {signing.name} for €{price:,}. Remaining budget €{team.budget:,}")
        else:
            print("No roster slot available unexpectedly; refunding.")
            team.receive(price)


# =========================
# SEASON PROCESSING
# =========================
def standings_table(teams):
    return sorted(teams, key=lambda t: (t.points, t.gf - t.ga, t.gf), reverse=True)


def process_rewards_penalties(table):
    if len(table) >= 1:
        table[0].receive(50)
    if len(table) >= 2:
        table[1].receive(40)
    if len(table) >= 3:
        table[2].receive(20)
    for pos, t in enumerate(table, start=1):
        if pos <= t.objective:
            t.receive(15)
    for pos, t in enumerate(table, start=1):
        if pos == t.objective + 1:
            t.budget = int(t.budget * 0.85)
    eligible = [t for i, t in enumerate(table, start=1) if 3 <= i <= 5]
    if eligible:
        lucky = random.choice(eligible)
        lucky.receive(50)
        print(f"\nLucky Club: {lucky.name} receives €50M")


def next_season_base_budget(t):
    return max(35, int(t.budget * 0.97))


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

    # Work on a single pool (all players), then reassign lists cleanly
    pool = team.all_players()[:]
    pool.sort(key=lambda p: p.rating, reverse=True)  # global best-first

    def take_best(match_pos=None):
        # Prefer exact-position match; fallback to best overall
        if match_pos:
            for i,p in enumerate(pool):
                if p.pos == match_pos:
                    return pool.pop(i)
        return pool.pop(0) if pool else None

    # Fill starters (exact formation positions)
    starters = []
    for pos in xi_positions:
        pick = take_best(pos)
        if pick: starters.append(pick)

    # Fill bench using suggested bench positions
    bench_positions = suggest_bench_positions(team.formation, BENCH)
    bench = []
    for pos in bench_positions:
        pick = take_best(pos)
        if pick: bench.append(pick)

    # Remaining players become reserves
    reserves = pool

    # Commit
    team.starters = starters[:STARTERS]            # safety cap
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
                # Print your roster before the transfer window
        

        # Transfer window
        print(f"\n--- Transfer Window: {TM_OPEN.isoformat()} to {TM_CLOSE.isoformat()} ---")
        fa = make_free_agent_pool(35)

        # Transfer order: previous table order (if exists) else alphabetical
        transfer_order = (prev_table if prev_table else sorted(teams, key=lambda x: x.name))
        for t in transfer_order:
            if t is user:
                continue
            ai_transfers(t, fa)

        # User transfers
        user_transfers(user, fa)
        for t in teams:
            organize_squad(t)

        print("\n=== Your Current Roster ===")
        print("Starters:")
        for p in user.starters:
            print(f"  {p.pos} {p.name} ({p.nation}) - {p.rating} OVR, {p.age}y")

        print("\nBench:")
        for p in user.bench:
            print(f"  {p.pos} {p.name} ({p.nation}) - {p.rating} OVR, {p.age}y")

        print("\nReserves:")
        for p in user.reserves:
            print(f"  {p.pos} {p.name} ({p.nation}) - {p.rating} OVR, {p.age}y")


        # Injuries for the season
        print("\nAssigning season injuries...")
        for t in teams:
            assign_season_injuries(t, SEASON_START, SEASON_END)
        print("Injuries assigned.\n")

        # Fixtures: each pair 4 times (2x home, 2x away)
        global _neutral_idx
        _neutral_idx = 0
        fixtures = build_four_meetings(teams)
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
