import random
def next_season_base_budget(t):
    return max(30, int(t.budget * 0.97))

def process_rewards_penalties(table):
    if len(table) >= 1:
        table[0].receive(70)
    if len(table) >= 2:
        table[1].receive(40)
    if len(table) >= 3:
        table[2].receive(35)

    for pos, t in enumerate(table, start=1):
        if pos <= t.objective:
            t.receive(5)

    for pos, t in enumerate(table, start=1):
        if pos == t.objective + 1:
            t.budget = int(t.budget * 0.85)

    # Two random clubs from positions 3–10 get €25M each
    eligible = [t for i, t in enumerate(table, start=1) if 3 <= i <= 11]
    if len(eligible) >= 2:
        lucky_three = random.sample(eligible, 3)
        for lucky in lucky_three:
            lucky.receive(40)
            print(f"\nLucky Club: {lucky.name} receives €40M")

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
        lowest_rated = sorted(table, key=lambda team: team.avg_rating())[:5]
        if lowest_rated:
            beneficiary = random.choice(lowest_rated)
            beneficiary.receive(120)
            print(f"\nInternational Investment: {beneficiary.name} receives €120M")
