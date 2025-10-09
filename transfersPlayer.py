from constants import RESERVES
from prompts import prompt_int
import random
from organizeSquad import organize_squad

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

