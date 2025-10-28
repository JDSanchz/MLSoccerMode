import random
from playerCost import est_cost_eur
from constants import *
from randomName import random_name
from models.player import Player
from organizeSquad import organize_squad

def trim_ai_reserves(team):
    over = len(team.reserves) - RESERVES
    if over <= 0:
        return

    total_fee = 0

    # Step 1: randomly drop 2 of the 5 oldest (up to needed)
    oldest5 = sorted(team.reserves, key=lambda p: p.age, reverse=True)[:5]
    k = min(2, over, len(oldest5))
    victims = set()
    if k > 0:
        drop = set(random.sample(oldest5, k))
        victims.update(drop)
        over -= k

    # Step 2: drop the rest by lowest market value
    if over > 0:
        by_value = sorted(team.reserves, key=lambda p: est_cost_eur(p.age, p.rating))
        victims.update(by_value[:over])

    # Apply the trimming and fees
    team.reserves = [p for p in team.reserves if p not in victims]
    total_fee = len(victims) * 1  # €1 per release
    team.budget -= total_fee

    print(f"{team.name} released {len(victims)} reserve(s), paying €{total_fee} in total fees.")


def ai_transfers(team, free_agents):
    """Handle AI-controlled team transfers automatically during transfer windows."""
    # Skip entire window if budget is below €5M at this point
    if team.budget < 5:
        print(f"{team.name} skips transfers (budget €{team.budget:,}M < €5M).")
        return

    organize_squad(team)

    def capture_needs():
        """Return (display_order, priority_order)."""
        details = team.weakest_positions(return_details=True)
        if not details:
            return [], []
        priority = sorted(details, key=lambda item: (item["delta"], -item["avg"]), reverse=True)
        return [d["pos"] for d in details], [d["pos"] for d in priority]

    def try_sign_future_star():
        prospects = [
            p for p in free_agents
            if p.age < 23 and getattr(p, "potential", p.rating) > 90
        ]
        if not prospects:
            return False
        prospects.sort(
            key=lambda x: (getattr(x, "potential", x.rating), x.rating),
            reverse=True,
        )
        for prospect in prospects:
            price = est_cost_eur(prospect.age, prospect.rating)
            if price > team.budget:
                continue
            if team.pay(price):
                free_agents.remove(prospect)
                team.reserves.append(prospect)
                print(f"{team.name} has signed {prospect.name} a future start")
                organize_squad(team)
                return True
        return False

    n_transfers = random.randint(1, 3)
    lock_primary_need = False

    # If planned multi-signing leaves < €40M per signing, do just one
    if n_transfers > 1 and (team.budget // n_transfers) < 40:
        n_transfers = 1
        lock_primary_need = True


    for i in range(n_transfers):
        # If budget dropped under €5M during the window, stop signing more
        if team.budget < 5:
            print(f"{team.name} stops transfers (budget €{team.budget:,}M < €5M).")
            break
        if not free_agents:
            break

        weakest_by_avg, priority_by_delta = capture_needs()
        if not priority_by_delta:
            break
        print(f"Weakest positions: {', '.join(weakest_by_avg)}")

        if lock_primary_need:
            target_positions = priority_by_delta[:1]
        else:
            target_positions = priority_by_delta[:2]
        if not target_positions:
            target_positions = priority_by_delta

        roster = team.all_players()
        total_rating = sum(p.rating for p in roster)
        roster_size = len(roster)
        current_avg = (total_rating / roster_size) if roster_size else 0

        def acceptable(player):
            if not roster_size:
                return True
            new_avg = (total_rating + player.rating) / (roster_size + 1)
            if new_avg >= current_avg:
                return True
            projected = getattr(player, "potential", player.rating)
            return projected >= 87 and player.age < 26

        # Spend roughly a fraction of remaining budget for this signing
        remaining = n_transfers - i
        val = max(1, team.budget // remaining)

        same_pos = [
            p for p in free_agents
            if est_cost_eur(p.age, p.rating) <= val and p.pos in target_positions
        ]

        if not same_pos and not lock_primary_need:
            remaining_targets = [pos for pos in priority_by_delta if pos not in target_positions]
            if remaining_targets:
                same_pos = [
                    p for p in free_agents
                    if est_cost_eur(p.age, p.rating) <= val and p.pos in remaining_targets
                ]

        candidates = same_pos if same_pos else [
            p for p in free_agents if est_cost_eur(p.age, p.rating) <= val
        ]
        print(f"Available candidates: {len(candidates)}")
        if not candidates:
            try_sign_future_star()
            continue

        viable = [p for p in candidates if acceptable(p)]
        if not viable:
            try_sign_future_star()
            continue

        # Prefer top-rated affordable targets;  add a little randomness
        target_pool = sorted(viable, key=lambda x: x.rating, reverse=True)[:6]
        signing = random.choice(target_pool)
        price = est_cost_eur(signing.age, signing.rating)

        if team.pay(price):
            free_agents.remove(signing)
            team.reserves.append(signing)
            print(f"📝 {team.name} signed {signing.name} ({signing.pos}, {signing.rating} OVR, Age {signing.age}) "
          f"for €{price:,}M.")
            organize_squad(team)


def champion_poach_user(
    prev_table,
    user,
    top_chance=0.90,
    bottom_chance=0.30,
    premium_rate=0.15,
    free_roll_chance=0.95
):
    if not prev_table or not user.all_players():
        return

    if hasattr(user, "cleanup_poach_protected"):
        user.cleanup_poach_protected()
    protected = set(getattr(user, "poach_protected", []))

    def est_price_with_premium(player):
        base = est_cost_eur(player.age, player.rating)
        prem = max(1, int(round(base * premium_rate)))
        return base, prem, base + prem

    def remove_from_user_and_add_to_buyer(target, buyer, base, prem, total, allow_negative=False):
        if not allow_negative and buyer.budget < total:
            print(f"\n{buyer.name} wanted {target.name} but cannot afford €{total:,}. No transfer.")
            return False

        buyer.budget -= total  # may go negative if allow_negative=True
        user.receive(total)

        source_group = "Reserves"
        for label, group in (("Starters", user.starters), ("Bench", user.bench), ("Reserves", user.reserves)):
            if target in group:
                source_group = label
                group.remove(target)
                break
        source_label = {
            "Starters": "starting lineup",
            "Bench": "bench",
            "Reserves": "reserves",
        }.get(source_group, source_group.lower())

        buyer.reserves.append(target)
        if hasattr(user, "unprotect_player"):
            user.unprotect_player(target)
        protected.discard(target)

        flag = target.flag() if hasattr(target, "flag") else f"({target.nation})"
        neg_note = " (budget now negative)" if buyer.budget < 0 else ""
        print(
            f"\nPOACH! {buyer.name} signed {target.name} {flag} "
            f"({target.pos}, {target.rating} OVR) from your {source_label} "
            f"for €{base:,} + {int(premium_rate*100)}% (€{prem:,}) = €{total:,}."
        )
        print(f"{user.name} receives €{total:,}. {buyer.name} budget: €{buyer.budget:,}{neg_note}")
        return True

    def free_move_from_user_reserves(target, dest_team):
        # Remove strictly from reserves (per your spec)
        source_group = "Reserves"
        if target in user.reserves:
            user.reserves.remove(target)
        else:
            # Safety: remove if it slipped into other groups
            for label, group in (("Starters", user.starters), ("Bench", user.bench)):
                if target in group:
                    source_group = label
                    group.remove(target)
                    break
        source_label = {
            "Starters": "starting lineup",
            "Bench": "bench",
            "Reserves": "reserves",
        }.get(source_group, source_group.lower())
        dest_team.reserves.append(target)
        if hasattr(user, "unprotect_player"):
            user.unprotect_player(target)
        protected.discard(target)
        flag = target.flag() if hasattr(target, "flag") else f"({target.nation})"
        print(
            f"\nFREE TRANSFER: {target.name} {flag} left {user.name} "
            f"({target.pos}, {target.rating} OVR, {source_label}) for {dest_team.name} "
            f"(lowest avg rating: {dest_team.avg_rating():.1f})."
        )

    def calc_max_potential(p):
        if hasattr(p, "max_potential"):
            try:
                return p.max_potential()
            except Exception:
                pass
        for delta_name in ("potential_delta", "pot_delta", "growth", "potential_growth"):
            if hasattr(p, delta_name):
                return p.rating + getattr(p, delta_name)
        if hasattr(p, "potential"):
            pot = getattr(p, "potential")
            return pot if pot >= p.rating else p.rating + pot
        return p.rating

    # ---------- Roll 1: 90% — richest top-2 non-user teams buy affordable top-3 ----------
    if random.random() < top_chance:
        non_user = [t for t in prev_table if t is not user]
        richest_top2 = sorted(non_user, key=lambda t: t.budget, reverse=True)[:2]
        if richest_top2:
            buyer = random.choice(richest_top2)
            affordable = []
            for p in user.all_players():
                if p in protected:
                    continue
                _, _, total = est_price_with_premium(p)
                if total <= buyer.budget:
                    affordable.append((p, total))
            if affordable:
                top3_affordable = sorted(affordable, key=lambda pt: pt[0].rating, reverse=True)[:3]
                target, total = random.choice(top3_affordable)
                base, prem, _ = est_price_with_premium(target)
                remove_from_user_and_add_to_buyer(target, buyer, base, prem, total, allow_negative=False)

    # ---------- Roll 2: 30% — bottom-3 in table buy from top-5 potential reserves (can go negative) ----------
    if random.random() < bottom_chance:
        bottom3 = [t for t in prev_table[-3:] if t is not user]
        if bottom3 and user.reserves:
            buyer = random.choice(bottom3)
            reserves_by_pot = [
                p for p in user.reserves if p not in protected
            ]
            reserves_by_pot = sorted(reserves_by_pot, key=lambda p: calc_max_potential(p), reverse=True)[:5]
            if reserves_by_pot:
                target = random.choice(reserves_by_pot)
                base, prem, total = est_price_with_premium(target)
                remove_from_user_and_add_to_buyer(target, buyer, base, prem, total, allow_negative=True)

    # ---------- Roll 3: 95% — free move if >3 reserves rated >81 to lowest-avg team ----------
    if random.random() < free_roll_chance:
        strong_reserves = [p for p in user.reserves if p.rating > 81 and p not in protected]
        candidates = [t for t in prev_table if t is not user]
        if len(strong_reserves) > 3 and candidates:
            dest = min(candidates, key=lambda t: t.avg_rating())
            target = random.choice(strong_reserves)
            free_move_from_user_reserves(target, dest)



def make_free_agent_pool(num=75):
    base_positions = ["GK", "CB", "LB", "RB", "CDM", "CAM", "CM", "ST", "LW", "RW"]
    all_origins = [n for arr in ORIGINS.values() for n in arr]

    def pick_origin():
        return random.choice(all_origins)

    def roll_potential(rating):
        pot = random.randint(79, 94)
        pot = max(rating + 1, pot) if pot <= rating else pot
        if pot > 91 and random.randint(1, 20) != 1:  # 95% cap at 91
            pot = 91
        return pot

    def make_player(pos, age_lo, age_hi, rating_lo, rating_hi):
        nation = pick_origin()
        age = random.randint(age_lo, age_hi)
        rating = random.randint(rating_lo, rating_hi)
        pot = roll_potential(rating)
        return Player(random_name(nation), pos, nation, age, rating, pot - rating)

    # Create full pool
    pool = [make_player(random.choice(base_positions), 18, 34, 74, 88) for _ in range(num)]

    # 1) Remove 5 lowest-rated players age ≥ 30
    over29 = [p for p in pool if p.age >= 30]
    remove1 = set(sorted(over29, key=lambda p: p.rating)[:5])

    remaining = [p for p in pool if p not in remove1]

    # 2) From remaining, remove 5 lowest market value
    remove2 = set(sorted(remaining, key=lambda p: p.value())[:5])

    final_pool = [p for p in remaining if p not in remove2]
    return final_pool
