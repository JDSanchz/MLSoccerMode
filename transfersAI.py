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

def champion_poach_user(prev_table, user, top_chance=0.33, bottom_chance=0.20, premium_rate=0.18):
    """
    1) 33% chance: one of the top-3 NON-user teams poaches a random player from user's top-3 by rating.
    2) Then roll again: 20% chance one of the bottom-2 NON-user teams poaches a random user reserve
       (picked from up to 5 reserves rated 75-80).
    Buyer pays (cost + premium_rate), can go negative; user receives the money.
    """
    if not prev_table or not user.all_players():
        return

    def remove_from_user_and_add_to_buyer(target, buyer, premium_rate):
        base_price = est_cost_eur(target.age, target.rating)
        premium = max(1, int(round(base_price * premium_rate)))
        total = base_price + premium

        buyer.budget -= total          # allow negatives
        user.receive(total)

        if target in user.starters:
            user.starters.remove(target)
        elif target in user.bench:
            user.bench.remove(target)
        elif target in user.reserves:
            user.reserves.remove(target)

        buyer.reserves.append(target)

        flag = target.flag() if hasattr(target, "flag") else f"({target.nation})"
        neg = " (budget now negative)" if buyer.budget < 0 else ""
        print(f"\nPOACH! {buyer.name} signed {target.name} {flag} "
              f"for €{base_price:,} + {int(premium_rate*100)}% (€{premium:,}) = €{total:,}.")
        print(f"{user.name} receives €{total:,}. {buyer.name} budget: €{buyer.budget:,}{neg}")

    # ----- Roll 1: Top-3 teams (not user) poach from user's top-3 by rating -----
    if random.random() < top_chance:
        top_three = [t for t in prev_table[:3] if t is not user]
        if top_three:
            buyer = random.choice(top_three)
            top3_players = sorted(user.all_players(), key=lambda p: p.rating, reverse=True)[:3]
            if top3_players:
                target = random.choice(top3_players)
                remove_from_user_and_add_to_buyer(target, buyer, premium_rate)

    # ----- Roll 2: Bottom-2 teams (not user) poach from user reserves (75-80 OVR) -----
    if random.random() < bottom_chance:
        bottom_two = [t for t in prev_table[-2:] if t is not user]
        if bottom_two:
            buyer = random.choice(bottom_two)
            pool = [p for p in user.reserves if 75 <= p.rating <= 80]
            if pool:
                # Limit the candidate set to 5 if more are available, then pick one
                candidates = random.sample(pool, k=min(5, len(pool)))
                target = random.choice(candidates)
                remove_from_user_and_add_to_buyer(target, buyer, premium_rate)