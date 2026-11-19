"""
Multi-Store Manager & Multi-Tenant Storefront Fleet Orchestrator.
Enables horizontal scaling across multiple Shopify, TikTok Shop, Etsy, and WooCommerce storefronts.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from nexus_engine.config import config
from nexus_engine.core.database import db
from nexus_engine.models import PlatformType, StoreConfig
from nexus_engine.clients.shopify import ShopifyClient

logger = logging.getLogger("nexus.multi_store")


class MultiStoreManager:
    """Orchestrates multi-store registry and multi-tenant catalog partitioning."""

    def __init__(self):
        self.ensure_default_stores()

    def ensure_default_stores(self) -> None:
        """Seeds default multi-niche storefront network if empty."""
        stores = db.list_stores()
        if not stores:
            default_stores = [
                StoreConfig(
                    store_id="store-streetwear-01",
                    name="Atelier Quant Streetwear",
                    platform=PlatformType.SHOPIFY,
                    shop_url="https://atelier-quant.myshopify.com",
                    target_niche="Quant & Cyberpunk Developer Streetwear",
                    currency="USD",
                    is_active=True,
                ),
                StoreConfig(
                    store_id="store-desktech-02",
                    name="Lumina Ergonomic Tech & EDC",
                    platform=PlatformType.SHOPIFY,
                    shop_url="https://lumina-desktech.myshopify.com",
                    target_niche="Ergonomic Desk Tech & Ambient Workspace",
                    currency="USD",
                    is_active=True,
                ),
                StoreConfig(
                    store_id="store-decor-03",
                    name="Khora Geometric Wall Decor",
                    platform=PlatformType.SHOPIFY,
                    shop_url="https://khora-decor.myshopify.com",
                    target_niche="Minimalist Mathematical & Geometric Wall Decor",
                    currency="USD",
                    is_active=True,
                ),
            ]
            for s in default_stores:
                db.save_store(s)
            logger.info("Initialized default 3-store niche network.")

    def register_store(
        self,
        name: str,
        shop_url: str,
        target_niche: str,
        platform: PlatformType = PlatformType.SHOPIFY,
        access_token: str = "",
        webhook_secret: str = "",
        currency: str = "USD",
    ) -> StoreConfig:
        """Registers a new store into the autonomous network."""
        store_id = f"store-{uuid.uuid4().hex[:8]}"
        store = StoreConfig(
            store_id=store_id,
            name=name,
            platform=platform,
            shop_url=shop_url,
            access_token=access_token,
            webhook_secret=webhook_secret,
            target_niche=target_niche,
            currency=currency,
            is_active=True,
        )
        db.save_store(store)
        logger.info("Registered new store: %s [%s] (%s)", name, store_id, shop_url)
        return store

    def list_stores(self, active_only: bool = False) -> List[StoreConfig]:
        return db.list_stores(active_only=active_only)

    def get_store(self, store_id: str) -> Optional[StoreConfig]:
        return db.get_store(store_id)

    def get_client_for_store(self, store_id: str) -> ShopifyClient:
        """Returns an API client bound to a specific store's credentials."""
        store = self.get_store(store_id)
        if not store:
            return ShopifyClient()
        return ShopifyClient(
            shop_url=store.shop_url,
            access_token=store.access_token or config.shopify_access_token,
        )


multi_store_manager = MultiStoreManager()
