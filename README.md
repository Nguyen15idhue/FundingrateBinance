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

Mở `.env`, điền **3 loại key tách biệt**:

| Key | Dùng cho | Quyền bật | Tuyệt đối không bật |
|---|---|---|---|
| **Trade** (`BINANCE_API_KEY/SECRET`) | executor đặt/hủy lệnh, transfer buffer | Reading, Spot & Margin Trading, Futures; Universal Transfer **chỉ khi** bật buffer manager | Withdraw |
| **Read-only** (`BINANCE_READONLY_KEY/SECRET`) | monitor, reconciler, dashboard độc lập | Reading | Spot/Futures trading, Withdraw, Universal Transfer |
| **Demo** (`BINANCE_DEMO_API_KEY/SECRET`) | chạy thử toàn luồng trên ví ảo | Reading, Spot, Futures | Không liên quan tiền thật |

Cách tạo:

1. **Trade key**: đăng nhập binance.com → avatar → **Account → API Management** → **Create API** → chọn **System generated** (HMAC; code dùng HMAC SHA256) → xác nhận 2FA/email → bật đúng quyền như bảng → **Restrict access to trusted IPs only** và nhập IP VPS → lưu secret (chỉ hiện 1 lần).
2. **Read-only key**: làm lại bước trên, chỉ bật **Enable Reading**, cùng whitelist IP.
3. **Demo key**: đăng nhập binance.com → **Trade → Demo Trading** (hoặc demo.binance.com) → avatar → **API Management** (`demo.binance.com/en/my/settings/api-management`) → **Create API** → bật Reading + Spot + Futures. Đặt `BINANCE_USE_DEMO=true` để client tự dùng `demo-api.binance.com` / `demo-fapi.binance.com`.

Mặc định an toàn: `DRY_RUN=true`, `LIVE_TRADING_ENABLED=false`. Khi chạy demo: `BINANCE_USE_DEMO=true`, `DRY_RUN=false`, **giữ** `LIVE_TRADING_ENABLED=false`.

> Demo Trading thay cho testnet cũ. Demo gần như cùng tính năng và dữ liệu sát live, nhưng **không đo được slippage/fill/funding thật** — mục đích là kiểm tra kỹ thuật (order lifecycle, rollback, reconcile).

> Nếu bot chạy trên VPS, whitelist API key phải có **IP VPS `43.240.117.54`** (và IP nhà nếu chạy local). File `.env` phải lưu **UTF-8 không BOM**; không dùng `Set-Content -Encoding utf8` trên PowerShell 5.1 vì sẽ làm hỏng tiếng Việt.


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
