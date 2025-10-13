import random
from constants import *
from retirement import season_end_retirements
from matchEngineSchedules import *
from prompts import prompt_int
from economy import process_rewards_penalties, next_season_base_budget
from organizeSquad import organize_squad
from models.team import Team
from utils import *
from injuries import recover_injuries, assign_season_injuries
from preseason import preseason_loop
from transfersAI import *
from transfersPlayer import *
from survey import *

def standings_table(teams):
    return sorted(teams, key=lambda t: (t.points, t.gf - t.ga, t.gf), reverse=True)
def apply_retirements(teams):
    print("\nApplying retirements")
    for t in teams:
        keep_starters, keep_bench, keep_res = [], [], []
        for lst, keep in [(t.starters, keep_starters), (t.bench, keep_bench), (t.reserves, keep_res)]:
            for p in lst:
                must_retire = (p.age >= 39) or p.retiring_notice 
                if not must_retire:
                    keep.append(p)
        t.starters, t.bench, t.reserves = keep_starters, keep_bench, keep_res

# =========================
# MAIN FLOW (CONTINUOUS SEASONS)
# =========================
def main():
    random.seed(42)
    teams = [Team(m) for m in TEAMS_INIT]
    for t in teams:
        t.generate_initial_squad()

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

        for t in teams:
            t.reset_season_stats()
            t.top_up_youth(is_user=(t is user))

        preseason_loop(user, teams, TM_OPEN, TM_CLOSE,
                       make_free_agent_pool, champion_poach_user,
                       ai_transfers, user_transfers, organize_squad, trim_ai_reserves,
                       prev_table)

        apply_retirements(teams)

        print("\nAssigning season injuries...")
        for t in teams:
            assign_season_injuries(t, SEASON_START, SEASON_END, is_user=(t is user))
        print("Injuries assigned.\n")

        fixtures = build_home_and_away(teams)
        scheduled = assign_dates(fixtures, SEASON_START, SEASON_END)

        print(f"--- Season {SEASON_START} to {SEASON_END} ---\n")
        for when, (A, B, venue) in scheduled:
            recover_injuries(A, when, is_user=(A is user))
            recover_injuries(B, when, is_user=(B is user))
            organize_squad(A)
            organize_squad(B)
            simulate_match(A, B, venue, when)

        table = standings_table(teams)
        print("\n=== FINAL TABLE ===")
        print("Pos Team                Pts   GF  GA  GD   AvgRoster  Budget(€)")
        for i, t in enumerate(table, start=1):
            print(f"{i:>2}. {t.name:<18} {t.points:>3}  {t.gf:>3} {t.ga:>3} {t.gf-t.ga:>3}   {t.avg_rating():>9}  €{t.budget:,}")

        process_rewards_penalties(table)
        season_end_retirements(teams)

        for t in teams:
            for p in t.all_players():
                p.season_progression()

        print("\n=== NEXT SEASON BASE BUDGETS (APPLIED) ===")
        for t in teams:
            base = next_season_base_budget(t)
            t.budget = base
            print(f"{t.name:<18} -> Base Budget: €{t.budget:,}")

        user = manager_switch_option(user, table)
        prev_table = table[:]
        year += 1

        cont = yesno("\nRun another season? (y/n): ")

        # ✳️ Ask for 3 price labels after every season, even if user decides to stop
        collect_price_labels(user, n=3, csv_path="price_labels.csv", year=year)

        if not cont:
            print("Thanks for playing!")
            break

if __name__ == "__main__":
    main()