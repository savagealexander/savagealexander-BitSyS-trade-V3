"""Exchange connector package."""

from .binance import BinanceConnector
from .bitget import BitgetConnector

try:  # pragma: no cover - optional dependency
    from .binance_sdk_connector import BinanceSDKConnector
except Exception:  # noqa: BLE001
    BinanceSDKConnector = None  # type: ignore

__all__ = ["BinanceConnector", "BitgetConnector", "BinanceSDKConnector"]
