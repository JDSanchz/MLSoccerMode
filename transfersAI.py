import random
from playerCost import est_cost_eur

def terminate_random_reserve(team):
    """Randomly remove one of the lowest-rated reserve players from a team."""
    if not team.reserves:
        return None  # No reserves available to release

    # Sort reserves by rating (ascending) and pick up to the 4 lowest-rated
    lowest = sorted(team.reserves, key=lambda x: x.rating)[:min(4, len(team.reserves))]

    # Randomly choose one of these weaker players to terminate their contract
    victim = random.choice(lowest)

    # Remove the chosen player from the reserves list
    team.reserves.remove(victim)

    # Return the released player (useful for debugging or logging)
    return victim


def ai_transfers(team, free_agents, order_hint=1):
    """Handle AI-controlled team transfers automatically during transfer windows."""
    # Skip entire window if budget is below €5M at this point
    if team.budget < 5:
        print(f"{team.name} skips transfers (budget €{team.budget:,}M < €5M).")
        return

    n_transfers = random.randint(1, 3)
    weak3 = team.weakest_positions()
    pick_positions = random.sample(weak3, k=min(2, len(weak3)))

    for i in range(n_transfers):
        # If budget dropped under €5M during the window, stop signing more
        if team.budget < 5:
            print(f"{team.name} stops transfers (budget €{team.budget:,}M < €5M).")
            break

        if not free_agents:
            break

        if not terminate_random_reserve(team):
            break

        # Spend roughly a fraction of remaining budget for this signing
        remaining = n_transfers - i
        val = max(1, team.budget // remaining)

        same_pos = [p for p in free_agents
                    if est_cost_eur(p.age, p.rating) <= val and p.pos in pick_positions]

        candidates = same_pos if same_pos else [
            p for p in free_agents if est_cost_eur(p.age, p.rating) <= val
        ]
        if not candidates:
            continue

        target = sorted(candidates, key=lambda x: x.rating, reverse=True)[:6]
        signing = random.choice(target)
        price = est_cost_eur(signing.age, signing.rating)

        if team.pay(price):
            free_agents.remove(signing)
            team.reserves.append(signing)  # New players go directly to reserves

def champion_poach_user(prev_table, user, chance=0.33):
    """33% chance last season's #1 buys a random player from user's top-3 by rating.
       Champion pays (cost + 18%) to user; champion budget may go negative.
    """
    if not prev_table or not user.all_players():
        return

    if random.random() >= chance:
        return

    champion = prev_table[0]
    if champion is user:
        return

    # Pick random from user's top-3 by rating
    top3 = sorted(user.all_players(), key=lambda p: p.rating, reverse=True)[:3]
    if not top3:
        return
    target = random.choice(top3)

    base_price = est_cost_eur(target.age, target.rating)
    premium = max(1, int(round(base_price * 0.18)))
    total = base_price + premium

    # ALWAYS charge champion (allow negative), ALWAYS credit user
    champion.budget -= total          # <-- can go negative
    user.receive(total)

    # Remove target from user's lists
    if target in user.starters:
        user.starters.remove(target)
    elif target in user.bench:
        user.bench.remove(target)
    elif target in user.reserves:
        user.reserves.remove(target)

    # Move to champion reserves
    champion.reserves.append(target)

    flag = target.flag() if hasattr(target, "flag") else f"({target.nation})"
    went_negative = " (budget now negative)" if champion.budget < 0 else ""
    print(f"\nPOACH! {champion.name} signed {target.name} {flag} "
          f"for €{base_price:,} + 18% (€{premium:,}) = €{total:,}.")
    print(f"{user.name} receives €{total:,}. {champion.name} budget: €{champion.budget:,}{went_negative}")

