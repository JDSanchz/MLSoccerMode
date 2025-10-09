from constants import FORMATIONS, BENCH, STARTERS

def organize_squad(team, on=None):
    def available(p):
        return p.injured_until is None if on is None else (p.injured_until is None or on > p.injured_until)

    xi_positions = []
    for pos, c in FORMATIONS[team.formation].items():
        xi_positions += [pos] * c

    injured = [p for p in team.all_players() if not available(p)]
    pool = [p for p in team.all_players() if available(p)]
    pool.sort(key=lambda p: p.rating, reverse=True)

    def take_best_pos(position):
        for i, p in enumerate(pool):
            if p.pos == position:
                return pool.pop(i)
        return None

    def take_best_any():
        return pool.pop(0) if pool else None

    starters = []
    for pos in xi_positions:
        pick = take_best_pos(pos) or take_best_any()
        if pick:
            starters.append(pick)

    bench = []
    gk = take_best_pos("GK")
    if gk: bench.append(gk)
    cb = take_best_pos("CB")
    if cb: bench.append(cb)
    while len(bench) < BENCH and pool:
        bench.append(take_best_any())

    reserves = pool + injured  # injured always end up here

    team.starters = starters[:STARTERS]
    team.bench = bench[:BENCH]
    team.reserves = reserves