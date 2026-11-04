"""Generate the WakaDash dark horizontal stats card.

Uses stat_card.py and wakatime.py from https://github.com/Anant-mishra1729/WakaDash
(MIT, see LICENSE in this folder). Run from the repo root:

    WAKATIME_API_KEY=... WAKADASH_OUT_DIR=assets/wakadash python scripts/wakadash/generate.py

Writes stats_card_dark.svg into $WAKADASH_OUT_DIR (default: ./results).
"""

import os

from stat_card import create_wakatime_summary_card
from wakatime import WakaTimeClient

# last_7_days, last_30_days, last_6_months, last_year or all_time
STATS_RANGE = "last_7_days"

waka = WakaTimeClient(os.getenv("WAKATIME_API_KEY"), STATS_RANGE)
stats = waka.fetch_stats()

create_wakatime_summary_card(
    daily_avg=stats["human_readable_daily_average"],
    best_day_dict=stats["best_day"],
    theme="dark",
    layout="horizontal",
    width=700,
    height=180,
)
