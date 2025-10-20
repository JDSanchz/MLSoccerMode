import random
def next_season_base_budget(t):
    return max(30, int(t.budget * 0.97))

def process_rewards_penalties(table):
    if len(table) >= 1:
        table[0].receive(50)
    if len(table) >= 2:
        table[1].receive(40)
    if len(table) >= 3:
        table[2].receive(20)

    for pos, t in enumerate(table, start=1):
        if pos <= t.objective:
            t.receive(5)

    for pos, t in enumerate(table, start=1):
        if pos == t.objective + 1:
            t.budget = int(t.budget * 0.85)

    # Two random clubs from positions 3–10 get €25M each
    eligible = [t for i, t in enumerate(table, start=1) if 3 <= i <= 10]
    if len(eligible) >= 2:
        lucky_two = random.sample(eligible, 2)
        for lucky in lucky_two:
            lucky.receive(25)
            print(f"\nLucky Club: {lucky.name} receives €25M")

    dynasty_candidates = []
    for pos, t in enumerate(table, start=1):
        streak = getattr(t, "top3_streak", 0)
        if pos <= 3:
            streak += 1
        else:
            streak = 0
        t.top3_streak = streak
        if streak >= 3:
            dynasty_candidates.append(t)

    if dynasty_candidates:
        parity_pool = [
            team for i, team in enumerate(table, start=1)
            if i >= 2 and getattr(team, "top3_streak", 0) < 3
        ]
        if parity_pool:
            beneficiary = random.choice(parity_pool)
            beneficiary.receive(150)
            print(f"\nParity Boost: {beneficiary.name} receives €150M")
