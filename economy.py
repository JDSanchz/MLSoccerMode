import random
def next_season_base_budget(t):
    return max(50, int(t.budget * 0.97))


def process_rewards_penalties(table):
    if not table:
        print("\n=== NEXT SEASON BUDGETS ===\n(no teams registered)")
        return

    events = []

    # Rewards for top 3
    if len(table) >= 1: table[0].receive(70)
    if len(table) >= 2: table[1].receive(60)
    if len(table) >= 3: table[2].receive(50)

    # Objective bonus
    for pos, t in enumerate(table, start=1):
        if pos <= getattr(t, "objective", 0):
            t.receive(10)

    # Track dynasty streaks (3+ consecutive top-3 finishes)
    dynasty_exists = False
    for pos, t in enumerate(table, start=1):
        streak = getattr(t, "top3_streak", 0)
        t.top3_streak = streak + 1 if pos <= 3 else 0
        if t.top3_streak >= 3:
            dynasty_exists = True

    # Randomly boost two teams outside the top 3 to avoid stagnation
    non_podium = [t for pos, t in enumerate(table, start=1) if pos > 3]
    if non_podium:
        bonus_recipients = random.sample(non_podium, k=min(2, len(non_podium)))
        for beneficiary in bonus_recipients:
            bonus = 75 if random.random() < 0.25 else 50
            beneficiary.receive(bonus)
            events.append(("Lottery Bonus", beneficiary.name, bonus))


    # If a dynasty exists, invest €120M in a random team from the 2 lowest-rated OUTSIDE top 3
    if dynasty_exists:
        non_top3 = [t for pos, t in enumerate(table, start=1) if pos > 3]
        lowest_eligible = sorted(non_top3, key=lambda team: team.avg_rating())[:2]
        if lowest_eligible:
            beneficiary = random.choice(lowest_eligible)
            beneficiary.receive(200)
            events.append(("International Investment", beneficiary.name, 200))

    sorted_table = sorted(table, key=lambda team: team.budget, reverse=True)
    name_width = max(len(team.name) for team in sorted_table)
    budget_strings = [f"€{team.budget:,}M" for team in sorted_table]
    budget_width = max(len("Budget"), max(len(display) for display in budget_strings))

    if events:
        print("\n=== FINANCIAL EVENTS ===")
        for label, name, amount in events:
            print(f"- {label:<24} {name:<{name_width}} +€{amount:,}M")

    print("\n=== NEXT SEASON BASE BUDGETS (APPLIED) ===")
    print(f"{'Team'.ljust(name_width)}  {'Budget'.rjust(budget_width)}")
    print(f"{'-' * name_width}  {'-' * budget_width}")
    for team, budget_display in zip(sorted_table, budget_strings):
        print(f"{team.name.ljust(name_width)}  {budget_display.rjust(budget_width)}")
