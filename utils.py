from datetime import date
from prompts import prompt_int

def season_dates(year: int):
    tm_open = date(year, 6, 16)
    tm_close = date(year, 8, 13)
    processing = date(year, 8, 14)
    season_start = date(year, 8, 15)
    season_end = date(year + 1, 6, 15)
    return tm_open, tm_close, processing, season_start, season_end

def yesno(msg: str) -> bool:
    return input(msg).strip().lower().startswith("y")

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def manager_switch_option(user, table):
    bottom3 = table[-3:]
    print("\nBottom 3 teams (eligible to switch):")
    for i, t in enumerate(bottom3):
        print(f"  {i+1}. {t.name}  (Pts {t.points})")
    if yesno("Do you want to switch to one of them? (y/n): "):
        k = prompt_int("Pick (1..{}): ".format(len(bottom3)), 1, len(bottom3)) - 1
        print(f"You now manage {bottom3[k].name}.")
        return bottom3[k]
    return user