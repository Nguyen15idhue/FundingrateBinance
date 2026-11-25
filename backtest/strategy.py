"""Feature, screener và mô phỏng $500/1x cho Phase 1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtest import config as cfg

DATA = cfg.DATA_DIR
EPS = 1e-12


# ---------------------------------------------------------------- data
def load_raw() -> dict[str, pd.DataFrame]:
    out = {}
    for name in ("universe", "funding", "klines", "premium", "spot_klines", "oi"):
        p = DATA / f"{name}.parquet"
        out[name] = pd.read_parquet(p) if p.exists() else pd.DataFrame()
    return out


def build_prices(klines: pd.DataFrame, spot: pd.DataFrame) -> pd.DataFrame:
    f = klines[klines["market"] == "futures"].copy()
    s = spot.copy()
    m = f.merge(
        s[["symbol", "open_time", "close"]],
        on=["symbol", "open_time"], how="inner", suffixes=("_fut", "_spot"),
    )
    m["close_dt"] = m["dt"] + pd.Timedelta(hours=4)
    m["basis"] = m["close_fut"] / m["close_spot"] - 1
    m["range"] = (m["high"] / m["low"] - 1).abs()
    m = m.sort_values(["symbol", "open_time"]).reset_index(drop=True)
    m["volume24"] = m.groupby("symbol")["quote_volume"].transform(
        lambda x: x.rolling(6, min_periods=3).sum()
    )
    m["move24"] = m.groupby("symbol")["range"].transform(
        lambda x: x.rolling(6, min_periods=1).max()
    )
    m["basis_sigma"] = m.groupby("symbol")["basis"].transform(
        lambda x: x.rolling(84, min_periods=20).std()
    )
    return m


def funding_arrays(funding: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    out = {}
    for sym, g in funding.groupby("symbol"):
        t = g["fundingTime"].to_numpy(dtype=np.int64)
        r = g["fundingRate"].to_numpy(dtype=float)
        out[sym] = (t, r, np.cumsum(r))
    return out


def _sum_window(t: np.ndarray, r: np.ndarray, start_ms: int, end_ms: int) -> tuple[float, int]:
    i = int(np.searchsorted(t, start_ms, side="right"))
    j = int(np.searchsorted(t, end_ms, side="right"))
    if j <= i:
        return 0.0, 0
    return float(r[i:j].sum()), j - i


# ---------------------------------------------------------------- features
def features_for_date(
    date: pd.Timestamp,
    funding: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    prices: dict[str, tuple[np.ndarray, ...]],
    universe: pd.DataFrame,
    prev_neg: dict[str, int] | None = None,
) -> pd.DataFrame:
    end_ms = int(date.timestamp() * 1000)
    rows = []
    for _, u in universe.iterrows():
        sym = u["symbol"]
        if sym not in funding or sym not in prices:
            continue
        t, r, _ = funding[sym]
        s3, n3 = _sum_window(t, r, end_ms - 3 * 86400_000, end_ms)
        s7, n7 = _sum_window(t, r, end_ms - 7 * 86400_000, end_ms)
        s14, n14 = _sum_window(t, r, end_ms - 14 * 86400_000, end_ms)
        if n14 < 4:
            continue
        apr3, apr7, apr14 = s3 * 365 / 3, s7 * 365 / 7, s14 * 365 / 14
        mean14 = s14 / n14
        var = float(np.var(r[np.searchsorted(t, end_ms - 14 * 86400_000, side="right"):np.searchsorted(t, end_ms, side="right")])) if n14 > 1 else 0.0
        cv = (np.sqrt(var) / mean14) if mean14 > EPS else 99.0
        pos_ratio = float((r[np.searchsorted(t, end_ms - 14 * 86400_000, side="right"):np.searchsorted(t, end_ms, side="right")] > 0).sum()) / n14
        zero_rate = float((np.abs(r[np.searchsorted(t, end_ms - 14 * 86400_000, side="right"):np.searchsorted(t, end_ms, side="right")]) <= 1e-9).sum()) / n14
        forward = min(apr7, apr14)
        decay = apr7 / apr14 if apr14 > EPS else 0.0
        net_apr = forward - cfg.DRAG_APR

        ct, fc, sc, vol, move, basis, bsigma = prices[sym]
        idx = int(np.searchsorted(ct, int(date.timestamp() * 1_000_000_000), side="right")) - 1
        if idx < 0:
            continue
        perp, spot = float(fc[idx]), float(sc[idx])
        if not np.isfinite(perp) or not np.isfinite(spot) or perp <= 0 or spot <= 0:
            continue
        volume24 = float(vol[idx])
        bz = float(basis[idx] / bsigma[idx]) if bsigma[idx] and np.isfinite(bsigma[idx]) and bsigma[idx] > EPS else 0.0

        qf = np.floor(cfg.NOTIONAL_PER_COIN / perp / u["fut_step_size"]) * u["fut_step_size"]
        qs = np.floor(cfg.NOTIONAL_PER_COIN / spot / u["spot_step_size"]) * u["spot_step_size"]
        nf, ns = qf * perp, qs * spot
        min_ok = qf > 0 and qs > 0 and nf >= u["fut_min_notional"] and ns >= u["spot_min_notional"]

        j_end = int(np.searchsorted(t, end_ms, side="right"))
        recent_t = t[max(0, j_end - 30):j_end]
        median_iv = float(np.median(np.diff(recent_t))) / 3_600_000 if len(recent_t) > 2 else 8.0
        expected14 = 14 * 24 / max(1.0, median_iv)
        data_ok = n14 >= 0.8 * expected14 and n7 >= 0.8 * (7 * 24 / max(1.0, median_iv))

        f = {
            "date": date,
            "symbol": sym,
            "apr3": apr3, "apr7": apr7, "apr14": apr14,
            "forward": forward, "excess": apr14 - cfg.BASELINE_APR,
            "pos_ratio": pos_ratio, "zero_rate": zero_rate, "cv": cv,
            "decay": decay, "predicted": apr3, "net_apr": net_apr,
            "volume24": volume24, "price_move24": float(move[idx]),
            "basis_z": bz, "slippage": float(u["slippage_pct"]),
            "perp": perp, "spot": spot, "qty_fut": qf, "qty_spot": qs,
            "notional_fut": nf, "notional_spot": ns, "min_ok": min_ok,
            "data_ok": data_ok, "n14": n14,
            "score": net_apr * min(1.0, 1.0 / max(cv, 1e-6)) * min(1.0, volume24 / 20_000_000),
        }
        f["pass_all"] = (
            data_ok and min_ok
            and cfg.FILTER["apr_min"] <= forward <= cfg.FILTER["apr_max"]
            and f["excess"] >= cfg.FILTER["excess_min"]
            and pos_ratio >= cfg.FILTER["pos_ratio_min"]
            and zero_rate <= cfg.FILTER["zero_rate_max"]
            and cv <= cfg.FILTER["cv_max"]
            and decay >= cfg.FILTER["decay_min"]
            and apr3 >= 0.5 * apr7
            and apr3 <= 3.0 * apr7
            and net_apr >= cfg.FILTER["net_apr_min"]
            and volume24 >= cfg.FILTER["volume_min"]
            and f["slippage"] <= cfg.FILTER["slippage_max"]
        )
        rows.append(f)
    return pd.DataFrame(rows)


def price_dict(prices_df: pd.DataFrame) -> dict[str, tuple[np.ndarray, ...]]:
    out = {}
    for sym, g in prices_df.groupby("symbol"):
        ct = (g["close_dt"].astype("int64")).to_numpy()
        out[sym] = (
            ct,
            g["close_fut"].to_numpy(float),
            g["close_spot"].to_numpy(float),
            g["volume24"].to_numpy(float),
            g["move24"].to_numpy(float),
            g["basis"].to_numpy(float),
            g["basis_sigma"].to_numpy(float),
        )
    return out


def build_features(raw: dict[str, pd.DataFrame], *, save: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, tuple[np.ndarray, ...]], dict]:
    universe = raw["universe"].copy()
    prices_df = build_prices(raw["klines"], raw["spot_klines"])
    farr = funding_arrays(raw["funding"])
    pdict = price_dict(prices_df)
    dates = pd.date_range(cfg.START, cfg.END, freq="D", tz="UTC")
    rows = []
    for d in dates:
        f = features_for_date(d, farr, pdict, universe)
        if not f.empty:
            rows.append(f)
    features = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if save and not features.empty:
        features.to_parquet(DATA / "features.parquet", index=False)
    meta = {"dates": len(dates), "features": int(len(features)), "symbols": int(len(universe))}
    return features, prices_df, pdict, meta


# ---------------------------------------------------------------- simulation
@dataclass
class Position:
    symbol: str
    entry_date: pd.Timestamp
    spot0: float
    perp0: float
    qty_spot: float
    qty_perp: float
    notional: float
    entry_cost: float
    neg_streak: int = 0


@dataclass
class Result:
    equity: pd.Series
    episodes: pd.DataFrame
    positions: pd.DataFrame
    metrics: dict[str, Any] = field(default_factory=dict)


def _price_at(prices: dict[str, tuple[np.ndarray, ...]], sym: str, date: pd.Timestamp) -> tuple[float, float] | None:
    if sym not in prices:
        return None
    ct, fc, sc, *_ = prices[sym]
    idx = int(np.searchsorted(ct, int(date.timestamp() * 1_000_000_000), side="right")) - 1
    if idx < 0:
        return None
    p, s = float(fc[idx]), float(sc[idx])
    if not np.isfinite(p) or not np.isfinite(s) or p <= 0 or s <= 0:
        return None
    return p, s


def _funding_sum(farr: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]], sym: str, start: pd.Timestamp, end: pd.Timestamp) -> float:
    if sym not in farr:
        return 0.0
    t, r, _ = farr[sym]
    i = int(np.searchsorted(t, int(start.timestamp() * 1000), side="left"))
    j = int(np.searchsorted(t, int(end.timestamp() * 1000), side="right"))
    return float(r[i:j].sum())


def run_backtest(
    features: pd.DataFrame,
    prices: dict[str, tuple[np.ndarray, ...]],
    farr: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    funding_mult: float = 1.0,
    cost_roundtrip: float = cfg.COST_ROUNDTRIP,
    signal_lag_days: int = 0,
    basis_shock: float = 0.0,
    shock_day: int = 90,
    truncate: dict[str, str] | None = None,
) -> Result:
    dates = pd.date_range(cfg.START, cfg.END, freq="D", tz="UTC")
    feat_by_date = {d: g.set_index("symbol").to_dict("index") for d, g in features.groupby("date")}
    half_cost = cost_roundtrip / 2
    cash = cfg.CAPITAL
    positions: dict[str, Position] = {}
    cooldown: dict[str, pd.Timestamp] = {}
    equity_rows, pos_rows, episodes = [], [], []
    fees = funding_total = price_total = 0.0
    killed = False

    def close_pos(pos: Position, d: pd.Timestamp, px: tuple[float, float]) -> None:
        nonlocal cash, fees, funding_total, price_total
        perp, spot = px
        pnl_price = pos.qty_spot * (spot - pos.spot0) + pos.qty_perp * (pos.perp0 - perp)
        fsum = _funding_sum(farr, pos.symbol, pos.entry_date, d) * funding_mult
        pnl_fund = pos.notional * fsum
        exit_cost = pos.notional * half_cost
        cash += pnl_price + pnl_fund - exit_cost
        fees += exit_cost
        funding_total += pnl_fund
        price_total += pnl_price
        episodes.append({
            "symbol": pos.symbol,
            "entry": pos.entry_date,
            "exit": d,
            "hold_days": (d - pos.entry_date).days,
            "notional": pos.notional,
            "price_pnl": pnl_price,
            "funding_pnl": pnl_fund,
            "cost": pos.entry_cost + exit_cost,
            "pnl": pnl_price + pnl_fund - pos.entry_cost - exit_cost,
        })

    def enter(sym: str, d: pd.Timestamp, px: tuple[float, float], row: dict) -> None:
        nonlocal cash, fees
        perp, spot = px
        n = cfg.NOTIONAL_PER_COIN
        qf = float(row["qty_fut"])
        qs = float(row["qty_spot"])
        if qf <= 0 or qs <= 0:
            return
        cost = n * half_cost
        cash -= cost
        fees += cost
        positions[sym] = Position(sym, d, spot, perp, qs, qf, n, cost)

    for di, d in enumerate(dates):
        if truncate:
            for sym, cutoff in truncate.items():
                if d >= pd.Timestamp(cutoff, tz="UTC") and sym in positions:
                    px = _price_at(prices, sym, d)
                    if px:
                        close_pos(positions.pop(sym), d, px)
                    cooldown[sym] = d + pd.Timedelta(days=14)

        decision_date = d - pd.Timedelta(days=signal_lag_days)
        fday = feat_by_date.get(decision_date, {})
        px_now = {sym: _price_at(prices, sym, d) for sym in positions}

        # mark to market
        unreal = 0.0
        for sym, pos in positions.items():
            px = px_now.get(sym)
            if not px:
                continue
            perp, spot = px
            unreal += pos.qty_spot * (spot - pos.spot0) + pos.qty_perp * (pos.perp0 - perp)
            unreal += pos.notional * _funding_sum(farr, sym, pos.entry_date, d) * funding_mult
        equity = cash + unreal
        peak = max([r["equity"] for r in equity_rows] + [cfg.CAPITAL])
        dd = equity / peak - 1

        # exits
        for sym in list(positions):
            pos = positions[sym]
            row = fday.get(sym, {})
            px = px_now.get(sym)
            reason = None
            if not px:
                reason = "missing_price"
            elif not row or not row.get("data_ok", False):
                reason = "missing_data"
            else:
                pred = row.get("predicted", 0.0)
                pos.neg_streak = pos.neg_streak + 1 if pred < 0 else 0
                if pos.neg_streak >= 2:
                    reason = "fr_negative_2"
                elif pred < 0.5 * row.get("apr7", 0.0):
                    reason = "decay"
                elif row.get("price_move24", 0.0) > 0.15:
                    reason = "price_move"
                elif abs(row.get("basis_z", 0.0)) > 3:
                    reason = "basis_3sigma"
            if reason is None and (d - pos.entry_date).days >= cfg.MAX_HOLD_DAYS:
                reason = "max_hold"
            if reason is None and dd <= -cfg.DD_KILL:
                reason = "dd_kill"
            if reason and px:
                close_pos(positions.pop(sym), d, px)
                cooldown[sym] = d + pd.Timedelta(days=7)

        if dd <= -cfg.DD_KILL:
            killed = True

        # điền slot trống mỗi ngày; không thay vị thế đang giữ nếu chưa có exit
        if not killed:
            cand = fday
            ranked = sorted(
                (
                    (sym, row)
                    for sym, row in cand.items()
                    if row.get("pass_all")
                    and sym not in positions
                    and (sym not in cooldown or cooldown[sym] <= d)
                    and not (truncate and sym in truncate and d >= pd.Timestamp(truncate[sym], tz="UTC"))
                ),
                key=lambda x: -x[1].get("score", 0),
            )
            for sym, row in ranked:
                if len(positions) >= cfg.COINS:
                    break
                px = _price_at(prices, sym, d)
                if px:
                    enter(sym, d, px, row)

        # shock
        if basis_shock and di == shock_day and positions:
            loss = sum(p.notional for p in positions.values()) * basis_shock
            cash -= loss
            price_total -= loss

        # final mark
        unreal = 0.0
        for sym, pos in positions.items():
            px = _price_at(prices, sym, d)
            if not px:
                continue
            perp, spot = px
            unreal += pos.qty_spot * (spot - pos.spot0) + pos.qty_perp * (pos.perp0 - perp)
            unreal += pos.notional * _funding_sum(farr, sym, pos.entry_date, d) * funding_mult
        equity = cash + unreal
        equity_rows.append({"date": d, "equity": equity, "positions": len(positions), "killed": killed})
        pos_rows.append({"date": d, "positions": len(positions), "symbols": ",".join(sorted(positions))})

    # close all at end
    for sym in list(positions):
        d = dates[-1]
        px = _price_at(prices, sym, d)
        if px:
            close_pos(positions.pop(sym), d, px)
        equity_rows[-1]["equity"] = cash

    eq = pd.DataFrame(equity_rows).set_index("date")["equity"]
    ep = pd.DataFrame(episodes)
    daily_pos = pd.DataFrame(pos_rows).set_index("date")["positions"]
    metrics = _metrics(eq, ep, daily_pos, fees, funding_total, price_total)
    return Result(eq, ep, daily_pos.to_frame(), metrics)


def _metrics(eq: pd.Series, ep: pd.DataFrame, daily_pos: pd.Series, fees: float, funding: float, price: float) -> dict:
    days = max(1, (eq.index[-1] - eq.index[0]).days)
    final = float(eq.iloc[-1])
    total = final / cfg.CAPITAL - 1
    apr = (final / cfg.CAPITAL) ** (365 / days) - 1 if final > 0 else -1
    peak = eq.cummax()
    dd = (eq / peak - 1).min()
    me = eq.resample("ME").last()
    monthly = me.pct_change()
    if len(monthly):
        monthly.iloc[0] = me.iloc[0] / cfg.CAPITAL - 1
        monthly = monthly.dropna()
    pos_share = float((daily_pos > 0).mean()) if len(daily_pos) else 0.0
    avg_pos = float(daily_pos.mean()) if len(daily_pos) else 0.0
    hit = float((ep["pnl"] > 0).mean()) if len(ep) else 0.0
    turnover = float(ep["notional"].sum()) / float(eq.mean()) * 365 / days if len(ep) else 0.0
    drag = fees / float(eq.mean()) * 365 / days if len(eq) else 0.0
    be = ep["cost"] / (ep["funding_pnl"] / ep["hold_days"].clip(lower=1)) if len(ep) else pd.Series(dtype=float)
    be = be[(be > 0) & np.isfinite(be)]
    return {
        "final_equity": round(final, 4),
        "total_return": round(total, 4),
        "apr": round(apr, 4),
        "max_dd": round(float(dd), 4),
        "monthly_returns": [round(float(x), 4) for x in monthly.tolist()],
        "positive_month_ratio": round(float((monthly > 0).mean()), 4) if len(monthly) else 0.0,
        "deployment_rate": round(pos_share, 4),
        "avg_positions": round(avg_pos, 2),
        "episodes": int(len(ep)),
        "hit_rate": round(hit, 4),
        "turnover": round(turnover, 2),
        "fee_drag_apr": round(drag, 4),
        "funding_pnl": round(float(funding), 4),
        "price_pnl": round(float(price), 4),
        "fees": round(float(fees), 4),
        "break_even_days": round(float(be.mean()), 2) if len(be) else None,
    }
