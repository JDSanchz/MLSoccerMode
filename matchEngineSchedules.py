import random
import math
import numpy as np
from datetime import timedelta

def spread_pick(dates, k):
    """Evenly pick k entries across date list."""
    n = len(dates)
    if k <= 1:
        return [dates[0]] if k == 1 else []
    out = []
    for i in range(k):
        idx = int(round(i * (n - 1) / (k - 1)))
        out.append(dates[idx])
    return out


def frisa_dates(start, end):
    d = start
    while d <= end:
        # Fri=4, Sat=5, Sun=6
        if d.weekday() in (4, 5, 6):
            yield d
        d += timedelta(days=1)


def match_probabilities(rA, rB, venue):
    home_adv = 1.4
    if venue == "homeA": rA, rB = rA + home_adv, rB - home_adv
    elif venue == "homeB": rA, rB = rA - home_adv, rB + home_adv

    gap = max(-15, min(15, rA - rB))
    p_draw = max(0.12, min(0.28 - 0.015 * abs(gap), 0.28))
    T = 5.5

    def sigmoid(x):
        return 1 / (1 + pow(2.71828, -x))

    pA = sigmoid(gap / T) * (1 - p_draw)
    pB = (1 - p_draw) - pA
    pA = max(pA, 0.12)
    pB = max(pB, 0.12)
    return pA, p_draw, pB



def result_score(a_wins):
    if a_wins is True:
        gA = random.choice([1, 2, 2, 3, 3, 4])
        gB = random.choice([0, 0, 1, 1, 2])
        if gB >= gA:
            gB = max(0, gA - 1)
    elif a_wins is False:
        gB = random.choice([1, 2, 2, 3, 3, 4])
        gA = random.choice([0, 0, 1, 1, 2])
        if gA >= gB:
            gA = max(0, gB - 1)
    else:
        g = random.choice([0, 1, 1, 2, 2])
        return g, g
    return gA, gB


_neutral_idx = 0


def simulate_match(teamA, teamB, venue, when):
    rA = teamA.avg_rating()
    rB = teamB.avg_rating()
    pA, pD, pB = match_probabilities(rA, rB, venue)
    roll = random.random()
    if roll < pA:
        gA, gB = result_score(True)
        teamA.points += 3
    elif roll < pA + pD:
        gA, gB = result_score(None)
        teamA.points += 1
        teamB.points += 1
    else:
        gA, gB = result_score(False)
        teamB.points += 3
    teamA.gf += gA
    teamA.ga += gB
    teamB.gf += gB
    teamB.ga += gA
    return gA, gB


# =========================
# SCHEDULING
# =========================
def all_pairs(teams):
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            yield teams[i], teams[j]


def build_home_and_away(teams):
    fixtures = []
    for A, B in all_pairs(teams):
        fixtures.append((A, B, "homeA"))  # A hosts once
        fixtures.append((A, B, "homeB"))  # B hosts once
    return fixtures


def assign_dates(fixtures, season_start, season_end):
    if not fixtures:
        return []

    all_weekend = list(frisa_dates(season_start, season_end))
    if not all_weekend:
        raise RuntimeError("Season calendar has no Fri/Sat/Sun dates.")

    slots_per_day = max(1, math.ceil(len(fixtures) / len(all_weekend)))
    expanded_days = []
    for day in all_weekend:
        expanded_days.extend([day] * slots_per_day)

    match_days = expanded_days[:len(fixtures)]
    scheduled = list(zip(match_days, fixtures))
    scheduled.sort(key=lambda x: x[0])
    return scheduled
