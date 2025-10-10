from prompts import prompt_int

def print_header(title: str):
    line = "=" * 46
    print(f"\n{line}\n{title}\n{line}")

def print_subtitle(title: str):
    print(f"\n--- {title} ---")

def run_menu(title: str, options: list[tuple[str, callable]]):
    while True:
        print_header(title)
        for i, (label, _) in enumerate(options, 1):
            print(f"  {i}) {label}")
        choice = prompt_int("Choice: ", 1, len(options))
        action = options[choice - 1][1]
        res = action()
        if res == "back":
            return

def show_player_list(label, players):
    print(f"\n{label}:")
    if not players:
        print("  (none)")
        return
    for i, p in enumerate(players, 1):
        flag = p.flag() if hasattr(p, "flag") else f"({p.nation})"
        pot_display = f"| Pot {getattr(p, 'potential_range', ''):<7}" \
                      if getattr(p, "display_potential_range", False) else " " * 13
        print(
            f"  {i:>2}. "
            f"{p.pos:<3} "
            f"{p.rating:>2} OVR  "
            f"{p.name:<28} "
            f"{p.age:>2}y  "
            f"{pot_display}  "
            f"Value €{p.value():,}  {flag}"
        )
