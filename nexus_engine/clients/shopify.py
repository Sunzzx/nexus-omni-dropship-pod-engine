"""
Shopify Admin API Client (REST & GraphQL).
Provides automated product creation, inventory management, order listening, and fulfillment synchronization.
Includes built-in sandbox simulation mode.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from nexus_engine.config import config
from nexus_engine.models import CatalogProduct, CustomerOrder, FulfillmentRecord, OrderItem, ShippingAddress, SupplierType

logger = logging.getLogger("nexus.shopify")


class ShopifyClient:
    def __init__(self, shop_url: Optional[str] = None, access_token: Optional[str] = None):
        self.shop_url = (shop_url or config.shopify_shop_url).rstrip("/")
        self.access_token = access_token or config.shopify_access_token
        self.api_version = config.shopify_api_version
        self.simulation = config.simulation_mode or not bool(self.access_token)

    def _get_base_url(self) -> str:
        return f"{self.shop_url}/admin/api/{self.api_version}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
            "User-Agent": "NexusOmniDropshipEngine/1.0",
        }

    def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.simulation:
            logger.info("[SIMULATION] Shopify %s %s with %s", method, endpoint, data)
            return self._mock_response(method, endpoint, data)

        url = f"{self._get_base_url()}/{endpoint.lstrip('/')}"
        req_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=req_data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error("Shopify HTTPError %s %s: %s", e.code, e.reason, err_body)
            raise RuntimeError(f"Shopify API Error ({e.code}): {err_body}")
        except Exception as e:
            logger.error("Shopify Request Exception: %s", e)
            raise

    # ---------------- API Methods ----------------

    def create_product(self, product: CatalogProduct) -> Dict[str, Any]:
        """Publishes a product and its variants to Shopify."""
        variants_payload = []
        for v in product.variants:
            variants_payload.append({
                "title": v.title,
                "price": str(v.retail_price),
                "sku": v.sku,
                "inventory_management": "shopify",
                "inventory_policy": "continue",
                "option1": v.size or "Default",
                "option2": v.color or None,
            })

        options_payload = [{"name": "Size"}]
        if any(v.color for v in product.variants):
            options_payload.append({"name": "Color"})

        images_payload = [{"src": img} for img in product.images]

        payload = {
            "product": {
                "title": product.title,
                "body_html": product.description_html,
                "vendor": product.vendor,
                "product_type": product.product_type,
                "tags": ", ".join(product.tags),
                "options": options_payload,
                "variants": variants_payload,
                "images": images_payload,
                "status": "active",
            }
        }

        res = self._request("POST", "products.json", payload)
        prod_data = res.get("product", {})
        shopify_id = str(prod_data.get("id", ""))
        logger.info("Successfully pushed product to Shopify: %s (ID: %s)", product.title, shopify_id)
        return prod_data

    def create_fulfillment(self, shopify_order_id: str, tracking_number: str, carrier: str, tracking_url: Optional[str] = None) -> Dict[str, Any]:
        """Pushes tracking number and marks order fulfilled on Shopify."""
        # Under Shopify API 2024-10, fulfillments are created via fulfillment orders or legacy fulfillments
        payload = {
            "fulfillment": {
                "tracking_number": tracking_number,
                "tracking_company": carrier,
                "tracking_url": tracking_url or f"https://www.17track.net/en/track?nums={tracking_number}",
                "notify_customer": True,
            }
        }
        res = self._request("POST", f"orders/{shopify_order_id}/fulfillments.json", payload)
        logger.info("Created Shopify fulfillment for Order #%s with Tracking %s", shopify_order_id, tracking_number)
        return res

    def register_webhook(self, topic: str, address: str) -> Dict[str, Any]:
        """Subscribes to Shopify event webhooks (e.g. orders/create, orders/paid)."""
        payload = {
            "webhook": {
                "topic": topic,
                "address": address,
                "format": "json"
            }
        }
        return self._request("POST", "webhooks.json", payload)

    # ---------------- Simulation Mocking ----------------

    def _mock_response(self, method: str, endpoint: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        import time
        mock_id = int(time.time())
        if "products.json" in endpoint and method == "POST":
            prod = data.get("product", {}) if data else {}
            return {
                "product": {
                    "id": mock_id,
                    "title": prod.get("title", "Mock Product"),
                    "handle": "mock-product-" + str(mock_id),
                    "vendor": prod.get("vendor", "Nexus Dropship"),
                    "variants": [{"id": mock_id + 1, "sku": v.get("sku"), "price": v.get("price")} for v in prod.get("variants", [])],
                    "status": "active"
                }
            }
        elif "fulfillments.json" in endpoint:
            return {
                "fulfillment": {
                    "id": mock_id,
                    "order_id": endpoint.split("/")[1] if "/" in endpoint else mock_id,
                    "status": "success",
                    "tracking_company": data.get("fulfillment", {}).get("tracking_company", "CJ Packet"),
                    "tracking_number": data.get("fulfillment", {}).get("tracking_number", "CJ99284102US")
                }
            }
        elif "webhooks.json" in endpoint:
            return {
                "webhook": {
                    "id": mock_id,
                    "topic": data.get("webhook", {}).get("topic", "orders/create"),
                    "address": data.get("webhook", {}).get("address")
                }
            }
        return {"status": "ok", "mock_id": mock_id}
