from constants import FORMATIONS, BENCH, STARTERS

SIMILAR_POS = {
    "GK":  ["ST"],
    "CB":  ["CDM", "RB", "LB"],
    "LB":  ["RB", "CB"],
    "RB":  ["LB", "CB"],
    "CDM": ["CB", "CM"],
    "CM":  ["CAM", "CDM", "ST"],
    "CAM": ["CM", "CDM", "ST", "RW", "LW"],
    "ST":  ["CAM", "LW", "RW"],
    "RW":  ["RB", "CAM"],
    "LW":  ["LB", "CAM"],
}

SIMILAR_DIFF = 4 

def organize_squad(team, on=None):
    """
    Builds starters/bench/reserves:
      1) Fill starters per formation.
         - Try exact position first.
         - Else try similar positions in priority order, but ONLY if candidate >= best primary + SIMILAR_DIFF.
         - If no primary exists, take the first candidate from the similarity ladder.
         - Else, fall back to best-any.
      2) Bench: ensure GK and CB first, then best remaining.
      3) Reserves: leftovers + injured.
    """
    def available(p):
        # Available now or by a given date 'on'
        return p.injured_until is None if on is None else (p.injured_until is None or on > p.injured_until)

    # Build the XI slot list from formation (e.g., {"CB":2,"CM":3} -> ["CB","CB","CM","CM","CM"])
    xi_positions = []
    for pos, c in FORMATIONS[team.formation].items():
        xi_positions += [pos] * c

    # Split injured vs available, and sort available by rating desc (so first match of a pos is best of that pos)
    injured = [p for p in team.all_players() if not available(p)]
    pool = [p for p in team.all_players() if available(p)]
    pool.sort(key=lambda p: p.rating, reverse=True)

    # --- helpers over the sorted pool (descending by rating) ---

    def pop_first_matching_pos(position):
        """Pop the highest-rated player of a specific position (first match due to global rating sort)."""
        for i, p in enumerate(pool):
            if p.pos == position:
                return pool.pop(i)
        return None

    def peek_best_primary_rating(position):
        """Return (index, rating) of best primary candidate without popping; (None, None) if none."""
        for i, p in enumerate(pool):
            if p.pos == position:
                return i, p.rating
        return None, None

    def pop_first_from_positions_in_order(positions, min_rating=None):
        """
        Scan the similarity ladder in order; for each position, take the highest-rated
        (first match) that also meets min_rating (if given).
        """
        for pos in positions:
            for i, p in enumerate(pool):
                if p.pos == pos and (min_rating is None or p.rating >= min_rating):
                    return pool.pop(i)
        return None

    def pop_best_any():
        return pool.pop(0) if pool else None

    # --- Fill starters with priority & threshold logic ---
    starters = []
    for pos in xi_positions:
        # Find best primary candidate rating (without consuming yet)
        primary_idx, primary_rating = peek_best_primary_rating(pos)

        if primary_idx is not None:
            # There is at least one true primary candidate for this slot
            # Check ladder for a strictly better alternative (>= primary + SIMILAR_DIFF)
            ladder = SIMILAR_POS.get(pos, [])
            better_similar = pop_first_from_positions_in_order(ladder, min_rating=primary_rating + SIMILAR_DIFF)
            if better_similar:
                starters.append(better_similar)
            else:
                # No sufficiently better similar option; take the best primary
                starters.append(pool.pop(primary_idx))
        else:
            # No primary available; try ladder without threshold, then any
            ladder = SIMILAR_POS.get(pos, [])
            pick = pop_first_from_positions_in_order(ladder) or pop_best_any()
            if pick:
                starters.append(pick)

    # --- Build bench: ensure GK and CB if possible, then best remaining by rating ---
    bench = []
    gk = pop_first_matching_pos("GK")
    if gk: bench.append(gk)
    cb = pop_first_matching_pos("CB")
    if cb: bench.append(cb)
    while len(bench) < BENCH and pool:
        bench.append(pop_best_any())

    # --- Reserves are whatever is left + all injured (injured always here) ---
    reserves = pool + injured

    team.starters = starters[:STARTERS]
    team.bench = bench[:BENCH]
    team.reserves = reserves
