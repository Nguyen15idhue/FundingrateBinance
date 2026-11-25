"""Kiểm tra kết nối Binance — Phase 0.

Chạy:
    python scripts/check_connection.py

Không gửi lệnh, không rút tiền. Chỉ đọc.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.binance.checks import run_checks  # noqa: E402
from src.config import get_settings  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    settings = get_settings()
    errors = settings.validate()

    print("=== CẤU HÌNH ===")
    print(f"Vốn        : ${settings.get('capital.total_usd')}")
    print(
        f"Phân bổ    : spot ${settings.get('capital.spot_usd')} / "
        f"futures ${settings.get('capital.futures_usd')} "
        f"(margin ${settings.get('capital.margin_usd')} + buffer ${settings.get('capital.buffer_usd')})"
    )
    print(
        f"Chiến lược : {settings.get('capital.leverage')}x, "
        f"{settings.get('capital.coins')} coin, notional ${settings.get('capital.notional_per_leg_usd')}/leg"
    )
    print(
        f"An toàn    : DRY_RUN={settings.dry_run} | "
        f"LIVE={settings.live_trading_enabled} | demo={settings.use_demo}"
    )
    print(f"Config     : {'OK' if not errors else 'LỖI'}")
    for err in errors:
        print(f"  - {err}")

    report = run_checks(settings)

    print("\n=== PUBLIC ===")
    public = report.public
    if "server_time" in public:
        print(f"Futures time   : {public['server_time']}")
        print(f"Latency        : {public.get('latency_ms')} ms")
        print(f"Clock offset   : {public.get('clock_offset_ms')} ms")
    print(f"Premium symbols: {public.get('premium_symbols', 'n/a')}")
    print(f"USDT perpetual : {public.get('usdt_perpetual_symbols', 'n/a')}")
    if "btc_last_funding_pct" in public:
        print(f"BTC funding    : {public['btc_last_funding_pct']:.4f}% (last settled)")
    for row in public.get("btc_funding_history", []):
        print(f"  - {row['time']}: {row['rate_pct']:.4f}%")

    print("\n=== PRIVATE ===")
    if not report.private:
        print("(bỏ qua — chưa có key)")
    else:
        private = report.private
        if "futures_wallet_usd" in private:
            print(
                f"Futures wallet : {private['futures_wallet_usd']:.2f} USDT "
                f"(available {private.get('futures_available_usd', 0):.2f})"
            )
        if "spot_usdt" in private:
            print(f"Spot USDT      : {private['spot_usdt']:.2f}")
        if "futures_fee_pct" in private:
            fee = private["futures_fee_pct"]
            print(f"Futures fee    : maker {fee['maker']:.4f}% / taker {fee['taker']:.4f}%")
        if "api_restrictions" in private:
            r = private["api_restrictions"]
            print(
                "API quyền      : "
                f"withdraw={r['enable_withdrawals']} | "
                f"futures={r['enable_futures']} | "
                f"spot={r['enable_spot']} | ip_restrict={r['ip_restrict']}"
            )
        positions = private.get("open_positions", [])
        print(f"Open positions : {len(positions)}")
        for p in positions:
            print(
                f"  - {p['symbol']} amt={p['amt']} lev={p['leverage']} "
                f"margin={p['margin_type']} liq={p['liquidation_price']}"
            )

    if report.warnings:
        print("\n=== WARNINGS ===")
        for warning in report.warnings:
            print(f"  - {warning}")

    print("\n=== ERRORS ===")
    if report.errors:
        for error in report.errors:
            print(f"  - {error}")
    else:
        print("  (không có)")

    if errors:
        print("\nKẾT LUẬN: cấu hình LỖI — sửa trước khi chạy tiếp.")
        return 1
    if report.errors:
        print("\nKẾT LUẬN: có lỗi kết nối/quyền — xem mục ERRORS.")
        return 1
    print("\nKẾT LUẬN: OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
