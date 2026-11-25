"""Kiểm tra kết nối, quyền API, số dư, phí, margin — dùng cho Phase 0.

Không bao giờ gọi endpoint rút tiền. Chỉ đọc.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from src.binance.client import BinanceAPIError, BinanceClient
from src.config import Settings


@dataclass
class CheckReport:
    public: dict[str, Any] = field(default_factory=dict)
    private: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _pct(value: Any) -> float:
    try:
        return float(value) * 100.0
    except (TypeError, ValueError):
        return 0.0


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def run_checks(settings: Settings) -> CheckReport:
    report = CheckReport()
    client = BinanceClient(settings)
    if settings.use_demo:
        report.warnings.append(
            "Đang chạy DEMO Trading (ví ảo) — số dư/fill không phải tiền thật."
        )

    # ---------- public ----------
    try:
        started = time.perf_counter()
        server = client.server_time("futures")
        latency_ms = (time.perf_counter() - started) * 1000
        offset_ms = int(server["serverTime"]) - int(time.time() * 1000)
        report.public["server_time"] = server["serverTime"]
        report.public["latency_ms"] = round(latency_ms, 1)
        report.public["clock_offset_ms"] = offset_ms
        if abs(offset_ms) > 1000:
            report.warnings.append(f"Lệch giờ {offset_ms} ms (>1000 ms) — kiểm tra NTP.")
        if latency_ms > 2000:
            report.warnings.append(f"Latency futures {latency_ms:.0f} ms (>2000 ms).")
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"Không gọi được /fapi/v1/time: {exc}")

    try:
        premium = client.premium_index()
        report.public["premium_symbols"] = len(premium) if isinstance(premium, list) else 1
        btc = next((p for p in premium if p.get("symbol") == "BTCUSDT"), None) if isinstance(premium, list) else premium
        if btc:
            report.public["btc_last_funding_pct"] = _pct(btc.get("lastFundingRate"))
            report.public["btc_next_funding_time"] = btc.get("nextFundingTime")
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"Không đọc được premiumIndex: {exc}")

    try:
        info = client.exchange_info()
        symbols = info.get("symbols", [])
        perpetual = [
            s for s in symbols
            if s.get("contractType") == "PERPETUAL"
            and s.get("status") == "TRADING"
            and s.get("quoteAsset") == "USDT"
        ]
        report.public["usdt_perpetual_symbols"] = len(perpetual)
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"Không đọc được exchangeInfo: {exc}")

    try:
        rates = client.funding_rate("BTCUSDT", limit=3)
        report.public["btc_funding_history"] = [
            {
                "time": r.get("fundingTime"),
                "rate_pct": _pct(r.get("fundingRate")),
            }
            for r in rates
        ]
    except Exception as exc:  # noqa: BLE001
        report.warnings.append(f"Không đọc được fundingRate BTCUSDT: {exc}")

    # ---------- private ----------
    if not client.has_keys:
        report.warnings.append("Chưa có API key — bỏ qua kiểm tra private.")
        client.close()
        return report

    # Futures account
    try:
        account = client.account_futures()
        assets = [
            {
                "asset": a.get("asset"),
                "wallet": _f(a.get("walletBalance")),
                "available": _f(a.get("availableBalance")),
            }
            for a in account.get("assets", [])
            if _f(a.get("walletBalance")) > 0
        ]
        report.private["futures_wallet_usd"] = _f(account.get("totalWalletBalance"))
        report.private["futures_available_usd"] = _f(account.get("availableBalance"))
        report.private["futures_assets"] = assets
        expected = float(settings.get("capital.futures_usd", 265))
        if not settings.use_demo and abs(
            report.private["futures_wallet_usd"] - expected
        ) > max(1.0, expected * 0.02):
            report.warnings.append(
                f"Futures wallet {report.private['futures_wallet_usd']:.2f} "
                f"lệch kỳ vọng {expected:.2f} (>2%)."
            )
    except BinanceAPIError as exc:
        report.errors.append(f"account_futures: {exc}")
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"account_futures lỗi: {exc}")

    # Spot account
    try:
        account = client.account_spot()
        balances = [
            {
                "asset": b.get("asset"),
                "free": _f(b.get("free")),
                "locked": _f(b.get("locked")),
            }
            for b in account.get("balances", [])
            if _f(b.get("free")) + _f(b.get("locked")) > 0
        ]
        report.private["spot_balances"] = balances
        usdt = next((b for b in balances if b["asset"] == "USDT"), None)
        report.private["spot_usdt"] = usdt["free"] if usdt else 0.0
        expected_spot = float(settings.get("capital.spot_usd", 235))
        if not settings.use_demo and usdt and abs(
            usdt["free"] - expected_spot
        ) > max(1.0, expected_spot * 0.02):
            report.warnings.append(
                f"Spot USDT {usdt['free']:.2f} lệch kỳ vọng {expected_spot:.2f} (>2%)."
            )
    except BinanceAPIError as exc:
        report.errors.append(f"account_spot: {exc}")
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"account_spot lỗi: {exc}")

    # API permissions
    try:
        restrictions = client.api_restrictions()
        report.private["api_restrictions"] = {
            "enable_withdrawals": restrictions.get("enableWithdrawals"),
            "enable_futures": restrictions.get("enableFutures"),
            "enable_spot": restrictions.get("enableSpotAndMarginTrading"),
            "ip_restrict": restrictions.get("ipRestrict"),
        }
        if restrictions.get("enableWithdrawals"):
            report.errors.append("API KEY ĐANG BẬT WITHDRAW — phải tắt ngay.")
        if restrictions.get("enableFutures") is False:
            report.errors.append("API key chưa bật quyền Futures.")
    except BinanceAPIError as exc:
        report.warnings.append(f"Không đọc được apiRestrictions: {exc}")
    except Exception as exc:  # noqa: BLE001
        report.warnings.append(f"apiRestrictions lỗi: {exc}")

    # Fees
    try:
        commission = client.commission_rate("BTCUSDT")
        report.private["futures_fee_pct"] = {
            "maker": _pct(commission.get("makerCommissionRate")),
            "taker": _pct(commission.get("takerCommissionRate")),
        }
    except BinanceAPIError as exc:
        report.warnings.append(f"Không đọc được commissionRate: {exc}")

    try:
        fees = client.spot_trade_fee("BTCUSDT")
        report.private["spot_fee_pct"] = fees
    except BinanceAPIError as exc:
        report.warnings.append(f"Không đọc được spot tradeFee: {exc}")

    # Positions (nếu có)
    try:
        positions = client.position_risk()
        open_positions = []
        for p in positions:
            amt = _f(p.get("positionAmt"))
            if abs(amt) > 0:
                open_positions.append(
                    {
                        "symbol": p.get("symbol"),
                        "amt": amt,
                        "leverage": p.get("leverage"),
                        "margin_type": p.get("marginType"),
                        "liquidation_price": _f(p.get("liquidationPrice")),
                        "unrealized": _f(p.get("unRealizedProfit")),
                    }
                )
        report.private["open_positions"] = open_positions
        if open_positions:
            for p in open_positions:
                if str(p["margin_type"]).lower() not in {"cross", "crossed"}:
                    report.warnings.append(
                        f"{p['symbol']} đang {p['margin_type']} — phải là CROSS."
                    )
                if int(_f(p["leverage"], 0)) != 1:
                    report.warnings.append(
                        f"{p['symbol']} leverage {p['leverage']}x — kế hoạch yêu cầu 1x."
                    )
    except BinanceAPIError as exc:
        report.warnings.append(f"Không đọc được positionRisk: {exc}")

    # Time offset (lần nữa, sau khi cache)
    try:
        offset = client._server_offset("futures")  # noqa: SLF001
        report.private["futures_clock_offset_ms"] = offset
        if abs(offset) > 1000:
            report.warnings.append(f"Lệch giờ futures {offset} ms — kiểm tra NTP.")
    except Exception:  # noqa: BLE001
        pass

    client.close()
    return report
