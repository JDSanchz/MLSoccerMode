def prompt_int(msg, lo, hi):
    while True:
        try:
            v = int(input(msg))
            if lo <= v <= hi:
                return v
        except Exception:
            pass
        print(f"Enter a number between {lo} and {hi}.")