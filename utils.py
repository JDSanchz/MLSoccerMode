from datetime import date
def season_dates(year):
    """Return (TM_OPEN, TM_CLOSE, PROCESSING_DAY, SEASON_START, SEASON_END) for a given starting year."""
    tm_open = date(year, 6, 16)
    tm_close = date(year, 8, 13)
    processing = date(year, 8, 14)
    season_start = date(year, 8, 15)
    season_end = date(year+1, 6, 15)
    return tm_open, tm_close, processing, season_start, season_end


def yesno(msg):
    return input(msg).strip().lower().startswith("y")


def clamp(x, lo, hi):
    return max(lo, min(hi, x))