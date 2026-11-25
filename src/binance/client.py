"""Binance REST client tối giản cho Binance Spot + USDⓈ-M Futures.

- Public endpoints: không cần key.
- Signed endpoints: HMAC SHA256, tự đồng bộ giờ server.
- Có sẵn guard: không gửi lệnh nếu DRY_RUN=true hoặc chưa bật LIVE_TRADING_ENABLED (trừ Demo Trading).

KHÔNG dùng key có quyền Withdraw. Key demo chỉ dùng cho demo.binance.com.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from src.config import Settings


class BinanceAPIError(RuntimeError):
    def __init__(self, status_code: int, code: int | None, msg: str, endpoint: str = ""):
        self.status_code = status_code
        self.code = code
        self.msg = msg
        self.endpoint = endpoint
        super().__init__(f"{endpoint} -> HTTP {status_code} code={code}: {msg}")


class BinanceClient:
    SPOT_LIVE = "https://api.binance.com"
    FUTURES_LIVE = "https://fapi.binance.com"
    # Demo Trading (demo.binance.com) — ví ảo, dữ liệu thị trường sát live.
    # Không phải testnet cũ; key demo chỉ dùng được trên endpoint demo.
    SPOT_DEMO = "https://demo-api.binance.com"
    FUTURES_DEMO = "https://demo-fapi.binance.com"

    def __init__(
        self,
        settings: Settings,
        *,
        readonly: bool = False,
        demo: bool | None = None,
    ):
        self.settings = settings
        self.readonly = readonly
        self.demo = settings.use_demo if demo is None else demo

        spot_override = settings.env("BINANCE_SPOT_BASE_URL")
        futures_override = settings.env("BINANCE_FUTURES_BASE_URL")
        self.spot_base = spot_override or (self.SPOT_DEMO if self.demo else self.SPOT_LIVE)
        self.futures_base = futures_override or (
            self.FUTURES_DEMO if self.demo else self.FUTURES_LIVE
        )

        if self.demo:
            if readonly:
                self.api_key = settings.demo_readonly_key or settings.demo_key
                self.api_secret = settings.demo_readonly_secret or settings.demo_secret
            else:
                self.api_key = settings.demo_key
                self.api_secret = settings.demo_secret
        elif readonly:
            self.api_key = settings.readonly_key
            self.api_secret = settings.readonly_secret
        else:
            self.api_key = settings.api_key
            self.api_secret = settings.api_secret

        self.recv_window = settings.env_int(
            "BINANCE_RECV_WINDOW", int(settings.get("api.recv_window", 5000))
        )
        timeout = settings.env_int(
            "BINANCE_TIMEOUT_SECONDS", int(settings.get("api.timeout_seconds", 15))
        )
        self._http = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "funding-harvest/0.1"},
        )
        self._offsets: dict[str, int] = {}

    # ---------- lifecycle ----------
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BinanceClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    @property
    def has_keys(self) -> bool:
        return bool(self.api_key and self.api_secret)

    # ---------- low level ----------
    def _base(self, market: str) -> str:
        return self.spot_base if market == "spot" else self.futures_base

    def _json(self, response: httpx.Response, endpoint: str) -> Any:
        try:
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            body = response.text[:300]
            raise BinanceAPIError(response.status_code, None, f"Non-JSON response: {body}") from exc
        if response.status_code >= 400:
            code = data.get("code") if isinstance(data, dict) else None
            msg = data.get("msg") if isinstance(data, dict) else str(data)
            raise BinanceAPIError(response.status_code, code, msg or "unknown", endpoint)
        return data

    def _get(self, market: str, path: str, params: dict[str, Any] | None = None) -> Any:
        url = self._base(market) + path
        response = self._http.get(url, params=params or {})
        return self._json(response, path)

    def _server_offset(self, market: str) -> int:
        if market in self._offsets:
            return self._offsets[market]
        path = "/api/v3/time" if market == "spot" else "/fapi/v1/time"
        data = self._get(market, path)
        offset = int(data["serverTime"]) - int(time.time() * 1000)
        self._offsets[market] = offset
        return offset

    def _signed(
        self,
        method: str,
        market: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        if not self.has_keys:
            raise BinanceAPIError(0, None, "Missing API key/secret", path)
        payload = dict(params or {})
        payload["timestamp"] = int(time.time() * 1000) + self._server_offset(market)
        payload["recvWindow"] = self.recv_window
        query = urlencode(payload)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        url = f"{self._base(market)}{path}?{query}&signature={signature}"
        response = self._http.request(method, url, headers={"X-MBX-APIKEY": self.api_key})
        return self._json(response, f"{path} [signed]")

    # ---------- public: market data ----------
    def server_time(self, market: str = "futures") -> dict[str, Any]:
        path = "/api/v3/time" if market == "spot" else "/fapi/v1/time"
        return self._get(market, path)

    def exchange_info(self) -> dict[str, Any]:
        return self._get("futures", "/fapi/v1/exchangeInfo")

    def premium_index(self, symbol: str | None = None) -> Any:
        params = {"symbol": symbol} if symbol else None
        return self._get("futures", "/fapi/v1/premiumIndex", params)

    def funding_rate(self, symbol: str, limit: int = 120) -> list[dict[str, Any]]:
        return self._get(
            "futures",
            "/fapi/v1/fundingRate",
            {"symbol": symbol, "limit": max(1, min(int(limit), 1000))},
        )

    def ticker_24hr(self) -> list[dict[str, Any]]:
        return self._get("futures", "/fapi/v1/ticker/24hr")

    def depth(self, symbol: str, limit: int = 50) -> dict[str, Any]:
        return self._get("futures", "/fapi/v1/depth", {"symbol": symbol, "limit": limit})

    def open_interest(self, symbol: str) -> dict[str, Any]:
        return self._get("futures", "/fapi/v1/openInterest", {"symbol": symbol})

    def open_interest_hist(
        self, symbol: str, period: str = "1h", limit: int = 30
    ) -> list[dict[str, Any]]:
        return self._get(
            "futures",
            "/futures/data/openInterestHist",
            {"symbol": symbol, "period": period, "limit": limit},
        )

    # ---------- private: account ----------
    def account_spot(self) -> dict[str, Any]:
        return self._signed("GET", "spot", "/api/v3/account")

    def account_futures(self) -> dict[str, Any]:
        return self._signed("GET", "futures", "/fapi/v2/account")

    def position_risk(self, symbol: str | None = None) -> Any:
        params = {"symbol": symbol} if symbol else None
        return self._signed("GET", "futures", "/fapi/v2/positionRisk", params)

    def api_restrictions(self) -> dict[str, Any]:
        return self._signed("GET", "spot", "/sapi/v1/account/apiRestrictions")

    def commission_rate(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        return self._signed("GET", "futures", "/fapi/v1/commissionRate", {"symbol": symbol})

    def spot_trade_fee(self, symbol: str | None = None) -> Any:
        params = {"symbol": symbol} if symbol else None
        return self._signed("GET", "spot", "/sapi/v1/asset/tradeFee", params)

    # ---------- private: settings ----------
    def _write_guard(self, action: str) -> None:
        if self.readonly:
            raise BinanceAPIError(0, None, f"Read-only client — không {action}")

    def set_leverage(self, symbol: str, leverage: int = 1) -> dict[str, Any]:
        self._write_guard("đổi leverage")
        return self._signed(
            "POST", "futures", "/fapi/v1/leverage", {"symbol": symbol, "leverage": leverage}
        )

    def set_margin_type(self, symbol: str, margin_type: str = "CROSSED") -> dict[str, Any]:
        self._write_guard("đổi margin type")
        try:
            return self._signed(
                "POST",
                "futures",
                "/fapi/v1/marginType",
                {"symbol": symbol, "marginType": margin_type},
            )
        except BinanceAPIError as exc:
            # -4046: No need to change margin type (đã đúng)
            if exc.code == -4046:
                return {"code": 200, "msg": "already set"}
            raise

    def universal_transfer(self, asset: str, amount: float, transfer_type: str) -> dict[str, Any]:
        """transfer_type: MAIN_UMFUTURE (Spot→Futures) | UMFUTURE_MAIN (Futures→Spot)."""
        self._write_guard("chuyển tiền")
        return self._signed(
            "POST",
            "spot",
            "/sapi/v1/asset/transfer",
            {"type": transfer_type, "asset": asset, "amount": f"{amount:.8f}"},
        )

    # ---------- private: orders (có guard) ----------
    def _order_guard(self) -> None:
        self._write_guard("gửi/hủy lệnh")
        if self.settings.dry_run:
            raise BinanceAPIError(0, None, "DRY_RUN=true — không gửi lệnh thật")
        if not (self.settings.live_trading_enabled or self.settings.use_demo):
            raise BinanceAPIError(
                0, None, "LIVE_TRADING_ENABLED=false — không gửi lệnh thật"
            )

    def place_futures_order(self, **params: Any) -> dict[str, Any]:
        self._order_guard()
        return self._signed("POST", "futures", "/fapi/v1/order", params)

    def place_spot_order(self, **params: Any) -> dict[str, Any]:
        self._order_guard()
        return self._signed("POST", "spot", "/api/v3/order", params)

    def query_futures_order(
        self,
        symbol: str,
        *,
        order_id: int | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"symbol": symbol}
        if order_id is not None:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        return self._signed("GET", "futures", "/fapi/v1/order", params)

    def cancel_futures_order(
        self,
        symbol: str,
        *,
        order_id: int | None = None,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"symbol": symbol}
        if order_id is not None:
            params["orderId"] = order_id
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        self._write_guard("hủy lệnh")
        return self._signed("DELETE", "futures", "/fapi/v1/order", params)

    def cancel_all_futures_orders(self, symbol: str) -> dict[str, Any]:
        self._write_guard("hủy lệnh")
        return self._signed("DELETE", "futures", "/fapi/v1/allOpenOrders", {"symbol": symbol})
