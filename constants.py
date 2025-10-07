TEAMS_INIT = [
    {"name": "PSG",            "avg": 88, "budget": 250, "objective": 1, "formation": "4-3-3", "stadium": "Parc des Princes"},
    {"name": "Liverpool",      "avg": 88, "budget": 300, "objective": 1, "formation": "4-4-2", "stadium": "Anfield"},
    {"name": "Barcelona",      "avg": 86, "budget": 100, "objective": 2, "formation": "4-3-3", "stadium": "Spotify Camp Nou"},
    {"name": "Real Madrid",    "avg": 86, "budget": 180, "objective": 2, "formation": "4-4-2", "stadium": "Santiago Bernabéu Stadium"},
    {"name": "Bayern Munich",  "avg": 85, "budget": 120, "objective": 2, "formation": "4-3-3", "stadium": "Allianz Arena"},
    {"name": "America",        "avg": 80, "budget": 40, "objective": 5, "formation": "4-4-2", "stadium": "El Nido"},
    {"name": "Ajax",            "avg": 82, "budget": 35, "objective": 4, "formation": "4-3-3", "stadium": "Ajax Arena"},
]

ORIGINS = {
    "PSG": ["France","Morocco","Argentina","Belgium","Nigeria"],
    "Liverpool": ["England","France","Brazil","Colombia","Uruguay"],
    "Barcelona": ["Spain","United States","Argentina","Netherlands","Chile"],
    "Real Madrid": ["Spain","England","Brazil","Belgium","Argentina"],
    "Bayern Munich": ["Germany","Japan","Portugal","France","United States"],
    "America": ["Mexico","Brazil","Uruguay","Chile","Colombia"],
    "Ajax": ["Netherlands","United States","Argentina","Mexico"],
}

FORMATIONS = {
    "4-3-3": {"GK":1,"CB":2,"LB":1,"RB":1,"CM":3,"LW":1,"RW":1,"ST":1},
    "4-4-2": {"GK":1,"CB":2,"LB":1,"RB":1,"CDM":1,"CAM":1,"LW":1,"RW":1,"ST":2},
}

INIT_YEAR = 2025  # first season start (Aug 15, 2025)
STARTERS = 11
BENCH = 9
RESERVES = 10

# Youth new-season additions
YOUTH_OVR_MIN, YOUTH_OVR_MAX = 70, 74
YOUTH_AGE_MIN, YOUTH_AGE_MAX = 16, 25
YOUTH_POT_USER = (77, 95)
YOUTH_POT_AI   = (80, 92)