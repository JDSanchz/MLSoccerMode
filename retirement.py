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

            # If marked to retire, add "RET " at the beginning of their name (only once)
            if p.retiring_notice and not p.name.startswith("RET "):
                p.name = "RET " + p.name
