"""Cấu hình trung tâm: đọc .env + config/settings.yaml.

Thứ tự ưu tiên:
1. Biến môi trường (.env hoặc system env) — cho phép override nhanh
2. config/settings.yaml — tham số chiến lược
3. Giá trị mặc định trong code

Không bao giờ log/print secret.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


class ConfigError(RuntimeError):
    """Cấu hình sai ở mức không được phép chạy."""


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text == "":
        return default
    return text in {"1", "true", "yes", "y", "on"}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _deep_get(data: dict, path: str, default: Any = None) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _deep_set(data: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


_ENV_OVERRIDES: tuple[tuple[str, str, str], ...] = (
    ("CAPITAL_TOTAL_USD", "capital.total_usd", "int"),
    ("CAPITAL_SPOT_USD", "capital.spot_usd", "int"),
    ("CAPITAL_FUTURES_USD", "capital.futures_usd", "int"),
    ("PERP_LEVERAGE", "capital.leverage", "int"),
    ("MAX_COINS", "capital.coins", "int"),
    ("MAX_ORDER_NOTIONAL_USD", "risk.max_order_notional_usd", "int"),
    ("SCREENER_MAX_SYMBOLS", "screener.max_symbols", "int"),
)


class Settings:
    def __init__(self, config: dict[str, Any], root: Path = ROOT, *, use_env: bool = True):
        self.root = Path(root)
        self.config = config
        self.env_file = self.root / ".env"
        if use_env:
            load_dotenv(self.env_file, override=False)

        if not use_env:
            return

        for env_name, path, kind in _ENV_OVERRIDES:
            raw = self.env(env_name)
            if raw == "":
                continue
            if kind == "int":
                _deep_set(self.config, path, _as_int(raw, _as_int(_deep_get(self.config, path, 0), 0)))
            elif kind == "float":
                _deep_set(self.config, path, _as_float(raw, _as_float(_deep_get(self.config, path, 0.0), 0.0)))

    # ---------- truy cập ----------
    def get(self, path: str, default: Any = None) -> Any:
        return _deep_get(self.config, path, default)

    def env(self, name: str, default: str = "") -> str:
        return (os.getenv(name) or default).strip()

    def env_bool(self, name: str, default: bool = False) -> bool:
        return _as_bool(os.getenv(name), default)

    def env_int(self, name: str, default: int = 0) -> int:
        return _as_int(os.getenv(name), default)

    def env_float(self, name: str, default: float = 0.0) -> float:
        return _as_float(os.getenv(name), default)

    # ---------- an toàn ----------
    @property
    def dry_run(self) -> bool:
        return self.env_bool("DRY_RUN", True)

    @property
    def live_trading_enabled(self) -> bool:
        return self.env_bool("LIVE_TRADING_ENABLED", False)

    @property
    def kill_switch_enabled(self) -> bool:
        return self.env_bool("KILL_SWITCH_ENABLED", True)

    @property
    def use_demo(self) -> bool:
        """True = dùng Binance Demo Trading (demo.binance.com), không phải tiền thật."""
        return self.env_bool("BINANCE_USE_DEMO", False)

    # ---------- keys ----------
    @property
    def api_key(self) -> str:
        return self.env("BINANCE_API_KEY")

    @property
    def api_secret(self) -> str:
        return self.env("BINANCE_API_SECRET")

    @property
    def readonly_key(self) -> str:
        return self.env("BINANCE_READONLY_KEY")

    @property
    def readonly_secret(self) -> str:
        return self.env("BINANCE_READONLY_SECRET")

    @property
    def demo_key(self) -> str:
        return self.env("BINANCE_DEMO_API_KEY")

    @property
    def demo_secret(self) -> str:
        return self.env("BINANCE_DEMO_API_SECRET")

    @property
    def demo_readonly_key(self) -> str:
        return self.env("BINANCE_DEMO_READONLY_KEY")

    @property
    def demo_readonly_secret(self) -> str:
        return self.env("BINANCE_DEMO_READONLY_SECRET")

    def has_trade_keys(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def has_readonly_keys(self) -> bool:
        return bool(self.readonly_key and self.readonly_secret)

    def has_demo_keys(self) -> bool:
        return bool(self.demo_key and self.demo_secret)

    # ---------- kiểm tra ----------
    def validate(self) -> list[str]:
        """Trả về danh sách lỗi cứng. Rỗng = hợp lệ."""
        errors: list[str] = []

        total = self.get("capital.total_usd", 0)
        spot = self.get("capital.spot_usd", 0)
        futures = self.get("capital.futures_usd", 0)
        margin = self.get("capital.margin_usd", 0)
        buffer = self.get("capital.buffer_usd", 0)
        leverage = self.get("capital.leverage", 1)
        coins = self.get("capital.coins", 0)
        notional = self.get("capital.notional_per_leg_usd", 0)
        per_coin = self.get("capital.notional_per_coin_usd", 0)

        if spot + futures != total:
            errors.append(f"spot ({spot}) + futures ({futures}) != total ({total})")
        if margin + buffer != futures:
            errors.append(f"margin ({margin}) + buffer ({buffer}) != futures ({futures})")
        if margin != notional:
            errors.append(f"margin ({margin}) != notional_per_leg ({notional}) ở 1x")
        if leverage != 1:
            errors.append(f"leverage phải = 1 ở giai đoạn 1, đang là {leverage}")
        if coins <= 0:
            errors.append("coins phải > 0")
        if coins and per_coin and abs(coins * per_coin - notional) > 1:
            errors.append(f"coins ({coins}) × per_coin ({per_coin}) lệch notional ({notional}) > $1")
        if self.get("risk.max_order_notional_usd", 0) <= 0:
            errors.append("max_order_notional_usd phải > 0")

        return errors

    def warnings(self) -> list[str]:
        warnings: list[str] = []
        if self.live_trading_enabled and self.dry_run:
            warnings.append("LIVE_TRADING_ENABLED=true nhưng DRY_RUN=true — bot sẽ chỉ chạy mô phỏng.")
        if self.live_trading_enabled and not self.has_trade_keys():
            warnings.append("LIVE_TRADING_ENABLED=true nhưng chưa có BINANCE_API_KEY/SECRET.")
        if self.use_demo and self.live_trading_enabled:
            warnings.append("Đang bật demo nhưng LIVE_TRADING_ENABLED=true — kiểm tra lại ý định.")
        if self.use_demo and not self.has_demo_keys():
            warnings.append("BINANCE_USE_DEMO=true nhưng chưa có BINANCE_DEMO_API_KEY/SECRET.")
        if not self.use_demo and not self.has_trade_keys():
            warnings.append("Chưa có key Binance — các kiểm tra private sẽ bị bỏ qua.")
        return warnings

    def require_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise ConfigError("; ".join(errors))


def load_settings(config_path: str | Path | None = None) -> Settings:
    path = Path(config_path) if config_path else (ROOT / "config" / "settings.yaml")
    if not path.exists():
        raise ConfigError(f"Không tìm thấy file cấu hình: {path}")
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    return Settings(config)


def get_settings() -> Settings:
    return load_settings()
