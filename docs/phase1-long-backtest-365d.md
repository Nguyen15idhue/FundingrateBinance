# Phase 1 — Backtest dài 365 ngày (so sánh 180d)

**Ngày:** 25/11/2026  
**Mục đích:** kiểm tra liệu 180 ngày có phải regime xấu; kéo dài 365 ngày có tạo đủ candidate cho spot+perp Binance không.

## 1. Cách chạy

```powershell
$env:BT_DAYS='365'; $env:BT_DATA_DIR='data/backtest_365'; $env:BT_REPORT_DIR='reports/phase1_365'
python -m backtest.data
python -m backtest.run_phase1
python -m backtest.compare
```

- Cache theo từng symbol: `data/backtest_365/cache/`; nếu restart, chạy lại sẽ resume (`BT_RESUME=0` để bỏ cache).
- Bản 180 ngày giữ nguyên ở `reports/phase1/`.

## 2. Kết quả 180d vs 365d

| Chỉ số | 180 ngày | 365 ngày |
|---|---:|---:|
| Universe | 104 symbol | 101 symbol |
| Feature rows | 18.291 | 34.325 |
| Net APR vốn | −0,15% | **−0,11%** |
| Return | −0,07% | −0,11% |
| Deployment | 0,55% | **0,55%** |
| Episodes | 1 | 2 |
| Hit rate | 0% | 0% |
| Max DD | −0,07% | −0,11% |
| Tháng dương | 0% | 0% |
| P1 tests | 9/12 | 9/12 |
| Quyết định | Không đạt | **Không đạt** |

## 3. Candidate trong 365 ngày

Chỉ có **7 dòng pass**, thuộc 2 coin:

| Coin | Ngày pass | Forward APR | Ghi chú |
|---|---|---:|---|
| KITEUSDT | 07–08/02/2026 (2 ngày) | 31,5% → 30,6% | Episode 2 ngày |
| 牛来USDT | 11–15/09/2026 (5 ngày) | 57,0% → 34,7% | Episode 5 ngày |
| MARSCOINUSDT | gần pass | 34,7% | `data_ok=False`, không vào |

- **0 ngày** có ≥2 candidate.
- Snapshot 24/11/2026: **0 candidate**.
- 4 mã tham chiếu EVAA/AVAAI/PIEVERSE/PHAROS vẫn **không có Spot Binance**.

## 4. Kết luận

- Kéo dài từ 180 → 365 ngày **không cải thiện**: deployment vẫn 0,55%, net APR vẫn âm.
- Nguyên nhân không phải "chu kỳ ngắn" mà là **cấu trúc universe**: coin funding cao không có Spot Binance; coin có Spot gần như chỉ funding baseline ~10,7%.
- Vì vậy **không nên tiếp tục kéo dài thời gian** trên universe Binance spot+perp. Cần đổi universe/venue:
  - Cross-venue spot + perp (Spot ở Bybit/Gate/Bitget/MEXC + short perp Binance) — hướng chính.
  - Cross-venue perp–perp cho coin không có Spot.
- Gate Phase 2 vẫn giữ: net APR ≥9% vốn, DD ≤4%, ≥70% tháng dương, deployment ≥50%.
