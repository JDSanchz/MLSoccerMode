import random
def season_end_retirements(teams):
    for t in teams:
        for p in t.all_players():
            # Mandatory retirement at age 39+
            if p.age >= 39:
                p.retiring_notice = True
            # 50% chance to retire if age > 33
            elif p.age > 33 and random.random() < 0.5:
                p.retiring_notice = True
