from constants import FORMATIONS, BENCH, STARTERS

def organize_squad(team):
    # Build required starter slots from formation
    xi_positions = []
    for pos, c in FORMATIONS[team.formation].items():
        xi_positions += [pos] * c

    # Single sorted pool
    pool = team.all_players()[:]
    pool.sort(key=lambda p: p.rating, reverse=True)

    def take_best_pos(position):
        for i, p in enumerate(pool):
            if p.pos == position:
                return pool.pop(i)
        return None

    def take_best_any():
        return pool.pop(0) if pool else None

    # Fill starters (exact formation positions preferred)
    starters = []
    for pos in xi_positions:
        pick = take_best_pos(pos) or take_best_any()
        if pick:
            starters.append(pick)

    # Bench rule:
    bench = []

    # 1) Second GK (best remaining GK)
    bench_gk = take_best_pos("GK")
    if bench_gk:
        bench.append(bench_gk)

    # 2) Next best CB
    bench_cb = take_best_pos("CB")
    if bench_cb:
        bench.append(bench_cb)

    # 3) Fill remaining bench slots by best rating
    while len(bench) < BENCH and pool:
        bench.append(take_best_any())

    # Remaining = reserves
    reserves = pool

    # Commit with safety caps
    team.starters = starters[:STARTERS]
    team.bench = bench[:BENCH]
    team.reserves = reserves
