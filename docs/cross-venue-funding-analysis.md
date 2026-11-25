# Phân tích cross-exchange funding arbitrage (perp–perp)

**Ngày:** 25/11/2026  
**Bối cảnh:** Phase 1 spot+perp thất bại vì 4 mã funding cao (EVAA, AVAAI, PIEVERSE, PHAROS) không có Spot trên Binance.  
**Câu hỏi:** có thể long perp sàn A + short perp sàn B cùng coin để ăn chênh funding không?

## 1. Kết luận ngắn

- **Kỹ thuật: khả thi.** Cả 4 mã đều có perp trên Bybit; một số có thêm Bitget/OKX/Gate/MEXC.
- **Kinh tế: biên, chưa đủ để thay thế kế hoạch hiện tại.** Chênh funding Binance–Bybit trung bình 180 ngày chỉ **8,5–13,1pp/năm**; sau phí, slippage và hệ số 2 leg, net trên vốn thường **0–4%/năm**, dưới mục tiêu 9%.
- Chênh 14 ngày hiện tại lớn hơn (12–49pp) nhưng **không bền**; chỉ một số cửa sổ đủ lời.
- **Đề xuất:** làm **Phase 1b cross-venue backtest 6–12 tháng** với Binance + Bybit trước; chỉ cân nhắc Bitget/OKX/Gate/MEXC sau khi định lượng rủi ro venue. Chưa xây automation.

## 2. Cơ chế và công thức

Hai lệnh cùng coin, cùng size:
- **Short perp sàn A** (funding cao hơn) — nhận funding.
- **Long perp sàn B** (funding thấp hơn) — trả funding.
- Delta giá gần 0; PnL chủ yếu từ **chênh funding** + **chênh basis giữa 2 sàn**.

```text
funding_net = funding_nhận_A − funding_trả_B        (trên cùng notional)
pnl_basis   ≈ N × (basis_exit − basis_entry)         (basis = P_B/P_A − 1)
pnl         = funding_net + pnl_basis − fees − slippage
```

Nếu long sàn B rẻ hơn (basis âm) và basis hội tụ về 0, long B/short A có thêm lời một lần; ngược lại là rủi ro.

**Quy đổi APR trên vốn** (3 coin, $78/leg/vị thế, 2 leg, buffer $30):

```text
net_APR_vốn ≈ 0,47 × (differential_APR − cost_roundtrip × 365 / holding_days)
```

Với cost round-trip 0,35–0,50% (4 lần taker + slippage):
- Giữ 14 ngày: cần differential **~28–32pp** để đạt 9%/năm trên vốn.
- Giữ 30 ngày: cần **~23–25pp**.
- Giữ 60 ngày: cần **~21–22pp**.

## 3. Dữ liệu thực tế

### 3.1 Snapshot 14 ngày (25/11/2026)

APR 14 ngày tính bằng tổng funding/14 ngày × 365; basis so với Binance.

| Symbol | Binance APR | Bybit APR | Bitget | OKX | Gate | MEXC | Basis Bybit |
|---|---:|---:|---:|---:|---:|---:|---:|
| EVAA | 60,2% | 36,7% | 11,0% | — | 19,0% | 59,9% | −0,382% |
| AVAAI | 38,1% | 11,8% | — | — | 25,8% | 37,2% | −0,066% |
| PIEVERSE | 33,2% | 20,7% | 18,1% | 12,1% | 9,4% | 33,2% | +0,081% |
| PHAROS | 34,7% | 11,3% | — | — | — | 34,9% | −0,062% |

- Snapshot cho thấy chênh lớn: EVAA–Bitget ~49pp, AVAAI–Bybit ~26pp, PHAROS–Bybit ~23pp.
- Nhưng đây chỉ là **một thời điểm**, không phải edge bền.

### 3.2 Differential 180 ngày: Binance − Bybit

| Symbol | Mean | Median | P10 | P90 | % ngày >9,1pp | % ngày >28pp |
|---|---:|---:|---:|---:|---:|---:|
| EVAA | −2,9% | −2,5% | −20,5% | +12,4% | 18% | 0% |
| AVAAI | **+13,1%** | +10,8% | +3,2% | +27,9% | 57% | 9% |
| PIEVERSE | +8,5% | +8,1% | +3,0% | +13,8% | 41% | 0% |
| PHAROS | **+12,0%** | +14,5% | −0,5% | +34,0% | 75% | 14% |

- EVAA trung bình **âm** (Bybit funding cao hơn Binance); snapshot 14 ngày đã đảo chiều.
- AVAAI/PHAROS khá hơn nhưng mean 12–13pp vẫn dưới ngưỡng 23–25pp cho hold 30 ngày.
- `% ngày >28pp` chỉ 0–14% → edge không đủ thường xuyên.

### 3.3 Differential 90 ngày: Binance − Bitget (chỉ 2 mã có lịch sử)

| Symbol | Mean | Median | P10 | P90 | % ngày >9,1pp | % ngày >28pp |
|---|---:|---:|---:|---:|---:|---:|
| EVAA | **+18,9%** | +17,2% | −3,0% | +40,2% | 72% | 28% |
| PIEVERSE | +9,3% | +10,9% | +0,3% | +18,3% | 57% | 0% |

- EVAA–Bitget hấp dẫn hơn về số liệu, nhưng Bitget là venue rủi ro cao hơn, lịch sử chỉ 90 ngày, thanh khoản mỏng hơn.
- Không nên dồn vốn lớn vào venue nhỏ khi chưa có backtest 6–12 tháng.

## 4. Rủi ro chính (khác spot+perp)

| Rủi ro | Ảnh hưởng | Giảm thiểu |
|---|---|---|
| **Basis giữa 2 sàn** | 0,3–0,4% hiện tại; đủ xóa 1 tháng funding nếu đi ngược | Entry chỉ khi basis thuận/trung tính; stop khi basis z > 3σ |
| **Thanh lý 1 leg** | Giá một sàn chạy mạnh → leg còn lại mất hedge | 1x, buffer 15–20% (không phải 6%), theo dõi margin từng sàn |
| **Funding flip** | Differential đảo dấu; lỗ nhanh | Exit khi differential <10pp hoặc âm 2 kỳ |
| **Lệch giờ/interval** | Binance/Bybit 4h; Gate 8h; dòng tiền lệch | Chuẩn hóa theo tổng 24h/14d, không theo 1 kỳ |
| **Counterparty** | Bitget/Gate/MEXC rủi ro cao hơn Binance/Bybit | Ưu tiên Binance+Bybit; giới hạn vốn/venue |
| **Chuyển tiền** | Phí rút, mạng, trễ khi cần top-up | Giữ collateral 2 bên; hạn chế transfer |
| **Execution 2 leg** | Một leg khớp, leg kia fail → lệch | Executor retry/rollback, `clientOrderId` (Phase 3) |
| **Vận hành** | 2 account, 2 API key, IP whitelist, clock sync, reconcile | Thêm adapter + reconciler cross-venue |
| **Thuế/ KYC/ vùng** | Khác nhau giữa sàn | Kiểm tra trước khi mở tài khoản |

## 5. So sánh 3 phương án

| Phương án | Ưu | Nhược | Kết luận |
|---|---|---|---|
| Spot + perp Binance | 1 sàn, ít rủi ro counterparty | Không có Spot cho coin funding cao; Phase 1 fail | **Không khả thi** với universe hiện tại |
| **Perp–perp cross-venue** | Mở được universe perp-only; delta gần 0 | Thêm basis/venue/transfer risk; differential biên | **Khả thi kỹ thuật, kinh tế biên** |
| Perp-only | Đơn giản, không cần sàn 2 | Mất delta-neutral; rủi ro giá | **Không khuyến nghị** |

## 6. Đề xuất Phase 1b

Trước khi động vào Phase 2:

1. **Venue:** Binance + Bybit (Tier-1) là bắt buộc; Bitget/OKX/Gate/MEXC là optional sau khi có số liệu.
2. **Dữ liệu:** 6–12 tháng funding + 4h price/basis + fee + depth + funding interval cho 4 mã (và mở rộng danh sách perp-only).
3. **Backtest:** chọn hướng động (short sàn funding cao), entry khi differential ≥30pp (14d) hoặc ≥24pp (30d), hold 30–60 ngày, tính basis PnL, phí 4 lần, slippage, transfer delay, venue outage.
4. **Gate:** net APR ≥9% trên vốn; DD ≤4%; ≥70% tháng dương; deployment ≥50%; chỉ khi đó mới xây automation.
5. **Pilot nếu pass:** tối đa 3 coin, 1x, buffer 15–20%, ưu tiên Binance+Bybit; không dồn >20% vốn vào venue nhỏ.

## 7. Kỳ vọng ở $500

Với differential trung bình 12–13pp (AVAAI/PHAROS), hold 30 ngày, cost 0,4%:
- net ≈ 0,47 × (13 − 4,9) ≈ **3,8%/năm** ≈ **$1,6/tháng**.
- Chỉ các cửa sổ differential >28pp mới đạt ~9–11%/năm; nhưng chỉ 9–14% số ngày.

Vì vậy cross-venue **chưa đủ hấp dẫn ở $500** so với công vận hành; đáng cân nhắc lại ở $2.000+ hoặc nếu tìm được cặp venue/coin có differential bền >25pp.

## 8. Cùng Binance có làm 2 lệnh perp ngược nhau được không?

**Được về mặt kỹ thuật, nhưng không tạo funding arbitrage.**

| Cách | Có 2 funding rate khác nhau? | Kết quả |
|---|---|---|
| Long + short **cùng symbol** ở **hedge mode** | Không — cùng một rate | Funding nhận/pay bù trừ, còn phí + spread → lỗ |
| Long + short cùng symbol ở **one-way mode** | Không | Lệnh sau giảm/đảo vị thế, không giữ được 2 chiều |
| 2 tài khoản/sub-account cùng sàn | Không — cùng rate | Net funding = 0, thêm phí |
| **USDT-M perp vs COIN-M perp** | Có — 2 contract khác nhau | Khả thi lý thuyết, nhưng COIN-M chỉ 20 mã (BTC/ETH...), size $100, collateral BTC, inverse; **không có EVAA/AVAAI/PIEVERSE/PHAROS** |
| Perp vs quarterly delivery | Không — quarterly không funding | Là basis trade, không phải funding arb |
| Spot margin short + perp long | Có (funding + borrow) | Chỉ coin có Spot; không dùng được cho perp-only |
| **Cross-exchange perp–perp** | Có — rate khác theo sàn | Khả thi; kinh tế biên (xem trên) |

### Hedge mode trên Binance

- Bật `dualSidePosition=true`; đặt lệnh với `positionSide=LONG` hoặc `SHORT`.
- Có thể giữ cả hai cùng lúc, nhưng:
  - Funding rate áp dụng như nhau cho cả hai phía.
  - Long trả short nhận (khi rate dương); nếu bạn là cả hai, khoản này **tự bù trừ**.
  - Entry price khác nhau chỉ tạo lãi/lỗ spread; phí 2 lần vào + 2 lần ra làm kết quả âm.
- Hedge mode hữu ích để **hedge một vị thế khác** hoặc chạy 2 chiến lược độc lập, **không** để ăn funding.
- Bot hiện tại dùng **one-way mode** (`dualSidePosition=false`) theo kế hoạch; không nên đổi sang hedge mode cho mục tiêu này.

### Kết luận cho 4 mã perp-only

- Cùng contract cùng sàn: **không có edge**.
- COIN-M: **không có** 4 mã này.
- Spot: **không có**.
- Vậy con đường khả thi còn lại là **cross-exchange perp–perp** (Bybit/Bitget/OKX/Gate/MEXC), với các rủi ro đã phân tích.

## 9. Lợi nhuận thực tế & cách tối đa hóa (risk-adjusted)

### 9.1 Ước lượng lợi nhuận

Công thức 30 ngày, cost 0,4%, 3 coin, $500:

```text
net_APR_vốn ≈ 0,47 × (spread − 4,9pp)
```

| Kịch bản | Spread | Net APR vốn | $/tháng |
|---|---:|---:|---:|
| Binance–Bybit, mean 180 ngày | 8,5–13,1pp | 1,7–3,8% | $0,7–1,6 |
| Binance–Bybit, 30 ngày gần nhất | 19,7–29,4pp | 7,0–11,5% | $2,9–4,8 |
| EVAA–Bitget, 30 ngày | 42,2pp | ~17,5% | ~$7,3 |
| INX–Gate, 30 ngày | 62,6pp | ~27,1% | ~$11,3 |
| JCT–OKX, 30 ngày (lịch sử ngắn) | 50,7pp | ~21,5% | ~$9,0 |

**Đọc đúng:** 30 ngày gần nhất là regime tốt; 180 ngày Binance–Bybit chỉ 8,5–13,1pp. Không được lấy spread 42–63pp làm giả định bền.

### 9.2 Screen mở rộng — đòn bẩy lớn nhất

Screen 16 mã perp-only funding cao nhất của Binance trên 5 sàn (snapshot 14 ngày):

| Symbol | Binance | Sàn tốt nhất | Spread | Hướng |
|---|---:|---|---:|---|
| EVAA | 60,2% | Bitget 11,1% | **49,1pp** | short Binance / long Bitget |
| INX | 23,7% | Gate 71,3% | **47,6pp** | short Gate / long Binance |
| AVAAI | 38,1% | Bybit 11,8% | 26,3pp | short Binance / long Bybit |
| TA | 36,8% | Bybit 11,0% | 25,8pp | short Binance / long Bybit |
| PIEVERSE | 33,2% | Gate 9,4% | 23,8pp | short Binance / long Gate |
| JCT | 34,2% | OKX 10,6% | 23,6pp | short Binance / long OKX |
| PHAROS | 34,7% | Bybit 11,3% | 23,4pp | short Binance / long Bybit |
| XMR | 16,5% | Bitget 35,1% | 18,6pp | short Bitget / long Binance |

30 ngày gần nhất xác nhận một phần: EVAA–Bitget 42,2pp; INX–Gate 62,6pp; AVAAI–Bybit 29,4pp; TA–Bybit 26,5pp. Nhưng INX–Gate/JCT–OKX có lịch sử ngắn, thanh khoản và venue risk cao.

### 9.3 Các đòn tăng lợi nhuận, xếp theo hiệu quả/rủi ro

1. **Screen toàn universe + nhiều sàn** (lớn nhất): thay vì cố định 4 mã, mỗi ngày chọn top 3 spread 14d/30d sau chi phí. Đây là cách tìm 20–60pp thay vì 8–13pp.
2. **Ngưỡng entry động + giữ 30–60 ngày**: chỉ vào khi spread ≥25–30pp (30d) hoặc ≥15pp (60d); thoát khi spread <10pp hoặc đảo dấu. Hold dài amortize phí; hold 14 ngày dễ lỗ vì phí.
3. **Giảm phí**: maker/limit thay taker, VIP tier, BNB/token discount, rebate. Mỗi 0,1% cost giảm thêm ~1,2pp APR trên vốn (hold 30d).
4. **Chọn venue theo risk-adjusted spread**: Binance+Bybit Tier-1; Bitget/Gate/MEXC chỉ khi spread cao hơn đủ bù rủi ro; giới hạn ≤20% vốn/venue nhỏ.
5. **Basis-aware execution**: ưu tiên long sàn đang rẻ hơn (basis âm), tránh entry khi basis >0,2–0,3% bất lợi; exit nếu basis z >3σ.
6. **Tự động hóa 2 leg**: `clientOrderId`, retry/rollback, đồng bộ giờ; giảm slippage và leg risk — nhưng chỉ sau Phase 1b pass.
7. **Đòn bẩy 2x**: chỉ sau gate 60–90 ngày; tăng return ~2x nhưng DD/liquidation cũng ~2x. Ở $500 **không nên**.
8. **Tối ưu chuyển tiền**: giữ collateral cả 2 sàn, gom transfer, chọn mạng phí thấp; tránh rút/nạp nhiều lần.

### 9.4 Cấu hình đề xuất nếu làm Phase 1b

- 3 coin, 1x, Binance + Bybit là chính; thêm 1 venue nhỏ tối đa 20% vốn.
- Entry: spread 30d ≥25pp (hoặc 14d ≥30pp); hold 30 ngày; exit <10pp hoặc basis z >3.
- Buffer 15–20% (không phải 6%) vì 2 sàn/2 margin.
- Kỳ vọng risk-adjusted: **5–10%/năm** ở regime bình thường, **10–18%/năm** trong cửa sổ tốt; không cam kết.
- Gate: 6–12 tháng cross-venue backtest, net APR ≥9% vốn, DD ≤4%, ≥70% tháng dương, deployment ≥50%.

### 9.5 Điều không nên làm

- Không tăng leverage để "tối đa" — biến chiến lược funding thành cược basis/liquidation.
- Không chase spread snapshot 50–60pp nếu chưa kiểm tra 30/90/180 ngày.
- Không dồn vốn vào Bitget/Gate/MEXC chỉ vì spread cao.
- Không hạ ngưỡng APR/net để có trades; sẽ lặp lại lỗi Phase 1.

## 10. Tiền ở 2 sàn: các cách kiếm tốt hơn — xếp hạng

### 10.1 Cách tốt nhất: Spot + perp cross-venue

Thay vì 2 perp, dùng **long Spot trên sàn B + short perp trên Binance**. Spot leg không trả funding → ăn **toàn bộ funding Binance**, không chỉ phần chênh.

Ví dụ 30 ngày, cost 0,5%, 3 coin, $500:

| Coin | Spot ở đâu | Funding Binance 30d | Net APR vốn* | $/tháng | Ghi chú |
|---|---|---:|---:|---:|---|
| PIEVERSE | **Bybit** / Gate / MEXC | 29,4% | ~10,9% | ~$4,5 | Bybit Tier-1, spot $8,1M/ngày |
| TA | **Bybit** / Gate / MEXC | 38,1% | ~15,0% | ~$6,3 | Bybit spot $0,73M/ngày — kiểm tra depth |
| EVAA | Bitget / Gate / MEXC | 53,2% | ~22,1% | ~$9,2 | Venue risk cao hơn |
| AVAAI | Gate / MEXC | 40,8% | ~16,3% | ~$6,8 | Venue risk |
| INX | Gate / MEXC | 25,7% | ~9,2% | ~$3,8 | Venue risk |
| PHAROS | **Không có Spot** | 33,0% | perp–perp ~7,0% | ~$2,9 | Chỉ perp–perp |

*30 ngày, cost 0,5%, hệ số vốn 0,47; chưa tính basis.

**Điểm mạnh:** ăn full funding (29–53% ở regime hiện tại), spot leg không funding, dễ hiểu.
**Điểm yếu:** vẫn 2 sàn; spot custody/thanh khoản; basis spot–perp; nếu funding flip âm phải thoát.

### 10.2 Fallback: Perp–perp cross-venue

Dùng khi coin **không có Spot** (PHAROS, XMR) hoặc khi funding sàn kia cao hơn hẳn (INX–Gate):

| Cặp | Spread 30d | Net APR vốn* | $/tháng | Ghi chú |
|---|---:|---:|---:|---|
| INX–Gate | 62,6pp | ~27,1% | ~$11,3 | Gate funding cao hơn; venue risk |
| EVAA–Bitget | 42,2pp | ~17,5% | ~$7,3 | Bitget risk |
| AVAAI–Bybit | 29,4pp | ~11,5% | ~$4,8 | Tier-1 |
| TA–Bybit | 26,5pp | ~10,2% | ~$4,2 | Tier-1 |
| PHAROS–Bybit | 19,7pp | ~7,0% | ~$2,9 | Không spot |
| JCT–OKX | 50,7pp | ~21,5% | ~$9,0 | Lịch sử ngắn, OKX risk |

*30 ngày, cost 0,4%, hệ số 0,47.

### 10.3 Xếp hạng risk-adjusted

| Hạng | Cách | Kỳ vọng | Rủi ro | Độ phức tạp | Kết luận |
|---|---|---|---|---|---|
| **1** | **Spot + perp cross-venue** (Binance perp + Bybit/Gate spot) | 5–22% APR tùy regime | Trung bình–cao (2 sàn, spot custody, basis) | Trung bình | **Tốt nhất nếu spot đủ thanh khoản** |
| **2** | **Perp–perp cross-venue dynamic** | 5–27% trong cửa sổ tốt; 1–4% bình thường | Cao (basis/venue/transfer) | Cao | Fallback cho coin không spot |
| **3** | **USDT flexible earn trên idle collateral** | 3–8% APR | Thấp–trung bình (counterparty) | Thấp | **Dùng cho buffer/idle**, không phải edge chính |
| 4 | Basis/quarterly futures cross-venue | Episodic, 5–15% | Trung bình | Cao | Chỉ khi có basis rõ |
| 5 | Same-exchange spot+perp majors | 2–6% | Thấp | Thấp | Funding thấp, thường không đáng |
| 6 | Lending/borrow rate arb | Biến động | Trung bình–cao | Cao | Không phù hợp $500 |
| 7 | Grid/market making | Không delta-neutral | Cao | Cao | **Loại** cho mục tiêu funding |
| 8 | Dual investment/structured | 5–15% headline | Lockup/principal | Thấp | **Không** dùng vốn vận hành |
| 9 | 2x leverage | Gấp đôi return | Gấp đôi DD/liquidation | Thấp | **Không** ở $500 |

### 10.4 Cấu hình 2 sàn khuyến nghị

**Nếu chỉ dùng 2 sàn: Binance + Bybit**
- Spot + perp: PIEVERSE, TA (Bybit spot).
- Perp–perp: AVAAI, EVAA, PHAROS (Bybit perp).
- 3 coin, 1x, buffer 15–20%; idle USDT để flexible earn.
- Kỳ vọng: 5–10%/năm regime bình thường, 10–15% trong cửa sổ tốt.

**Nếu chấp nhận sàn thứ 3 (Gate/Bitget/MEXC)**
- Thêm spot + perp cho EVAA, AVAAI, INX.
- Tăng return nhưng tăng counterparty/liquidity risk; giới hạn ≤20% vốn/venue nhỏ.

### 10.5 Nguyên tắc tối đa hóa

1. **Tính cả 2 cấu trúc cho mỗi coin**: spot+perp vs perp–perp; chọn net cao hơn **sau phí, slippage, venue risk**.
2. **Chỉ vào khi spread đủ lớn**: 30d ≥25pp (perp–perp) hoặc funding Binance ≥25–30% (spot+perp); hold 30 ngày.
3. **Ưu tiên Tier-1**: Binance + Bybit; venue nhỏ chỉ khi spread bù được rủi ro.
4. **Kiểm tra depth spot** cho size $78; TA spot Bybit mỏng hơn PIEVERSE.
5. **Basis-aware**: tránh long spot/perp khi basis bất lợi >0,2–0,3%; exit nếu basis z >3σ.
6. **Idle yield**: giữ buffer trong flexible earn, nhưng phải rút được ngay khi cần margin.
7. **Không leverage, không chase spread snapshot, không hạ chuẩn.**

## 11. Rotation: chỉ vào coin FR cao, hết thì nhảy sang coin khác

### 11.1 Khi nào rotation có lợi?

Rotation là **lớp phân bổ vốn** trên cùng edge funding, không tạo ra edge mới.

- **Có lợi** khi: có nhiều coin FR cao > ngưỡng; FR decay/flip thường xuyên; hệ thống thoát đúng lúc và tìm được coin mới.
- **Không có lợi** khi: universe ít candidate; FR cao đã ở cuối chu kỳ; xoay quá nhanh làm phí ăn hết funding; basis/venue risk tăng.

### 11.2 Chi phí rotation quyết định tất cả

Mỗi lần xoay = 1 round-trip (vào + ra) trên notional; cost 0,35–0,50%.

```text
drag_APR_notional = cost_roundtrip × 365 / holding_days
net_APR_vốn       ≈ 0,47 × (FR − drag)
```

| Hold trung bình | Drag @ cost 0,4% | FR tối thiểu để net 9% vốn |
|---|---:|---:|
| 7 ngày | 20,9pp | ~40pp |
| 14 ngày | 10,4pp | ~29,6pp |
| 30 ngày | 4,9pp | ~24,0pp |
| 60 ngày | 2,4pp | ~21,6pp |

**Kết luận:** không nên xoay nhanh hơn 14 ngày; lý tưởng giữ 30–60 ngày hoặc chỉ thoát khi FR thật sự decay/flip. Xoay 7 ngày cần FR >40% mới đáng.

### 11.3 Binance spot+perp rotation: không giải quyết được bottleneck

Phase 1 cho thấy universe Binance spot+perp (104 symbol) gần như **không có candidate**:
- Snapshot 24/11: 0 mã pass.
- 180 ngày: 1 episode.
- 4 mã FR cao (EVAA/AVAAI/PIEVERSE/PHAROS) **không có Spot Binance**.

→ Rotation trong universe này **không tăng lợi nhuận đáng kể**, vì không có gì để xoay sang. Vấn đề là **nguồn candidate**, không phải logic rotation.

### 11.4 Cross-venue spot+perp rotation: khả thi hơn

Nếu Spot nằm ở sàn khác, rotation có nguyên liệu:

| Coin | Spot venue | FR Binance 30d | Hold 30d, net ước tính |
|---|---|---:|---:|
| EVAA | Bitget/Gate/MEXC | 53,2% | ~22% |
| AVAAI | Gate/MEXC | 40,8% | ~16% |
| TA | Bybit/Gate/MEXC | 38,1% | ~15% |
| PIEVERSE | Bybit/Gate/MEXC | 29,4% | ~11% |
| INX | Gate/MEXC | 25,7% | ~9% |

Rotation có thể giữ 3 slot được lấp khi coin này decay và coin khác xuất hiện; deployment tăng từ ~1% (Phase 1) lên 50–80% trong regime tốt.

**Nhưng:** đây là số 30 ngày gần nhất; 180 ngày Binance–Bybit thấp hơn nhiều. Cần backtest 6–12 tháng.

### 11.5 Thiết kế rotation đúng

1. **Universe:** Binance perp + Spot trên Bybit/Gate/Bitget/MEXC; chỉ coin có spot depth đủ cho $78.
2. **Signal:** FR 7d/14d, forward = min(7d,14d), pos ratio, CV, decay, predicted, net sau phí, basis.
3. **Entry/exit hysteresis:** vào khi net ≥30% (hoặc FR ≥30%); thoát khi predicted <0,5×trailing, FR âm 2 kỳ, hoặc net <10–15%. **Không xoay chỉ vì có coin khác cao hơn** nếu coin hiện tại vẫn tốt.
4. **Min hold 14–30 ngày**, max 1–2 rotation/tuần, cooldown 7 ngày sau exit.
5. **So sánh 2 cấu trúc mỗi coin:** spot+perp (full funding) vs perp–perp (spread); chọn net/risk cao hơn.
6. **Backtest walk-forward** 6–12 tháng, gồm phí/slippage/basis/transfer; so sánh static vs rotation.
7. **Gate:** net APR ≥9% vốn, DD ≤4%, ≥70% tháng dương, deployment ≥50%, turnover cost chấp nhận.

### 11.6 Kết luận rotation

- **Binance-only spot+perp:** rotation **không** tăng đáng kể vì thiếu candidate.
- **Cross-venue spot+perp:** rotation **có thể** tăng lợi nhuận (deployment + chọn coin mới), nhưng chỉ khi giữ đủ lâu và có candidate bền.
- **Không xoay nhanh:** 7 ngày cần FR >40%; 30 ngày cần >24%; 60 ngày cần >21,6%.
- **Không chạy rotation trước Phase 1b:** cần backtest cross-venue để chứng minh net APR và DD.

---

*Số liệu snapshot 25/11/2026; 180d Binance–Bybit; 30d cho các cặp mở rộng. Chưa phải backtest đầy đủ cross-venue — cần Phase 1b trước khi kết luận đầu tư.*
