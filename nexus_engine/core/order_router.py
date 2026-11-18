"""
Zero-Touch Multi-Supplier Order Routing & Autonomous Dispatcher.
Splits incoming Shopify orders by supplier (CJ vs Printify vs Printful) and executes wholesale fulfillment.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Tuple
from pathlib import Path

from nexus_engine.config import config
from nexus_engine.core.database import db
from nexus_engine.models import (
    CustomerOrder,
    FulfillmentRecord,
    FulfillmentStatus,
    OrderItem,
    ShippingAddress,
    SupplierType,
)
from nexus_engine.clients.cj_dropshipping import CJDropshippingClient
from nexus_engine.clients.printify import PrintifyClient
from nexus_engine.clients.shopify import ShopifyClient

logger = logging.getLogger("nexus.router")
WHATSAPP_SCRIPT = Path.home() / ".hermes" / "scripts" / "send_whatsapp.py"


class OrderRouter:
    def __init__(self):
        self.shopify_client = ShopifyClient()
        self.cj_client = CJDropshippingClient()
        self.printify_client = PrintifyClient()

    def process_incoming_shopify_order(self, raw_payload: Dict[str, Any]) -> CustomerOrder:
        """Parses a Shopify order webhook payload, routes items to suppliers, and logs fulfillment."""
        order_data = raw_payload.get("order", raw_payload)
        shopify_order_id = str(order_data.get("id", ""))
        order_number = str(order_data.get("order_number", order_data.get("name", "1001")))
        customer_email = order_data.get("email") or "customer@example.com"
        
        # Shipping address parsing
        raw_addr = order_data.get("shipping_address") or order_data.get("billing_address") or {}
        address = ShippingAddress(
            first_name=raw_addr.get("first_name", "Valued"),
            last_name=raw_addr.get("last_name", "Customer"),
            address1=raw_addr.get("address1", "123 Market St"),
            address2=raw_addr.get("address2", ""),
            city=raw_addr.get("city", "Austin"),
            province=raw_addr.get("province", "TX"),
            zip_code=raw_addr.get("zip", "78701"),
            country_code=raw_addr.get("country_code", "US"),
            country_name=raw_addr.get("country", "United States"),
            phone=raw_addr.get("phone", "+1-555-0199")
        )

        line_items: List[OrderItem] = []
        total_rev = float(order_data.get("total_price", "0.0") or 0.0)
        total_cost = 0.0

        raw_items = order_data.get("line_items", [])
        for it in raw_items:
            sku = it.get("sku", "")
            unit_price = float(it.get("price", "0.0") or 0.0)
            qty = int(it.get("quantity", 1))

            # Look up supplier mapping in database
            var_record = db.get_variant_by_sku(sku)
            if var_record:
                supplier = SupplierType(var_record["supplier_type"])
                cost = float(var_record["cost_price"]) * qty
                sup_prod_id = var_record["supplier_product_id"]
                sup_var_id = var_record["supplier_variant_id"]
            else:
                # Default heuristics by SKU prefix
                if sku.startswith("CJ-"):
                    supplier = SupplierType.CJ_DROPSHIPPING
                    cost = round(unit_price * 0.40, 2)
                elif sku.startswith("PRT-"):
                    supplier = SupplierType.PRINTIFY
                    cost = round(unit_price * 0.45, 2)
                else:
                    supplier = SupplierType.MANUAL
                    cost = round(unit_price * 0.50, 2)
                sup_prod_id = "MOCK-PROD-001"
                sup_var_id = "MOCK-VAR-001"

            total_cost += cost
            line_items.append(
                OrderItem(
                    line_item_id=str(it.get("id", uuid.uuid4().hex[:6])),
                    shopify_variant_id=str(it.get("variant_id", "")),
                    sku=sku,
                    title=it.get("title", "Product"),
                    quantity=qty,
                    unit_price=unit_price,
                    cost_price=cost,
                    supplier_type=supplier,
                    supplier_product_id=sup_prod_id,
                    supplier_variant_id=sup_var_id,
                )
            )

        if total_rev == 0.0:
            total_rev = sum(it.unit_price * it.quantity for it in line_items)

        net_profit = round(total_rev - total_cost, 2)
        internal_order_id = f"NEX-ORD-{uuid.uuid4().hex[:8].upper()}"

        customer_order = CustomerOrder(
            order_id=internal_order_id,
            shopify_order_id=shopify_order_id,
            shopify_order_number=order_number,
            customer_email=customer_email,
            customer_name=f"{address.first_name} {address.last_name}",
            currency=order_data.get("currency", "USD"),
            total_revenue=round(total_rev, 2),
            total_cost=round(total_cost, 2),
            net_profit=net_profit,
            shipping_address=address,
            items=line_items,
            status=FulfillmentStatus.DISPATCHED if config.auto_fulfill_orders else FulfillmentStatus.PENDING,
        )

        db.save_order(customer_order)
        logger.info("Saved Customer Order %s (Shopify #%s). Revenue: $%s | Profit: $%s", internal_order_id, order_number, total_rev, net_profit)

        # Execute automated dispatch to respective suppliers if enabled
        if config.auto_fulfill_orders:
            self.dispatch_to_suppliers(customer_order)

        return customer_order

    def dispatch_to_suppliers(self, order: CustomerOrder) -> List[FulfillmentRecord]:
        """Splits order line items by supplier and executes wholesale orders."""
        # Group items by supplier
        supplier_buckets: Dict[SupplierType, List[OrderItem]] = {}
        for it in order.items:
            supplier_buckets.setdefault(it.supplier_type, []).append(it)

        records: List[FulfillmentRecord] = []

        for supplier, items in supplier_buckets.items():
            f_id = f"FUL-{uuid.uuid4().hex[:8].upper()}"
            supplier_order_id = ""

            try:
                if supplier == SupplierType.CJ_DROPSHIPPING:
                    # Dispatch to CJ Dropshipping
                    cj_items = [{"sku": it.sku, "quantity": it.quantity, "supplier_variant_id": it.supplier_variant_id} for it in items]
                    res = self.cj_client.create_order(f"{order.shopify_order_number}-{f_id[:4]}", order.shipping_address, cj_items)
                    supplier_order_id = str(res.get("orderId", f"CJ_ORD_{uuid.uuid4().hex[:6]}"))
                    status = FulfillmentStatus.DISPATCHED

                elif supplier == SupplierType.PRINTIFY:
                    # Dispatch to Printify
                    prt_items = [{"supplier_product_id": it.supplier_product_id, "supplier_variant_id": it.supplier_variant_id, "quantity": it.quantity} for it in items]
                    res = self.printify_client.create_order(f"{order.shopify_order_number}-{f_id[:4]}", order.shipping_address, prt_items)
                    supplier_order_id = str(res.get("id", f"PRT_ORD_{uuid.uuid4().hex[:6]}"))
                    status = FulfillmentStatus.IN_PRODUCTION

                else:
                    supplier_order_id = f"MANUAL_{uuid.uuid4().hex[:6]}"
                    status = FulfillmentStatus.PENDING

            except Exception as e:
                logger.error("Failed to dispatch order %s to supplier %s: %s", order.order_id, supplier.value, e)
                supplier_order_id = "FAILED_ATTEMPT"
                status = FulfillmentStatus.FAILED

            record = FulfillmentRecord(
                fulfillment_id=f_id,
                order_id=order.order_id,
                shopify_order_id=order.shopify_order_id,
                supplier_type=supplier,
                supplier_order_id=supplier_order_id,
                status=status,
                supplier_cost=sum(it.cost_price for it in items),
            )
            db.save_fulfillment(record)
            records.append(record)

        # Notify operator
        self._notify_operator(order, records)
        return records

    def _notify_operator(self, order: CustomerOrder, fulfillments: List[FulfillmentRecord]):
        msg = (
            f"🛒 [NEW DROPSHIP/POD ORDER RECEIVED]\n"
            f"Order: #{order.shopify_order_number} ({order.customer_name})\n"
            f"Revenue: ${order.total_revenue:.2f} | Profit: ${order.net_profit:.2f}\n"
            f"Fulfillments Dispatched: {len(fulfillments)}\n"
        )
        for f in fulfillments:
            msg += f"  • {f.supplier_type.value}: {f.supplier_order_id} [{f.status.value}]\n"

        logger.info(msg)
        if WHATSAPP_SCRIPT.exists():
            import subprocess
            try:
                subprocess.run(
                    ["python3", str(WHATSAPP_SCRIPT), "--message", msg],
                    capture_output=True,
                    timeout=15,
                )
            except Exception:
                pass


order_router = OrderRouter()
