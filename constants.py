TEAMS_INIT = [
    {"name": "PSG",            "avg": 88, "budget": 250, "objective": 1, "formation": "4-3-3", "stadium": "Parc des Princes"},
    {"name": "Liverpool",      "avg": 88, "budget": 300, "objective": 1, "formation": "4-4-2", "stadium": "Anfield"},
    {"name": "Barcelona",      "avg": 86, "budget": 100, "objective": 2, "formation": "4-3-3", "stadium": "Spotify Camp Nou"},
    {"name": "Real Madrid",    "avg": 86, "budget": 180, "objective": 2, "formation": "4-4-2", "stadium": "Santiago Bernabéu Stadium"},
    {"name": "Bayern Munich",  "avg": 85, "budget": 120, "objective": 2, "formation": "4-3-3", "stadium": "Allianz Arena"},
    {"name": "Napoli",     "avg": 85, "budget": 90, "objective": 4, "formation": "4-4-2", "stadium": "San Paolo"},
    {"name": "Arsenal",         "avg": 86, "budget": 200, "objective": 2, "formation": "4-3-3", "stadium": "Emirates Stadium"},
    {"name": "Inter Milan",      "avg": 85, "budget": 70, "objective": 4, "formation": "3-5-2", "stadium": "San Siro"},
    {"name": "Chelsea",         "avg": 84, "budget": 180, "objective": 3, "formation": "4-3-3", "stadium": "Stamford Bridge"},
    {"name": "Porto",            "avg": 82, "budget": 30, "objective": 5, "formation": "4-3-3", "stadium": "Do Dragao"},
    {"name": "Olympique Lyonnais",       "avg": 80, "budget": 30, "objective": 8, "formation": "4-3-3", "stadium": "Stade Geoffroy Guichard"},
]

ORIGINS = {
    "PSG": ["France","Morocco","Argentina","Belgium","Nigeria"],
    "Liverpool": ["England","France","Brazil","Colombia","Uruguay","Nigeria"],
    "Barcelona": ["Spain","United States","Argentina","Netherlands","Chile"],
    "Real Madrid": ["Spain","England","Brazil","Belgium","Argentina","France"],
    "Bayern Munich": ["Germany","Japan","Portugal","France","United States"],
    "Arsenal": ["England","France","Spain","Germany","Netherlands"],
    "Chelsea": ["England","France","Brazil","Netherlands","Uruguay"],
    "Porto": ["Portugal","France","Brazil","Netherlands","Nigeria"],
    "Inter Milan": ["Italy","France","Brazil","Netherlands","Uruguay"],
    "Napoli": ["Italy","France","Brazil","Nigeria","Belgium"],
    "Olympique Lyonnais": ["France","Morocco","Argentina","Belgium","Nigeria"],
}

FORMATIONS = {
    "4-3-3": {"GK":1,"CB":2,"LB":1,"RB":1,"CM":3,"LW":1,"RW":1,"ST":1},
    "4-4-2": {"GK":1,"CB":2,"LB":1,"RB":1,"CDM":1,"CAM":1,"LW":1,"RW":1,"ST":2},
    "3-5-2": {"GK":1,"CB":3,"CDM":2,"CAM":1,"LW":1,"RW":1,"ST":2},
}

INIT_YEAR = 2025  # first season start (Aug 15, 2025)
STARTERS = 11
BENCH = 10
RESERVES = 11

# Youth new-season additions
YOUTH_OVR_MIN, YOUTH_OVR_MAX = 70, 74
YOUTH_AGE_MIN, YOUTH_AGE_MAX = 16, 24
YOUTH_POT_USER = (77, 95)
YOUTH_POT_AI   = (78, 92)