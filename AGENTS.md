# AGENTS.md — Funding Harvest Bot

## 1. Lệnh chạy & verify

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
python -m compileall -q src scripts backtest
python scripts\check_connection.py
python -m backtest.data        # cache 6 tháng (chỉ lần đầu)
python -m backtest.run_phase1  # backtest + stress + P1 tests
```

- Python 3.12; dependency `httpx`, `python-dotenv`, `PyYAML`, `pandas`, `numpy`, `pyarrow`.
- **Không có pytest/lint/typecheck.** `check_connection.py` + `backtest.run_phase1` là verification.
- Chạy live mặc định; demo: `$env:BINANCE_USE_DEMO='true'; python scripts\check_connection.py`.
- Phase 0 **không tạo `tests/`/`ui/`**; Phase 1 chỉ tạo `backtest/` (không tạo src runtime, ui).

## 2. Cấu trúc thật

- `src/config.py` — `Settings`: đọc `config/settings.yaml` + `.env` (`load_dotenv`, `override=False`). Entry `get_settings()`.
- `src/binance/client.py` — `BinanceClient`: REST Spot + USDⓈ-M Futures, HMAC SHA256, tự sync giờ server, guard ghi.
- `src/binance/checks.py` — `run_checks(settings)`: chỉ đọc, không gửi lệnh/rút tiền.
- `scripts/check_connection.py` — in cấu hình + public/private + warnings/errors; exit 1 nếu lỗi.
- `config/settings.yaml` — tham số chiến lược $500/1x/3 coin. `.env` chỉ override 7 biến trong `_ENV_OVERRIDES`; key/flag an toàn đọc trực tiếp bằng `env()`/`env_bool()`.
- `src/{ingest,allocator,risk,executor,reconciler,watchdog,report}/` là placeholder rỗng — không viết code vào đó khi chưa tới phase.
- `backtest/` — Phase 1: `data.py` (ingest public), `strategy.py` (feature/screener/sim), `run_phase1.py` (report + P1 tests). Cache `data/backtest/`, report `reports/phase1/` (gitignored).

## 3. Quy tắc phase (bắt buộc)

`docs/task-trien-khai-funding-rate.md` §0.3 cấm tạo file/thư mục phase chưa tới. Phase 0 chỉ được chạm: `.env`, `config/`, `src/config.py`, `src/binance/{client,checks}.py`, `scripts/check_connection.py`. Phase 1 chỉ `backtest/` (+ `requirements.txt`, docs). **Phase 1 đã fail → không tạo `ui/`, executor, screener** cho tới khi có quyết định mới.

## 4. An toàn tiền & key

- 3 loại key tách biệt: trade (`BINANCE_API_KEY/SECRET`), read-only (`BINANCE_READONLY_KEY/SECRET`), demo (`BINANCE_DEMO_*`).
- Trade key: Reading + Spot & Margin + Futures; **Withdraw luôn OFF**; Universal Transfer chỉ bật Phase 3. Read-only: chỉ Reading. Demo key tạo ở `demo.binance.com/en/my/settings/api-management`.
- Guard: `_write_guard` chặn mọi mutation khi `readonly=True`; `_order_guard` chặn khi `DRY_RUN=true`, live cần `LIVE_TRADING_ENABLED=true`, demo cần `BINANCE_USE_DEMO=true` + `DRY_RUN=false`.
- Live key phải whitelist **cả IP nhà và IP VPS `43.240.117.54`**. Đã whitelist; VPS live OK. Nếu VPS đổi IP, cập nhật lại trên Binance UI (endpoint IP restriction qua API trả 500 “không hỗ trợ” với tài khoản thường).
- Không tin demo read-only: đã gặp trường hợp vẫn đặt được lệnh; luôn dùng guard local và test lại bằng live read-only.
- Không bao giờ gọi endpoint withdraw. Kiểm tra quyền rút bằng `/sapi/v1/account/apiRestrictions` (`enableWithdrawals`).
- `.env` không commit; trên VPS mode `600`, owner `funding`. Không log/print secret, không dán key vào chat.
- BNB burn: `spotBNBBurn=true`, futures `feeBurn=true`; spot thực tế 0,075%, futures API trả base 0,05% (discount áp dụng lúc fill). BNB spot/futures ~0,02 mỗi ví.
- `BINANCE_SPOT_BASE_URL`/`BINANCE_FUTURES_BASE_URL` để trống = tự chọn live/demo. Không dùng URL testnet cũ.
- Demo không hỗ trợ `apiRestrictions`, `spot tradeFee` (404); funding demo là dữ liệu mô phỏng (BTCUSDT flat 0,01%) — không dùng research/backtest.

## 5. PowerShell, UTF-8 & secret (bắt buộc)

- Mọi file repo và `.env`: **UTF-8 không BOM, LF**. BOM/CP1258 làm hỏng tiếng Việt và có thể làm sai key đầu tiên.
- **Không dùng `Set-Content -Encoding utf8` trên PowerShell 5.1** (tạo BOM, decode sai CP1258). Đây là nguyên nhân `.env` bị lỗi comment trước đây.
- Ghi file an toàn:
  - Python: `Path(p).write_text(text, encoding="utf-8", newline="\n")`.
  - PowerShell: `[IO.File]::WriteAllText($p, $t, (New-Object Text.UTF8Encoding($false)))`.
- Sửa `.env` bằng Python regex, giữ nguyên value; không `Get-Content | Set-Content`.
- Pipe script sang SSH: lưu file `.sh` LF, rồi `Get-Content -Raw x.sh | ssh ... "tr -d '\r' | bash -s"`. Không nhúng `$(...)`/quote phức tạp vào lệnh PowerShell.
- Console Windows mặc định cp1258: đặt `$env:PYTHONIOENCODING='utf-8'` hoặc `python -X utf8` khi in tiếng Việt.
- Kiểm tra secret mà không lộ value: chỉ in tên key + `len(value)`; không `cat .env`.

## 6. Quy ước Python

- `from __future__ import annotations`; type hints đầy đủ; docstring/message tiếng Việt có dấu; identifier ASCII.
- Đọc cấu hình qua `Settings` (`get`, `env`, `env_bool`); không gọi `os.getenv` rải rác trong feature code.
- Mọi call signed qua `BinanceClient._signed`; public qua `_get`; không tự viết httpx ở module khác.
- Lỗi sàn: `BinanceAPIError(status_code, code, msg, endpoint)`; giữ `code` và xử lý code cụ thể (`-4046` margin đã đúng, `-2011` unknown order, `-1021` recvWindow, `-2015` key/IP/quyền).
- Thời gian: epoch ms UTC; dùng `datetime.now(timezone.utc)`; DB/log UTC, chỉ convert +7 khi hiển thị.
- Tiền/giá/qty: dùng `Decimal` hoặc string cho order params; không float. Phase 3 round theo `exchangeInfo` (`tickSize`, `stepSize`, `minNotional`).
- Order phải có `newClientOrderId` deterministic; retry phải query trạng thái trước, không retry mù (Phase 3).
- Mọi method mutate (order/cancel/leverage/margin/transfer) phải gọi `_write_guard` hoặc `_order_guard`.
- Không thêm dependency/abstraction mới khi stdlib đủ; không tạo file ngoài phase.

## 7. API facts đã xác minh

- Live: `api.binance.com` / `fapi.binance.com`; Demo: `demo-api.binance.com` / `demo-fapi.binance.com`.
- P0-T02 live read-only: leverage và order đều bị `401 -2015`; local client cũng chặn.
- `recvWindow=10000` trên VPS vì call lạnh có thể >5s; clock offset thực tế ~-44ms.
- `GET /sapi/v1/account/apiRestrictions` trả `enableWithdrawals`, `enableFutures`, `enableSpotAndMarginTrading`, `ipRestrict`.
- Endpoint quản lý IP restriction không dùng được cho tài khoản thường (HTTP 500 `100001002`); thêm IP bằng UI.
- Spot BNB fee thực tế 0,075% (commission asset BNB); futures `feeBurn=true`.
- **Universe delta-neutral phải là giao Spot USDT + Futures perp.** 4 mã tham chiếu Phase 1 (EVAA/AVAAI/PIEVERSE/PHAROS) đều không có Spot → không hedge được. Screen 283 symbol mở rộng hiện tại = 0 ứng viên 20–60% APR; Phase 1 không đạt, dừng trước Phase 2.

## 8. Hạ tầng VPS (dùng chung — cẩn thận)

- VPS `43.240.117.54:24700`, Tailscale `100.98.182.15`; local Tailscale `100.114.108.28`.
- Deploy `/opt/funding-bot`, user `funding` (nologin), `.env` mode 600. Venv `.venv`.
- systemd `funding-heartbeat` (placeholder, `Restart=always`) + `funding-backup.timer` 03:15 UTC; script `/usr/local/sbin/funding-{heartbeat,backup}`. Khi có bot thật, thay `ExecStart`, giữ `Restart=always`.
- VPS chạy chung `cors-prod` (Caddy 80/443, app 1508–1599, MySQL), `binance-demo-server` (127.0.0.1:8081), onedash/vector/vmagent. **Không bật UFW/đóng port**; service mới bind `127.0.0.1` và đi qua Tailscale.
- Sync code: tar loại `.env`/`.git`/`data`/`logs`/`reports`, scp, giải nén; scp `.env` riêng, `chmod 600`, `chown funding:funding`.
- Sau khi đổi `.env`/code: restart service liên quan. `check_connection.py` trên VPS OK; nếu đổi IP VPS phải whitelist lại cả 2 key.

## 9. Trước khi commit

1. `python -m compileall -q src scripts` pass.
2. `python scripts\check_connection.py` → `KẾT LUẬN: OK`.
3. `git grep -nE "[0-9]{9,10}:AA[A-Za-z0-9_-]{30,}"` → 0; `.env` không tracked.
4. `git status --short` không có `.env`, `*.db`, `data/*`, `logs/*`, `reports/*`.
5. Cập nhật kết quả vào `docs/task-trien-khai-funding-rate.md`; commit/push `origin/main`, message ngắn, không secret.
