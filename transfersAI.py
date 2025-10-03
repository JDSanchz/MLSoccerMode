import random
from playerCost import est_cost_eur
def terminate_random_reserve(team):
    if not team.reserves:
        return None
    lowest = sorted(team.reserves, key=lambda x: x.rating)[: min(4, len(team.reserves))]
    victim = random.choice(lowest)
    team.reserves.remove(victim)
    return victim


def ai_transfers(team, free_agents, order_hint=1):
    n_transfers = random.randint(1, 3)
    weak3 = team.weakest_positions()
    pick_positions = random.sample(weak3, k=min(2, len(weak3)))
    for _ in range(n_transfers):
        if not free_agents:
            break
        if not terminate_random_reserve(team):
            break
        val = max(1, team.budget // (n_transfers - 0 + 1))
        same_pos = [p for p in free_agents if est_cost_eur(p.age, p.rating) <= val and p.pos in pick_positions]
        candidates = same_pos if same_pos else [p for p in free_agents if est_cost_eur(p.age, p.rating) <= val]
        if not candidates:
            continue
        target = sorted(candidates, key=lambda x: x.rating, reverse=True)[:6]
        signing = random.choice(target)
        price = est_cost_eur(signing.age, signing.rating)
        if team.pay(price):
            free_agents.remove(signing)
            team.reserves.append(signing)