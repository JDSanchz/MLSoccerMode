import random
def next_season_base_budget(t):
    return max(50, int(t.budget * 0.97))


def process_rewards_penalties(table):
    # Rewards for top 3
    if len(table) >= 1: table[0].receive(70)
    if len(table) >= 2: table[1].receive(60)
    if len(table) >= 3: table[2].receive(50)

    # Objective bonus
    for pos, t in enumerate(table, start=1):
        if pos <= getattr(t, "objective", 0):
            t.receive(5)

    # Just-missed penalty
    for pos, t in enumerate(table, start=1):
        if pos == getattr(t, "objective", 0) + 1:
            t.budget = int(t.budget * 0.85)

    # Track dynasty streaks (3+ consecutive top-3 finishes)
    dynasty_exists = False
    for pos, t in enumerate(table, start=1):
        streak = getattr(t, "top3_streak", 0)
        t.top3_streak = streak + 1 if pos <= 3 else 0
        if t.top3_streak >= 3:
            dynasty_exists = True

    # If a dynasty exists, invest €120M in a random team from the 5 lowest-rated OUTSIDE top 3
    if dynasty_exists:
        non_top3 = [t for pos, t in enumerate(table, start=1) if pos > 3]
        lowest_eligible = sorted(non_top3, key=lambda team: team.avg_rating())[:5]
        if lowest_eligible:
            beneficiary = random.choice(lowest_eligible)
            beneficiary.receive(150)
            print(f"\nInternational Investment: {beneficiary.name} receives €150M")

