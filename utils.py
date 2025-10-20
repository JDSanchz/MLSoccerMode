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

def manager_switch_option(user, table, forced=False, firing_message=None):
    # Bottom 2 in the final table
    bottom2 = table[-2:]

    def is_user_team(t):
        return (t is user) or getattr(t, "is_user", False)

    # Only show teams that are NOT user-managed
    options = [t for t in bottom2 if not is_user_team(t)]

    print("\n" + "=" * 55)
    title = " ⚙️  MANDATORY REASSIGNMENT " if forced else " ⚙️  MANAGER SWITCH OPTION "
    print(title.center(55, " "))
    print("=" * 55)

    if forced and firing_message:
        print(f"{firing_message}\n")

    if not options:
        print("No eligible bottom-2 teams available for switching.")
        print("You will remain with your current club.")
        print("=" * 55)
        return user

    print("📉  Bottom 2 teams this season:")
    print("-" * 55)
    for i, t in enumerate(options, 1):
        print(f"  {i}. {t.name:<20} | Points: {t.points:>3} | GD: {t.gf - t.ga:+d}")
    print("-" * 55)

    if forced:
        print("You must accept a role at one of these clubs.")
        k = prompt_int(f"Pick (1–{len(options)}): ", 1, len(options)) - 1
        choice = options[k]
        print("\n" + "-" * 55)
        print(f"🆕  You are now managing: {choice.name}")
        print("-" * 55)
        return choice

    if yesno("Would you like to switch to one of these clubs? (y/n): "):
        k = prompt_int(f"Pick (1–{len(options)}): ", 1, len(options)) - 1
        choice = options[k]

        print("\n" + "-" * 55)
        print(f"🎯  You are now managing: {choice.name}")
        print("-" * 55)
        return choice

    print("🔒  You decided to stay with your current team.")
    print("=" * 55)
    return user
