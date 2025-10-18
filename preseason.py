import random
from prompts import prompt_int
from ui import print_subtitle, run_menu, show_player_list
from utils import yesno
from constants import FORMATIONS


def _fmt_currency(amount):
    if amount >= 1_000_000:
        amount_m = amount / 1_000_000
        if amount_m.is_integer():
            return f"€{int(amount_m):,}M"
        return f"€{amount_m:,.1f}M"
    return f"€{amount:,}M"

def end_contracts_flow(team):
    while True:
        show_player_list("Starters", team.starters)
        show_player_list("Bench", team.bench)
        show_player_list("Reserves", team.reserves)

        if not yesno("\nRelease someone? (y/n): "):
            break

        print("\nChoose a group to release from:")
        print("  1) Starters")
        print("  2) Bench")
        print("  3) Reserves")
        lst_choice = prompt_int("Group (1-3): ", 1, 3)

        pools = {1: ("Starters", team.starters), 2: ("Bench", team.bench), 3: ("Reserves", team.reserves)}
        pool_name, pool = pools[lst_choice]
        if not pool:
            print(f"{pool_name} currently has no players.")
            continue

        show_player_list(f"{pool_name} (selected)", pool)
        idx = prompt_int(f"Release which player (1..{len(pool)}): ", 1, len(pool)) - 1
        victim = pool[idx]
        value = victim.value()
        fee = min(10, max(1, int(round(value * 0.12))))
        capped = fee == 10

        print(f"\n{victim.name} — estimated value {_fmt_currency(value)}.")
        clause_note = " (cap reached)" if capped else ""
        print(f"Release payout (12% capped at €10M): {_fmt_currency(fee)}{clause_note}.")
        print(f"Club budget before release: {_fmt_currency(team.budget)}.")
        if yesno("Confirm release? (y/n): "):
            if team.pay(fee):
                pool.pop(idx)
                print(f"Released {victim.name}. New budget {_fmt_currency(team.budget)}.")
                # caller can reorganize after returning, or import locally:
                # from organizeSquad import organize_squad; organize_squad(team)
            else:
                print("Not enough funds to cover the release payout.")

def action_view_squad(user, organize_squad):
    def _inner():
        print_subtitle("See Squad / End Contracts")
        organize_squad(user)
        end_contracts_flow(user)
        return "again"
    return _inner

def action_change_formation(user, organize_squad):
    def _inner():
        print_subtitle("Change Team Formation")
        formations = list(FORMATIONS.keys())
        print(f"Current formation: {user.formation}")
        for i, formation in enumerate(formations, 1):
            marker = " (current)" if formation == user.formation else ""
            print(f"  {i}) {formation}{marker}")
        choice = prompt_int(f"Pick a formation (1-{len(formations)}): ", 1, len(formations)) - 1
        selected = formations[choice]
        if selected == user.formation:
            print(f"{user.name} already lines up in a {selected}. No changes made.")
        else:
            user.formation = selected
            organize_squad(user)
            print(f"{user.name} will now play a {selected}. Squad reorganized to match the new shape.")
        return "again"
    return _inner

def action_transfer_hub(user, teams, TM_OPEN, TM_CLOSE,
                        make_free_agent_pool, champion_poach_user, user_poach_players,
                        ai_transfers, user_transfers, organize_squad, trim_ai_reserves,
                        prev_table=None):
    def _inner():
        print_subtitle(f"Transfer Window: {TM_OPEN.isoformat()} → {TM_CLOSE.isoformat()}")
        fa = make_free_agent_pool(30)
        poach_premium_rate = 0.15
        champion_poach_user(prev_table, user, premium_rate=poach_premium_rate)
        user_poach_players(user, teams, premium_rate=poach_premium_rate)
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
        champion_poach_user(prev_table, user, top_chance=0.20, bottom_chance=0.20, premium_rate=0.20)
        for t in teams:
            organize_squad(t)
        return "back"
    return _inner

def preseason_loop(user, teams, TM_OPEN, TM_CLOSE,
                   make_free_agent_pool, champion_poach_user, user_poach_players,
                   ai_transfers, user_transfers, organize_squad, trim_ai_reserves,
                   prev_table=None):
    options = [
        ("See Squad / End Contracts", action_view_squad(user, organize_squad)),
        ("Change Team Formation", action_change_formation(user, organize_squad)),
        ("Transfer Hub", action_transfer_hub(
            user, teams, TM_OPEN, TM_CLOSE,
            make_free_agent_pool, champion_poach_user, user_poach_players,
            ai_transfers, user_transfers, organize_squad, trim_ai_reserves,
            prev_table
        )),
        ("Continue to next season", action_continue(user, teams, champion_poach_user, organize_squad, prev_table)),
    ]
    run_menu("Preseason Menu", options)
