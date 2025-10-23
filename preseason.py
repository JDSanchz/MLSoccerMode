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
        fee = 1  # flat €1M release payout

        print(f"\n{victim.name} — estimated value {_fmt_currency(value)}.")
        print(f"Release payout: {_fmt_currency(fee)}.")
        print(f"Club budget before release: {_fmt_currency(team.budget)}.")
        if yesno("Confirm release? (y/n): "):
            if team.pay(fee):
                pool.pop(idx)
                if hasattr(team, "unprotect_player"):
                    team.unprotect_player(victim)
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

def action_manage_no_poach(user, organize_squad):
    def _inner():
        print_subtitle("Protected From Poaching")
        organize_squad(user)
        if hasattr(user, "cleanup_poach_protected"):
            user.cleanup_poach_protected()

        while True:
            roster = []
            for group_name, group in [("Starters", user.starters), ("Bench", user.bench), ("Reserves", user.reserves)]:
                for player in group:
                    roster.append((group_name, player))

            if not roster:
                print("\nYou currently have no players to protect.")
                break

            protected = getattr(user, "poach_protected", [])
            print(f"\nProtection slots used: {len(protected)}/3")
            if protected:
                print("Currently protected:")
                for p in protected:
                    flag = p.flag() if hasattr(p, "flag") else f"({p.nation})"
                    print(f"  - {p.name} {flag} {p.pos} {p.rating} OVR")
            else:
                print("No players are protected right now.")

            print("\nToggle protection for a player (0 to finish):")
            for idx, (group_name, player) in enumerate(roster, 1):
                flag = player.flag() if hasattr(player, "flag") else f"({player.nation})"
                marker = "*" if player in protected else " "
                print(
                    f"  {idx:>2}. [{marker}] {group_name:<8} {player.pos:<3} "
                    f"{player.name:<25} {flag}  {player.rating:>2} OVR  {player.age:>2}y"
                )

            choice = prompt_int(f"Select (0..{len(roster)}): ", 0, len(roster))
            if choice == 0:
                break

            _, picked = roster[choice - 1]
            protected = getattr(user, "poach_protected", [])
            if picked in protected:
                if hasattr(user, "unprotect_player"):
                    user.unprotect_player(picked)
                print(f"Removed protection from {picked.name}.")
            else:
                if len(protected) >= 3:
                    print("You already protect 3 players. Remove someone before adding another.")
                else:
                    if hasattr(user, "protect_player"):
                        user.protect_player(picked)
                    print(f"{picked.name} is now protected from poaching.")
        protected = getattr(user, "poach_protected", [])
        if protected:
            names = ", ".join(p.name for p in protected)
            print(f"\nFinal protected list: {names}.")
        else:
            print("\nNo players are currently protected.")
        return "again"
    return _inner

def action_transfer_hub(user, teams, TM_OPEN, TM_CLOSE,
                        make_free_agent_pool, champion_poach_user, user_poach_players,
                        ai_transfers, user_transfers, organize_squad, trim_ai_reserves,
                        prev_table=None):
    def _inner():
        print_subtitle(f"Transfer Window: {TM_OPEN.isoformat()} → {TM_CLOSE.isoformat()}")
        fa = make_free_agent_pool()
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
        ("Set No-Poach Clauses", action_manage_no_poach(user, organize_squad)),
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
