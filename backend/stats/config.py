from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent  # -> backend/
STATS_DB = BACKEND_ROOT / "storage" / "stats.db"       # query log + hits (runtime, gitignored)

# How many months the admin statistics cover by default (the stats page needs 24:
# 12 for the "monthly" view plus history for "all time").
DEFAULT_MONTHS = 24
