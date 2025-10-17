from constants import RESERVES
from prompts import prompt_int
import random
from organizeSquad import organize_squad
from utils import yesno

def trim_user_reserves(team, severance_rate=0.0):
    """Ensure user reserves ≤ RESERVES. Let user choose who to release.
       Optionally charge severance (0.0 means no fee)."""
    while len(team.reserves) > RESERVES:
        print(f"\nYou have {len(team.reserves)} reserves. Pick one to release to reach {RESERVES}.")
        # Show reserves, lowest value first (easiest cuts first)
        sorted_res = sorted(team.reserves, key=lambda p: p.value())
        for i, p in enumerate(sorted_res, 1):
            flag = p.flag() if hasattr(p, "flag") else f"({p.nation})"
            print(f"  {i:>2}. {p.pos:<3} {p.name:<28} {flag} {p.rating} OVR  {p.age}y  Value €{p.value():,}")

        idx = prompt_int(f"Release which (1..{len(sorted_res)}): ", 1, len(sorted_res)) - 1
        victim = sorted_res[idx]
        if severance_rate > 0:
            fee = max(1, int(round(victim.value() * severance_rate)))
            team.budget -= fee
            print(f"Paid severance €{fee:,}. New budget €{team.budget:,}")
        team.reserves.remove(victim)
        print(f"Released {victim.name}. Reserves now {len(team.reserves)}/{RESERVES}.")

def user_poach_players(user, teams, premium_rate=0.15):
    """Allow the user to poach players from other teams using the same premium rate."""
    def opponent_teams():
        return [t for t in teams if t is not user and t.all_players()]

    def gather_affordable_targets():
        affordable = []
        for club in opponent_teams():
            entries = []
            buckets = [
                ("Starters", club.starters),
                ("Bench", club.bench),
                ("Reserves", club.reserves),
            ]
            for bucket_name, bucket in buckets:
                for player in bucket:
                    base = player.value()
                    premium = max(1, int(round(base * premium_rate)))
                    total = base + premium
                    if total <= user.budget:
                        entries.append((bucket_name, bucket, player, base, premium, total))
            if entries:
                affordable.append((club, entries))
        return affordable

    if not opponent_teams():
        print("\nNo opponent clubs currently have players available to poach.")
        return

    while True:
        if user.budget <= 0:
            print("\nYou have no budget remaining to fund a poach.")
            break

        if not yesno("\nAttempt to poach a player from another club? (y/n): "):
            break

        affordable_targets = gather_affordable_targets()
        if not affordable_targets:
            print("\nNo clubs have players you can currently afford to poach right now.")
            break

        print(f"\nClubs with affordable poach targets (your budget €{user.budget:,}):")
        for idx, (club, entries) in enumerate(affordable_targets, 1):
            print(
                f"  {idx:>2}. {club.name:<20} Avg {club.avg_rating():>4.1f}  "
                f"Budget €{club.budget:,}  Affordable players: {len(entries)}"
            )

        club_idx = prompt_int(f"Pick a club (1..{len(affordable_targets)}): ", 1, len(affordable_targets)) - 1
        target, roster_entries = affordable_targets[club_idx]

        print("\nBudget filter active: listing only players you can afford right now.")
        print(
            f"\nAffordable players from {target.name} "
            f"(cost includes {int(premium_rate * 100)}% poach premium):"
        )
        for idx, (bucket_name, _, player, base, premium, total) in enumerate(roster_entries, 1):
            flag = player.flag() if hasattr(player, "flag") else f"({player.nation})"
            print(
                f"  {idx:>2}. {bucket_name:<8} {player.pos:<3} "
                f"{player.rating:>2} OVR  {player.age:>2}y  {player.name:<28} {flag}  "
                f"€{total:,} (Base €{base:,} + Premium €{premium:,})"
            )

        pick_idx = prompt_int(f"Poach which player (1..{len(roster_entries)}): ", 1, len(roster_entries)) - 1
        bucket_name, bucket, player, base, premium, total = roster_entries[pick_idx]

        if total > user.budget:
            print(
                f"Insufficient funds for {player.name}: costs €{total:,} "
                f"but you have €{user.budget:,}."
            )
            continue

        print(
            f"\n{player.name} will cost €{base:,} + {int(premium_rate * 100)}% premium "
            f"(€{premium:,}) = €{total:,}."
        )
        if not yesno("Confirm this poach? (y/n): "):
            continue

        if not user.pay(total):
            print("Transaction failed due to insufficient funds.")
            continue

        target.receive(total)
        if player in bucket:
            bucket.remove(player)
        else:
            for group in (target.starters, target.bench, target.reserves):
                if player in group:
                    group.remove(player)
                    break

        user.reserves.append(player)
        organize_squad(user)
        organize_squad(target)
        trim_user_reserves(user)

        flag = player.flag() if hasattr(player, "flag") else f"({player.nation})"
        print(
            f"\nPOACH COMPLETE: {user.name} signed {player.name} {flag} from {target.name} "
            f"for €{total:,}."
        )
        print(f"{user.name} budget: €{user.budget:,}. {target.name} budget: €{target.budget:,}.")

        if not yesno("Poach another player? (y/n): "):
            break

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
