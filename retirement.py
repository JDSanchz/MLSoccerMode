import random

def season_end_retirements(teams):
    for t in teams:
        for p in t.all_players():
            if p.age >= 39 or (p.age > 34 and random.random() < 0.5):
                p.retiring_notice = True
                if not p.name.startswith("RET "):
                    p.name = "RET " + p.name

