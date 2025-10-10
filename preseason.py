import random
from prompts import prompt_int
from ui import print_subtitle, run_menu, show_player_list
from utils import yesno

def end_contracts_flow(team):
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
                # caller can reorganize after returning, or import locally:
                # from organizeSquad import organize_squad; organize_squad(team)
            else:
                print("Insufficient funds to pay release fee.")

def action_view_squad(user, organize_squad):
    def _inner():
        print_subtitle("See Squad / End Contracts")
        organize_squad(user)
        end_contracts_flow(user)
        return "again"
    return _inner

def action_transfer_hub(user, teams, TM_OPEN, TM_CLOSE,
                        make_free_agent_pool, champion_poach_user,
                        ai_transfers, user_transfers, organize_squad, trim_ai_reserves,
                        prev_table=None):
    def _inner():
        print_subtitle(f"Transfer Window: {TM_OPEN.isoformat()} → {TM_CLOSE.isoformat()}")
        fa = make_free_agent_pool(30)
        champion_poach_user(prev_table, user)
        order = teams[:]
        random.shuffle(order)

        user_transfers(user, fa)

        for t in order:
            if t is user:
                organize_squad(t)
                continue
            ai_transfers(t, fa)
            organize_squad(t)
            trim_ai_reserves(t)
        return "back"
    return _inner

def action_continue(user, teams, champion_poach_user, organize_squad, prev_table=None):
    def _inner():
        champion_poach_user(prev_table, user, top_chance=0.20, bottom_chance=0, premium_rate=0.25)
        for t in teams:
            organize_squad(t)
        return "back"
    return _inner

def preseason_loop(user, teams, TM_OPEN, TM_CLOSE,
                   make_free_agent_pool, champion_poach_user,
                   ai_transfers, user_transfers, organize_squad, trim_ai_reserves,
                   prev_table=None):
    options = [
        ("See Squad / End Contracts", action_view_squad(user, organize_squad)),
        ("Transfer Hub", action_transfer_hub(
            user, teams, TM_OPEN, TM_CLOSE,
            make_free_agent_pool, champion_poach_user,
            ai_transfers, user_transfers, organize_squad, trim_ai_reserves,
            prev_table
        )),
        ("Continue to next season", action_continue(user, teams, champion_poach_user, organize_squad, prev_table)),
    ]
    run_menu("Preseason Menu", options)
