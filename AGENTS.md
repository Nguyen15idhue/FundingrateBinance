# AGENTS.md — Funding Harvest Bot (Phase 0)

## Lệnh chạy
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
python scripts\check_connection.py
python -m compileall -q src scripts
```
- Không có pytest/lint/typecheck. `check_connection.py` là verification duy nhất hiện tại.
- Chạy trên Windows PowerShell; dùng `\` trong path.

## Cấu trúc thật
- `src/config.py` — `Settings`: đọc `config/settings.yaml` + `.env` (qua `load_dotenv`, `override=False`). Entry: `get_settings()`.
- `src/binance/client.py` — `BinanceClient`: REST Spot + USDⓈ-M Futures bằng `httpx`, ký HMAC SHA256. Entry cho mọi call sàn.
- `src/binance/checks.py` — `run_checks(settings)`: chỉ đọc, không gửi lệnh/rút tiền.
- `scripts/check_connection.py` — in cấu hình + public/private + warnings/errors, exit 1 nếu lỗi.
- `config/settings.yaml` — tham số chiến lược ($500/1x/3 coin). `.env` chỉ override 7 biến trong `_ENV_OVERRIDES` (`src/config.py:67-75`); các key/flag an toàn đọc trực tiếp qua `env()`/`env_bool()`.
- `src/{ingest,allocator,risk,executor,reconciler,watchdog,report}/` hiện là placeholder rỗng — **không viết code vào đó** (xem quy tắc phase).

## Quy tắc phase (bắt buộc)
`docs/task-trien-khai-funding-rate.md` §0.3 cấm tạo file/thư mục của phase chưa tới. Hiện tại Phase 0 chỉ được chạm: `.env`, `config/`, `src/config.py`, `src/binance/{client,checks}.py`, `scripts/check_connection.py`. Không tạo `ui/`, `tests/`, executor, screener.

## An toàn tiền + key
- Không bao giờ commit `.env` (đã gitignore). Không log/print secret.
- 3 loại key tách biệt: trade (`BINANCE_API_KEY/SECRET`), read-only (`BINANCE_READONLY_KEY/SECRET`), demo (`BINANCE_DEMO_API_KEY/SECRET` + `BINANCE_DEMO_READONLY_*`).
- Key trade: bật Reading + Spot & Margin Trading + Futures; **Withdraw luôn OFF**; Universal Transfer chỉ bật ở Phase 3. Key read-only: chỉ Reading. Key demo tạo ở `demo.binance.com/en/my/settings/api-management`.
- Guard gửi lệnh (`_order_guard` / `_write_guard` trong `client.py`): `readonly=True` chặn mọi lệnh/leverage/transfer ngay tại client; `DRY_RUN=true` → chặn; live cần `LIVE_TRADING_ENABLED=true`; demo cần `BINANCE_USE_DEMO=true` + `DRY_RUN=false`. Mặc định an toàn: `DRY_RUN=true`, `LIVE=false`.
- **Demo read-only key có thể vẫn trade được ở phía Binance** (đã gặp P0-T02) → không tin quyền của demo key; luôn dùng guard local và phải test lại bằng live read-only key.
- `BINANCE_SPOT_BASE_URL` / `BINANCE_FUTURES_BASE_URL` để trống = tự chọn live (`api`/`fapi.binance.com`) hay demo (`demo-api`/`demo-fapi.binance.com`). Chỉ điền khi override (VD bị chặn DNS).
- Không dùng URL testnet cũ (`testnet.binance.vision`, `testnet.binancefuture.com`).
- `checks.py` không bao giờ gọi endpoint rút tiền; `apiRestrictions` báo error cứng nếu `enableWithdrawals=true`.

## Quy ước code hiện tại
- `from __future__ import annotations`, type hints đầy đủ, docstring tiếng Việt ngắn.
- Lỗi sàn: raise `BinanceAPIError(status_code, code, msg, endpoint)`; giữ `code` (VD `-4046` = margin type đã đúng thì bỏ qua ở `set_margin_type`).
- Giờ server: `_server_offset()` cache theo market, cộng vào `timestamp`; cảnh báo nếu lệch > 1000ms, latency > 2000ms.
- Client là context manager (`with` hoặc `.close()`); `readonly=True` chọn key read-only; `demo=True/None` chọn key demo theo `BINANCE_USE_DEMO`.
- `Settings.validate()` là lỗi cứng: `spot+futures==total`, `margin+buffer==futures`, `margin==notional_per_leg` (1x), `leverage==1`, `max_order_notional_usd>0`. `warnings()` không chặn chạy.
- `TZ`, `DATABASE_URL`, `LOG_LEVEL` trong `.env` hiện chưa được code đọc — đừng dựa vào chúng.
- Endpoint private: account/position/fee/restrictions là GET signed; đặt leverage/marginType/transfer/order là POST signed với `X-MBX-APIKEY`.

## Hạ tầng VPS (dùng chung — cẩn thận)
- VPS `43.240.117.54:24700` (Ubuntu 24.04), deploy tại `/opt/funding-bot`, chạy bằng user `funding` (system user, nologin).
- VPS đang chạy chung `cors-prod` (Caddy 80/443, app 1508–1599, MySQL), `binance-demo-server` (127.0.0.1:8081), onedash/vector/vmagent. **Không bật UFW/đóng port** để tránh sập dịch vụ khác; service mới phải bind `127.0.0.1` và đi qua Tailscale.
- systemd: `funding-heartbeat` (placeholder, `Restart=always`) và `funding-backup.timer` 03:15 UTC; script `/usr/local/sbin/funding-{heartbeat,backup}`. Khi có bot thật, thay `ExecStart`, giữ `Restart=always`.
- `.env` trên VPS mode 600; hiện `BINANCE_USE_DEMO=true`, chưa có live key.
- Tailscale đã cài trên VPS nhưng chưa đăng nhập; Telegram bot có token nhưng chưa có `chat_id`.

## Verify trước khi xong
1. `python -m compileall -q src scripts` phải pass.
2. `python scripts\check_connection.py` phải `KẾT LUẬN: OK`. Public chạy được không cần key; private cần key đúng.
3. `git status --short` không hiện `.env`, `*.db`, `data/*`, `logs/*`, `reports/*`.
