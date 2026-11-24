# Funding Harvest — khung dự án

Khung tối thiểu để điền key Binance và kiểm tra kết nối. **Chưa có bot giao dịch, chưa gửi lệnh.**

## Có gì trong đây

```text
.env                  # điền key Binance tại đây
.env.example
config/settings.yaml  # tham số $500 / 1x / 3 coin
src/
├── config.py         # đọc .env + YAML
├── binance/
│   ├── client.py     # REST client Spot + Futures
│   └── checks.py     # kiểm tra quyền, số dư, phí
├── ingest/           # Phase 2 (trống)
├── allocator/        # Phase 3 (trống)
├── risk/             # Phase 3 (trống)
├── executor/         # Phase 3 (trống)
├── reconciler/       # Phase 3 (trống)
├── watchdog/         # Phase 3 (trống)
└── report/           # Phase 5 (trống)
scripts/check_connection.py
data/ logs/ reports/ backtest/
```

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Điền key

Mở `.env`, điền:

- `BINANCE_API_KEY` / `BINANCE_API_SECRET`: key giao dịch, bật **Spot + USDⓈ-M Futures**, **tắt Withdraw**, whitelist IP.
- `BINANCE_READONLY_KEY` / `BINANCE_READONLY_SECRET`: key chỉ đọc (không bắt buộc để test).
- `BINANCE_TESTNET_API_KEY` / `BINANCE_TESTNET_API_SECRET`: nếu test trên testnet.

Mặc định an toàn: `DRY_RUN=true`, `LIVE_TRADING_ENABLED=false`.

## Chạy kiểm tra

```powershell
python scripts\check_connection.py
```

Script sẽ báo:

- Kết nối futures, lệch giờ, latency
- Số symbol perpetual USDT
- Funding BTC gần nhất
- Số dư Spot / Futures so với kỳ vọng $235 / $265
- Quyền API (cảnh báo nếu Withdraw đang bật)
- Phí maker/taker
- Vị thế đang mở (nếu có) + leverage/margin type

Không có key vẫn chạy được phần public.

## Ghi chú

- Không commit `.env`.
- Không dùng key có quyền rút.
- Các phase tiếp theo làm theo `docs/task-trien-khai-funding-rate.md`.
