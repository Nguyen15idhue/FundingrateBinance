# Phase 1 — Backtest B0 ($500 / 1x)

## Chạy

```powershell
python -m backtest.data        # ingest/cache 6 tháng (chỉ cần lần đầu)
python -m backtest.run_phase1  # backtest + stress + P1-T01..T12
```

- Cache: `data/backtest/*.parquet` (gitignored).
- Report: `reports/phase1/{summary.json,report.md,daily_equity.csv,episodes.csv,snapshot.csv}`.
- Không dùng API key; chỉ public Binance.

## Universe

- Futures USDⓈ-M PERPETUAL `TRADING`, volume 24h ≥ $5M.
- **Bắt buộc có cặp Spot USDT** (volume ≥ $1M) để hedge delta-neutral.
- Loại BTC/ETH (min qty quá lớn ở $500).
- Kết quả: 104 symbol; 4 mã tham chiếu EVAA/AVAAI/PIEVERSE/PHAROS **không có Spot**.

## Kết quả tóm tắt (25/11/2026)

| Chỉ số | Giá trị |
|---|---:|
| Net APR trên vốn | **−0,15%** |
| Return 180 ngày | −0,07% |
| Deployment rate | 0,55% |
| Episodes | 1 |
| Hit rate | 0% |
| Max DD | −0,07% |
| DD stress basis 5% | −0,85% |
| P1 tests | **9/12** |

**Kết luận:** Phase 1 **không đạt**. Không chuyển Phase 2 khi chưa xử lý mâu thuẫn universe (spot pair) và regime funding.

## Finding chính

1. Bộ lọc 20–60% APR gần như không chọn được coin trong universe có Spot; đa số funding quanh baseline ~10,7%/năm.
2. Các coin funding cao trong snapshot 24/11 (EVAA, AVAAI, PIEVERSE, PHAROS) đều **perp-only**, không hedge được bằng Spot Binance.
3. Kết quả đúng theo tinh thần §1.5: deployment thấp là kết quả hợp lệ, không phải lỗi code; nhưng không đủ bằng chứng edge để xây automation.

## Hướng xử lý trước Phase 2

- Thêm venue Spot khác cho coin perp-only (cross-exchange), hoặc dùng margin/borrow để short spot.
- Hoặc chấp nhận universe hẹp và chờ regime funding (không hạ chuẩn net APR).
- Hoặc đổi chiến lược sang perp-only (không delta-neutral) — **không khuyến nghị** ở $500.
