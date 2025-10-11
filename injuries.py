import random
from datetime import timedelta
def assign_season_injuries(team, season_start, season_end, is_user=False):
    avg = team.avg_rating()
    n = random.randint(2, 5)
    pool = team.all_players()
    if not pool:
        return

    picks = random.sample(pool, k=min(n, len(pool)))
    span = (season_end - season_start).days

    if is_user:
        print(f"\n🩹 {team.name} Season Injuries:")

    for who in picks:
        # Weighted duration selection
        roll = random.random()
        if roll < 0.6:        # 60% chance
            days = random.randint(6, 14)
        elif roll < 0.9:      # 30% chance
            days = random.randint(15, 90)
        else:                 # 10% chance
            days = random.randint(91, 230)

        start_offset = 0 if span <= days else random.randint(0, span - days)
        when = season_start + timedelta(days=start_offset)
        who.injured_until = when + timedelta(days=days)

        if is_user:
            tier = (
                "🟢 Minor" if days <= 14 else
                "🟡 Moderate" if days <= 90 else
                "🔴 Severe"
            )
            print(f"  {tier:<9} | {who.rating} OVR - {who.name:<25} | Out {days:>3} days")



def recover_injuries(team, when, is_user=False):
    # If a player has recovered by 'when', clear injury and notify if user
    for p in team.all_players():
        if p.injured_until and when >= p.injured_until:
            p.injured_until = None
            if is_user:
                print(f"✅ {p.name} has recovered on {when.isoformat()}")