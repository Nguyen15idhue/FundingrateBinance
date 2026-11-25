# TASK — TRIỂN KHAI HỆ THỐNG HARVEST FUNDING RATE

**Mã task:** TASK-FR-001  
**Phiên bản:** 1.2  
**Ngày tạo:** 24/11/2026  
**Kế hoạch gốc:** `docs/ke-hoach-funding-rate.md` — phiên bản **2.4**  
**Cấu hình chốt:** vốn **$500**, spot $235 / futures $265, perp **1x**, 3 coin, **L3 tự động hoàn toàn có giám sát**  
**Hạ tầng:** **VPS sẵn có**, chạy 24/7, $0; dashboard realtime theo §7.4  
**Người thực hiện:** ____________________  
**Trạng thái tổng:** 🟡 Đang thực hiện Phase 0

---

## 0. QUY ƯỚC

### 0.1 Ký hiệu trạng thái

| Ký hiệu | Nghĩa |
|---|---|
| ⬜ | Chưa chạy |
| 🟡 | Đang chạy / chờ kết quả |
| ✅ | Pass |
| ❌ | Fail — phải sửa và chạy lại |
| ⏭️ | Bỏ qua có lý do (ghi rõ) |
| 🔒 | Blocked — không được qua phase |

### 0.2 Cách ghi kết quả test

- Mỗi test phải có **bằng chứng**: log, ảnh chụp màn hình, commit hash, hoặc file report.
- Không ghi "OK" chung chung. Ghi **số liệu thực tế** so với kỳ vọng.
- Test fail → ghi nguyên nhân, người sửa, ngày sửa, test lại.
- Không chuyển phase khi còn test ❌ chưa đóng.

### 0.3 Quy tắc tạo file theo phase (bắt buộc)

> **Cấm tạo file/thư mục của phase chưa tới.** Chỉ tạo đúng phần của phase hiện tại. File tạm phải ghi rõ và xóa trước khi qua phase.

| Phase | Được tạo | Không được tạo |
|---|---|---|
| 0 | `.env`, `.env.example`, `.gitignore`, `requirements.txt`, `config/`, `src/config.py`, `src/binance/{client,checks}.py`, `scripts/check_connection.py`, thư mục rỗng | ingest, features, screener, executor, ui, tests |
| 1 | `backtest/` | src runtime, ui |
| 2 | `src/ingest`, `src/features`, `src/screener.py`, `ui/` **read-only** | executor, reconciler, watchdog, STOP |
| 3 | `src/allocator`, `src/executor`, `src/risk`, `src/reconciler`, `src/watchdog`, UI positions/PnL/STOP | lịch sử 30/90 ngày |
| 4 | `tests/`, fixtures | feature mới |
| 5+ | report/history | thay đổi kiến trúc |

> **UI chỉ bắt đầu ở Phase 2.** Phase 0–1 không tạo `ui/`; Phase 2 chỉ read-only; STOP chỉ xuất hiện ở Phase 3.

### 0.4 Bảng tiến độ tổng

| Phase | Tên | Thời lượng dự kiến | Trạng thái | Bắt đầu | Kết thúc | Ghi chú |
|---|---|---|---|---|---|---|
| 0 | Chuẩn bị tài khoản & môi trường | 2–3 ngày | 🟡 | | | Hạ tầng OK; chờ live key/alert/Tailscale |
| 1 | B0 — Thu dữ liệu & backtest $500/1x | 5–7 ngày | ⬜ | | | |
| 2 | B1a — Ingest + Feature + Screener + UI read-only | 4–6 ngày | ⬜ | | | |
| 3 | B1b — Executor + Reconciler + Watchdog + UI STOP | 6–8 ngày | ⬜ | | | |
| 4 | B1c — Demo Trading + Dry-run 7 ngày | 7–10 ngày | ⬜ | | | |
| 5 | R1 — Live $500, 2 coin | 2 tuần | ⬜ | | | |
| 6 | R2 — Live $500, 3 coin | 3–4 tuần | ⬜ | | | |
| 7 | G — Gate 60–90 ngày | 1 tuần | ⬜ | | | |
| 8 | Scale — $1k / $2k / $5k | Tùy gate | ⬜ | | | |

> Tổng trước khi có tiền thật: **~3–4 tuần** (Phase 0 → 4). Xem §11 kế hoạch.
>
> UI read-only hoàn thành trong **Phase 2**; UI positions/PnL/STOP trong **Phase 3** (§7.4 kế hoạch).

---

## PHASE 0 — CHUẨN BỊ TÀI KHOẢN & MÔI TRƯỜNG

**Mục tiêu:** có tài khoản, ví, quyền API, hạ tầng và kênh cảnh báo đúng cấu hình trước khi viết code.

**Tham chiếu kế hoạch:** §4.1 (phí), §7.2 (dữ liệu), §8.1 (giám sát), §10.2 (margin cross-wallet), §15.2 (thresholds).

**Giải thích cơ bản:** Hệ chạy L3 nên mọi sai cấu hình ở đây sẽ được bot thực thi tự động. Đặc biệt: sai margin mode → buffer không bảo vệ được leg short; sai quyền API → rủi ro bảo mật; thiếu alert → "giám sát" thành giả định.

### 0.1 Các bước thực hiện

- [x] **0.1.1** Mở/kiểm tra tài khoản Binance, bật 2FA, anti-phishing code.
- [ ] **0.1.2** Tạo **API key chính** (trade): bật Spot + USDⓈ-M Futures; **tắt Withdraw**; whitelist IP. *(chưa có live key; đang dùng demo key)*
- [ ] **0.1.3** Tạo **API key read-only** riêng cho monitor/reconcile độc lập. *(demo read-only đã có nhưng vẫn đặt được lệnh — xem P0-T02)*
- [ ] **0.1.4** Nạp **$500**; quy đổi USDT; phân bổ đúng:
  - Spot wallet: **$235**
  - Futures wallet: **$265** (margin $235 + buffer $30)
- [ ] **0.1.5** Set Futures: **Cross margin**, **1x**, **One-way mode**.
- [ ] **0.1.6** Mua **BNB riêng** (ngoài $500): $10–15 mỗi ví Spot và Futures để hưởng phí giảm.
- [ ] **0.1.7** Xác nhận fee tier VIP0 + BNB discount (spot 0,075%; futures taker 0,045%). *(demo: 0,02/0,04%)*
- [x] **0.1.8** Tạo **Demo Trading** + **API key demo** (Spot + USDⓈ-M) — đã đặt/hủy lệnh demo thành công.
- [x] **0.1.9** Dựng repo theo cấu trúc đề xuất; `.env` nằm trong `.gitignore`.
- [ ] **0.1.10** Cấu hình alert: Telegram bot + SMS/email; test bắn thử. *(bot `@fr_farming_binance_bot` OK; chưa có chat_id/updates, chưa có SMTP)*
- [x] **0.1.11** Cấu hình **VPS** chạy 24/7: user `funding`, NTP (chrony), `systemd Restart=always`, backup DB ngày. *(firewall: ngoại lệ vì VPS dùng chung — xem P0-T09)*
- [ ] **0.1.12** Cài **Tailscale** VPS + máy cá nhân; xác nhận truy cập nội bộ. *(đã cài trên VPS, chờ đăng nhập)*
- [ ] **0.1.13** Cấu hình **dead-man ping ngoài** (dịch vụ khác, không đặt cùng VPS). *(chờ URL dịch vụ ngoài)*
- [x] **0.1.14** Chốt **alert severity**: P1 (phải xử lý ≤15 phút), P2 (≤24h), P3 (theo tuần).

### 0.1a Ba loại API key

| Key | Dùng cho | Quyền bật | Không được bật |
|---|---|---|---|
| **Trade** | Executor đặt/hủy lệnh, transfer buffer | Reading + Spot & Margin + Futures (+ Universal Transfer khi Phase 3) | Withdraw |
| **Read-only** | Monitor/reconciler/dashboard | Chỉ Reading | Trading, Withdraw, Transfer |
| **Demo** | Chạy thử trên ví ảo | Reading + Spot + Futures | Không dùng cho live |

- Tạo live key: `binance.com` → Account → API Management → **System generated** (HMAC SHA256), bật đúng bảng, **Withdraw OFF**, whitelist IPv4 VPS.
- Tạo demo key: `demo.binance.com` → avatar → API Management (`demo.binance.com/en/my/settings/api-management`).
- Demo dùng endpoint `demo-api.binance.com` / `demo-fapi.binance.com`; key demo không dùng được trên live và ngược lại.
- **Demo không đo được** slippage/fill/funding thật; chỉ dùng kiểm tra kỹ thuật (order lifecycle, rollback, reconcile).
- `.env` hiện tại: `BINANCE_USE_DEMO=true`, chỉ có demo keys; chưa có live trade/read-only key.

### 0.2 Cấu trúc repo đề xuất

```text
funding-bot/
├── config/                 # YAML theo §15.2, không chứa secret
├── src/
│   ├── ingest/             # funding, premium, ticker, OI, depth
│   ├── features/           # APR, excess, CV, decay, score
│   ├── allocator/          # chọn coin, size, direction
│   ├── risk/               # pre-trade gate, kill switch
│   ├── executor/           # 2 leg, retry, rollback
│   ├── reconciler/         # đối soát API ↔ state
│   ├── watchdog/           # heartbeat, dead-man
│   └── report/             # PnL attribution, daily report
├── ui/                     # Phase 2 (read-only), Phase 3 (STOP)
├── backtest/               # Phase 1
├── tests/                  # Phase 4
├── data/                   # DB, parquet (gitignored)
├── logs/                   # audit log (gitignored)
├── reports/                # report ngày/tuần (gitignored)
├── .env                    # gitignored
└── README.md
```

> Chỉ tạo các thư mục trên khi tới phase tương ứng (xem §0.3).

### 0.3 Kết quả cần đạt

- [ ] Ảnh chụp màn hình: Spot $235, Futures $265, Cross, 1x. *(chưa có live; demo 5000/5020)*
- [ ] API key chính **không** có quyền rút tiền; key read-only **không** đặt được lệnh. *(live chưa có; demo read-only vẫn trade được)*
- [ ] Alert test tới điện thoại trong < 10 giây. *(thiếu chat_id/updates)*
- [ ] VPS truy cập được qua Tailscale; `systemd` tự restart khi kill process; backup DB chạy và restore thử được. *(systemd + backup OK; Tailscale chờ đăng nhập)*
- [x] Không có secret nào trong git (đã kiểm tra `git grep`).
- [x] **Không tạo `ui/`, executor, screener ở phase này.**

### 0.4 Checklist test

| ID | Test | Cách kiểm | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| P0-T01 | Quyền rút bị tắt | Gọi API withdrawal bằng key chính | 401/403 | ⏭️ | Chưa có live key; demo không có chức năng rút |
| P0-T02 | Key read-only không trade | Gọi API đặt lệnh bằng key read-only | 401/403 | ❌ | Demo read-only **vẫn đặt được lệnh** (order 28694503202, đã hủy). Local `_write_guard` đã chặn; live chưa test |
| P0-T03 | Số dư đúng | GET balance Spot/Futures | 235 / 265 USDT | ⏭️ | Demo 5000 / 5020 USDT; live chưa nạp |
| P0-T04 | Cross + 1x | Kiểm tra app + API `positionRisk` | Cross, leverage 1 | 🟡 | Demo BTCUSDT: leverage=1, margin=cross; live chưa xác nhận |
| P0-T05 | BNB discount | Xem fee tier / thử lệnh nhỏ | Spot 0,075%; Fut 0,045% | ⏭️ | Demo futures maker 0,02% / taker 0,04%; spot fee endpoint 404 |
| P0-T06 | Alert Telegram | Bắn test message | Nhận < 10s | ⬜ | Bot `@fr_farming_binance_bot` getMe OK; 0 updates → chưa có chat_id |
| P0-T07 | Alert SMS/email | Bắn test message | Nhận < 60s | ⏭️ | Chưa cấu hình SMTP/email |
| P0-T08 | Time drift | So `time` API với local | Lệch < 1s | ✅ | Local 227 ms; VPS -64 ms |
| P0-T09 | Firewall VPS | Scan port từ ngoài | Chỉ SSH/Tailscale; 8080 không lộ | ❌ | VPS dùng chung: 443/1508 mở cho `cors-prod`; 8080 đóng. Không áp firewall để tránh sập dịch vụ khác |
| P0-T10 | Systemd restart | Kill process bot | Tự lên lại < 10s | ✅ | PID 1301809 → 1301994, service active |
| P0-T11 | Secret không vào git | `git grep -i "api_key\|secret"` | 0 kết quả | ✅ | 0 secret thật; chỉ placeholder trong `.env.example`; `.env` không tracked |
| P0-T12 | Demo Trading hoạt động | Đặt/hủy 1 lệnh demo | Khớp bình thường | ✅ | Order 28694503206: NEW → CANCELED; query khớp |
| P0-T13 | Backup DB | Chạy backup + restore thử | File có, restore OK | ✅ | `funding-20261125T024621Z.db.gz`, restore value=42 |

### 0.5 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Ngày chạy | 25/11/2026 |
| Người chạy | OpenCode agent (user review) |
| Pass / Fail | 5 ✅ / 2 ❌ / 1 🟡 / 1 ⬜ / 4 ⏭️ (tổng 13) |
| Bằng chứng (link log/ảnh/commit) | VPS `/opt/funding-bot`, systemd `funding-heartbeat`, backup `funding-20261125T024621Z.db.gz`; demo order `28694503206`; P0-T02 order `28694503202` (đã hủy); commit Phase 0 |
| Quyết định | ⬜ Đạt phase 0 / ✅ **Chạy lại** (chưa đạt: live key/fund, alert chat_id, Tailscale, dead-man) / ⬜ Dừng |

### 0.6 Ghi chú & rủi ro

- **BNB phải nằm ngoài $500.** Nếu trừ vào buffer, buffer còn ~$15 → vi phạm ngưỡng 6%, phải giảm notional.
- **Cross margin là bắt buộc.** Isolated + không auto-add margin → buffer không cứu được leg short (§10.2).
- **Không dùng API key có quyền rút** cho bot, kể cả khi tiện.
- **VPS là single point of failure.** VPS chết = bot + UI cùng mất → bắt buộc dead-man ping ngoài + backup DB ngày (§12.3).
- **UI không tạo ở phase này.** Chỉ `.env`, config và script check key; UI bắt đầu Phase 2.
- **VPS dùng chung:** đang chạy `cors-prod` (Caddy 80/443, app 1508–1599, MySQL), `binance-demo-server` (127.0.0.1:8081), onedash/vector/vmagent. Không bật UFW/đóng port để tránh sập dịch vụ khác; service của dự án phải bind `127.0.0.1` và đi qua Tailscale.
- **Demo read-only key chưa đủ an toàn:** P0-T02 cho thấy key demo read-only vẫn đặt được lệnh. Đã thêm `_write_guard` ở client để chặn local; vẫn phải tạo live read-only và test lại trước khi chạy tiền thật.
- **Demo không hỗ trợ** `apiRestrictions` và `spot tradeFee` (404) → không kiểm tra được quyền rút/phí spot trên demo; phải test bằng live key.
- **Funding trên demo là dữ liệu mô phỏng** (BTCUSDT trả flat 0,0100%) → không dùng demo để backtest/research; chỉ dùng public live data.
- **Deploy VPS:** `/opt/funding-bot` (user `funding`), venv `.venv`, `.env` mode 600; systemd `funding-heartbeat` (placeholder) và `funding-backup.timer` 03:15 UTC. Khi có bot thật, thay `ExecStart` của heartbeat, giữ `Restart=always`.

---

## PHASE 1 — B0: THU DỮ LIỆU & BACKTEST $500 / 1X

**Mục tiêu:** chứng minh chiến lược còn dương sau phí ở đúng cấu hình $500/1x, trước khi bỏ công xây automation.

**Tham chiếu kế hoạch:** §3 (bài học dữ liệu thật), §4 (chi phí & break-even), §5 (bộ lọc & scoring), §6.4 (mô phỏng $500), §11 B0, §12.1.

**Giải thích cơ bản:** Backtest không phải để "thấy lãi đẹp", mà để (1) xác nhận edge sau phí còn dương, (2) đo phân phối tháng/DD, (3) kiểm tra bộ lọc có chọn được coin không trong regime hiện tại. Cấu hình phải đúng: 3 coin, $78/leg, 1x, fee P2, slippage 0,1%/side.

### 1.1 Các bước thực hiện

- [ ] **1.1.1** Ingest 6–12 tháng dữ liệu: `fundingRate`, `premiumIndexKlines`, `klines`, `ticker/24hr`, `exchangeInfo`, `openInterestHist`, `depth`.
- [ ] **1.1.2** Chuẩn hóa: timestamp UTC, interval 1h/2h/4h/8h, tách **baseline 10,95%/năm** và **excess**.
- [ ] **1.1.3** Implement đúng bộ lọc §5.2: forward APR 20–60%, excess ≥15%, pos ≥0,85, zero ≤0,10, CV ≤2, decay 7d/14d ≥0,6, net ≥20%, slippage ≤0,2%/side, volume ≥$5M.
- [ ] **1.1.4** Implement score §5.4: `net_APR × min(1,1/CV) × min(1, volume/$20M)`.
- [ ] **1.1.5** Mô phỏng: 3 coin, $78/leg, 1x, spot $235 + margin $235 + buffer $30; fee 0,24% + slippage 0,11% (c=0,35%).
- [ ] **1.1.6** Exit theo §10.3 (flip, decay, OI, basis, giá, venue, DD) + rebalance hàng tuần.
- [ ] **1.1.7** Xuất báo cáo: phân phối PnL tháng, DD, hit rate, **deployment rate** (% thời gian có vốn trong lệnh), turnover, fee drag, break-even days.
- [ ] **1.1.8** Chạy stress: basis shock 2% và 5%; funding giảm 50%; slippage ×2.
- [ ] **1.1.9** So sánh với snapshot thực tế: bộ lọc hôm nay ra bao nhiêu ứng viên? (Tham chiếu báo cáo: 4 mã pass — EVAA, AVAAI, PIEVERSE, PHAROS.)

### 1.2 Kết quả cần đạt

- [ ] Net APR **≥ 9% trên vốn** sau chiết khấu quy mô nhỏ.
- [ ] **≥ 70% tháng dương**; không có tháng nào < −3% (ngoài tail shock).
- [ ] DD stress **≤ 4%** vốn.
- [ ] Deployment rate ≥ 50% thời gian (nếu thấp hơn, ghi rõ và điều chỉnh kỳ vọng lợi nhuận).
- [ ] Bộ lọc trả về **≥ 2 ứng viên** trong ≥ 50% số ngày; nếu không, ghi nhận "thị trường nghèo funding".
- [ ] Có báo cáo tái lập được bằng 1 lệnh, cùng seed/dữ liệu.

### 1.3 Checklist test

| ID | Test | Cách kiểm | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| P1-T01 | Không lookahead | Shift tín hiệu 1 kỳ; so sánh | Kết quả không đổi bất thường | ⬜ | |
| P1-T02 | Chuẩn hóa interval | So 4h/8h/1h cùng symbol | APR năm hóa khớp ±1% | ⬜ | |
| P1-T03 | Baseline/excess | Tính lại 1 symbol tay | Baseline ~10,95%; excess khớp | ⬜ | |
| P1-T04 | Phí & slippage | So c với 0,35% | Drag 9,13pp APR | ⬜ | |
| P1-T05 | Min notional & rounding | Mô phỏng $78/leg | Không lệnh nào < min | ⬜ | |
| P1-T06 | Survivorship/delist | Thêm symbol đã delist | Không crash, xử lý đúng | ⬜ | |
| P1-T07 | Missing data | Cắt 10% dữ liệu | Không lỗi silent, có cảnh báo | ⬜ | |
| P1-T08 | Timezone | So timestamp UTC | Khớp fundingTime | ⬜ | |
| P1-T09 | Tái lập snapshot | Chạy filter ngày 24/11 | Ra 4 mã pass như báo cáo | ⬜ | |
| P1-T10 | Stress basis 2%/5% | Chạy 2 kịch bản | DD ≤4% / ghi nhận tail | ⬜ | |
| P1-T11 | Funding giảm 50% | Chạy lại | Net APR vẫn >0 | ⬜ | |
| P1-T12 | Slippage ×2 | Chạy lại | Net APR >0, ghi rõ biên | ⬜ | |

### 1.4 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Ngày chạy | |
| Người chạy | |
| Pass / Fail | __ / 12 |
| Net APR / tháng | |
| Deployment rate | |
| DD stress | |
| Bằng chứng (report, commit) | |
| Quyết định | ⬜ Đạt / ⬜ Chạy lại / ⬜ Dừng |

### 1.5 Ghi chú & rủi ro

- **Không tối ưu tham số để đẹp backtest.** Nếu phải nới cap 60% hoặc hạ net 20% mới có lãi, ghi rõ đó là quyết định rủi ro.
- **Backtest là trần lý thuyết** (§6.3): survivorship, một vài regime, không mô hình liquidation/ADL/delist.
- **Deployment rate thấp là kết quả hợp lệ**, không phải lỗi. Thị trường funding hiện tại median ~4,2%/năm → đứng ngoài là bình thường.
- Nếu Phase 1 fail: **không** chuyển sang xây automation. Quay lại bộ lọc/cấu hình.

---

## PHASE 2 — B1a: INGEST + FEATURE + SCREENER + UI READ-ONLY

**Mục tiêu:** có service chạy 24/7, kéo dữ liệu sạch, tính điểm, xuất danh sách ứng viên giống hệt backtest — và **UI read-only** để nhìn dữ liệu.

**Tham chiếu kế hoạch:** §5 (bộ lọc), §6 (backtest), §7.1–7.3 (kiến trúc & API), **§7.4 (UI realtime)**, §15.2 (thresholds).

**Giải thích cơ bản:** Đây là "mắt" của hệ. Nếu screener lệch backtest, mọi bước sau vô nghĩa. Yêu cầu quan trọng nhất: **parity** giữa kết quả live và kết quả backtest trên cùng thời điểm. UI Phase 2 chỉ để nhìn, **chưa có STOP**. Các file `ui/` chỉ được tạo ở phase này.

### 2.1 Các bước thực hiện

- [ ] **2.1.1** Collector REST + WS: funding, premium, ticker, OI, depth, exchangeInfo (§7.3).
- [ ] **2.1.2** Lưu DB (SQLite/Postgres) + raw snapshot; ghi `ingested_at`, `source`.
- [ ] **2.1.3** Feature engine: APR 7d/14d, forward, excess, pos_ratio, zero_rate, CV, decay 7d/14d, score.
- [ ] **2.1.4** Screener: áp §5.2, xuất JSON + bảng Markdown + lưu DB.
- [ ] **2.1.5** Xử lý interval thay đổi giữa chừng (re-normalize toàn bộ chuỗi).
- [ ] **2.1.6** Backoff/retry khi 429/5xx; không retry mù.
- [ ] **2.1.7** Report ngày: top ứng viên, lý do loại, trạng thái dữ liệu.
- [ ] **2.1.8** Healthcheck: độ mới dữ liệu, số symbol, lỗi ingest.
- [ ] **2.1.9** Dựng `ui/`: FastAPI + SSE đọc SQLite; endpoint `/healthz`, `/api/stream`, `/api/candidates`; không đưa key xuống browser.
- [ ] **2.1.10** Trang HTML: header status + countdown funding, bảng ứng viên, funding thị trường; dark theme, responsive.
- [ ] **2.1.11** `systemd` service `funding-ui` riêng; truy cập qua Tailscale; không mở port ra internet.

### 2.2 Kết quả cần đạt

- [ ] Screener chạy mỗi 1–5 phút, không lỗi quá 5 phút.
- [ ] Kết quả **khớp 100%** với script backtest trên cùng snapshot.
- [ ] Không có gap dữ liệu > 2 kỳ funding cho symbol trong universe.
- [ ] Restart service không mất state, không nhân đôi dữ liệu.
- [ ] Report ngày đọc được bởi người không mở code.
- [ ] UI cập nhật trạng thái **≤ 2 giây** (SSE), candidates **≤ 60 giây**.
- [ ] UI **không** chứa API key/secret; chỉ read-only, không nút đặt lệnh.
- [ ] UI chết không làm screener/bot dừng.

### 2.3 Checklist test

| ID | Test | Cách kiểm | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| P2-T01 | Parity backtest | So danh sách live vs backtest | Khớp 100% | ⬜ | |
| P2-T02 | Interval change | Symbol đổi 4h→1h | APR năm hóa không nhảy | ⬜ | |
| P2-T03 | Negative funding | Chọn symbol âm | Bị loại đúng rule | ⬜ | |
| P2-T04 | Zero funding | Symbol zero-rate cao | Bị loại đúng rule | ⬜ | |
| P2-T05 | Delisted symbol | Symbol ngừng giao dịch | Bỏ khỏi universe, không crash | ⬜ | |
| P2-T06 | 429/5xx | Giả lập rate limit | Backoff, không mất dữ liệu | ⬜ | |
| P2-T07 | Restart | Kill service giữa chừng | Không duplicate, resume đúng | ⬜ | |
| P2-T08 | DB đầy/khóa | Giả lập DB locked | Cảnh báo, không silent fail | ⬜ | |
| P2-T09 | Clock skew | Đổi giờ máy +30s | Cảnh báo / tự sync | ⬜ | |
| P2-T10 | Thiếu depth | Symbol book mỏng | Không chọn hoặc cảnh báo | ⬜ | |
| P2-T11 | Latency | Đo từ ingest → screener | < 5 phút | ⬜ | |
| P2-T12 | Report ngày | Mở file report | Đủ top, lý do loại, healthcheck | ⬜ | |
| P2-T13 | UI realtime | Mở UI, đo update | ≤ 2s | ⬜ | |
| P2-T14 | Không lộ key | Grep HTML/JS + Network tab | 0 secret | ⬜ | |
| P2-T15 | Auth/Tailscale | Truy cập từ ngoài | Bị chặn | ⬜ | |
| P2-T16 | UI read-only | Thử POST order vào UI | 404/405; không có nút | ⬜ | |

### 2.4 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Ngày chạy | |
| Người chạy | |
| Pass / Fail | __ / 16 |
| Số symbol universe | |
| Số ứng viên pass / ngày | |
| Bằng chứng (log, report) | |
| Quyết định | ⬜ Đạt / ⬜ Chạy lại / ⬜ Dừng |

### 2.5 Ghi chú & rủi ro

- **Parity là điều kiện cứng.** Lệch > 0 ứng viên phải tìm nguyên nhân trước khi tiếp tục.
- Baseline 10,95% **không trừ khỏi P&L**, chỉ dùng cho excess/score (§5.2 note).
- Nếu universe < 3 ứng viên nhiều ngày: ghi nhận, không hạ chuẩn để có lệnh.
- **UI Phase 2 chỉ read-only.** Không thêm nút STOP/mua/bán; STOP thuộc Phase 3. Không tạo file UI trước phase này.

---

## PHASE 3 — B1b: EXECUTOR + RECONCILER + WATCHDOG + UI POSITIONS/STOP

**Mục tiêu:** bot tự vào/ra 2 leg an toàn, tự đối soát, tự dừng khi bất thường — không cần người bấm lệnh; UI hiển thị vị thế/PnL và có **STOP**.

**Tham chiếu kế hoạch:** §7.1 (7 khối + Watchdog), **§7.4 (UI)**, §8 (L3, lớp giám sát, runbook), §8.2 (runbook), §8.3 (điều kiện bật live), §10.3 (kill switch), §11 B1.

**Giải thích cơ bản:** Rủi ro lớn nhất là **lệch chân** (leg 1 khớp, leg 2 fail) và **state lệch sàn**. Vì vậy executor phải idempotent, có rollback; reconciler phải chạy độc lập; watchdog phải phát hiện bot chết và báo ngay.

### 3.1 Các bước thực hiện

- [ ] **3.1.1** State machine: `IDLE → ENTERING → HEDGED → EXITING → CLOSED` + `ERROR`.
- [ ] **3.1.2** Order manager: `clientOrderId` idempotent; precision/qty step từ `exchangeInfo`; check min notional trước khi gửi.
- [ ] **3.1.3** Executor 2 leg: gửi spot trước hay perp trước (chốt 1 chiều), retry ≤ 3 với giá giới hạn, rollback nếu leg 2 fail.
- [ ] **3.1.4** Hard cap trong code: max order notional = 25% vốn ($125); max coin = 3; leverage = 1x; max slippage.
- [ ] **3.1.5** Reconciler: mỗi 60s so position/balance API ↔ state; lệch > 1% → dừng vào mới + P1.
- [ ] **3.1.6** Watchdog: heartbeat 30s; mất > 2 phút alert; > 5 phút chặn vào mới + dead-man.
- [ ] **3.1.7** Buffer manager: auto transfer Spot ↔ Futures khi buffer < 50% nhu cầu; không transfer nếu đang có lệnh treo.
- [ ] **3.1.8** Kill switch theo §10.3; người không override được.
- [ ] **3.1.9** Audit log bất biến: order, fill, retry, override, transfer, alert.
- [ ] **3.1.10** UI Phase 3: positions 2 leg + delta, funding hiện tại/kế tiếp, PnL attribution, reconcile diff, alert log; **STOP ALL** confirm 2 bước; không nút mua/bán.
- [ ] **3.1.11** Cơ chế **resume sau P1 cần người xác nhận** (`resume_after_p1_requires_human: true`).

### 3.2 Kết quả cần đạt

- [ ] Không có lệnh trùng khi retry/timeout.
- [ ] Leg 2 fail → leg 1 được đóng trong ≤ 60 giây, có log.
- [ ] Reconcile diff = 0 liên tục 24h trên Demo Trading.
- [ ] Kill switch + dead-man hoạt động trong ≤ 5 phút kể từ sự cố giả lập.
- [ ] Không có đường nào để bot mở > $125/order hoặc > 3 coin.
- [ ] Mọi alert P1 tới điện thoại trong < 15 giây.
- [ ] UI hiển thị đúng 2 leg + PnL khớp report ±1%; cập nhật ≤ 2 giây.
- [ ] STOP từ UI dừng bot ≤ 5 giây, có audit log; UI chết không ảnh hưởng bot.

### 3.3 Checklist test (matrix bắt buộc)

| ID | Test | Cách kiểm | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| P3-T01 | Leg 2 fail | Giả lập reject leg perp | Đóng leg spot, state ERROR, P1 | ⬜ | |
| P3-T02 | Partial fill | Khớp 50% | Retry phần còn lại hoặc rollback | ⬜ | |
| P3-T03 | Timeout | Không phản hồi 10s | Không gửi trùng; query order | ⬜ | |
| P3-T04 | API 429 | Giả lập rate limit | Backoff, không retry mù | ⬜ | |
| P3-T05 | API 5xx | Giả lập 500 | Retry có giới hạn + alert | ⬜ | |
| P3-T06 | Mất mạng | Ngắt WAN 2 phút | Heartbeat alert; không lệnh mới | ⬜ | |
| P3-T07 | Mất mạng 6 phút | Ngắt WAN 6 phút | Dead-man chặn/flatten theo config | ⬜ | |
| P3-T08 | Sai số dư | Giảm balance | Không gửi lệnh; P1 | ⬜ | |
| P3-T09 | Precision/qty | Coin bước giá thô | Qty làm tròn đúng, không reject | ⬜ | |
| P3-T10 | Min notional | Size < min | Chặn trước khi gửi | ⬜ | |
| P3-T11 | Lệnh trùng | Retry cùng clientOrderId | Chỉ 1 lệnh trên sàn | ⬜ | |
| P3-T12 | Reconcile lệch | Sửa state nội bộ | Dừng vào mới + P1 ≤ 60s | ⬜ | |
| P3-T13 | Kill switch flip | Đưa FR flip 2 kỳ | Đóng coin đúng rule | ⬜ | |
| P3-T14 | Kill switch giá | Giá move 15%/1h | Giảm/đóng đúng rule | ⬜ | |
| P3-T15 | Kill switch DD | Giảm vốn 20% | Kill toàn hệ | ⬜ | |
| P3-T16 | Buffer transfer | Buffer < ngưỡng | Auto transfer đúng, không lặp | ⬜ | |
| P3-T17 | Restart giữa vị thế | Kill bot khi HEDGED | Khôi phục đúng state, không mở thêm | ⬜ | |
| P3-T18 | DB down | Tắt DB | Bot dừng an toàn, không mất state | ⬜ | |
| P3-T19 | Clock skew | Lệch giờ 30s | Không gửi lệnh sai timestamp | ⬜ | |
| P3-T20 | Resume sau P1 | Sau sự cố | Không tự mở lại khi chưa xác nhận | ⬜ | |
| P3-T21 | UI positions | So UI với state/report | Khớp 2 leg, PnL ±1% | ⬜ | |
| P3-T22 | STOP từ UI | Bấm STOP + confirm | Dừng ≤ 5s, audit log | ⬜ | |
| P3-T23 | Không nút mua/bán | Kiểm UI + API | Không có endpoint đặt lệnh | ⬜ | |
| P3-T24 | UI chết | Tắt funding-ui | Bot vẫn chạy bình thường | ⬜ | |

### 3.4 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Ngày chạy | |
| Người chạy | |
| Pass / Fail | __ / 24 |
| Reconcile 24h | diff = 0? |
| Alert P1 latency | |
| Bằng chứng (log, video, commit) | |
| Quyết định | ⬜ Đạt / ⬜ Chạy lại / ⬜ Dừng |

### 3.5 Ghi chú & rủi ro

- **Không dùng retry mù.** Mỗi retry phải query trạng thái lệnh trước.
- **Không sửa tay lệnh bot đang chạy** — chỉ kill/blacklist (§11 luật cứng).
- **Reconciler phải chạy process riêng**, không chung vòng lặp executor.
- Nếu bất kỳ test P3-T01/P3-T05/P3-T12 fail → **không** sang Phase 4.
- UI chỉ có 1 nút **STOP** (giảm rủi ro); không thêm nút mua/bán. STOP phải ghi audit và không được là đường dừng duy nhất.

---

## PHASE 4 — B1c: DEMO TRADING + DRY-RUN 7 NGÀY

**Mục tiêu:** chạy đúng luồng trên **Demo Trading** (ví ảo, gần như cùng tính năng live) và dry-run dữ liệu thật 7 ngày, đo slippage/fill trước khi dùng tiền thật.

**Tham chiếu kế hoạch:** §8.3 (điều kiện bật live), §11 B1, §12.5 (ngân sách thiệt hại).

**Giải thích cơ bản:** Demo Trading kiểm tra kỹ thuật (order lifecycle, rollback, reconcile) trên ví ảo; dry-run kiểm tra quyết định trên thị trường thật mà không gửi lệnh. Demo không đo được slippage/fill thật — phần đó để dry-run + live $500.

### 4.1 Các bước thực hiện

- [ ] **4.1.1** Chạy toàn bộ luồng trên **Demo Trading**: vào 2 leg, rollback, exit, transfer (dùng `BINANCE_USE_DEMO=true`, `DRY_RUN=false`, `LIVE_TRADING_ENABLED=false`).
- [ ] **4.1.2** Chạy **dry-run ≥ 7 ngày** trên dữ liệu thật: bot quyết định nhưng **không gửi lệnh**; ghi giá "nếu vào thì khớp nào".
- [ ] **4.1.3** Ghi log từng episode giấy: coin, thời điểm, size, giá dự kiến, giá thực tế tại thời điểm đó, funding dự kiến.
- [ ] **4.1.4** Đo slippage giả định vs model 0,1%/side.
- [ ] **4.1.5** Diễn tập: kill switch, dead-man, restart giữa vị thế, mất mạng.
- [ ] **4.1.6** So sánh danh sách dry-run với backtest cùng ngày.
- [ ] **4.1.7** Quan sát UI trong dry-run: trạng thái DRY, candidates, countdown; xác nhận **không có** nút STOP/mua/bán.

### 4.2 Kết quả cần đạt

- [ ] ≥ **10 episode giấy** hoặc ≥ 7 ngày chạy liên tục (tùy cái nào đến trước).
- [ ] Slippage giả định **≤ 0,15%/side** ở ≥ 80% episode.
- [ ] Uptime ≥ 99% trong 7 ngày.
- [ ] **0 sự cố P1**; mọi P2 có root-cause.
- [ ] Kill switch + dead-man diễn tập thành công.
- [ ] Reconcile diff = 0 toàn bộ 7 ngày.
- [ ] UI hiển thị đúng trạng thái dry-run và không gửi lệnh.

### 4.3 Checklist test

| ID | Test | Cách kiểm | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| P4-T01 | Dry-run đủ ngày | Log ngày | ≥ 7 ngày | ⬜ | |
| P4-T02 | Số episode giấy | Đếm log | ≥ 10 | ⬜ | |
| P4-T03 | Slippage | So giá dự kiến/thực tế | ≤ 0,15%/side, ≥80% | ⬜ | |
| P4-T04 | Uptime | Healthcheck | ≥ 99% | ⬜ | |
| P4-T05 | P1 count | Log alert | 0 | ⬜ | |
| P4-T06 | Kill switch drill | Giả lập trigger | Đóng đúng, ≤ 60s | ⬜ | |
| P4-T07 | Dead-man drill | Ngắt heartbeat | Chặn/flatten đúng, ≤ 5 phút | ⬜ | |
| P4-T08 | Restart giữa vị thế | Kill process | Khôi phục đúng | ⬜ | |
| P4-T09 | Parity backtest | So cùng ngày | Khớp danh sách | ⬜ | |
| P4-T10 | Alert test | Bắn P1/P2 | Nhận đúng kênh | ⬜ | |
| P4-T11 | Audit log | Kiểm 1 episode | Đủ order/fill/retry | ⬜ | |
| P4-T12 | Báo cáo ngày | Mở report | Đủ PnL, funding, lỗi | ⬜ | |
| P4-T13 | UI dry-run | Mở UI khi DRY_RUN=true | Hiện DRY, không có nút lệnh | ⬜ | |

### 4.4 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Ngày chạy | |
| Người chạy | |
| Pass / Fail | __ / 13 |
| Số episode giấy | |
| Slippage TB / p90 | |
| Bằng chứng (log, report) | |
| Quyết định | ⬜ Đạt / ⬜ Chạy lại / ⬜ Dừng |

### 4.5 Ghi chú & rủi ro

- Dry-run **không được** gửi lệnh thật; kiểm tra API key đang ở chế độ read-only **hoặc** `BINANCE_USE_DEMO=true` với key demo.
- Demo không thay thế đo lường thật: slippage/fill/funding chỉ đo được ở live $500; không nới gate vì "demo chạy đẹp".
- Nếu slippage thực tế > 0,2%/side → quay lại chọn coin thanh khoản hơn, không hạ chuẩn.
- Nếu uptime < 99% → sửa hạ tầng trước khi live.

---

## PHASE 5 — R1: LIVE $500, 2 COIN

**Mục tiêu:** xác nhận ngoài đời với tiền thật, quy mô nhỏ, 2 coin, 1x, L3 hoàn toàn.

**Tham chiếu kế hoạch:** §11 R1, §13 (checklist vận hành), §10 (risk & kill switch), §12.5 (ngân sách thiệt hại).

**Giải thích cơ bản:** Đây là lần đầu bot dùng tiền thật. Mục tiêu **không phải lãi**, mà là: khớp lệnh đúng, funding thực nhận đúng kỳ vọng, không lỗi vận hành. Hai tuần đầu người trực 24/7.

### 5.1 Các bước thực hiện

- [ ] **5.1.1** Bật bot với **2 coin × $78/leg**, 1x, 3 slot còn 1 để trống.
- [ ] **5.1.2** Trực 24/7 trong 14 ngày; kiểm tra checklist ngày §13.
- [ ] **5.1.3** Ghi nhận từng kỳ funding thực nhận vs dự kiến.
- [ ] **5.1.4** Kiểm tra reconcile mỗi ngày; lưu bằng chứng.
- [ ] **5.1.5** Đo slippage thực từng lệnh.
- [ ] **5.1.6** Review tuần: PnL attribution, phí, funding, lỗi.
- [ ] **5.1.7** **Không** thêm coin, **không** tăng size, **không** bật 2x trong phase này.
- [ ] **5.1.8** Dùng UI làm nguồn giám sát chính; mỗi ngày đối chiếu UI với app sàn.

### 5.2 Kết quả cần đạt

- [ ] ≥ 10 ngày live, ≥ 1 chu kỳ vào/ra hoàn chỉnh.
- [ ] Funding thực nhận lệch kỳ vọng **< 20%**.
- [ ] **0 sự cố P1**; mọi P2 có root-cause trong 48h.
- [ ] Reconcile diff = 0 mỗi ngày.
- [ ] DD thực **< 5%** vốn.
- [ ] Không có lần nào phải sửa tay lệnh.
- [ ] Slippage thực ≤ 0,2%/side.
- [ ] UI khớp vị thế/PnL thực tế ±1%.

### 5.3 Checklist test

| ID | Test | Cách kiểm | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| P5-T01 | Entry end-to-end | Lần vào đầu tiên | 2 leg khớp, delta-neutral | ⬜ | |
| P5-T02 | Funding thực | So payment với dự kiến | Lệch < 20% | ⬜ | |
| P5-T03 | Exit end-to-end | Lần ra đầu tiên | Đóng đủ 2 leg, không treo | ⬜ | |
| P5-T04 | Reconcile ngày | So API ↔ state | diff = 0 | ⬜ | |
| P5-T05 | Buffer transfer | Khi buffer < ngưỡng | Tự nạp đúng | ⬜ | |
| P5-T06 | Slippage | Log từng fill | ≤ 0,2%/side | ⬜ | |
| P5-T07 | Alert thực | Sự cố/giả lập | Nhận đúng kênh | ⬜ | |
| P5-T08 | Kill switch thực | Trigger nhỏ (nếu an toàn) | Đóng đúng, có log | ⬜ | |
| P5-T09 | DD | Theo dõi ngày | < 5% | ⬜ | |
| P5-T10 | Không sửa tay | Audit log | 0 manual order | ⬜ | |
| P5-T11 | UI khớp thực tế | So UI với app sàn | Vị thế/PnL ±1% | ⬜ | |

### 5.4 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Ngày bắt đầu / kết thúc | |
| Người trực | |
| Pass / Fail | __ / 11 |
| Funding thực / dự kiến | |
| Slippage TB | |
| P1 / P2 count | |
| Bằng chứng (report, ảnh) | |
| Quyết định | ⬜ Đạt / ⬜ Chạy tiếp / ⬜ Dừng |

### 5.5 Ghi chú & rủi ro

- Ngân sách "học phí" 3 tháng: **$50–150**. Chạm ngưỡng → dừng, review, **không nạp thêm để gỡ**.
- Nếu funding flip liên tục: giảm size hoặc đứng ngoài, không cố giữ.
- Nếu bot lỗi P1: dừng bot, reconcile tay, chỉ resume sau khi root-cause.

---

## PHASE 6 — R2: LIVE $500, 3 COIN

**Mục tiêu:** mở đủ 3 slot theo cấu hình chuẩn, duy trì L3 ổn định 3–4 tuần.

**Tham chiếu kế hoạch:** §11 R2, §12.2, §10.1 (risk budget), §13.

**Giải thích cơ bản:** Tăng từ 2 lên 3 coin làm tăng notional từ $156 lên $235, gần đúng cấu hình. Đây là mức vốn tối đa của $500; không tăng thêm.

### 6.1 Các bước thực hiện

- [ ] **6.1.1** Chỉ thêm coin thứ 3 khi nó pass đủ §5.2 và score xếp trên coin dự bị.
- [ ] **6.1.2** Kiểm tra correlation/tổng exposure ≤ 60% notional.
- [ ] **6.1.3** Theo dõi 3 coin trong 3–4 tuần; rebalance tuần.
- [ ] **6.1.4** Nếu thiếu ứng viên: giữ 2 coin hoặc tiền mặt, **không hạ chuẩn**.
- [ ] **6.1.5** Chuẩn bị hồ sơ gate Phase 7.

### 6.2 Kết quả cần đạt

- [ ] 3 coin chạy đồng thời ≥ 14 ngày (hoặc ghi rõ lý do không đủ ứng viên).
- [ ] Tổng notional ≤ $235; spot ≤ $235; margin ≤ $235; buffer ≥ $30.
- [ ] Không coin nào vượt 15,7% vốn notional.
- [ ] 0 P1; DD < 5%.
- [ ] PnL attribution đúng: funding vs basis vs phí.

### 6.3 Checklist test

| ID | Test | Cách kiểm | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| P6-T01 | 3 coin đồng thời | State | Đúng 3 vị thế | ⬜ | |
| P6-T02 | Tổng exposure | Tính notional | ≤ $235 | ⬜ | |
| P6-T03 | Correlation | Ma trận 14d | Không vượt cap | ⬜ | |
| P6-T04 | Buffer | Balance | ≥ $30 | ⬜ | |
| P6-T05 | Rebalance tuần | Log | Đúng rule | ⬜ | |
| P6-T06 | Thiếu ứng viên | Ngày không đủ 3 | Giữ tiền mặt, không hạ chuẩn | ⬜ | |
| P6-T07 | PnL attribution | Report tháng | Khớp funding − phí ± basis | ⬜ | |
| P6-T08 | 0 P1 | Alert log | 0 | ⬜ | |
| P6-T09 | DD | Report | < 5% | ⬜ | |
| P6-T10 | Audit log | Mẫu 10 lệnh | Đúng rule, đúng size | ⬜ | |

### 6.4 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Ngày bắt đầu / kết thúc | |
| Pass / Fail | __ / 10 |
| Số ngày đủ 3 coin | |
| Notional TB / max | |
| Funding thực | |
| Bằng chứng | |
| Quyết định | ⬜ Đạt / ⬜ Chạy tiếp / ⬜ Dừng |

### 6.5 Ghi chú & rủi ro

- 3 coin đều mid/small-cap, 4h interval → correlation cao. Nếu 3 coin cùng beta, có thể chỉ nên giữ 2.
- Không thêm coin thứ 4 ở $500 (vi phạm risk budget, min notional).

---

## PHASE 7 — G: GATE 60–90 NGÀY

**Mục tiêu:** quyết định có nâng vốn lên $1.000 hay tiếp tục ở $500; có nên lên 2x hay không.

**Tham chiếu kế hoạch:** §12.4 (11 điều kiện gate), §12.2 (nâng vốn), §13 (review tháng).

**Giải thích cơ bản:** Gate là "cửa an toàn" duy nhất để tăng vốn. Không đạt đủ 11 điều kiện thì giữ nguyên, không thương lượng.

### 7.1 Các bước thực hiện

- [ ] **7.1.1** Tổng hợp 60–90 ngày: PnL, funding thực, phí, slippage, DD, uptime, sự cố.
- [ ] **7.1.2** Đối chiếu **11 điều kiện §12.4**.
- [ ] **7.1.3** Audit log mẫu 20 lệnh: đúng rule, đúng size, rollback đúng.
- [ ] **7.1.4** Kiểm tra alert + kill switch + dead-man trong 7 ngày gần nhất.
- [ ] **7.1.5** Quyết định: (a) giữ $500, (b) lên $1.000, (c) xét 2x sau thêm 30 ngày.
- [ ] **7.1.6** Ghi biên bản quyết định + lý do.

### 7.2 Kết quả cần đạt

- [ ] Có báo cáo đủ 11 mục gate, kèm bằng chứng.
- [ ] Quyết định được ghi log, có người ký.
- [ ] Nếu nâng vốn: kế hoạch chuyển tiền, thay đổi size, cập nhật config.
- [ ] Nếu không: ngày review lại.

### 7.3 Checklist test (gate)

| ID | Điều kiện §12.4 | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|
| P7-T01 | ≥ 60 ngày live | Có | ⬜ | |
| P7-T02 | Net dương sau phí | Có | ⬜ | |
| P7-T03 | Slippage ≤ 0,15% ở ≥80% lệnh | Có | ⬜ | |
| P7-T04 | 0 lỗi vận hành chưa khắc phục | Có | ⬜ | |
| P7-T05 | Max DD < 10% | Có | ⬜ | |
| P7-T06 | Funding lệch < 20% | Có | ⬜ | |
| P7-T07 | Giải thích được từng tháng | Có | ⬜ | |
| P7-T08 | Reconcile diff = 0 trong 30 ngày | Có | ⬜ | |
| P7-T09 | 0 P1 chưa root-cause | Có | ⬜ | |
| P7-T10 | Alert/kill test trong 7 ngày | Có | ⬜ | |
| P7-T11 | Nếu xét 2x: 30 ngày DD <5%, không chạm buffer | Có | ⬜ | |
| P7-T12 | UI healthcheck uptime ≥99% trong 30 ngày (bổ sung của task) | Có | ⬜ | |

### 7.4 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Ngày review | |
| Số ngày live | |
| Pass / Fail | __ / 12 |
| Net APR thực | |
| Quyết định | ⬜ Giữ $500 / ⬜ Lên $1.000 / ⬜ Xét 2x / ⬜ Dừng |
| Người ký | |

### 7.5 Ghi chú & rủi ro

- **Không nâng vốn vì "thấy lãi tốt"** — phải đủ 11 mục.
- 2x chỉ xét sau khi 1x sạch lỗi ≥ 60–90 ngày và qua gate riêng.
- Nếu fail gate: giữ nguyên 30 ngày, không hạ chuẩn.

---

## PHASE 8 — SCALE: $1.000 / $2.000 / $5.000

**Mục tiêu:** nhân bản hệ thống đã chứng minh, thay đổi đúng những gì cần thay đổi.

**Tham chiếu kế hoạch:** §12.2 (bảng nâng vốn), §12.3 (chi phí ẩn), §10.1 (risk budget).

**Giải thích cơ bản:** Không đổi chiến lược, bộ lọc hay mức L3. Chỉ đổi số coin, size, hạ tầng và mức redundancy. Mỗi lần nâng tối đa gấp đôi, cách nhau ≥ 60 ngày.

### 8.1 Các bước theo mức vốn

| Mức | Notional/leg | Coin | N/coin | Buffer | Hạ tầng | Việc phải làm thêm |
|---|---|---|---|---|---|---|
| $500 | $235 | 3 | $78 | $30 | VPS sẵn có (bot + UI) | — |
| $1.000 | $470 | 5 | $94 | $60 | VPS sẵn có + backup | Thêm 2 coin; alert 2 kênh; maker leg spot |
| $2.000 | $940 | 7 | $134 | $120 | VPS sẵn có + monitoring | PnL attribution tự động; chaos drill; hardening |
| $5.000 | $2.350 | 9 | $261 | $300 | VPS sẵn có + redundancy ngoài | Sub-account buffer; ping/watchdog ngoài; audit export |

### 8.2 Kết quả cần đạt mỗi mức

- [ ] Reconcile diff = 0 trong 30 ngày đầu ở mức mới.
- [ ] Không P1; DD < 5% (mức $1k–$2k) hoặc < 4% ($5k).
- [ ] Slippage không tăng > 0,05%/side so với mức trước.
- [ ] **VPS hiện tại** chạy ổn định ≥ 99,5% uptime; redundancy/ping ngoài chỉ cần từ $5k.
- [ ] Gate §12.4 được chạy lại trước mỗi lần nâng.

### 8.3 Checklist test (mỗi lần nâng)

| ID | Test | Kỳ vọng | Kết quả | Ghi chú |
|---|---|---|---|---|
| P8-T01 | Số dư & phân bổ mới | Đúng bảng §12.2 | ⬜ | |
| P8-T02 | Buffer mới | Đúng ngưỡng 6% | ⬜ | |
| P8-T03 | Coin mới pass filter | 100% | ⬜ | |
| P8-T04 | Correlation | ≤ 60% notional | ⬜ | |
| P8-T05 | Reconcile 30 ngày | diff = 0 | ⬜ | |
| P8-T06 | Alert/kill test | Pass | ⬜ | |
| P8-T07 | Uptime | ≥ 99,5% | ⬜ | |
| P8-T08 | Slippage | Không tăng > 0,05% | ⬜ | |
| P8-T09 | Gate §12.4 | Đủ 11 mục + UI uptime | ⬜ | |
| P8-T10 | Rollback plan | Có, đã test | ⬜ | |
| P8-T11 | UI mức vốn mới | Đúng vốn/notional | ⬜ | |

### 8.4 Kết quả test (biên bản)

| Hạng mục | Giá trị |
|---|---|
| Mức vốn | |
| Ngày nâng | |
| Pass / Fail | __ / 11 |
| Vốn mới / notional | |
| Người ký | |
| Quyết định | ⬜ Đạt / ⬜ Quay lại mức cũ |

### 8.5 Ghi chú & rủi ro

- **Không nâng vốn và đổi chiến lược cùng lúc.** Mỗi lần chỉ đổi một biến.
- **VPS đã có sẵn ($0)**, nhưng vẫn là single point of failure: từ $5.000 thêm redundancy/ping ngoài; backup DB ngày ở mọi mức.
- Không dùng đòn bẩy để "tăng tốc" — 2x chỉ sau gate riêng.

---

## PHỤ LỤC A — RUNBOOK NHANH (P1)

Tham chiếu §8.2.

| Sự cố | Máy tự xử lý | Người làm | SLA |
|---|---|---|---|
| Bot chết/mất heartbeat > 5 phút | Chặn vào mới; dead-man | Kiểm tra máy/mạng, restart, reconcile | 15 phút |
| Leg 2 fail | Retry ≤3; rollback leg 1 | Xác nhận rollback, ghi log | 15 phút |
| Reconcile lệch | Dừng vào mới | Đối chiếu app, sửa state có audit | 30 phút |
| API 429/5xx | Backoff | Kiểm tra status sàn | 30 phút |
| Sàn pause rút/tag/đổi interval | Đóng vị thế liên quan | Rút phần được, blacklist | Ngay |
| Funding flip 2 kỳ | Đóng coin | Review vào lại | Theo kỳ |

> Sau P1: **không tự mở lại** cho tới khi người xác nhận root-cause + reconcile khớp.

## PHỤ LỤC B — CHECKLIST NGÀY/TUẦN/THÁNG

Tham chiếu §13.

**Ngày (15 phút):** heartbeat + reconcile; alert tồn; funding thực vs kỳ vọng; predicted FR; OI/basis/giá; buffer Futures; lệnh treo; thông báo sàn.

**Tuần:** re-rank universe; decay/spike; PnL attribution; correlation/exposure; slippage thực; lịch unlock; test alert/kill/dead-man; BNB 2 ví.

**Tháng:** hiệu suất vs kỳ vọng; model drift; audit log 20 lệnh; chaos drill; post-mortem; siết risk budget nếu cần.

## PHỤ LỤC C — THAM SỐ CHỐT (theo §15.2)

```yaml
capital: 500
spot: 235
futures: 265          # margin 235 + buffer 30
leverage: 1
coins: 3
notional_per_leg: 235
notional_per_coin: 78
fee_roundtrip: 0.35   # gồm slippage 0.11%
net_drag_apr: 9.13    # điểm APR
baseline_apr: 10.95
apr_forward_min: 20
apr_forward_max: 60
excess_min: 15
net_apr_min: 20
pos_ratio_14d_min: 0.85
zero_rate_14d_max: 0.10
cv_14d_max: 2.0
decay_7d_vs_14d_min: 0.6
slippage_max: 0.2
volume_min_usd: 5000000
dd_kill: 0.20
heartbeat_s: 30
reconcile_s: 60
deadman_s: 300
max_order_notional: 125
infra: existing_vps          # $0
ui_transport: sse
ui_refresh_s: 1
ui_candidates_s: 60
ui_allow_manual_orders: false
ui_stop_requires_confirm: true
```

## PHỤ LỤC D — SIGN-OFF

| Phase | Người thực hiện | Ngày | Kết quả | Người review |
|---|---|---|---|---|
| 0 | | | ⬜ | |
| 1 | | | ⬜ | |
| 2 | | | ⬜ | |
| 3 | | | ⬜ | |
| 4 | | | ⬜ | |
| 5 | | | ⬜ | |
| 6 | | | ⬜ | |
| 7 | | | ⬜ | |
| 8 | | | ⬜ | |

---

## NHẬT KÝ THAY ĐỔI TASK

| Phiên bản | Ngày | Thay đổi |
|---|---|---|
| 1.0 | 24/11/2026 | Tạo task từ kế hoạch v2.2: $500, 1x, 3 coin, L3; 9 phase; checklist test + biên bản kết quả từng phase |
| 1.1 | 24/11/2026 | Thêm **UI realtime trên VPS sẵn có** (§7.4): UI read-only Phase 2, positions/PnL/STOP Phase 3; bỏ phương án UPS/4G; thêm **quy tắc cấm tạo file trước phase**; cập nhật test (0: 13, 2: 16, 3: 24, 4: 13, 5: 11, 7: 12, 8: 11) |
| 1.2 | 25/11/2026 | Chuyển Testnet → **Demo Trading**; thêm §0.1a (3 loại key); triển khai VPS `/opt/funding-bot` (user funding, systemd, backup); ghi kết quả P0 5✅/2❌/1🟡/1⬜/4⏭️; thêm guard read-only + ngoại lệ firewall VPS dùng chung |

---

*Hết task. Cập nhật kết quả test trực tiếp vào file này sau mỗi phase; không tạo file kết quả rời.*
