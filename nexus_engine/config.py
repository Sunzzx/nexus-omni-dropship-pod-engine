"""
Configuration and credentials manager for Nexus Dropship & POD Engine.
Supports live API credentials with graceful fallback to sandbox/simulation mode.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
CONFIG_FILE = ROOT_DIR / "nexus_config.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class NexusConfig:
    # Shopify Credentials
    shopify_shop_url: str = os.getenv("SHOPIFY_SHOP_URL", "https://nexus-demo-store.myshopify.com")
    shopify_access_token: str = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    shopify_api_version: str = os.getenv("SHOPIFY_API_VERSION", "2024-10")
    shopify_webhook_secret: str = os.getenv("SHOPIFY_WEBHOOK_SECRET", "whsec_nexus_demo_test_key_123")

    # CJ Dropshipping Open API Credentials
    cj_email: str = os.getenv("CJ_EMAIL", "ayufrom03@gmail.com")
    cj_api_key: str = os.getenv("CJ_API_KEY", "")
    cj_access_token: str = os.getenv("CJ_ACCESS_TOKEN", "")

    # Print-On-Demand (Printify & Printful) Credentials
    printify_api_token: str = os.getenv("PRINTIFY_API_TOKEN", "")
    printify_shop_id: str = os.getenv("PRINTIFY_SHOP_ID", "10849201")
    printful_api_token: str = os.getenv("PRINTFUL_API_TOKEN", "")

    # Business Rules & Margin Controls
    default_markup_percent: float = float(os.getenv("DEFAULT_MARKUP_PERCENT", "220.0"))  # 2.2x multiplier (120% margin)
    min_profit_dollars: float = float(os.getenv("MIN_PROFIT_DOLLARS", "12.00"))
    free_shipping_threshold: float = float(os.getenv("FREE_SHIPPING_THRESHOLD", "50.00"))
    auto_fulfill_orders: bool = os.getenv("AUTO_FULFILL_ORDERS", "true").lower() in ("true", "1", "yes")

    # Server settings
    server_host: str = os.getenv("NEXUS_SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("NEXUS_SERVER_PORT", "8090"))
    simulation_mode: bool = os.getenv("NEXUS_SIMULATION_MODE", "true").lower() in ("true", "1", "yes")

    @classmethod
    def load(cls) -> NexusConfig:
        cfg = cls()
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(cfg, k):
                            setattr(cfg, k, v)
            except Exception:
                pass
        return cfg

    def save(self) -> None:
        data = {
            "shopify_shop_url": self.shopify_shop_url,
            "shopify_api_version": self.shopify_api_version,
            "shopify_webhook_secret": self.shopify_webhook_secret,
            "cj_email": self.cj_email,
            "printify_shop_id": self.printify_shop_id,
            "default_markup_percent": self.default_markup_percent,
            "min_profit_dollars": self.min_profit_dollars,
            "free_shipping_threshold": self.free_shipping_threshold,
            "auto_fulfill_orders": self.auto_fulfill_orders,
            "server_host": self.server_host,
            "server_port": self.server_port,
            "simulation_mode": self.simulation_mode,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


config = NexusConfig.load()
