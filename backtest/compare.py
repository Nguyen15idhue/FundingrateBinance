"""So sánh backtest 180d và 365d."""

from __future__ import annotations

import json
from pathlib import Path


def load(path: str) -> dict | None:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def row(label: str, a: dict | None, b: dict | None) -> str:
    def g(d, key, mult=1.0, fmt="{:.2f}"):
        try:
            return fmt.format(d["baseline"][key] * mult)
        except Exception:
            return "—"

    return f"| {label} | {g(a,'apr',100)}% | {g(b,'apr',100)}% | {g(a,'deployment_rate',100)}% | {g(b,'deployment_rate',100)}% | {g(a,'total_return',100)}% | {g(b,'total_return',100)}% |"


def main() -> None:
    a = load("reports/phase1/summary.json")
    b = load("reports/phase1_365/summary.json")
    print("| Chỉ số | 180d | 365d |")
    print("|---|---:|---:|")
    for label, key, mult in (
        ("Net APR", "apr", 100), ("Return", "total_return", 100),
        ("Deployment", "deployment_rate", 100), ("Max DD", "max_dd", 100),
        ("Positive months", "positive_month_ratio", 100),
        ("Episodes", "episodes", 1), ("Hit rate", "hit_rate", 100),
        ("Fee drag APR", "fee_drag_apr", 100),
    ):
        av = f"{a['baseline'][key]*mult:.2f}" if a else "—"
        bv = f"{b['baseline'][key]*mult:.2f}" if b else "—"
        print(f"| {label} | {av} | {bv} |")
    for label, key in (("P1 tests pass", "passed_tests"), ("Decision", "decision")):
        print(f"| {label} | {a.get(key) if a else '—'} | {b.get(key) if b else '—'} |")


if __name__ == "__main__":
    main()
