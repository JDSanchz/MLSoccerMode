import random
from datetime import timedelta
def assign_season_injuries(team, season_start, season_end, is_user=False):
    avg = team.avg_rating()
    n = random.randint(2, 3) if avg < 85 else random.randint(4, 7)
    pool = team.all_players()
    if not pool:
        return

    picks = random.sample(pool, k=min(n, len(pool)))
    span = (season_end - season_start).days

    if is_user:
        print(f"\n🩹 {team.name} Season Injuries:")

    for who in picks:
        days = random.randint(20, 280)
        start_offset = 0 if span <= days else random.randint(0, span - days)
        when = season_start + timedelta(days=start_offset)
        who.injured_until = when + timedelta(days=days)

        if is_user:
            print(f"  {who.rating} OVR - {who.name:<25} | Out for {days} days")


def recover_injuries(team, when, is_user=False):
    # If a player has recovered by 'when', clear injury and notify if user
    for p in team.all_players():
        if p.injured_until and when >= p.injured_until:
            p.injured_until = None
            if is_user:
                print(f"✅ {p.name} has recovered on {when.isoformat()}")