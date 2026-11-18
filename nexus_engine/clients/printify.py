"""
Printify Print-On-Demand (POD) REST API Client.
Automates product blueprint configuration, print provider routing, and order creation.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from nexus_engine.config import config
from nexus_engine.models import ShippingAddress

logger = logging.getLogger("nexus.printify")

PRINTIFY_BASE_URL = "https://api.printify.com/v1"


class PrintifyClient:
    def __init__(self, api_token: Optional[str] = None, shop_id: Optional[str] = None):
        self.api_token = api_token or config.printify_api_token
        self.shop_id = shop_id or config.printify_shop_id
        self.simulation = config.simulation_mode or not bool(self.api_token)

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}",
            "User-Agent": "NexusOmniDropshipEngine/1.0",
        }

    def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.simulation:
            logger.info("[SIMULATION] Printify %s %s with %s", method, endpoint, data)
            return self._mock_response(method, endpoint, data)

        url = f"{PRINTIFY_BASE_URL}/{endpoint.lstrip('/')}"
        req_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=req_data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8")
            logger.error("Printify HTTPError %s: %s", e.code, err)
            raise RuntimeError(f"Printify API Error ({e.code}): {err}")
        except Exception as e:
            logger.error("Printify Request Exception: %s", e)
            raise

    # ---------------- API Methods ----------------

    def get_blueprints(self) -> List[Dict[str, Any]]:
        """List available blanks (tees, hoodies, hats, mugs, canvas)."""
        res = self._request("GET", "catalog/blueprints.json")
        return res if isinstance(res, list) else res.get("data", [])

    def create_pod_product(self, title: str, description: str, blueprint_id: int, print_provider_id: int, image_url: str) -> Dict[str, Any]:
        """Creates a tailored POD product inside Printify."""
        payload = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id,
            "print_provider_id": print_provider_id,
            "variants": [
                {"id": 101, "price": 2800, "is_enabled": True},
                {"id": 102, "price": 2800, "is_enabled": True},
                {"id": 103, "price": 2800, "is_enabled": True},
            ],
            "print_areas": [
                {
                    "position": "front",
                    "images": [{"src": image_url, "scale": 1.0, "x": 0.5, "y": 0.5}]
                }
            ]
        }
        return self._request("POST", f"shops/{self.shop_id}/products.json", payload)

    def create_order(self, external_id: str, address: ShippingAddress, line_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Submits an order to Printify production."""
        items_payload = []
        for it in line_items:
            var_raw = it.get("supplier_variant_id")
            try:
                var_int = int(var_raw) if var_raw else 101
            except (ValueError, TypeError):
                var_int = 101
            items_payload.append({
                "product_id": it.get("supplier_product_id") or "64d029194e8a",
                "variant_id": var_int,
                "quantity": it.get("quantity", 1)
            })

        payload = {
            "external_id": external_id,
            "label": f"Nexus Shopify Order #{external_id}",
            "line_items": items_payload,
            "shipping_method": 1,  # Standard Flat Rate
            "send_shipping_notification": False,
            "address_to": {
                "first_name": address.first_name,
                "last_name": address.last_name,
                "email": "customer@example.com",
                "phone": address.phone or "+1-555-0100",
                "country": address.country_code,
                "region": address.province or address.city,
                "address1": address.address1,
                "address2": address.address2 or "",
                "city": address.city,
                "zip": address.zip_code
            }
        }
        res = self._request("POST", f"shops/{self.shop_id}/orders.json", payload)
        logger.info("Created Printify Order for #%s -> Printify ID: %s", external_id, res.get("id"))
        return res

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Gets production and fulfillment status from Printify."""
        return self._request("GET", f"shops/{self.shop_id}/orders/{order_id}.json")

    # ---------------- Simulation Mocking ----------------

    def _mock_response(self, method: str, endpoint: str, data: Any) -> Dict[str, Any]:
        import time
        mock_id = f"PRT_{int(time.time())}"
        if "catalog/blueprints" in endpoint:
            return [
                {"id": 12, "title": "Unisex Heavyweight Boxy Tee (Lane Seven)", "brand": "Lane Seven"},
                {"id": 384, "title": "Heavy Blend Hooded Sweatshirt (Gildan 18500)", "brand": "Gildan"},
                {"id": 68, "title": "Ceramic Mug 15oz", "brand": "Generic"}
            ]
        elif "orders" in endpoint and method == "POST":
            return {
                "id": mock_id,
                "status": "pending",
                "total_price": 1420,  # $14.20 in cents
                "total_shipping": 450,
            }
        elif "orders/" in endpoint and method == "GET":
            return {
                "id": endpoint.split("/")[-1].replace(".json", ""),
                "status": "fulfilled",
                "shipments": [
                    {
                        "carrier": "USPS",
                        "number": "9400111899562537198210",
                        "url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400111899562537198210"
                    }
                ]
            }
        return {"id": mock_id, "status": "ok"}
