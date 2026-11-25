"""Thu dữ liệu public Binance cho backtest Phase 1.

Chỉ đọc public API, không dùng key. Cache Parquet trong data/backtest/.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from backtest import config as cfg

OUT = cfg.DATA_DIR
CACHE = OUT / "cache"
FAPI = "https://fapi.binance.com"
SAPI = "https://api.binance.com"


class BinancePublic:
    def __init__(self) -> None:
        self.http = httpx.Client(
            timeout=30,
            headers={"User-Agent": "funding-backtest/1.0"},
        )
        self.calls = 0

    def close(self) -> None:
        self.http.close()

    def get(self, base: str, path: str, params: dict[str, Any] | None = None) -> Any:
        delay = 1.0
        for attempt in range(6):
            try:
                r = self.http.get(base + path, params=params or {})
                self.calls += 1
                if r.status_code in (418, 429):
                    time.sleep(min(60, delay * 4))
                    delay *= 2
                    continue
                if r.status_code >= 500:
                    time.sleep(delay)
                    delay *= 2
                    continue
                r.raise_for_status()
                time.sleep(0.08)
                return r.json()
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 5:
                    raise
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(f"Binance request failed: {path}")

    def funding(self, symbol: str) -> list[dict]:
        rows: list[dict] = []
        start = cfg.START_MS
        while start < cfg.END_MS:
            batch = self.get(
                FAPI,
                "/fapi/v1/fundingRate",
                {"symbol": symbol, "startTime": start, "endTime": cfg.END_MS, "limit": 1000},
            )
            if not batch:
                break
            rows.extend(batch)
            last = max(int(x["fundingTime"]) for x in batch)
            if len(batch) < 1000 or last <= start:
                break
            start = last + 1
        return rows

    def klines(self, base: str, path: str, symbol: str) -> list[list]:
        rows: list[list] = []
        start = cfg.START_MS
        while start < cfg.END_MS:
            batch = self.get(
                base,
                path,
                {"symbol": symbol, "interval": cfg.INTERVAL, "startTime": start, "endTime": cfg.END_MS, "limit": 1500},
            )
            if not batch:
                break
            rows.extend(batch)
            last = int(batch[-1][0])
            if len(batch) < 1500 or last <= start:
                break
            start = last + 1
        return rows

    def depth_slippage(self, symbol: str, notional: float) -> tuple[float, float]:
        try:
            d = self.get(FAPI, "/fapi/v1/depth", {"symbol": symbol, "limit": 100})
            bids = [(float(p), float(q)) for p, q in d.get("bids", [])]
            asks = [(float(p), float(q)) for p, q in d.get("asks", [])]
            if not bids or not asks:
                return 0.1, 0.1
            mid = (bids[0][0] + asks[0][0]) / 2
            buy = _vwap(asks, notional)
            sell = _vwap(bids, notional)
            return (
                max(0.0, (buy / mid - 1) * 100),
                max(0.0, (1 - sell / mid) * 100),
            )
        except Exception:  # noqa: BLE001
            return 0.1, 0.1

    def oi_hist(self, symbol: str) -> list[dict]:
        try:
            return self.get(
                FAPI,
                "/futures/data/openInterestHist",
                {"symbol": symbol, "period": "1h", "limit": 500},
            )
        except Exception:  # noqa: BLE001
            return []


def _vwap(levels: list[tuple[float, float]], notional: float) -> float:
    remaining = notional
    cost = 0.0
    qty = 0.0
    for price, size in levels:
        take = min(remaining, price * size)
        cost += take
        qty += take / price
        remaining -= take
        if remaining <= 0:
            break
    return cost / qty if qty > 0 else levels[0][0]


def _filters(info: dict) -> dict[str, float]:
    out = {"min_notional": 5.0, "step_size": 1e-8, "tick_size": 1e-8}
    for f in info.get("filters", []):
        t = f.get("filterType")
        if t in ("MIN_NOTIONAL", "NOTIONAL"):
            out["min_notional"] = float(f.get("minNotional") or f.get("notional") or 5)
        elif t == "LOT_SIZE":
            out["step_size"] = float(f.get("stepSize") or 1e-8)
        elif t == "PRICE_FILTER":
            out["tick_size"] = float(f.get("tickSize") or 1e-8)
    return out


def select_universe(client: BinancePublic) -> tuple[list[dict], dict]:
    finfo = client.get(FAPI, "/fapi/v1/exchangeInfo")
    ftick = {x["symbol"]: x for x in client.get(FAPI, "/fapi/v1/ticker/24hr")}
    sinfo = client.get(SAPI, "/api/v3/exchangeInfo")
    stick = {x["symbol"]: x for x in client.get(SAPI, "/api/v3/ticker/24hr")}

    spot = {
        s["symbol"]: s for s in sinfo["symbols"]
        if s.get("status") == "TRADING" and s.get("quoteAsset") == "USDT"
    }
    fut = {
        s["symbol"]: s for s in finfo["symbols"]
        if s.get("contractType") == "PERPETUAL"
        and s.get("status") == "TRADING"
        and s.get("quoteAsset") == "USDT"
    }
    rows = []
    for sym, s in fut.items():
        if sym in cfg.EXCLUDE or sym not in spot:
            continue
        fv = float(ftick.get(sym, {}).get("quoteVolume", 0))
        sv = float(stick.get(sym, {}).get("quoteVolume", 0))
        if fv < cfg.FUT_VOLUME_MIN or sv < cfg.SPOT_VOLUME_MIN:
            continue
        ff = _filters(s)
        sf = _filters(spot[sym])
        rows.append({
            "symbol": sym,
            "fut_quote_volume": fv,
            "spot_quote_volume": sv,
            "last_price": float(ftick[sym]["lastPrice"]),
            "fut_min_notional": ff["min_notional"],
            "fut_step_size": ff["step_size"],
            "spot_min_notional": sf["min_notional"],
            "spot_step_size": sf["step_size"],
        })
    rows.sort(key=lambda x: -x["fut_quote_volume"])
    rows = rows[: cfg.UNIVERSE_TOP_N]

    refs = {}
    for sym in cfg.REF_SYMBOLS:
        refs[sym] = {
            "in_futures": sym in fut,
            "in_spot": sym in spot,
            "fut_volume": float(ftick.get(sym, {}).get("quoteVolume", 0)),
            "spot_volume": float(stick.get(sym, {}).get("quoteVolume", 0)),
        }
    meta = {"futures_perp": len(fut), "spot_usdt": len(spot), "selected": len(rows), "references": refs}
    return rows, meta


def _kline_frame(symbol: str, rows: list[list], market: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    df["symbol"] = symbol
    df["market"] = market
    for c in ("open", "high", "low", "close", "volume", "quote_volume", "taker_buy_quote"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce").astype("int64")
    df["dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df[["symbol", "market", "open_time", "dt", "open", "high", "low", "close", "volume", "quote_volume", "taker_buy_quote"]]


def _cache_dir(symbol: str) -> Path:
    return CACHE / symbol.replace("/", "_")


def _save_symbol(symbol: str, meta: dict, funding: pd.DataFrame, klines: pd.DataFrame,
                 premium: pd.DataFrame | None, spot: pd.DataFrame, oi: pd.DataFrame) -> None:
    d = _cache_dir(symbol)
    d.mkdir(parents=True, exist_ok=True)
    if not funding.empty:
        funding.to_parquet(d / "funding.parquet", index=False)
    if not klines.empty:
        klines.to_parquet(d / "klines.parquet", index=False)
    if premium is not None and not premium.empty:
        premium.to_parquet(d / "premium.parquet", index=False)
    if not spot.empty:
        spot.to_parquet(d / "spot.parquet", index=False)
    if not oi.empty:
        oi.to_parquet(d / "oi.parquet", index=False)
    (d / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_symbol(symbol: str) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame] | None:
    d = _cache_dir(symbol)
    mp = d / "meta.json"
    if not mp.exists():
        return None

    def rd(name: str) -> pd.DataFrame:
        p = d / f"{name}.parquet"
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()

    return (
        json.loads(mp.read_text(encoding="utf-8")),
        rd("funding"), rd("klines"), rd("premium"), rd("spot"), rd("oi"),
    )


def ingest() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    client = BinancePublic()
    warnings: list[str] = []
    try:
        universe, meta = select_universe(client)

        funding_rows, k_rows, p_rows, s_rows, oi_rows = [], [], [], [], []
        resume = os.getenv("BT_RESUME", "1") != "0"
        for i, u in enumerate(universe, 1):
            sym = u["symbol"]
            cached = _load_symbol(sym) if resume else None
            if cached and cached[0].get("_days") == cfg.DAYS:
                cu, cf, ck, cp, cs, co = cached
                u.update({k: v for k, v in cu.items() if not k.startswith("_")})
                if not cf.empty:
                    funding_rows += cf.to_dict("records")
                if not ck.empty:
                    k_rows.append(ck)
                if not cp.empty:
                    p_rows.append(cp)
                if not cs.empty:
                    s_rows.append(cs)
                if not co.empty:
                    oi_rows += co.to_dict("records")
                warnings.extend(cu.get("_warnings", []))
                if i % 10 == 0 or i == len(universe):
                    print(f"cached {i}/{len(universe)} {sym}", flush=True)
                continue
            try:
                f = client.funding(sym)
                fdf = pd.DataFrame([
                    {"symbol": sym, "fundingTime": int(x["fundingTime"]), "fundingRate": float(x["fundingRate"])}
                    for x in f
                ])
                funding_rows += fdf.to_dict("records")
                kdf = _kline_frame(sym, client.klines(FAPI, "/fapi/v1/klines", sym), "futures")
                k_rows.append(kdf)
                p = client.klines(FAPI, "/fapi/v1/premiumIndexKlines", sym)
                pdf = None
                if p:
                    pdf = pd.DataFrame(p).iloc[:, :6]
                    pdf.columns = ["open_time", "open", "high", "low", "close", "ignore"]
                    pdf["symbol"] = sym
                    pdf["open_time"] = pd.to_numeric(pdf["open_time"]).astype("int64")
                    pdf["dt"] = pd.to_datetime(pdf["open_time"], unit="ms", utc=True)
                    for c in ("open", "high", "low", "close"):
                        pdf[c] = pd.to_numeric(pdf[c], errors="coerce")
                    pdf = pdf[["symbol", "open_time", "dt", "open", "high", "low", "close"]]
                    p_rows.append(pdf)
                sdf = _kline_frame(sym, client.klines(SAPI, "/api/v3/klines", sym), "spot")
                s_rows.append(sdf)
                buy_slip, sell_slip = client.depth_slippage(sym, cfg.NOTIONAL_PER_COIN)
                slip = max(buy_slip, sell_slip)
                u["slippage_pct"] = round(slip, 4)
                u["slippage_buy_pct"] = round(buy_slip, 4)
                u["slippage_sell_pct"] = round(sell_slip, 4)
                odf = pd.DataFrame([
                    {
                        "symbol": sym,
                        "time": int(x["timestamp"]),
                        "oi": float(x["sumOpenInterest"]),
                        "oi_value": float(x["sumOpenInterestValue"]),
                    }
                    for x in client.oi_hist(sym)
                ])
                if not odf.empty:
                    oi_rows += odf.to_dict("records")
                w = []
                if fdf.empty:
                    w.append(f"{sym}: no funding")
                if not sdf.empty and len(sdf) < 900:
                    w.append(f"{sym}: spot klines only {len(sdf)}")
                u["_warnings"] = w
                u["_days"] = cfg.DAYS
                warnings += w
                _save_symbol(sym, u, fdf, kdf, pdf, sdf, odf)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{sym}: {exc}")
            if i % 10 == 0 or i == len(universe):
                print(f"ingest {i}/{len(universe)} {sym} calls={client.calls}", flush=True)
        for u in universe:
            u.pop("_warnings", None)
            u.pop("_days", None)
        pd.DataFrame(universe).to_parquet(OUT / "universe.parquet", index=False)
    finally:
        client.close()

    funding = pd.DataFrame(funding_rows)
    if not funding.empty:
        funding = funding.sort_values(["symbol", "fundingTime"]).drop_duplicates(["symbol", "fundingTime"])
        g = funding.groupby("symbol")["fundingTime"]
        funding["interval_hours"] = g.diff().div(3600000).fillna(8.0)
        funding.loc[funding["interval_hours"] <= 0, "interval_hours"] = 8.0
        funding["dt"] = pd.to_datetime(funding["fundingTime"], unit="ms", utc=True)
        funding.to_parquet(OUT / "funding.parquet", index=False)

    pd.concat([x for x in k_rows if not x.empty], ignore_index=True).to_parquet(OUT / "klines.parquet", index=False)
    if p_rows:
        pd.concat(p_rows, ignore_index=True).to_parquet(OUT / "premium.parquet", index=False)
    pd.concat([x for x in s_rows if not x.empty], ignore_index=True).to_parquet(OUT / "spot_klines.parquet", index=False)
    if oi_rows:
        pd.DataFrame(oi_rows).to_parquet(OUT / "oi.parquet", index=False)

    meta.update({
        "calls": client.calls,
        "funding_rows": int(len(funding)),
        "warnings": warnings,
        "start": cfg.START.isoformat(),
        "end": cfg.END.isoformat(),
    })
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print("done", meta["selected"], "symbols", meta["calls"], "calls", len(warnings), "warnings", flush=True)
    return meta


if __name__ == "__main__":
    ingest()
