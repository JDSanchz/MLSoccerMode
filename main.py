import random
from datetime import timedelta
from randomName import random_name
from constants import *
from retirement import season_end_retirements
from transfersAI import ai_transfers, champion_poach_user, trim_ai_reserves
from matchEngineSchedules import *
from prompts import prompt_int
from economy import process_rewards_penalties, next_season_base_budget
from transfersPlayer import user_transfers
from organizeSquad import organize_squad
from models.player import Player
from models.team import Team
from utils import *

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
