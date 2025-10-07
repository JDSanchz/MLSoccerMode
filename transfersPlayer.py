from constants import RESERVES
from prompts import prompt_int

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
