"""
Automated Multi-Supplier Tracking & Fulfillment Synchronization Daemon.
Polls CJ Dropshipping and Printify for shipped status and updates Shopify orders with live tracking.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List

from nexus_engine.clients.cj_dropshipping import CJDropshippingClient
from nexus_engine.clients.printify import PrintifyClient
from nexus_engine.clients.shopify import ShopifyClient
from nexus_engine.core.database import db
from nexus_engine.models import FulfillmentRecord, FulfillmentStatus, SupplierType

logger = logging.getLogger("nexus.tracker")


class FulfillmentTracker:
    def __init__(self):
        self.shopify_client = ShopifyClient()
        self.cj_client = CJDropshippingClient()
        self.printify_client = PrintifyClient()

    def sync_all_active_fulfillments(self) -> Dict[str, Any]:
        """Polls suppliers for active orders and pushes newly issued tracking numbers to Shopify."""
        active = db.list_active_fulfillments()
        logger.info("Found %d active fulfillments awaiting tracking numbers.", len(active))

        updated_count = 0
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for rec in active:
            try:
                tracking_number = None
                carrier = None
                tracking_url = None

                if rec.supplier_type == SupplierType.CJ_DROPSHIPPING:
                    # Query CJ Dropshipping
                    details = self.cj_client.get_order_tracking(rec.supplier_order_id)
                    tracking_number = details.get("trackingNumber")
                    carrier = details.get("logisticName", "CJ Packet")
                    tracking_url = details.get("trackingUrl")

                elif rec.supplier_type == SupplierType.PRINTIFY:
                    # Query Printify
                    details = self.printify_client.get_order(rec.supplier_order_id)
                    shipments = details.get("shipments", [])
                    if shipments:
                        sh = shipments[0]
                        tracking_number = sh.get("number")
                        carrier = sh.get("carrier", "USPS")
                        tracking_url = sh.get("url")

                # If tracking number is now available, close the loop with Shopify!
                if tracking_number:
                    rec.tracking_number = tracking_number
                    rec.carrier = carrier or "Standard Postal"
                    rec.tracking_url = tracking_url or f"https://www.17track.net/en/track?nums={tracking_number}"
                    rec.status = FulfillmentStatus.SHIPPED
                    rec.updated_at = now

                    # Push to Shopify
                    self.shopify_client.create_fulfillment(
                        shopify_order_id=rec.shopify_order_id,
                        tracking_number=rec.tracking_number,
                        carrier=rec.carrier,
                        tracking_url=rec.tracking_url
                    )

                    # Update local database
                    db.save_fulfillment(rec)
                    updated_count += 1
                    logger.info("✓ Synced Tracking for Order %s: %s (%s)", rec.shopify_order_id, tracking_number, carrier)

            except Exception as e:
                logger.error("Error checking tracking for fulfillment %s: %s", rec.fulfillment_id, e)

        return {
            "total_checked": len(active),
            "updated_to_shipped": updated_count,
            "timestamp": now,
        }


fulfillment_tracker = FulfillmentTracker()
