import random
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
        if d.weekday() in (4, 5):  # Fri, Sat
            yield d
        d += timedelta(days=1)

def match_probabilities(rA, rB, venue):
    if venue == "homeA":
        rA += 1.5
        rB -= 1.5
    elif venue == "homeB":
        rB += 1.5
        rA -= 1.5
    gap = rA - rB
    p_draw = 0.25 if abs(gap) <= 2 else 0.15

    def sigmoid(x):
        return 1 / (1 + pow(2.71828, -x))

    pA = sigmoid(gap / 6) * (1 - p_draw)
    pB = (1 - p_draw) - pA
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


# =========================
# SCHEDULING
# =========================
def all_pairs(teams):
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            yield teams[i], teams[j]


def build_four_meetings(teams):
    fixtures = []
    for A, B in all_pairs(teams):
        fixtures.extend([
            (A, B, "homeA"), (A, B, "homeA"),
            (A, B, "homeB"), (A, B, "homeB"),
        ])
    return fixtures


def assign_dates(fixtures, season_start, season_end):
    all_weekend = list(frisa_dates(season_start, season_end))
    if len(all_weekend) < len(fixtures):
        raise RuntimeError("Not enough Fri/Sat dates to host all matches.")
    picked = spread_pick(all_weekend, len(fixtures))
    scheduled = list(zip(picked, fixtures))
    scheduled.sort(key=lambda x: x[0])
    return scheduled
