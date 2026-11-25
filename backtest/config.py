"""Tham số Phase 1 — backtest $500/1x."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

END = datetime(2026, 11, 24, tzinfo=timezone.utc)
DAYS = int(os.getenv("BT_DAYS", "180"))
DATA_DIR = Path(os.getenv("BT_DATA_DIR", "data/backtest"))
REPORT_DIR = Path(os.getenv("BT_REPORT_DIR", "reports/phase1"))
START = END - timedelta(days=DAYS)
START_MS = int(START.timestamp() * 1000)
END_MS = int(END.timestamp() * 1000)

INTERVAL = "4h"
UNIVERSE_TOP_N = 120
FUT_VOLUME_MIN = 5_000_000.0
SPOT_VOLUME_MIN = 1_000_000.0
EXCLUDE = {"BTCUSDT", "ETHUSDT"}
REF_SYMBOLS = ("EVAAUSDT", "AVAAIUSDT", "PIEVERSEUSDT", "PHAROSUSDT")

CAPITAL = 500.0
COINS = 3
NOTIONAL_PER_COIN = 78.0
NOTIONAL_PER_LEG = NOTIONAL_PER_COIN * COINS
BUFFER = 30.0

SPOT_FEE = 0.00075
FUT_FEE = 0.00045
FEE_ROUNDTRIP = 2 * (SPOT_FEE + FUT_FEE)
SLIPPAGE_ROUNDTRIP = 0.0011
COST_ROUNDTRIP = FEE_ROUNDTRIP + SLIPPAGE_ROUNDTRIP
BASELINE_APR = 0.1095
DRAG_APR = COST_ROUNDTRIP * 365 / 14

FILTER = {
    "apr_min": 0.20,
    "apr_max": 0.60,
    "excess_min": 0.15,
    "pos_ratio_min": 0.85,
    "zero_rate_max": 0.10,
    "cv_max": 2.0,
    "decay_min": 0.60,
    "net_apr_min": 0.20,
    "slippage_max": 0.2,  # %/side
    "volume_min": FUT_VOLUME_MIN,
}
MAX_HOLD_DAYS = 28
REBALANCE_DAYS = 7
DD_KILL = 0.20
