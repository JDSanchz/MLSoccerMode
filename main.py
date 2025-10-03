#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from datetime import date, timedelta
from statistics import mean
import joblib
import pandas as pd
# Load the trained model
model = joblib.load("random_forest_model.pkl")

# =========================
# CONFIG & INPUT DATA
# =========================
INIT_YEAR = 2025  # first season start (Aug 15, 2025)

NEUTRAL_STADIUMS = [
    "Wembley Stadium",
    "Stade de France",
    "Old Trafford",
    "Estadio da Luz",
    "Estadio Azteca",
    "Rose Bowl",
    "Estadio Monumental Antonio Vespucio Liberti",
    "MetLife Stadium",
]

# Teams (from your CSV block)
TEAMS_INIT = [
    {"name": "PSG",            "avg": 88, "budget": 250_000_000, "objective": 1, "formation": "4-3-3", "stadium": "Parc des Princes"},
    {"name": "Liverpool",      "avg": 88, "budget": 300_000_000, "objective": 1, "formation": "4-4-2", "stadium": "Anfield"},
    {"name": "Barcelona",      "avg": 86, "budget": 100_000_000, "objective": 2, "formation": "4-3-3", "stadium": "Spotify Camp Nou"},
    {"name": "Real Madrid",    "avg": 86, "budget": 180_000_000, "objective": 2, "formation": "4-4-2", "stadium": "Santiago Bernabéu Stadium"},
    {"name": "Bayern Munich",  "avg": 85, "budget": 120_000_000, "objective": 2, "formation": "4-3-3", "stadium": "Allianz Arena"},
]

# Player origins (subset provided)
ORIGINS = {
    "PSG": ["France","Morocco","Argentina","Belgium","Nigeria"],
    "Liverpool": ["England","France","Brazil","Colombia","Uruguay"],
    "Barcelona": ["Spain","United States","Argentina","Netherlands","Chile"],
    "Real Madrid": ["Spain","England","Brazil","Belgium","Argentina"],
    "Bayern Munich": ["Germany","Japan","Portugal","France","United States"],
}

# Allowed formations
FORMATIONS = {
    "4-3-3": {"GK":1,"CB":2,"LB":1,"RB":1,"CM":3,"LW":1,"RW":1,"ST":1},
    "4-4-2": {"GK":1,"CB":2,"LB":1,"RB":1,"CDM":1,"CAM":1,"LW":1,"RW":1,"ST":2},
}

# Roster sizes
STARTERS = 11
BENCH = 8
RESERVES = 8

# Youth new-season additions
YOUTH_OVR_MIN, YOUTH_OVR_MAX = 70, 74
YOUTH_AGE_MIN, YOUTH_AGE_MAX = 16, 25
YOUTH_POT_USER = (77, 95)
YOUTH_POT_AI   = (80, 92)

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
            if lo <= v <= hi: return v
        except Exception:
            pass
        print(f"Enter a number between {lo} and {hi}.")

def yesno(msg):
    return input(msg).strip().lower().startswith("y")

def spread_pick(dates, k):
    """Evenly pick k entries across date list."""
    n = len(dates)
    if k <= 1: return [dates[0]] if k == 1 else []
    out = []
    for i in range(k):
        idx = int(round(i * (n - 1) / (k - 1)))
        out.append(dates[idx])
    return out

def frisa_dates(start, end):
    d = start
    while d <= end:
        if d.weekday() in (4,5):  # Fri, Sat
            yield d
        d += timedelta(days=1)

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

FEATURES = ["Age", "Rating"]

def est_cost_eur(age, rating):
    """Cost estimate using trained RandomForest model (euros)."""
    X = pd.DataFrame([[age, rating]], columns=FEATURES)
    raw = model.predict(X)[0]
    return max(int(round(raw)), 1)

def random_name(nation):
    syll = ["al","an","ar","be","da","di","en","el","fa","jo","ka","li","ma","mo","ni","ra","ro","sa","ti","ul","vi"]
    return (nation[:2].upper() + " " + "".join(random.choice(syll) for _ in range(2))).title()

# =========================
# DOMAIN OBJECTS
# =========================
class Player:
    def __init__(self, name, pos, nation, age, rating, potential_plus, contract_years):
        self.name = name
        self.pos = pos
        self.nation = nation
        self.age = age
        self.rating = rating
        self.potential = clamp(rating + potential_plus, 70, 95)
        self.contract = clamp(contract_years, 1, 4)
        self.injured_until = None
        self.retiring_notice = False

    def value(self):
        return est_cost_eur(self.age, self.rating)

    def is_available_on(self, when):
        return self.injured_until is None or when > self.injured_until

    def season_progression(self):
        # Growth till 34: +1..+3 not exceeding potential; decline after
        if self.age < 34:
            grow = random.randint(1,3)
            self.rating = min(self.potential, self.rating + grow)
        else:
            drop = random.randint(0,4)
            self.rating = max(50, self.rating - drop)
        self.age += 1
        self.contract = max(0, self.contract - 1)

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
        self.locked = set()  # intransferibles
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
        # XI from formation
        xi_positions = []
        for pos, c in FORMATIONS[self.formation].items():
            xi_positions += [pos] * c
        total_needed = STARTERS + BENCH + RESERVES
        ratings = generate_rating_set(total_needed, self.avg_target)

        # starters
        for i, pos in enumerate(xi_positions):
            nation = random.choice(self.origins)
            name = random_name(nation)
            age = random.randint(18,35)
            r = ratings[i]
            pot_plus = random.randint(1,3)
            contract = random.randint(1,4)
            self.starters.append(Player(name, pos, nation, age, r, pot_plus, contract))

        # bench + reserves
        bench_positions = suggest_bench_positions(self.formation, BENCH)
        res_positions   = suggest_bench_positions(self.formation, RESERVES)
        cursor = STARTERS
        for pos in bench_positions:
            nation = random.choice(self.origins)
            self.bench.append(Player(random_name(nation), pos, nation, random.randint(18,35),
                                     ratings[cursor], random.randint(1,3), random.randint(1,4)))
            cursor += 1
        for pos in res_positions:
            nation = random.choice(self.origins)
            self.reserves.append(Player(random_name(nation), pos, nation, random.randint(18,35),
                                        ratings[cursor], random.randint(1,3), random.randint(1,4)))
            cursor += 1

    def top_up_youth(self, is_user):
        """Fill open bench/reserve spots with youth (ages 16–25, OVR 70–74, potential per rules)."""
        def add_player(target_list, count):
            for _ in range(count):
                pos = random.choice(["GK","CB","LB","RB","CDM","CAM","CM","ST","LW","RW"])
                nation = random.choice(self.origins)
                age = random.randint(YOUTH_AGE_MIN, YOUTH_AGE_MAX)
                ovr = random.randint(YOUTH_OVR_MIN, YOUTH_OVR_MAX)
                pot_min, pot_max = (YOUTH_POT_USER if is_user else YOUTH_POT_AI)
                potential_plus = random.randint(max(1, pot_min - ovr), max(1, pot_max - ovr))
                years = random.randint(1,3)
                target_list.append(Player(random_name(nation), pos, nation, age, ovr, potential_plus, years))

        if len(self.bench) < BENCH:
            add_player(self.bench, BENCH - len(self.bench))
        if len(self.reserves) < RESERVES:
            add_player(self.reserves, RESERVES - len(self.reserves))

    def weakest_positions(self):
        pos_scores = {}
        pool = self.starters + self.bench
        if not pool:
            return ["ST","CB","CM"]
        sums, counts = {}, {}
        for p in pool:
            sums[p.pos] = sums.get(p.pos, 0) + p.rating
            counts[p.pos] = counts.get(p.pos, 0) + 1
        for pos in FORMATIONS[self.formation].keys():
            pos_scores[pos] = (sums.get(pos,0) / counts.get(pos,1)) if counts.get(pos) else 0
        order = sorted(pos_scores.items(), key=lambda kv: kv[1])  # lowest first
        return [k for k,_ in order][:3]

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
        "4-3-3": ["GK","CB","LB","RB","CM","CM","LW","RW","ST"],
        "4-4-2": ["GK","CB","LB","RB","CDM","CAM","LW","RW","ST"],
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
    if venue == "homeA": rA += 1.5; rB -= 1.5
    elif venue == "homeB": rB += 1.5; rA -= 1.5
    gap = rA - rB
    p_draw = 0.25 if abs(gap) <= 2 else 0.15
    def sigmoid(x): return 1 / (1 + pow(2.71828, -x))
    pA = sigmoid(gap / 6) * (1 - p_draw)
    pB = (1 - p_draw) - pA
    return pA, p_draw, pB

def result_score(a_wins):
    if a_wins is True:
        gA = random.choice([1,2,2,3,3,4]); gB = random.choice([0,0,1,1,2])
        if gB >= gA: gB = max(0, gA-1)
    elif a_wins is False:
        gB = random.choice([1,2,2,3,3,4]); gA = random.choice([0,0,1,1,2])
        if gA >= gB: gA = max(0, gB-1)
    else:
        g = random.choice([0,1,1,2,2]); return g, g
    return gA, gB

_neutral_idx = 0
def next_neutral():
    global _neutral_idx
    v = NEUTRAL_STADIUMS[_neutral_idx % len(NEUTRAL_STADIUMS)]
    _neutral_idx += 1
    return v

def simulate_match(teamA, teamB, venue, when):
    rA = teamA.avg_rating()
    rB = teamB.avg_rating()
    pA, pD, pB = match_probabilities(rA, rB, venue)
    roll = random.random()
    if roll < pA:
        gA, gB = result_score(True); teamA.points += 3
    elif roll < pA + pD:
        gA, gB = result_score(None); teamA.points += 1; teamB.points += 1
    else:
        gA, gB = result_score(False); teamB.points += 3
    teamA.gf += gA; teamA.ga += gB
    teamB.gf += gB; teamB.ga += gA
    label = {"homeA":"HOME","homeB":"AWAY","neutral":"NEUTRAL"}[venue]
    venue_name = (teamA.stadium if venue=="homeA" else teamB.stadium if venue=="homeB" else next_neutral())
    print(f"{when.isoformat()} [{label}] {teamA.name} {gA}-{gB} {teamB.name} @ {venue_name}")

# =========================
# SCHEDULING
# =========================
def all_pairs(teams):
    for i in range(len(teams)):
        for j in range(i+1, len(teams)):
            yield teams[i], teams[j]

def build_five_meetings(teams):
    fixtures = []
    for A,B in all_pairs(teams):
        fixtures.extend([(A,B,"homeA"), (A,B,"homeB"), (A,B,"neutral"), (A,B,"neutral"), (A,B,"neutral")])
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
    n = random.randint(3,5)
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
            team.starters.remove(who); team.reserves.append(who)
        elif who in team.bench:
            team.bench.remove(who); team.reserves.append(who)

def season_end_retirements(teams):
    for t in teams:
        above34 = [p for p in t.all_players() if p.age > 34]
        random.shuffle(above34)
        for p in above34[:4]:
            p.retiring_notice = True
        for p in t.all_players():
            if p.age > 38:
                p.retiring_notice = True

# =========================
# TRANSFER MARKET (MINIMAL)
# =========================
def make_free_agent_pool(num=35):
    pool = []
    base_positions = ["GK","CB","LB","RB","CDM","CAM","CM","ST","LW","RW"]
    for _ in range(num):
        pos = random.choice(base_positions)
        nation = random.choice([n for arr in ORIGINS.values() for n in arr])
        name = random_name(nation)
        age = random.randint(16,38)
        rating = random.randint(70,86)
        pot = random.randint(77,95)
        years = random.randint(1,3)
        p = Player(name,pos,nation,age,rating, max(1, pot-rating), years)
        pool.append(p)
    if len(pool) > 35:
        young = sorted([p for p in pool if p.age<=25], key=lambda x:x.rating, reverse=True)[:20]
        old  = sorted([p for p in pool if 26<=p.age<=38], key=lambda x:x.rating, reverse=True)[:15]
        pool = young + old
    return pool

def ai_renewals(team):
    for p in team.all_players():
        if p.contract == 1:
            keep = (random.random() < 0.95) if p.rating > 79 else (random.random() < 0.80)
            if keep:
                years = random.choice([2,3])
                cost = int(p.value() * 0.10 * years)
                if team.pay(cost):
                    p.contract = years

def terminate_random_reserve(team):
    if not team.reserves:
        return None
    lowest = sorted(team.reserves, key=lambda x:x.rating)[:min(4,len(team.reserves))]
    victim = random.choice(lowest)
    team.reserves.remove(victim)
    return victim

def ai_transfers(team, free_agents, order_hint=1):
    n_transfers = random.randint(1,3)
    weak3 = team.weakest_positions()
    pick_positions = random.sample(weak3, k=min(2, len(weak3)))
    for _ in range(n_transfers):
        if not free_agents: break
        if not terminate_random_reserve(team): break
        val = max(1, team.budget // (n_transfers - 0 + 1))
        same_pos = [p for p in free_agents if est_cost_eur(p.age, p.rating) <= val and p.pos in pick_positions]
        candidates = same_pos if same_pos else [p for p in free_agents if est_cost_eur(p.age, p.rating) <= val]
        if not candidates: continue
        target = sorted(candidates, key=lambda x:x.rating, reverse=True)[:6]
        signing = random.choice(target)
        price = est_cost_eur(signing.age, signing.rating)
        if team.pay(price):
            free_agents.remove(signing)
            team.reserves.append(signing)

def user_lock_intransferibles(team):
    team.locked.clear()
    roster = team.all_players()
    if not roster: return
    print("\nLock up to 3 players as intransferable (by index, comma-separated). Enter to skip.")
    for i,p in enumerate(roster):
        print(f"{i+1:>2}. {p.pos:<3} {p.name:<22} {p.rating:>2} OVR  ({p.age}y)")
    s = input("Your picks: ").strip()
    if not s: return
    try:
        picks = [int(x)-1 for x in s.split(",") if x.strip().isdigit()]
        for i in picks[:3]:
            if 0<=i<len(roster): team.locked.add(roster[i].name)
    except:
        pass

def user_transfers(team, free_agents):
    print(f"\nYour budget: €{team.budget:,}")
    print("You can make up to 3 signings. You must free a reserve slot before each signing (contract termination = 4% of value).")
    made = 0
    while made < 3 and free_agents:
        ans = input("Make a signing? (y/n): ").strip().lower()
        if ans != "y": break
        if not team.reserves:
            print("You have no reserves to terminate.")
            break
        lowest = sorted(team.reserves, key=lambda x:x.rating)[:min(4,len(team.reserves))]
        print("Choose a reserve to terminate:")
        for i,p in enumerate(lowest):
            print(f"  {i+1}. {p.pos} {p.name} {p.rating} OVR  Value €{p.value():,}")
        k = prompt_int("Terminate which (1..{}): ".format(len(lowest)), 1, len(lowest)) - 1
        victim = lowest[k]
        fee = int(victim.value() * 0.04)  # per your last snippet
        if team.pay(fee):
            team.reserves.remove(victim)
            print(f"Terminated {victim.name} (fee €{fee:,}).")
        else:
            print("Insufficient funds."); continue

        affordable = [p for p in free_agents if p.value() <= team.budget and p.name not in team.locked]
        if not affordable:
            print("No affordable free agents right now."); break
        shortlisted = sorted(affordable, key=lambda x:x.rating, reverse=True)[:12]
        print("\nFree Agents (top affordable):")
        for i,p in enumerate(shortlisted):
            print(f"  {i+1:>2}. {p.pos:<3} {p.name:<22} {p.rating} OVR  {p.age}y  Value €{p.value():,}")
        k = prompt_int("Sign which (1..{}): ".format(len(shortlisted)), 1, len(shortlisted)) - 1
        signing = shortlisted[k]
        price = signing.value()
        if team.pay(price):
            free_agents.remove(signing)
            team.reserves.append(signing)
            made += 1
            print(f"Signed {signing.name} for €{price:,}. Remaining budget €{team.budget:,}")
        else:
            print("Insufficient funds.")

# =========================
# SEASON PROCESSING
# =========================
def standings_table(teams):
    return sorted(teams, key=lambda t: (t.points, t.gf - t.ga, t.gf), reverse=True)

def process_rewards_penalties(table):
    if len(table) >= 1: table[0].receive(50_000_000)
    if len(table) >= 2: table[1].receive(40_000_000)
    if len(table) >= 3: table[2].receive(20_000_000)
    for pos, t in enumerate(table, start=1):
        if pos <= t.objective:
            t.receive(15_000_000)
    for pos, t in enumerate(table, start=1):
        if pos == t.objective + 1:
            t.budget = int(t.budget * 0.85)
    eligible = [t for i,t in enumerate(table, start=1) if 3 <= i <= 5]
    if eligible:
        lucky = random.choice(eligible); lucky.receive(50_000_000)
        print(f"\nLucky Club: {lucky.name} receives €50,000,000")

def next_season_base_budget(t):
    return max(35_000_000, int(t.budget * 0.97))

def manager_switch_option(user, table):
    bottom3 = table[-3:]
    print("\nBottom 3 teams (eligible to switch):")
    for i,t in enumerate(bottom3):
        print(f"  {i+1}. {t.name}  (Pts {t.points})")
    if yesno("Do you want to switch to one of them? (y/n): "):
        k = prompt_int("Pick (1..{}): ".format(len(bottom3)), 1, len(bottom3)) - 1
        print(f"You now manage {bottom3[k].name}.")
        return bottom3[k]
    return user

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
    for i,t in enumerate(teams):
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

        # --- Start-of-season: lock up to 3 players (cleared last season) ---
        print("\nBefore the transfer window, lock your 3 intransferibles:")
        user_lock_intransferibles(user)

        # Top up youth (fill bench/reserve) at season start
        for t in teams:
            t.top_up_youth(is_user=(t is user))

        # Transfer window
        print(f"\n--- Transfer Window: {TM_OPEN.isoformat()} to {TM_CLOSE.isoformat()} ---")
        fa = make_free_agent_pool(35)

        # AI renewals
        for t in teams:
            if t is user: continue
            ai_renewals(t)

        # Transfer order: previous table order (if exists) else alphabetical
        transfer_order = (prev_table if prev_table else sorted(teams, key=lambda x:x.name))
        for t in transfer_order:
            if t is user: continue
            ai_transfers(t, fa)

        # User transfers
        user_transfers(user, fa)

        # Injuries for the season
        print("\nAssigning season injuries...")
        for t in teams:
            assign_season_injuries(t, SEASON_START, SEASON_END)
        print("Injuries assigned.\n")

        # Fixtures: each pair 5 times (home, away, 3x neutral)
        global _neutral_idx
        _neutral_idx = 0  # reset neutral stadium rotation each season
        fixtures = build_five_meetings(teams)
        scheduled = assign_dates(fixtures, SEASON_START, SEASON_END)

        # Simulate season
        print(f"--- Season {SEASON_START} to {SEASON_END} ---\n")
        for when, (A,B,venue) in scheduled:
            simulate_match(A, B, venue, when)

        # Final table
        table = standings_table(teams)
        print("\n=== FINAL TABLE ===")
        print("Pos Team                Pts   GF  GA  GD   AvgRoster  Budget(€)")
        for i,t in enumerate(table, start=1):
            print(f"{i:>2}. {t.name:<18} {t.points:>3}  {t.gf:>3} {t.ga:>3} {t.gf-t.ga:>3}   {t.avg_rating():>9}  €{t.budget:,}")

        # End-of-season processing (rewards/penalties/lucky)
        process_rewards_penalties(table)

        # Retirement notices
        season_end_retirements(teams)

        # Player progression & contract ticks
        for t in teams:
            for p in t.all_players():
                p.season_progression()

        # Expire contracts -> FA pool (kept implicit)
        expired = 0
        for t in teams:
            keep = []
            for p in t.all_players():
                if p.contract == 0:
                    expired += 1
                else:
                    keep.append(p)
            t.starters = [p for p in keep if p in t.starters]
            t.bench    = [p for p in keep if p in t.bench]
            t.reserves = [p for p in keep if p in t.reserves]
        if expired:
            print(f"\nContracts expired -> free agents this off-season: {expired}")

        # Next-season base budgets (apply and print)
        print("\n=== NEXT SEASON BASE BUDGETS (APPLIED) ===")
        for t in teams:
            base = next_season_base_budget(t)
            t.budget = base
            print(f"{t.name:<18} -> Base Budget: €{t.budget:,}")

        # Clear locks at end of season (you’ll be prompted again next season)
        for t in teams:
            t.locked.clear()

        # Manager switch option (to a bottom-3 side)
        user = manager_switch_option(user, table)

        prev_table = table[:]  # keep order for next transfer window
        year += 1

        if not yesno("\nRun another season? (y/n): "):
            print("Thanks for playing!")
            break

if __name__ == "__main__":
    main()
