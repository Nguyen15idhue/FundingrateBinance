# KẾ HOẠCH HỆ THỐNG HARVEST FUNDING RATE (FR)

**Phiên bản:** 2.2  
**Ngày:** 24/11/2026  
**Phạm vi:** Binance USDⓈ-M Perpetual  
**Vốn khởi điểm:** **$500** (v1.0: 200 triệu VND ~ $7.500)  
**Mục tiêu:** Thu funding rate delta-neutral, **L3 tự động hoàn toàn có giám sát**, hướng tới vận hành ổn định.

> **Thay đổi chính ở v2.x:** vốn khởi điểm $500; bỏ lộ trình chạy chậm (alert-only → shadow → canary nhiều tháng); chỉ **backtest + xây automation + dry-run ~3–4 tuần** rồi **live luôn $500**; **L3 ngay từ lệnh live đầu tiên**, không bán tự động/thủ công; **1x trước, 2x chỉ sau 60–90 ngày đạt gate**; thêm bảng nâng vốn $1k/$2k/$5k. Lý do và ngân sách thiệt hại: §12.5.

> **Miễn trừ:** Tài liệu này là phân tích kỹ thuật và kế hoạch vận hành, không phải lời khuyên đầu tư. Mọi số liệu là snapshot tại thời điểm ghi và sẽ thay đổi. Chỉ dùng vốn chấp nhận mất được.

---

## MỤC LỤC

1. Tóm tắt điều hành
2. Bản chất chiến lược
3. Bài học từ dữ liệu thật
4. Chi phí ăn mòn & break-even
5. Bộ lọc & scoring
6. Kết quả backtest
7. Kiến trúc hệ thống
8. Mức tự động hóa
9. AI layer
10. Quản trị rủi ro
11. Kế hoạch triển khai
12. Kỳ vọng lợi nhuận & vốn
13. Checklist vận hành
14. Sai lầm cần tránh
15. Phụ lục

---

## 1. TÓM TẮT ĐIỀU HÀNH

**Chiến lược:** Long spot + short perp (FR dương), hoặc short spot (vay) + long perp (FR âm), giữ delta-neutral, thu funding mỗi kỳ.

**Kỳ vọng thực tế:** **9–12% APR trên vốn** ở cấu trúc **1x + buffer nhỏ** (không phải 70%+), biên độ 0–35%, có tháng âm nhỏ, tail hiếm nhưng đậm. Con số 20–25% ở v1.0 giả định notional = 0,75 vốn, tương đương perp ~3–4x và gần như không buffer — không khớp quy tắc 1–2x.

**Vốn khởi điểm v2.2: $500 — cấu hình 1x**

| Khoản | Số tiền |
|---|---|
| Spot (leg hedge) | **$235** |
| Futures | **$265** |
| ├ Margin short perp (1x) | $235 |
| └ Buffer USDT tự do | $30 |
| Notional mỗi leg | **$235** (0,47 × vốn), 3 coin × ~$78 |

| Chỉ số | Giá trị |
|---|---|
| Kỳ vọng trung tâm | **$4–5/tháng** (~100–125k VND), đã chiết khấu quy mô nhỏ |
| Dải bình thường | $0 – $8/tháng |
| Tháng xấu | −$5 đến −$10 |
| Tail (basis shock/halt) | −$25 đến −$60 |
| Mất toàn bộ do sàn | −$500 |
| Kill switch drawdown | −$100 (−20% vốn) |

**Quyết định triển khai:** **chỉ backtest + xây automation + mô phỏng 3–4 tuần, rồi live luôn $500.** Không chạy alert-only 2 tháng, không shadow dài, không canary $50–100 kéo dài. Đánh đổi được chấp nhận vì xác suất lỗ thấp và độ lớn lỗ nhỏ; **$500 là học phí** để đổi lấy 3–5 tháng.

**Mức tự động hóa:** **L3 — tự động hoàn toàn có giám sát** ngay từ lệnh live đầu tiên. Máy tự vào/ra 2 leg, rebalance, transfer buffer và kill switch; người chỉ giám sát, audit và xử lý bất thường. **Không có giai đoạn bán tự động hay xác nhận tay từng lệnh** (§8).

**Điều kiện tiên quyết:**
- Hold **1–4 tuần** mỗi episode (không lướt vài giờ).
- **1x giai đoạn đầu**; 2x chỉ sau 60–90 ngày đạt gate; không bao giờ > 3x.
- **3 coin ở $500** → 5/7/9 coin ở $1k/$2k/$5k.
- Bộ lọc + rolling exit quan trọng hơn chọn coin.
- Ngân sách "học phí" 3 tháng đầu: **$50–150**. Chạm ngưỡng → dừng, review, **không nạp thêm để gỡ**.

**Ba câu chốt:**
1. Funding rate đo **crowding/vị thế**, không đo biến động giá.
2. Lợi nhuận đến từ **thời gian**, không từ biến động giá.
3. Đây là **bán bảo hiểm rủi ro giá** (negative skew), không phải đầu tư an toàn.

---

## 2. BẢN CHẤT CHIẾN LƯỢC

### 2.1 Funding rate là gì

FR là khoản thanh toán định kỳ giữa long và short trên perp, để neo giá perp về spot.

- **FR dương:** long trả short.
- **FR âm:** short trả long.
- Sàn **không thu phí** funding; tiền chuyển trực tiếp giữa trader.

Công thức Binance:

```
F = [P + clamp(I − P, +0,05%, −0,05%)] / (8 / N)
```

Trong đó:
- `P` = average premium index
- `I` = interest rate 8h (0,01% cho hầu hết symbol)
- `N` = funding interval (giờ)

**Hệ quả quan trọng:** với interval 4h, baseline = `0,01% / 2 = 0,005%`. Nghĩa là **FR gần như luôn ≥ 0,005% về mặt cơ học**, kể cả khi premium ≈ 0. Vì vậy "chuỗi dương" bị thổi phồng bởi baseline — phải tách phần **excess** (FR − baseline) mới thấy crowding thật.

### 2.2 Delta-neutral

Với `X` coin spot + `X` coin perp:

```
PnL spot = X × (S_T − S_0)
PnL perp = −X × (F_T − F_0)

Net giá = X × (Basis_0 − Basis_T)
```

→ **Giá tăng/giảm bao nhiêu cũng bù nhau.** Cái còn lại chỉ là **thay đổi basis**. Lợi nhuận thực = funding − chi phí ± basis.

> **Không cộng funding và basis gain như hai nguồn thu.** Chúng là hai mặt của cùng một đồng xu. Giả định an toàn: chỉ tính funding, coi basis là rủi ro.

### 2.3 FR dương vs FR âm

| Tiêu chí | FR dương | FR âm |
|---|---|---|
| Cách ăn | Long spot + short perp | Short spot (vay) + long perp |
| Hedge cần gì | Mua spot — ai cũng làm được | **Vay coin** — hạn chế |
| Chi phí hedge | ~0 | Borrow 0,02–0,5%/ngày |
| Leg có margin risk | Chỉ perp khi giá tăng | Perp khi giá giảm + margin spot khi giá tăng |
| Spot leg bị liquidate? | Không | **Có** |
| Tần suất | Thường xuyên, bền | Hiếm, theo đợt sập |
| APR điển hình | 10–100% | 100–1.500% nhưng ngắn |
| Capacity | Lớn | Nhỏ |
| **Phù hợp retail** | **Mặc định** | Chỉ khi có hạ tầng borrow |

### 2.4 Negative skew — mô hình đúng

| | Trade định hướng | Ăn FR delta-neutral |
|---|---|---|
| Rủi ro giá | Toàn bộ, −100% | Gần 0 |
| Rủi ro basis | Không | **Có** |
| Rủi ro funding flip | Không | **Có** |
| Tần suất lỗ | Thường xuyên | **Hiếm** |
| Độ lớn khi lỗ | Trung bình | **Có thể rất đậm** |
| Phân phối | Gần đối xứng | **Nhiều lãi nhỏ + ít lỗ lớn** |

---

## 3. BÀI HỌC TỪ DỮ LIỆU THẬT

### 3.1 PLAY — FR dương bền, capacity nhỏ

| Chỉ số | Giá trị |
|---|---|
| Symbol | PLAYUSDT, interval 4h |
| Lịch sử | **200/200 kỳ dương = 33,3 ngày** |
| 14 ngày | 84/84 dương, tổng 2,6795%, avg 0,0319%/4h |
| APR gộp | **69,9%** |
| Phân bố | min 0,005%, median 0,0234%, p90 0,0665%, max 0,1196% |
| Baseline cơ học | 0,42% (15,7% tổng) → excess thật 2,2595% (~59% APR) |
| Volume 24h | $1,79M |
| OI | ~$2,44M |
| Break-even | 10,7 kỳ (~43h) chỉ tính phí |

**Mô phỏng $10k, 14 ngày:**
- Funding: $267,95
- Phí: $34, slippage $15, opp cost $20,46
- **Net: $198,49 = 1,98% notional = 38,8% APR trên $13,33k vốn**

**Bài học:**
- Edge nằm ở **duration**, không phải level.
- "14 ngày dương" một phần là baseline cơ học.
- Capacity thật chỉ **$5–20k**.
- Ở $500 (1x): cùng episode chỉ vào được **~$78 notional/coin** → funding ~$2,1/14 ngày, phí ~$0,27. Vẫn đáng làm vì mục tiêu là **học + xác nhận khớp lệnh**, không phải lãi.

### 3.2 INIT — FR âm sâu, mirror case

| Chỉ số | Giá trị |
|---|---|
| Symbol | INITUSDT, interval **4h → 1h** (đổi 10/11 16:00) |
| Lịch sử | **332/332 kỳ âm** trong 14 ngày |
| Tổng 14 ngày | −58,47% |
| APR (trả cho long) | **~1.515%** |
| Giá | −72,5% trong 2 tuần |
| Volume 24h | $21,8M |
| OI | ~$8M |

**Bài học:**
- Trade **đảo chiều**: phải long perp + short spot (borrow).
- Funding cực đoan xuất hiện đúng lúc rủi ro cực đoan.
- Sàn **đổi interval giữa chừng** khi vol tăng — phải chuẩn hóa lại mọi thống kê.
- Long trần vẫn lỗ dù nhận funding khổng lồ: giá −72,5% > funding.

### 3.3 BULLA — trailing đẹp nhưng decay

| Chỉ số | Giá trị |
|---|---|
| Interval | 4h |
| APR 7d / 14d | 77% / 96% |
| **Predicted** | **11%** (decay ratio 0,14) |
| CV 30d | 11,12 |
| 24h | −10,5% |

**Bài học:**
- **APR trailing cao chưa đủ.** Phải kiểm tra predicted/trailing.
- Predicted < 50% trailing → **decay**, không vào.
- Đây là ví dụ điển hình của "late entry".

---

## 4. CHI PHÍ ĂN MÒN & BREAK-EVEN

### 4.1 Phí Binance (VIP0)

| Leg | Maker | Taker | Maker + BNB | Taker + BNB |
|---|---|---|---|---|
| Spot | 0,100% | 0,100% | 0,075% | 0,075% |
| Futures | 0,020% | 0,050% | 0,018% | 0,045% |

**Round-trip (vào + ra):**

| Cấu hình | Phí |
|---|---|
| Taker cả 2 leg, không BNB | **0,300%** |
| Taker cả 2 leg, có BNB | **0,240%** |
| Maker cả 2 leg, có BNB | **0,186%** |

### 4.2 Các chi phí khác

| Khoản | Ước tính |
|---|---|
| Spread | 0,01–0,10% (meme có thể 0,3%+) |
| Slippage | 0,02–0,50%+ tùy depth |
| Borrow (nếu FR âm) | 0,02–0,5%/ngày |
| Opportunity cost | 3–5%/năm |
| Vốn chia đôi | ×1,1–1,33 |
| VPS | $5–20/tháng |
| Thuế | Tùy quy định |

### 4.3 Cost profiles

| Profile | Cấu hình | c |
|---|---|---|
| **P1 Tối ưu** | Maker + BNB + thanh khoản cao | **0,23%** |
| **P2 Thực tế** | Taker + BNB + mid-cap | **0,34%** |
| **P3 Meme** | Taker + không BNB + book mỏng | **0,80%** |

### 4.4 Break-even

```
Số kỳ hòa vốn: H* = c / FR
Số ngày hòa vốn = 365 × c / APR_notional
Với c = 0,35% → ≈ 128 / APR_notional(%)
```

> **APR trong bảng là APR trên NOTIONAL**, không phải trên vốn. Ở cấu hình 1x (notional = 0,47 × vốn), APR trên vốn = 0,47 × APR notional. Ví dụ notional 24% ↔ vốn ~11,3%: break-even vẫn ~5,3 ngày, nhưng lãi ròng trên vốn chỉ ~11%/năm.

**Hằng số thay đổi theo chi phí thực:**

| c (round-trip) | Cấu hình | Hằng số 365c | Break-even @24% notional |
|---|---|---|---|
| 0,30% | Maker + BNB + slippage 0,11% | 108 | 4,5 ngày |
| **0,35%** | **Taker + BNB + slippage 0,11%** | **128** | **5,3 ngày** |
| 0,41% | Taker không BNB + slippage 0,11% | 150 | 6,3 ngày |

| APR notional | Funding/ngày | Break-even | Để lãi ~2× phí |
|---|---|---|---|
| 10% | 0,027% | 12,8 ngày | ~26 ngày |
| 20% | 0,055% | 6,4 ngày | ~13 ngày |
| 30% | 0,082% | 4,3 ngày | ~9 ngày |
| 50% | 0,137% | 2,6 ngày | ~5 ngày |
| 100% | 0,274% | 1,3 ngày | ~3 ngày |

**Kết luận:** phải giữ **1–4 tuần** với coin mid (20–60% APR notional). Không có "lướt vài giờ ăn FR" với coin ổn định. Với interval 4h, số **kỳ** hòa vốn gấp đôi so với 8h, nhưng số **ngày** không đổi.

> **Kiểm tra thực tế (snapshot 24/11/2026, Binance USDⓈ-M, volume ≥ $5M):** median funding 7 ngày của top-30 volume chỉ **~4,2%/năm trên notional** → break-even ~30 ngày, tức không đáng vào. Trong 80 symbol có funding dương cao nhất, chỉ **19 symbol** đạt bộ lọc 20–60% + ổn định 7 ngày, chủ yếu interval **4h** và là mid/small-cap. Vì vậy "mặc định đứng ngoài" là trạng thái bình thường.

### 4.5 Công thức net APR

```
cost_roundtrip = 0,24% + 2 × slippage_per_side
funding_14d    = forward_APR × 14 / 365
net_14d        = funding_14d − cost_roundtrip
net_APR        = net_14d × 365 / 14
```

---

## 5. BỘ LỌC & SCORING

### 5.1 Universe

- USDⓈ-M PERPETUAL, status `TRADING`.
- Volume 24h ≥ **$5M** (nghiên cứu có thể ≥ $2M).
- Ưu tiên top volume để đảm bảo capacity.

### 5.2 Điều kiện vào (tất cả phải đạt)

| Điều kiện | Ngưỡng | Mục đích |
|---|---|---|
| **APR (forward)** | 20–60% trên **forward = min(APR 7d, APR 14d)** | Đủ bù phí, chưa quá căng |
| **Excess APR** | ≥ 15% (= APR − baseline ~10,95%/năm) | Tránh coin chỉ ăn baseline cơ học |
| **% kỳ cùng dấu (14d)** | ≥ 0,85 | Tránh flip |
| **Zero-rate (14d)** | ≤ 0,10 | Tránh funding chết |
| **CV (14d)** | ≤ 2,0 | Tránh APR cao nhưng giật |
| **Forward APR** | = min(APR 7d, APR 14d) ≥ 20% | Tránh lạc quan |
| **Decay 7d/14d** | APR 7d ≥ 0,6 × APR 14d | Tránh coin đang nguội nhanh (late entry) |
| **Decay check** | predicted ≥ 0,5 × trailing 7d | Tránh late entry |
| **Spike check** | predicted > 3× trailing → không tin | Tránh premium tạm thời |
| **Slippage ở size thực** | ≤ 0,2%/side (size $78–261/leg) | Đảm bảo khớp được |
| **Net APR (14d)** | ≥ 20% (gross − 9,13pp phí) | Đủ lợi nhuận sau phí |

> **Baseline ~10,95%/năm** (I = 0,01%/8h) **vẫn là tiền thật bạn nhận**, nên không trừ khỏi P&L; chỉ dùng để đo crowding: `excess = APR − 10,95%`. Coin 25% APR chỉ có ~14% excess — vẫn vào được nếu net ≥ 20%, nhưng xếp hạng thấp.
>
> **Cap 60% áp lên forward**, không áp lên APR 14d (coin đang nguội sẽ bị phạt oan); bù lại bằng rule decay 7d/14d.

### 5.3 Quy đổi APR → FR mỗi kỳ

| Interval | FR cho 20% APR | FR cho 60% APR |
|---|---|---|
| 1h | 0,0023% | 0,0069% |
| 2h | 0,0046% | 0,0137% |
| 4h | 0,0091% | 0,0274% |
| 8h | 0,0183% | 0,0548% |

### 5.4 Score xếp hạng

```
score = net_APR × stability_factor × liquidity_factor

stability_factor = min(1, 1 / CV)
liquidity_factor = min(1, volume / $20M)
```

Ưu tiên: net_APR cao, CV thấp, volume lớn, decay thấp.

### 5.5 Nhóm coin (từ backtest)

| Nhóm | APR | Đặc điểm | Vai trò |
|---|---|---|---|
| **Low** | < 20% | Ổn định, lãi mỏng | Không đáng làm trụ cột |
| **Mid** | **20–60%** | **Sweet spot** | **Trụ cột** |
| **High** | > 60% | Lãi lớn, bất ổn | Tỷ trọng nhỏ |
| **Choppy** | Bất kỳ | Flip nhiều, hit thấp | **Loại** |

---

## 6. KẾT QUẢ BACKTEST

### 6.1 Backtest 60 ngày (150 coin, 45 selected)

| Nhóm | Số coin | APR TB | Net 60d | Hit rate | Deployed |
|---|---|---|---|---|---|
| Low | 52 | 9% | +1,02% | 87% | 95% |
| **Mid** | 23 | 32% | **+4,40%** | **96%** | 96% |
| High | 4 | 101% | +11,42% | 75% | 90% |
| Choppy | 71 | 31% | +1,18% | **35%** | 62% |

**Portfolio:**

| Portfolio | Net 60d | APR | Hit |
|---|---|---|---|
| Stable rolling | **+4,00%** | **24%** | 100% |
| Stable static | +2,69% | 16% | 100% |
| All universe | +1,89% | 12% | 63% |
| Choppy only | +1,18% | 7% | 35% |

**Phân phối mid (22 coin):** mean +4,80%, median +4,12%, p25 +3,87%, p75 +5,00%, min +3,29%, max +8,89%, **100% dương**.

### 6.2 Backtest 180 ngày (8–10 coin)

| k | Mean | P5 | P95 | Min | Max | Std | DD med | DD xấu nhất |
|---|---|---|---|---|---|---|---|---|
| 8 | +9,50% | +5,30% | +14,09% | +2,83% | +16,93% | 2,73 | −0,19% | −0,72% |
| 10 | +9,53% | +6,01% | +12,94% | +3,66% | +14,74% | 2,18 | −0,19% | −0,33% |
| 15 | +9,54% | +7,15% | +11,18% | +6,05% | +12,16% | 1,18 | −0,16% | −0,17% |

- Tương quan trung bình: **0,11** (đa dạng hóa tốt).
- Top-10 cụ thể: **+12,12%/180 ngày** (~24,6% APR), DD −0,20%.
- **Stress test** (30% xác suất basis shock −2% toàn thị trường): mean +8,89%, DD P5 **−1,99%**, worst **−2,24%**.
- Worst 10-coin sample: +4,16%.

### 6.3 Caveats của backtest

1. **Survivorship bias** — chỉ coin còn sống.
2. **60–180 ngày, một vài regime** — chưa đủ dài.
3. **Không mô hình liquidation, ADL, sàn, delist.**
4. **Basis lấy từ nến 4h/8h** — bỏ qua spike intraday.
5. **Borrow 0,05%/ngày giả định.**
6. **DD −0,2% là quá đẹp** — thực tế sâu hơn.
7. **Ở $500 chỉ 3 coin** — variance cao hơn backtest 8–10 coin; số liệu §6.4 đã chiết khấu thêm 20–30%.

> Đọc backtest là **trần lý thuyết**, chiết khấu 30–50%.

### 6.4 Mô phỏng ở vốn $500

**Cấu hình:** 3 coin, notional $78/coin **mỗi leg**, tổng notional $235/leg (0,47 × vốn); spot $235, margin perp **1x** $235, buffer $30 (6% vốn). Taker + BNB, slippage 0,10%/side, giữ 1–4 tuần.

**Quy đổi từ §6.2:** số ở §6.2 giả định notional = 0,75 vốn, nên nhân thêm **0,47 / 0,75 ≈ 0,63**.

**Kết quả 180 ngày quy ra $** (ngoại suy cho 3 coin):

| Chỉ số | % vốn/180 ngày | $ @ $500 |
|---|---|---|
| Mean | +5,3% | +$26 |
| P5 | +2,5% | +$12 |
| Worst sample | −1,3% | −$6 |
| DD trung vị | −0,2% | −$1 |
| DD stress P5 | −1,5% | −$8 |
| DD stress xấu nhất | −1,9% | −$9 |

**Sau chiết khấu quy mô nhỏ 10–20%** (3 coin thay vì 10, min notional, spread rộng hơn): mean **~+$21–24/6 tháng ≈ $3,5–4/tháng**. §12.1 dùng **$4–5** cho regime trung bình–tốt.

**Ràng buộc chỉ xuất hiện ở quy mô nhỏ:**

| Ràng buộc | Thực tế | Hệ quả |
|---|---|---|
| Min notional futures | $5–20/lệnh | $78/leg vẫn qua, nhưng chia 7+ coin ở $500 là chạm sàn |
| Bước giá BTCUSDT | min qty 0,001 ≈ $100+ | **Không dùng BTC/ETH ở $500** |
| Làm tròn qty | coin giá cao bị thô | Ưu tiên coin $0,1–20 |
| Phí cố định (rút/nạp, network) | $1–2/lần | Gom chuyển tiền 1 lần/tháng |
| VPS | $5/tháng = ~85% lãi $500 | Dùng máy nhà + UPS/4G + dead-man ping ngoài; lên VPS từ $2.000 |
| Buffer nằm chờ | 6% vốn không sinh lãi | APR trên vốn thấp hơn APR notional (~0,47×) |
| BNB giảm phí | Phải có BNB ở **cả** ví Spot và Futures | Giữ $10–20 BNB mỗi ví |

---

## 7. KIẾN TRÚC HỆ THỐNG

```
[Ingest]  WS/REST đa sàn
    ↓
[Normalizer] → [TSDB: tick + funding + book snapshot]
    ↓
[Feature Engine streaming]
    ├─ FR Quality
    ├─ Reversal Risk
    └─ Capacity
    ↓
[Episode Allocator]  ← portfolio, correlation cap
    ↓
[Pre-trade Risk Gate]
    ↓
[Execution Router]  (2 leg, cross-venue)
    ↓
[Position Reconciler + PnL Attribution]
    ↓
[Live Risk Monitor] → kill switch
```

### 7.1 Bảy khối chức năng

| Khối | Input | Làm gì | Output |
|---|---|---|---|
| Ingest | WS/REST | Kéo FR, predicted, premium, OI, depth, liq | Chuỗi sạch |
| Feature | Dữ liệu thô | Tính FR Quality, Reversal Risk, Capacity | Điểm mỗi coin/phút |
| Allocator | Điểm | Chọn episode, size, chiều | Danh sách lệnh chờ |
| Risk Gate | Lệnh chờ | Chặn nếu margin/basis/correlation/venue fail | Duyệt/từ chối |
| Executor | Lệnh duyệt | Vào 2 leg, xử lý partial fill, rollback | Vị thế delta-neutral |
| Reconciler | Fills + API | Đối soát vị thế, funding thực vs kỳ vọng | PnL attribution |
| Risk Monitor | Vị thế live | Canh flip, basis, OI, ADL, venue | Kill switch |
| **Watchdog** | Heartbeat + state nội bộ | Phát hiện treo/mất kết nối/lệch vị thế | Dead-man switch, alert P1 |

> **Vì chạy L3, Watchdog là khối bắt buộc — không phải optional.** Nó là thứ biến "tự động" thành "tự động có giám sát": nếu bot treo, mất mạng, hoặc state lệch sàn, Watchdog chặn vào lệnh mới và báo người ngay.

### 7.2 Data cần thu

| Nhóm | Chi tiết |
|---|---|
| Funding | Lịch sử, predicted, interval, cap/floor, countdown |
| Giá & basis | Mark, index, premium, spot, dated future |
| Vị thế | OI, ΔOI, volume, taker ratio, CVD, liquidation |
| Thanh khoản | Depth ±0,5/1/2%, spread, slippage ước tính |
| Rủi ro | Monitoring tag, margin tier, ADL, nạp/rút, unlock, listing age |

### 7.3 API endpoints (Binance public)

```
GET /fapi/v1/fundingRate?symbol=&startTime=&limit=
GET /fapi/v1/premiumIndex?symbol=        (hoặc không symbol = tất cả)
GET /fapi/v1/premiumIndexKlines?symbol=&interval=
GET /fapi/v1/klines?symbol=&interval=
GET /fapi/v1/ticker/24hr
GET /fapi/v1/openInterest?symbol=
GET /futures/data/openInterestHist?symbol=&period=
GET /fapi/v1/depth?symbol=&limit=
GET /fapi/v1/exchangeInfo
```

---

## 8. MỨC TỰ ĐỘNG HÓA — L3 TỪ NGÀY ĐẦU

**Quyết định:** chạy **L3 — tự động hoàn toàn có giám sát** ngay từ lệnh live đầu tiên. Không có giai đoạn bán tự động, không xác nhận tay từng lệnh.

| Mức | Tên | Ai làm gì | Dùng ở đây |
|---|---|---|---|
| L0 | Thủ công | Tự xem, tự đặt | Không |
| L1 | Alert-only | Hệ thống báo, người bấm | Chỉ trong B0/B1 để kiểm tra tín hiệu |
| L2 | Bán tự động | Hệ thống dựng lệnh, người xác nhận | **Không dùng** |
| **L3** | **Tự động hoàn toàn có giám sát** | **Máy vào/ra/hedge/transfer/kill switch; người giám sát, audit, xử lý bất thường** | **Chạy chính thức từ $500** |
| L4 | Tự động không giám sát | Không ai canh | Không (bỏ) |

### 8.1 Định nghĩa & lớp giám sát

**"Tự động hoàn toàn" nghĩa là:** mọi quyết định chọn coin, size, chiều, vào/ra 2 leg, rebalance delta, nạp/rút buffer và kill switch đều do rule engine thực thi. Không có bước "chờ người bấm".

**"Có giám sát kỹ lưỡng" nghĩa là:** người không nằm trong vòng lặp lệnh, nhưng nằm trong vòng giám sát:

| Lớp giám sát | Cơ chế | Ngưỡng/ hành động |
|---|---|---|
| Sức khỏe hệ thống | Heartbeat 30–60s + Watchdog | Mất > 2 phút: alert; > 5 phút: chặn vào mới + dead-man switch |
| Đồng bộ vị thế | Reconcile API ↔ state mỗi 1–5 phút | Lệch qty/giá vốn: dừng vào mới, alert P1 |
| Giới hạn rủi ro | Hard cap trong code (không đọc từ config runtime) | Max order notional, max coin, max leverage, max slippage |
| Bất thường thị trường | Rule engine canh flip/basis/OI/ADL | Tự đóng theo §10.3, không chờ người |
| PnL attribution | Đối soát funding thực vs kỳ vọng mỗi kỳ | Lệch > 20%: alert P2, review trong 24h |
| Audit | Log bất biến mọi order/fill/retry/override | Truy vết được từng lệnh bằng correlation id |

**Vận hành giám sát:**
- Dashboard realtime + alert Telegram/SMS cho P1/P2.
- **2 tuần đầu: người trực 24/7.** Sau đó on-call, SLA phản hồi P1 ≤ 15 phút.
- Với một người vận hành, "trực 24/7" nghĩa là **alert phải đánh thức được + dead-man tự xử lý**, không phải ngồi nhìn màn hình.
- Review 15 phút/ngày; post-mortem mọi bất thường trong 48h.
- Alert phải được **test định kỳ hàng tuần** (bắn thử, kiểm tra có tới điện thoại).

### 8.2 Runbook sự cố

| Sự cố | Phát hiện | Máy tự xử lý | Người làm | SLA |
|---|---|---|---|---|
| Bot chết / mất heartbeat > 5 phút | Watchdog | Chặn vào mới; dead-man flatten theo cấu hình | Kiểm tra VPS/mạng, khởi động lại, reconcile trước khi mở lại | 15 phút |
| Leg 2 fail | Executor | Retry ≤ 3 với giá giới hạn; vẫn fail → đóng leg 1 | Xác nhận rollback, kiểm tra phí/slippage, ghi log | 15 phút |
| Reconcile lệch qty/giá vốn | Reconciler | Dừng vào mới; đóng phần lệch nếu vượt ngưỡng | Đối chiếu trên app, sửa state có audit | 30 phút |
| API 429/5xx kéo dài | Gateway | Backoff, không retry mù; rollback nếu đang mở 2 leg | Kiểm tra status sàn, tạm dừng coin mới | 30 phút |
| Sàn pause rút / tag / đổi interval | Risk Monitor | Đóng vị thế liên quan ngay | Rút phần rút được, blacklist coin, ghi nhận | Ngay |
| Funding flip 2 kỳ | Risk Monitor | Đóng coin | Review có vào lại hay không | Theo kỳ |

> **Sau sự cố P1, hệ không tự mở lại:** phải có người xác nhận đã root-cause và reconcile khớp. Đây là ngoại lệ duy nhất của "tự động hoàn toàn" — và là điều kiện để L3 không thành L4.

### 8.3 Điều kiện bật live

**Vì sao L3 an toàn hơn L2 ở quy mô $500:** rủi ro lớn nhất nằm ở khoảng giữa 2 leg (leg 1 khớp, leg 2 fail). Để người bấm giữa 2 leg làm **tăng** thời gian lệch chân, không giảm. Tự động + rollback + reconcile + hard cap tốt hơn "bấm tay cẩn thận". Ngoài ra cùng một codebase dùng tiếp ở $1k–$5k, nên viết đúng ngay từ đầu không phải làm lại.

**Bắt buộc trước khi bật L3 live:**
1. **Dry-run ≥ 7 ngày** trên dữ liệu thật (không gửi lệnh) + **testnet** cho toàn bộ luồng order/rollback.
2. Test bắt buộc: leg 2 fail, partial fill, timeout, API 429/5xx, mất mạng, sai số dư, interval đổi giữa chừng, funding flip đúng lúc.
3. Mỗi loại lỗi phải có hành vi xác định: rollback, retry có giới hạn, hay flatten — không có "treo chờ người".
4. Kill switch + dead-man switch đã test bằng giả lập sự cố.
5. Hard cap nằm trong code; đổi cap phải deploy, không sửa file config nóng.
6. Reconcile chạy độc lập với executor (khác process/khác nguồn dữ liệu).

### 8.4 Ranh giới tự động / người

| Máy làm (không cần xác nhận) | Người làm (giám sát, không xen vào lệnh) |
|---|---|
| Kéo dữ liệu, tính điểm, xếp hạng | Đặt ngưỡng rủi ro & hard cap |
| Chọn coin, size, chiều; vào/ra 2 leg | Duyệt coin/venue mới vào universe |
| Rollback leg lỗi, retry, rebalance delta | Review alert, xử lý sự cố lạ |
| Transfer buffer Spot ↔ Futures | Review model drift & slippage thực |
| Thoát khi flip/basis/OI/ADL | Post-mortem, cập nhật rule |
| Kill switch + dead-man switch | **Chỉ được dừng; không override để chạy tiếp** |

> Nguyên tắc: người chỉ có quyền **giảm rủi ro** (kill, hạ size, blacklist coin, siết cap), không có quyền tăng size hay mở lệnh ngoài rule.

### 8.5 Vì sao không lên L4

- Hai leg không atomic → leg 1 khớp, leg 2 fail.
- Borrow availability không báo trước.
- Interval đổi giữa chừng.
- ADL không có API báo trước.
- API rate limit/outage đúng lúc biến động.
- Bug có blast radius lớn và có thể lặp âm thầm nhiều ngày nếu không ai xem.
- Ở quy mô nhỏ, chi phí giám sát thấp hơn rất nhiều so với một sự cố không được phát hiện.

---

## 9. AI LAYER

### 9.1 AI nên dùng

| Use case | Giá trị | Vì sao |
|---|---|---|
| Parse tin tức/thông báo sàn | ⭐⭐⭐⭐⭐ | Tail risk nằm ở văn bản phi cấu trúc |
| Triage sự cố | ⭐⭐⭐⭐ | Tóm tắt log + tin + on-chain |
| Query tự nhiên | ⭐⭐⭐ | Tiện, không phải edge |
| Research/viết backtest | ⭐⭐⭐⭐ | Offline, không rủi ro runtime |
| Post-mortem | ⭐⭐⭐ | Tách alpha decay vs bug |

### 9.2 ML (không phải LLM) nên dùng

| Use case | Giá trị |
|---|---|
| Dự đoán slippage từ book | ⭐⭐⭐⭐ |
| Anomaly detection microstructure | ⭐⭐⭐⭐ |
| Phân loại regime | ⭐⭐⭐ |
| Dự đoán FR kỳ tới | ⭐ (đã có công thức, không cần ML) |

### 9.3 AI không nên dùng

| Không nên | Lý do |
|---|---|
| LLM ra quyết định vào/ra | Non-deterministic, không backtest được |
| LLM trong hot path | Latency, không ổn định |
| LLM làm kill switch | Phải là rule cứng |
| ML dự đoán hướng giá | Ngoài phạm vi chiến lược |
| Agent tự chọn coin | Không giải thích/tái lập được |

### 9.4 Nguyên tắc

> **AI đọc và cảnh báo; rule engine quyết và thực thi.** AI có thể *hạ* size hoặc *chặn* (an toàn), không bao giờ *tăng* size hay *mở* vị thế ngoài rule.

---

## 10. QUẢN TRỊ RỦI RO

### 10.1 Cấu trúc vốn & risk budget

```
C = vốn;  N = notional mỗi leg (spot = perp = N)
Giai đoạn 1: perp 1x  →  margin = N;  buffer = C − 2N
Ở $500: N = 0,47C = $235 → spot $235, margin $235, buffer $30 (6% vốn)
Liquidation ≈ (C − N)/N → ~+113% ở $500
Max loss/episode (basis + slippage): 10% notional
Cap tổng exposure cùng beta ≤ 60% notional
```

> **Giai đoạn 2 (chỉ sau gate §12.4):** 2x, N = 0,55C = $275, margin $137,5, buffer $87,5 (17,5%), liquidate ~+81%. Đổi ~$1/tháng lấy ngưỡng chết gần hơn — chỉ đáng khi automation đã chứng minh ổn định.

| Vốn (1x) | Notional/leg | Số coin | N/coin | Margin perp (1x) | Buffer | Max loss 1 coin (10%) | Kill DD |
|---|---|---|---|---|---|---|---|
| **$500** | $235 | 3 | $78 | $235 | $30 (6%) | $7,8 (1,6%) | −$100 (−20%) |
| $1.000 | $470 | 5 | $94 | $470 | $60 (6%) | $9,4 (0,9%) | −$200 (−20%) |
| $2.000 | $940 | 7 | $134 | $940 | $120 (6%) | $13,4 (0,7%) | −$300 (−15%) |
| $5.000 | $2.350 | 9 | $261 | $2.350 | $300 (6%) | $26,1 (0,5%) | −$600 (−12%) |

### 10.2 Leverage & liquidation

| Leverage | Giá tăng bao nhiêu thì short perp liquidate |
|---|---|
| 1x | ~+99% |
| 2x | ~+49% |
| **3x** | **~+33%** |
| 5x | ~+19% |
| 10x | ~+9,5% |

**Quy tắc:** perp **1x giai đoạn 1**; buffer ≥ 6% vốn; 2x chỉ sau gate; không bao giờ > 3x.

> **Lưu ý cross-wallet (quan trọng ở vốn nhỏ):** giá tăng → short perp lỗ trong ví **Futures**, spot lãi trong ví **Spot** nhưng chưa bán. Thiếu buffer ở Futures = bị liquidate dù tổng vốn vẫn dương. Ở $500: giữ **≥ $30 trong ví Futures** ngoài margin; nạp thêm khi buffer < 50% nhu cầu phí/funding 1 tháng. Giai đoạn 2 (2x): ≥ $80.

### 10.3 Kill switch

| Trigger | Hành động |
|---|---|
| Predicted FR flip âm 2 kỳ liền | Đóng coin đó |
| Predicted FR < 0,5 × trailing | Đóng |
| ΔOI < −15%/1h | Giảm 50%/đóng |
| Realized vol > 2,5× entry | Giảm size |
| Basis > 3σ | Đóng (hedge fail) |
| Giá move > 15%/1h | Giảm/đóng |
| Liq cascade trong ±0,5% | Flatten khẩn |
| ADL queue chạm top | Đóng leg thắng, hedge lại |
| Venue: pause rút, tag, đổi interval | Đóng ngay |
| Drawdown tổng > ngưỡng (20% @$500/$1k, 15% @$2k, 12% @$5k) | Kill toàn hệ, review |
| Heartbeat mất > 5 phút / executor treo | Chặn vào mới; flatten theo cấu hình |
| Reconcile lệch qty/giá vốn > 1% | Dừng vào mới, alert P1 |
| API 429/5xx liên tục > 60s | Backoff có giới hạn; rollback nếu đang mở 2 leg |

> **Tất cả trigger trên do rule engine tự thực thi**, không chờ người. Người chỉ nhận alert và có quyền dừng; **không có quyền bỏ qua kill switch**. Mọi lần can thiệp tay đều ghi audit log.

### 10.4 Event risk

**Định nghĩa:** sự việc rời rạc gây gap/halt/vỡ basis — khác biến động thường ngày.

| Tầng | Ví dụ | Ảnh hưởng |
|---|---|---|
| Tài sản | Unlock, exploit, team xả, delist | Giá sập/bật, basis vỡ, halt |
| Thị trường | Liquidation cascade, MM rút | Tất cả coin gap cùng lúc |
| Sàn | Đổi interval, margin tier, freeze rút | Không thoát/re-hedge được |

**Vì sao nguy hiểm:** delta-neutral không cứu được basis gap, halt, mất thanh khoản.

**Con số:** APR 47% ≈ 3,9%/tháng. Basis gap 2,3% = 0,6 tháng. Halt/settle lệch 10% = 2,5 tháng.

**Cách giảm:**
- Tránh coin đang có event.
- Kiểm tra lịch unlock.
- Size nhỏ trên coin mới/vol cao.
- 1x, buffer ≥ 6% vốn (2x + 17,5% chỉ sau gate).
- Rule cứng: giá move >15%/1h hoặc basis >3σ → thoát.
- Không giữ qua event đã biết.

### 10.5 Rủi ro sàn — đừng dựa vào đền bù

- SAFU là **quỹ thiện chí**, không phải bảo hiểm.
- Hack là rủi ro **ít xảy ra nhất**.
- Hay gặp hơn và **không được đền**: freeze rút, hạn chế tài khoản, delisting, ADL, API outage.
- **Giả định đúng:** vốn trên sàn có thể bị khóa bất cứ lúc nào.

---

## 11. KẾ HOẠCH TRIỂN KHAI (v2.x — rút gọn)

**Thay đổi so với v1.0:** bỏ collector 2 tuần riêng, bỏ alert-only, bỏ shadow 4 tuần, bỏ canary nhiều tháng. Gộp thành **B0 backtest → B1 xây automation + dry-run → live $500 chạy L3**, tổng ~3–4 tuần. Thời gian dài nhất là **xây đúng automation**, không phải chờ thị trường.

| Bước | Thời lượng | Làm gì | Điều kiện qua |
|---|---|---|---|
| **B0 — Backtest** | 5–7 ngày | 6–12 tháng dữ liệu; mô phỏng đúng $500 (3 coin, $78/leg, perp 1x, buffer 6%, min notional, cost P2 0,34%, slippage 0,10%/side); ra phân phối tháng, DD, tỷ lệ tháng âm | Net APR ≥ 9% trên vốn sau chiết khấu; ≥ 70% tháng dương; DD stress ≤ 4% |
| **B1 — Xây automation + dry-run** | 10–14 ngày | Viết executor 2 leg, reconciler, watchdog, kill switch, alert, dashboard; testnet toàn bộ luồng; **dry-run ≥ 7 ngày** trên dữ liệu thật (không gửi lệnh) | Pass checklist §8; reconcile diff = 0; alert + kill switch + dead-man đã test; 0 lỗi state |
| **R1 — Live $500 (L3)** | Tuần 4–5 | **2 coin × $78 notional/leg, perp 1x, bot tự chạy hoàn toàn**; người trực 24/7, không xác nhận lệnh | Funding thực khớp kỳ vọng ±20%; 0 sự cố P1; reconcile diff = 0 |
| **R2 — Live đủ cấu hình** | Tuần 6–8 | 3 coin, notional 0,47 vốn, giữ 1–4 tuần, vẫn 1x + L3 | — |
| **G — Review nâng vốn** | Ngày 60–90 | Đối chiếu gate §12.4, quyết định lên $1.000 hay giữ nguyên | Xem §12.4 |

**Luật cứng trong giai đoạn $500:**
- Không nạp thêm vốn trước ngày 60.
- Không tăng size để gỡ lỗ.
- **Không sửa tay lệnh bot đang chạy** — can thiệp bằng kill switch/blacklist.
- Kill switch do máy thực thi; người không override.
- Không deploy thay đổi trong 2h trước funding hoặc khi realized vol > 2,5× entry.
- Mọi thay đổi rule/code phải qua dry-run ≥ 24h trước khi live.
- Không chạy auto trên đường truyền không có UPS + 4G backup (hoặc VPS có SLA).
- **Không bật 2x trước ngày 60/gate** — kể cả khi thấy lãi tốt.

> **Vì sao bỏ được phase chậm:** dry-run + testnet thay thế shadow/canary cho phần **kỹ thuật**. Phần chỉ đo được bằng tiền thật (slippage, fill, funding thực) thì $500 đo trực tiếp với chi phí tối đa ~$100–150 (§12.5) — rẻ hơn 3–5 tháng chờ và không làm tăng độ chính xác của backtest.

---

## 12. KỲ VỌNG LỢI NHUẬN & VỐN

### 12.1 Ở vốn $500

| Kịch bản | Net APR trên vốn | $/tháng | Ghi chú |
|---|---|---|---|
| Năm xấu | 0% | $0 | Funding chết, đứng ngoài |
| Thấp | 4% | $1,7 | Vài tháng/năm |
| **Cơ sở** | **9–12%** | **$3,8–5,0** | Đã chiết khấu quy mô nhỏ; trước chi phí cố định |
| Tốt | 16% | $6,7 | |
| Rất tốt | 22% | $9,2 | Hiếm, 1–2 tháng/năm |
| Tháng âm | −2% | −$10 | |

> APR trên **vốn** ≈ **0,47 × APR trên notional** (spot 47% + margin 47% + buffer 6%). Đừng so APR notional với lãi rút ra. Nếu lên 2x sau gate, hệ số thành ~0,55.

### 12.2 Nâng vốn: $500 → $1.000 → $2.000 → $5.000

| Hạng mục | $500 | $1.000 | $2.000 | $5.000 |
|---|---|---|---|---|
| Notional/leg (0,47×) | $235 | $470 | $940 | $2.350 |
| Số coin | 3 | 5 | 7 | 9 |
| Notional/coin (mỗi leg) | $78 | $94 | $134 | $261 |
| Margin perp 1x / coin | $78 | $94 | $134 | $261 |
| Buffer ví Futures | $30 (6%) | $60 | $120 | $300 |
| Size/coin (% vốn) | 15,7% | 9,4% | 6,7% | 5,2% |
| Universe | Mid-cap giá thấp; **loại BTC/ETH** | Thêm ETH; BTC còn thô | BTC/ETH dùng được | Đủ universe |
| Leverage | 1x | 1x | 1x | 1x |
| Phí | Taker + BNB | Ưu tiên maker leg spot | Maker + BNB | Maker, theo dõi VIP1 |
| Hạ tầng | Máy nhà + UPS/4G + dead-man ping ngoài | Máy nhà + UPS/4G + watchdog ngoài | VPS $5–6 + 4G backup | VPS $10–12 + redundancy |
| Tự động hóa | **L3 toàn phần** | **L3 toàn phần** | **L3 + chaos test định kỳ** | **L3 + sub-account + redundancy** |
| Kỳ vọng/tháng (~10,5% APR) | $4,4 | $8,8 | $17,5 | $43,8 |
| Sau chi phí cố định | **$4** | **$8–9** | **$12–13** | **$33–34** |
| Kill switch DD | −$100 (20%) | −$200 (20%) | −$300 (15%) | −$600 (12%) |

**Thay đổi cụ thể từng bước:**

**$500 → $1.000 (giữ nguyên L3, chưa cần VPS):**
- 3 → 5 coin; thêm 1–2 coin APR thấp nhưng ổn định làm trụ.
- Bắt đầu đặt **maker ở leg spot** (tiết kiệm ~0,025%/side).
- Alert 2 kênh (Telegram + SMS/email); đưa test automation vào CI.
- Buffer Futures lên $60; giữ BNB ở cả 2 ví.

**$1.000 → $2.000:**
- 5 → 7 coin; **đo slippage thực theo từng coin**, loại coin có slippage > 0,2%/side.
- **PnL attribution tự động** (funding vs basis vs phí) — bắt buộc trước khi lên $5k.
- **Chaos drill hàng tháng:** giả lập API 429/5xx, mất mạng, leg 2 fail, reconcile lệch.
- Chuyển bot lên **VPS $5–6 + 4G backup**; bắt đầu deploy canary cho code (dry-run 24h trước khi bật).

**$2.000 → $5.000:**
- 7 → 9 coin; **sub-account/ví riêng cho buffer**; auto transfer + đối soát.
- Thêm **instance watchdog thứ 2 (read-only)** ở máy/VPS khác để phát hiện bot chính chết.
- Audit trail export; sổ thuế & đối soát; theo dõi volume 30 ngày tiến tới VIP1 (ở $5k còn rất xa).

**Không thay đổi theo quy mô:** chiến lược, bộ lọc, ngưỡng APR/CV/decay, cấu trúc 2 leg, **1x + buffer 6%**, **mức L3**. Quy mô chỉ đổi **số coin, hạ tầng/redundancy và chi phí cố định**.

**Giai đoạn 2 (sau gate §12.4):** có thể nâng **2x** — notional 0,55 × vốn, margin N/2, buffer 17,5%, liquidate ~+81%, thêm ~$1–2/tháng ở $500. Chỉ bật khi: 60–90 ngày 1x sạch lỗi, reconcile diff = 0, DD < 5%, và automation đã qua chaos test.

### 12.3 Chi phí ẩn ở quy mô nhỏ

- Phí giao dịch tính theo **% notional** → gần như không đổi theo quy mô; break-even ngày giữ nguyên.
- **Chi phí cố định mới là vấn đề:** VPS $5/tháng ăn **>100% lãi kỳ vọng ở $500**, ~57% ở $1.000, ~29% ở $2.000 và ~23% ở $5.000. Vì vậy ở $500–$1.000 ưu tiên **máy nhà + UPS/4G + dead-man ping ngoài**; từ $2.000 mới thuê VPS.
- **Uptime là điều kiện của L3:** mất kết nối 5 phút không nguy hiểm bằng mất kết nối 5 giờ mà không ai biết. Ưu tiên **heartbeat + alert + dead-man** hơn mọi tối ưu tốc độ. Nếu máy nhà không đạt (UPS < 30 phút, không 4G) → buộc lên VPS $5 và chấp nhận lãi ròng âm nhẹ (~−$0,6/tháng) ở mức $500.
- **Độ thô của size:** $78/leg ở $500 là mức tối thiểu thực tế; nhỏ hơn nữa thì min notional + làm tròn qty ăn vào edge.
- **Buffer không sinh lãi:** 6% vốn nằm chờ → APR trên vốn thấp hơn APR notional (~0,47×).
- **Chuyển tiền:** rút ra ngoài (on-chain) $1–2/lần → gom 1 lần/tháng; **transfer nội bộ Spot ↔ Futures miễn phí và do bot tự động**.
- **BNB:** hết BNB âm thầm làm phí tăng ~0,06%/round-trip; kiểm tra hàng tuần.
- **Sổ sách:** ở $500 chưa đáng quan tâm, nhưng ghi từ ngày đầu để lên $5.000 không phải dựng lại.

### 12.4 Điều kiện nâng vốn (gate)

Chỉ nâng khi đạt **tất cả**:
1. ≥ 60 ngày live (khuyến nghị 90).
2. Net dương sau phí + slippage + funding thực.
3. Slippage thực ≤ mô hình (0,15%/side) ở ≥ 80% lệnh.
4. 0 lỗi vận hành chưa khắc phục (leg 2 fail không rollback, sai size, buffer không tự nạp).
5. Max drawdown thực < 10% vốn.
6. Funding thực nhận lệch kỳ vọng < 20%.
7. Giải thích được **từng** tháng lãi/lỗ bằng log.
8. Reconcile diff = 0 trong 30 ngày liên tục.
9. 0 sự cố P1 chưa tìm được root cause.
10. Alert + kill switch + dead-man switch được test trong 7 ngày gần nhất.
11. **Nếu xét nâng 2x:** thêm 30 ngày ở 1x với DD < 5%, không có lần nào chạm buffer, và đã diễn tập partial-unwind khi giá pump.

Không đạt → giữ nguyên thêm 30 ngày. Đạt 2 lần liên tiếp → nhân đôi vốn, tối đa gấp đôi mỗi lần và cách nhau ≥ 60 ngày.

### 12.5 Thiệt hại chấp nhận được (vì sao live sớm)

| Sự kiện | Xác suất ước tính | Thiệt hại @ $500 |
|---|---|---|
| Tháng funding thấp/âm nhẹ | 1–3 tháng/năm | −$3 … −$15 |
| Basis shock 2% toàn thị trường | 10–30%/năm | −$4 … −$7 |
| Basis shock 5% ở 1 coin | 5–10%/năm | −$3 … −$6 |
| Halt/settle lệch 10% ở 1 coin | Hiếm | −$7 … −$15 |
| Lỗi automation (leg 2 fail, sai size, retry mù) | Khá chắc có 1 lần trong 3 tháng đầu | −$10 … −$50 |
| Bot chết/state lệch nhưng không ai biết | Có thể nếu giám sát kém | −$10 … −$40 |
| Freeze/hack sàn | Rất hiếm | −$500 |
| **Tổng thiệt hại sự kiện (3 tháng đầu, kỳ vọng)** | — | **−$20 … −$60** |

> Đây là **thiệt hại do sự kiện**, không phải kết quả ròng. Nếu 3 tháng không có sự kiện lớn, kỳ vọng lãi ròng ≈ **+$15 … +$25**; mục tiêu 3 tháng đầu vẫn là vận hành đúng, không phải lãi.

**So sánh:** 3–5 tháng chạy phase chậm = 3–5 tháng không có dữ liệu thật, không có track record, và vẫn phải trả đúng khoản học phí đó sau. $500 đổi lấy 3–5 tháng ≈ **$2–3/tuần** tiền học phí kỳ vọng — rẻ hơn một khóa học, và rẻ hơn rất nhiều so với việc phát hiện bug ở quy mô $5.000.

**Điều kiện để "chấp nhận thiệt hại" là đúng:**
- Giới hạn bằng **con số** (−$150 trong 3 tháng), không bằng niềm tin.
- Không nạp quá **$500** lên sàn; phần vốn lớn hơn (nếu có) giữ ngoài.
- Lỗi automation **không** nằm trong backtest — đây là rủi ro chính, không phải funding flip.
- Watchdog + alert phải chạy **độc lập** với bot (máy/VPS khác); nếu không, "giám sát" chỉ là giả định.
- Ở $500, một lỗi $50 = 10% vốn: mỗi lần sai phải ghi log và sửa quy trình ngay.

---

## 13. CHECKLIST VẬN HÀNH (L3 — giám sát, không bấm lệnh)

### Hàng ngày (15 phút)

- [ ] Heartbeat + lần reconcile cuối; diff qty/giá vốn = 0.
- [ ] Không còn alert P1/P2 chưa xử lý; kênh alert còn hoạt động.
- [ ] Funding thực nhận vs kỳ vọng (±20%).
- [ ] Predicted FR của các coin đang giữ.
- [ ] OI, basis, giá có bất thường không.
- [ ] Buffer ví Futures ≥ ngưỡng §10.2; margin ratio an toàn.
- [ ] Không có lệnh treo/partial fill chưa xử lý.
- [ ] Thông báo sàn (delist, interval, margin).

### Hàng tuần

- [ ] Re-rank universe, cập nhật watchlist.
- [ ] Kiểm tra decay/spike của các coin đang giữ.
- [ ] Review PnL attribution: funding vs basis vs phí.
- [ ] Kiểm tra correlation và tổng exposure.
- [ ] Slippage thực vs mô hình, theo từng coin.
- [ ] Cập nhật lịch unlock/event sắp tới.
- [ ] **Test alert + kill switch + dead-man switch** (bắn thử).
- [ ] BNB còn đủ ở cả 2 ví; phí thực/round-trip.

### Hàng tháng

- [ ] Review hiệu suất vs kỳ vọng; đối chiếu gate §12.4 nếu xét nâng vốn.
- [ ] Kiểm tra model drift (ngưỡng còn đúng không).
- [ ] Audit log mẫu ~20 lệnh: đúng rule, đúng size, rollback đúng.
- [ ] Chaos drill: API 429/5xx, mất mạng, leg 2 fail, reconcile lệch.
- [ ] Post-mortem các episode thua và mọi sự cố P1.
- [ ] Cập nhật risk budget/cap nếu cần (chỉ siết, không nới tùy tiện).

---

## 14. SAI LẦM CẦN TRÁNH

| Sai lầm | Hậu quả |
|---|---|
| Chạy 5–10x vì "delta-neutral an toàn" | Liquidate leg perp, mất hedge |
| Lướt 1–2 kỳ | Phí ăn hết, chắc chắn lỗ |
| Chase APR cao, bỏ qua CV | ACE/ENSO: APR 69% nhưng net âm |
| Bỏ qua decay | BULLA: trailing 96% → predicted 11% |
| Tin "chuỗi dương" | Một phần là baseline cơ học |
| All-in 1 coin | Selection risk + event risk |
| Giữ qua unlock/event | Basis gap, halt |
| Dựa vào "sàn đền bù" | Freeze rút không được đền |
| Đặt LLM vào quyết định | Non-deterministic, không backtest |
| Kỳ vọng 70% APR | Thực tế 9–12% trên vốn (1x + buffer) |
| Không có kill switch | Tail event xóa nhiều tháng |
| Kill switch cho phép override | Mất tác dụng đúng lúc cần |
| Auto mà không có reconcile/watchdog | Bot sai âm thầm nhiều ngày |
| Sửa tay lệnh bot đang chạy | State lệch, mất khả năng truy vết |
| Deploy code sát giờ funding | Sự cố đúng lúc không được phép sai |
| Người xác nhận giữa 2 leg | Lệch chân lâu hơn, lỗi nhiều hơn |
| Chạy auto trên mạng nhà không UPS/4G | Mất kết nối = mù vị thế |

---

## 15. PHỤ LỤC

### 15.1 Công thức tổng hợp

```
# Funding Binance
F = [P + clamp(I − P, +0,05%, −0,05%)] / (8 / N)

# Delta-neutral PnL
Net giá = X × (Basis_0 − Basis_T)
Net tổng = Σ(FR_t × Notional_t) − phí − slippage − borrow − opp + ΔBasis

# Break-even
H* = c / FR
days ≈ 128 / APR(%)

# Net APR
cost = 0,24% + 2 × slippage
net_14d = forward_APR × 14/365 − cost
net_APR = net_14d × 365/14

# Score
score = net_APR × min(1, 1/CV) × min(1, volume/$20M)
```

### 15.2 Thresholds mặc định

```yaml
universe:
  volume_min_usd: 5_000_000
  status: TRADING
  contract: PERPETUAL
  quote: USDT
  exclude_symbols: [BTCUSDT, ETHUSDT]   # chỉ ở vốn $500 (bước giá quá thô)

filter:
  apr_basis: forward     # min(apr_7d, apr_14d)
  apr_min: 20
  apr_max: 60
  excess_apr_min: 15     # APR - baseline 10,95%/năm
  pos_ratio_14d_min: 0.85
  zero_rate_14d_max: 0.10
  cv_14d_max: 2.0
  decay_7d_vs_14d_min: 0.6
  decay_min: 0.5          # predicted / trailing7
  spike_max: 3.0          # predicted / trailing7
  slippage_max: 0.2       # % per side, ở size thực
  net_apr_14d_min: 20

capital_tiers:
  - capital_usd: 500
    coins: 3
    notional_ratio: 0.47       # N mỗi leg / vốn; spot N + margin N (1x)
    perp_leverage: 1
    phase2_leverage: 2         # chỉ sau gate §12.4
    size_per_coin_max: 0.16
    leverage_max: 1
    futures_buffer_min_usd: 30
    infrastructure: home_ups_4g_external_watchdog
    automation: L3
    dd_kill: 0.20
  - capital_usd: 1000
    coins: 5
    notional_ratio: 0.47
    perp_leverage: 1
    phase2_leverage: 2
    size_per_coin_max: 0.10
    leverage_max: 1
    futures_buffer_min_usd: 60
    infrastructure: home_ups_4g_external_watchdog
    automation: L3
    dd_kill: 0.20
  - capital_usd: 2000
    coins: 7
    notional_ratio: 0.47
    perp_leverage: 1
    phase2_leverage: 2
    size_per_coin_max: 0.07
    leverage_max: 1
    futures_buffer_min_usd: 120
    infrastructure: vps_5_6_4g
    automation: L3_chaos_tested
    dd_kill: 0.15
  - capital_usd: 5000
    coins: 9
    notional_ratio: 0.47
    perp_leverage: 1
    phase2_leverage: 2
    size_per_coin_max: 0.06
    leverage_max: 1
    futures_buffer_min_usd: 300
    infrastructure: vps_10_12_redundant
    automation: L3_subaccount
    dd_kill: 0.12

risk:
  leverage_max: 1              # giai đoạn 1; 2x chỉ sau gate
  phase2_leverage_max: 2
  margin_buffer_min: 0.06
  size_per_coin_max: 0.16      # @ $500; xem capital_tiers
  aggregate_exposure_max: 0.60
  max_coins: 10
  min_coins: 3

exit:
  predicted_fr_vs_trailing: 0.5
  oi_drop_1h: -0.15
  basis_sigma: 3
  price_move_1h: 0.15
  vol_spike: 2.5

automation:
  mode: L3_fully_automated_supervised
  manual_order_confirmation: false   # không bán tự động, không xác nhận tay
  human_override_kill_switch: false
  resume_after_p1_requires_human: true
  heartbeat_seconds: 30
  reconcile_seconds: 60
  deadman_after_seconds: 300
  dry_run_days: 7
  alert_test_days: 7
  max_order_notional_ratio: 0.25     # × vốn, hard cap trong code
  deploy_freeze_minutes_before_funding: 120
```

### 15.3 Thuật ngữ

| Thuật ngữ | Nghĩa |
|---|---|
| FR | Funding rate |
| APR | Annualized percentage rate |
| Basis | Chênh lệch perp − spot |
| Premium index | Chỉ số premium của perp so với index |
| OI | Open interest |
| CV | Coefficient of variation (std/mean) |
| Delta-neutral | Hedged, không lệch hướng giá |
| Decay | FR giảm dần |
| Spike | FR tăng đột biến tạm thời |
| ADL | Auto-deleveraging |
| Event risk | Rủi ro sự kiện rời rạc |
| Negative skew | Lãi đều, lỗ hiếm nhưng đậm |

### 15.4 Tài liệu tham chiếu

- Binance Futures funding rate FAQ.
- Binance API docs: `/fapi/v1/fundingRate`, `/fapi/v1/premiumIndex`.
- Dữ liệu backtest: Binance public API, snapshot 24/11/2026.

### 15.5 Nhật ký thay đổi

| Phiên bản | Ngày | Thay đổi |
|---|---|---|
| 1.0 | 24/11/2026 | Bản đầu: vốn 200tr, 5 phase, alert-only + shadow + canary |
| 2.0 | 24/11/2026 | Vốn khởi điểm $500; bỏ phase chậm, chỉ backtest + mô phỏng rồi live; thêm bảng nâng vốn $1k/$2k/$5k; ràng buộc quy mô nhỏ; gate nâng vốn; ngân sách thiệt hại |
| 2.1 | 24/11/2026 | Chuyển sang **L3 tự động hoàn toàn có giám sát** ngay từ live; bỏ L2/thủ công; thêm lớp giám sát, test matrix, dry-run/testnet bắt buộc; hạ tầng & redundancy theo quy mô |
| 2.2 | 24/11/2026 | Chuyển cấu hình mặc định sang **1x**: spot $235 / futures $265 / margin $235 / buffer $30; notional 0,47 vốn; liquidate ~+113%; 2x chỉ sau gate 60–90 ngày |

---

## KẾT LUẬN

Hệ thống này **khả thi** nhưng không phải "in tiền". Nó là:

> **Một cái máy lọc + kỷ luật:** chỉ vào khi edge sau phí vượt ngưỡng, giữ đến khi edge biến mất hoặc rủi ro vượt ngưỡng, và mặc định đứng ngoài.

**Bốn điều quyết định thành bại:**
1. **Kỷ luật leverage và size** — không phải tín hiệu.
2. **Bộ lọc + rolling exit** — không phải chọn coin APR cao.
3. **Quản trị event risk và tail** — không phải tối ưu lợi nhuận trung bình.
4. **Độ tin cậy của automation + giám sát** — vì hệ chạy L3, một bug không ai thấy còn nguy hiểm hơn một tháng funding xấu.

**Kỳ vọng đúng:** 9–12% APR trên vốn, 8–10 tháng xanh nhẹ, 2–4 tháng đỏ nhẹ, 0 tháng đỏ thảm họa. Đó là thành công. Ở $500, thành công của 3 tháng đầu là **hệ thống chạy đúng, reconcile khớp, không lỗi P1** — lợi nhuận chỉ là chỉ số phụ.

---

*Hết tài liệu. Cập nhật khi có dữ liệu live 6–12 tháng và kết quả vận hành L3.*
