"""
CJ Dropshipping Open API v2.0 Client.
Provides automated product sourcing, stock checking, wholesale order dispatch, and live logistics tracking.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from nexus_engine.config import config
from nexus_engine.models import CatalogProduct, ProductVariant, ShippingAddress, SupplierType

logger = logging.getLogger("nexus.cj")

CJ_BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"


class CJDropshippingClient:
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        self.api_key = api_key or config.cj_api_key
        self.email = email or config.cj_email
        self.access_token = config.cj_access_token
        self.simulation = config.simulation_mode or not bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NexusOmniDropshipEngine/1.0",
        }
        if self.access_token:
            headers["CJ-Access-Token"] = self.access_token
        return headers

    def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if self.simulation:
            logger.info("[SIMULATION] CJ Dropshipping %s %s with %s", method, endpoint, data or params)
            return self._mock_response(endpoint, data or params)

        url = f"{CJ_BASE_URL}/{endpoint.lstrip('/')}"
        if params:
            import urllib.parse
            url += "?" + urllib.parse.urlencode(params)

        req_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=req_data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if not res.get("result", True):
                    raise RuntimeError(f"CJ API Error: {res.get('message')}")
                return res.get("data", res)
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8")
            logger.error("CJ API HTTPError %s: %s", e.code, err)
            raise RuntimeError(f"CJ HTTPError: {err}")
        except Exception as e:
            logger.error("CJ API Exception: %s", e)
            raise

    # ---------------- API Methods ----------------

    def search_products(self, keyword: str, page: int = 1, size: int = 20) -> List[Dict[str, Any]]:
        """Search CJ global supplier warehouse catalog."""
        params = {"productNameEn": keyword, "pageNum": str(page), "pageSize": str(size)}
        res = self._request("GET", "product/list", params=params)
        return res.get("list", []) if isinstance(res, dict) else res

    def get_product_details(self, pid: str) -> Dict[str, Any]:
        """Fetch full specs, images, variant weights, and inventory."""
        params = {"pid": pid}
        return self._request("GET", "product/query", params=params)

    def calculate_freight(self, country_code: str, weight_grams: float) -> Dict[str, Any]:
        """Calculates exact shipping cost and estimated transit days."""
        payload = {
            "endCountryCode": country_code,
            "weight": weight_grams,
            "productType": "NORMAL"
        }
        res = self._request("POST", "logistic/freightCalculate", payload)
        return res

    def create_order(self, order_number: str, address: ShippingAddress, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Dispatches an order to CJ warehouse for automated picking, packing & shipment."""
        products_payload = []
        for it in items:
            products_payload.append({
                "vid": it.get("supplier_variant_id") or "VID_MOCK_9921",
                "quantity": it.get("quantity", 1),
                "sku": it.get("sku")
            })

        payload = {
            "orderNumber": order_number,
            "shippingCountryCode": address.country_code,
            "shippingCountry": address.country_name,
            "shippingProvince": address.province or address.city,
            "shippingCity": address.city,
            "shippingAddress": address.address1 + (" " + address.address2 if address.address2 else ""),
            "shippingCustomerName": f"{address.first_name} {address.last_name}",
            "shippingPhone": address.phone or "+1-555-0199",
            "shippingZip": address.zip_code,
            "products": products_payload,
            "logisticName": "CJ Packet Ordinary"
        }
        res = self._request("POST", "shopping/order/createOrder", payload)
        logger.info("Created CJ Dropshipping Order for #%s -> CJ Order ID: %s", order_number, res.get("orderId"))
        return res

    def get_order_tracking(self, cj_order_id: str) -> Dict[str, Any]:
        """Retrieves tracking number, carrier name, and latest checkpoint."""
        params = {"orderId": cj_order_id}
        return self._request("GET", "shopping/order/getOrderDetail", params=params)

    # ---------------- Simulation Mocking ----------------

    def _mock_response(self, endpoint: str, data: Any) -> Dict[str, Any]:
        if "product/list" in endpoint:
            return {
                "list": [
                    {
                        "pid": "CJ-PROD-991",
                        "productNameEn": "MagSafe Ambient Glow 15W Fast Wireless Charging Dock",
                        "productImage": "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=800",
                        "sellPrice": "14.50",
                        "weight": 220,
                        "variants": [
                            {"vid": "CJ-VID-101", "variantSku": "CJ-CHG-BLK", "variantName": "Midnight Black", "sellPrice": "14.50"},
                            {"vid": "CJ-VID-102", "variantSku": "CJ-CHG-WHT", "variantName": "Arctic White", "sellPrice": "14.50"}
                        ]
                    },
                    {
                        "pid": "CJ-PROD-992",
                        "productNameEn": "Titanium EDC Mechanical Haptic Fidget Pen",
                        "productImage": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=800",
                        "sellPrice": "9.80",
                        "weight": 85,
                        "variants": [
                            {"vid": "CJ-VID-201", "variantSku": "CJ-PEN-RAW", "variantName": "Raw Titanium", "sellPrice": "9.80"},
                            {"vid": "CJ-VID-202", "variantSku": "CJ-PEN-BLK", "variantName": "Stealth Black", "sellPrice": "9.80"}
                        ]
                    }
                ]
            }
        elif "shopping/order/createOrder" in endpoint:
            import time
            return {
                "orderId": f"CJ_ORD_{int(time.time())}",
                "status": "PAID_VERIFIED",
                "cost": 17.50,
                "shippingCost": 4.80,
            }
        elif "shopping/order/getOrderDetail" in endpoint:
            return {
                "orderId": data.get("orderId", "CJ_ORD_12345"),
                "status": "SHIPPED",
                "trackingNumber": "CJ994810293US",
                "logisticName": "CJ Packet Express",
                "trackingUrl": "https://www.17track.net/en/track?nums=CJ994810293US"
            }
        elif "logistic/freightCalculate" in endpoint:
            return {
                "logisticList": [
                    {"logisticName": "CJ Packet Ordinary", "price": 4.50, "aging": "7-12 days"},
                    {"logisticName": "CJ Packet Fast", "price": 6.80, "aging": "5-8 days"}
                ]
            }
        return {"status": "ok"}
