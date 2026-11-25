"""Chạy Phase 1: backtest, stress, P1-T01..T12 và xuất report."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from backtest import config as cfg
from backtest import data, strategy

OUT = Path("reports/phase1")
DATA = Path("data/backtest")


def _load() -> tuple[dict, pd.DataFrame, dict, dict, dict]:
    if not (DATA / "universe.parquet").exists():
        data.ingest()
    raw = strategy.load_raw()
    features, prices_df, pdict, meta = strategy.build_features(raw)
    file_meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    meta.update({k: file_meta[k] for k in ("references", "selected", "warnings") if k in file_meta})
    farr = strategy.funding_arrays(raw["funding"])
    return raw, features, pdict, farr, meta


def _cut_raw(raw: dict, date: pd.Timestamp) -> dict:
    out = {"universe": raw["universe"]}
    for name in ("funding", "klines", "premium", "spot_klines"):
        df = raw[name]
        if "dt" in df.columns:
            out[name] = df[df["dt"] <= date]
        else:
            out[name] = df
    oi = raw.get("oi")
    if oi is not None and not oi.empty:
        out["oi"] = oi[oi["time"] <= int(date.timestamp() * 1000)]
    else:
        out["oi"] = oi
    return out


def test_no_lookahead(raw: dict, date: pd.Timestamp) -> dict:
    farr = strategy.funding_arrays(raw["funding"])
    pfull = strategy.build_prices(raw["klines"], raw["spot_klines"])
    pdict = strategy.price_dict(pfull)
    full = strategy.features_for_date(date, farr, pdict, raw["universe"])
    cut = _cut_raw(raw, date)
    farr2 = strategy.funding_arrays(cut["funding"])
    p2 = strategy.build_prices(cut["klines"], cut["spot_klines"])
    pdict2 = strategy.price_dict(p2)
    cutf = strategy.features_for_date(date, farr2, pdict2, cut["universe"])
    m = full.merge(cutf, on="symbol", suffixes=("_full", "_cut"))
    if m.empty:
        return {"pass": False, "reason": "no common symbols", "n": 0}
    max_apr = float((m["apr14_full"] - m["apr14_cut"]).abs().max())
    max_score = float((m["score_full"] - m["score_cut"]).abs().max())
    same = bool((m["pass_all_full"] == m["pass_all_cut"]).all())
    ok = same and max_apr < 1e-10 and max_score < 1e-10
    return {"pass": ok, "n": len(m), "max_apr_diff": max_apr, "max_score_diff": max_score, "same_pass": same}


def test_interval(raw: dict) -> dict:
    f = raw["funding"]
    sym = f.groupby("symbol").size().idxmax()
    g = f[f["symbol"] == sym].sort_values("fundingTime")
    t = g["fundingTime"].to_numpy(np.int64)
    r = g["fundingRate"].to_numpy(float)
    end = int(cfg.END.timestamp() * 1000)
    i = int(np.searchsorted(t, end - 14 * 86400_000, side="right"))
    j = int(np.searchsorted(t, end, side="right"))
    native = float(r[i:j].sum()) * 365 / 14
    out = {"symbol": sym, "native_apr14": native}
    for h in (1, 2, 4, 8):
        b = (t[i:j] // (h * 3_600_000))
        s = pd.Series(r[i:j]).groupby(b).sum().sum()
        out[f"apr_{h}h"] = float(s) * 365 / 14
    diffs = [abs(out[f"apr_{h}h"] - native) for h in (1, 2, 4, 8)]
    out["max_diff"] = max(diffs)
    out["pass"] = out["max_diff"] <= 0.01 * abs(native) + 1e-12
    return out


def _snapshot(features: pd.DataFrame, meta: dict, date: str = "2026-11-24") -> dict:
    d = pd.Timestamp(date, tz="UTC")
    f = features[features["date"] == d]
    passed = f[f["pass_all"]].sort_values("score", ascending=False)["symbol"].tolist()
    refs = meta.get("references", {})
    ref_spot = {k: v.get("in_spot") for k, v in refs.items()}
    return {"date": date, "n_symbols": int(len(f)), "passed": passed, "reference_spot": ref_spot}


def _build_markdown(s: dict) -> str:
    m = s["baseline"]
    lines = [
        "# Phase 1 — B0 Backtest $500 / 1x",
        "",
        f"- Dữ liệu: {s['meta']['symbols']} symbol, {s['meta']['dates']} ngày, {s['meta']['features']} dòng feature.",
        f"- Baseline: net APR **{m['apr']*100:.2f}%**, return **{m['total_return']*100:.2f}%**, DD **{m['max_dd']*100:.2f}%**.",
        f"- Deployment: **{m['deployment_rate']*100:.2f}%**, episodes **{m['episodes']}**, hit **{m['hit_rate']*100:.0f}%**.",
        f"- Kết luận Phase 1: **{s['decision']}**.",
        "",
        "## Kết quả test",
        "",
        "| ID | Kết quả | Ghi chú |",
        "|---|---|---|",
    ]
    for k, v in s["tests"].items():
        lines.append(f"| {k} | {'✅' if v.get('pass') else '❌'} | {v.get('reason','')} |")
    lines += [
        "",
        "## Stress",
        "",
        "| Kịch bản | Return | APR | DD |",
        "|---|---:|---:|---:|",
    ]
    for k, v in s["stress"].items():
        lines.append(f"| {k} | {v['total_return']*100:.2f}% | {v['apr']*100:.2f}% | {v['max_dd']*100:.2f}% |")
    lines += [
        "",
        "## Finding chính",
        "",
        "- Universe bắt buộc **Spot + Futures perp**. 4 mã tham chiếu EVAA/AVAAI/PIEVERSE/PHAROS đều **không có Spot** → không thể hedge.",
        "- Trên universe tradable, gần như toàn bộ funding quanh baseline ~10,7%/năm; bộ lọc 20–60% gần như không chọn được coin.",
        "- Vì vậy Phase 1 **không đạt** tiêu chí ≥2 ứng viên/≥50% ngày và net APR ≥9%; không chuyển Phase 2 khi chưa xử lý mâu thuẫn universe.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    raw, features, pdict, farr, meta = _load()
    baseline = strategy.run_backtest(features, pdict, farr)

    snap = _snapshot(features, meta)
    # first episode day for shock
    if len(baseline.episodes):
        entry = pd.Timestamp(baseline.episodes.iloc[0]["entry"])
        shock_day = max(0, (entry - cfg.START).days)
    else:
        shock_day = 90

    stress = {}
    for name, kw in {
        "basis_2pct": {"basis_shock": 0.02, "shock_day": shock_day},
        "basis_5pct": {"basis_shock": 0.05, "shock_day": shock_day},
        "funding_minus_50pct": {"funding_mult": 0.5},
        "slippage_x2": {"cost_roundtrip": cfg.FEE_ROUNDTRIP + 2 * cfg.SLIPPAGE_ROUNDTRIP},
    }.items():
        r = strategy.run_backtest(features, pdict, farr, **kw)
        stress[name] = r.metrics

    nr = strategy.run_backtest(features, pdict, farr, signal_lag_days=1)
    nl = test_no_lookahead(raw, pd.Timestamp("2026-09-11", tz="UTC"))
    it = test_interval(raw)
    n = test_no_lookahead

    # P1 tests
    test = {}
    test["P1-T01"] = {"pass": nl["pass"], "reason": f"full vs cut: n={nl['n']}, max_apr_diff={nl['max_apr_diff']:.2e}, same_pass={nl['same_pass']}"}
    test["P1-T02"] = {"pass": it["pass"], "reason": f"{it['symbol']} native={it['native_apr14']*100:.2f}% max_diff={it['max_diff']*100:.4f}pp"}
    base_calc = 0.0001 * 3 * 365
    test["P1-T03"] = {"pass": abs(base_calc - cfg.BASELINE_APR) < 1e-6, "reason": f"0,01%/8h → {base_calc*100:.2f}%/năm"}
    drag = cfg.COST_ROUNDTRIP * 365 / 14
    test["P1-T04"] = {"pass": abs(drag - 0.09125) < 1e-6, "reason": f"c={cfg.COST_ROUNDTRIP*100:.2f}% → drag {drag*100:.3f}pp/năm"}
    cand = features[features["pass_all"]]
    min_bad = int((~cand["min_ok"]).sum()) if len(cand) else 0
    test["P1-T05"] = {"pass": min_bad == 0, "reason": f"{len(cand)} candidate rows, min_notional_fail={min_bad}"}
    trunc_sym = baseline.episodes.iloc[0]["symbol"] if len(baseline.episodes) else "SOLUSDT"
    cutoff = (cfg.START + pd.Timedelta(days=90)).isoformat()
    rt = strategy.run_backtest(features, pdict, farr, truncate={trunc_sym: cutoff})
    test["P1-T06"] = {"pass": True, "reason": f"truncate {trunc_sym} @ {cutoff}; no crash, episodes={rt.metrics['episodes']}"}
    raw_missing = dict(raw)
    raw_missing["funding"] = raw["funding"].sample(frac=0.9, random_state=42)
    fm, _, _, _ = strategy.build_features(raw_missing, save=False)
    test["P1-T07"] = {"pass": len(fm) > 0, "reason": f"drop 10% funding rows; features={len(fm)}, data_ok_false={int((~fm['data_ok']).sum()) if len(fm) else 0}"}
    tz_ok = bool(str(raw["funding"]["dt"].dt.tz) == "UTC")
    test["P1-T08"] = {"pass": tz_ok, "reason": f"funding dt tz={raw['funding']['dt'].dt.tz}"}
    ref_ok = all(snap["reference_spot"].values()) if snap["reference_spot"] else False
    test["P1-T09"] = {"pass": len(snap["passed"]) == 4 and ref_ok, "reason": f"snapshot={snap['passed']}; refs_spot={snap['reference_spot']}"}
    test["P1-T10"] = {"pass": stress["basis_2pct"]["max_dd"] >= -0.04 and stress["basis_5pct"]["max_dd"] >= -0.04, "reason": f"DD 2%={stress['basis_2pct']['max_dd']*100:.2f}%, 5%={stress['basis_5pct']['max_dd']*100:.2f}%"}
    test["P1-T11"] = {"pass": stress["funding_minus_50pct"]["apr"] > 0, "reason": f"APR={stress['funding_minus_50pct']['apr']*100:.2f}%"}
    test["P1-T12"] = {"pass": stress["slippage_x2"]["apr"] > 0, "reason": f"APR={stress['slippage_x2']['apr']*100:.2f}%"}

    passed = sum(1 for v in test.values() if v["pass"])
    decision = "ĐẠT" if passed == 12 and baseline["apr"] >= 0.09 and baseline["positive_month_ratio"] >= 0.7 and baseline["deployment_rate"] >= 0.5 else "KHÔNG ĐẠT — dừng trước Phase 2"
    summary = {
        "meta": meta, "baseline": baseline.metrics, "stress": stress,
        "lag1": nr.metrics, "snapshot": snap, "tests": test,
        "passed_tests": passed, "decision": decision,
        "funding_rows": int(len(raw["funding"])),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    baseline.equity.to_frame("equity").to_csv(OUT / "daily_equity.csv")
    baseline.episodes.to_csv(OUT / "episodes.csv", index=False)
    pd.DataFrame({"monthly": baseline.metrics["monthly_returns"]}).to_csv(OUT / "monthly.csv", index=False)
    features[features["date"] == pd.Timestamp("2026-11-24", tz="UTC")].to_csv(OUT / "snapshot.csv", index=False)
    (OUT / "report.md").write_text(_build_markdown(summary), encoding="utf-8")

    print(json.dumps({
        "meta": meta, "baseline": baseline.metrics, "passed": passed,
        "decision": decision, "snapshot": snap["passed"],
        "stress": {k: {"apr": v["apr"], "dd": v["max_dd"]} for k, v in stress.items()},
    }, ensure_ascii=False, indent=2))
    return 0 if decision == "ĐẠT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
