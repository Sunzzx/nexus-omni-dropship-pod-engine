"""
End-to-End Test Suite for Nexus Omni-Dropship & POD Engine.
Tests supplier routing, margin calculation, catalog generation, and tracking sync.
"""

import unittest
from nexus_engine.config import config
from nexus_engine.core.database import db
from nexus_engine.core.niche_scout import niche_scout
from nexus_engine.core.order_router import order_router
from nexus_engine.core.fulfillment_tracker import fulfillment_tracker
from nexus_engine.clients.shopify import ShopifyClient
from nexus_engine.clients.cj_dropshipping import CJDropshippingClient
from nexus_engine.clients.printify import PrintifyClient
from nexus_engine.models import SupplierType, FulfillmentStatus


class TestNexusEngine(unittest.TestCase):
    def setUp(self):
        config.simulation_mode = True

    def test_niche_scout_generates_catalog(self):
        catalog = niche_scout.generate_curated_catalog()
        self.assertGreaterEqual(len(catalog), 3)
        for p in catalog:
            self.assertTrue(p.title)
            self.assertGreater(len(p.variants), 0)
            self.assertIn(p.supplier_type, [SupplierType.CJ_DROPSHIPPING, SupplierType.PRINTIFY])
            # Verify retail price > cost price (positive margin)
            for v in p.variants:
                self.assertGreater(v.retail_price, v.cost_price)

    def test_database_persistence(self):
        catalog = niche_scout.generate_curated_catalog()
        prod = catalog[0]
        db.save_product(prod)
        loaded = db.get_product(prod.product_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, prod.title)

    def test_shopify_client(self):
        client = ShopifyClient()
        catalog = niche_scout.generate_curated_catalog()
        res = client.create_product(catalog[0])
        self.assertIn("id", res)
        self.assertEqual(res["status"], "active")

        # Test fulfillment
        ful_res = client.create_fulfillment("998811", "CJ99482103US", "CJ Packet")
        self.assertIn("fulfillment", ful_res)

    def test_cj_client(self):
        client = CJDropshippingClient()
        prods = client.search_products("charger")
        self.assertGreaterEqual(len(prods), 1)
        self.assertTrue(prods[0]["pid"].startswith("CJ-"))

        freight = client.calculate_freight("US", 250)
        self.assertIn("logisticList", freight)

    def test_printify_client(self):
        client = PrintifyClient()
        blueprints = client.get_blueprints()
        self.assertGreaterEqual(len(blueprints), 1)

    def test_order_router_multi_supplier_split(self):
        # Seed catalog first so SKUs exist in DB
        catalog = niche_scout.generate_curated_catalog()
        for p in catalog:
            db.save_product(p)

        mock_payload = {
            "id": 7712398,
            "order_number": "1099",
            "email": "test@domain.com",
            "total_price": "85.00",
            "shipping_address": {
                "first_name": "Tony",
                "last_name": "Stark",
                "address1": "10880 Malibu Point",
                "city": "Malibu",
                "province": "CA",
                "zip": "90265",
                "country_code": "US"
            },
            "line_items": [
                {
                    "id": 1,
                    "sku": "CJ-CHG-BLK",
                    "title": "MagSafe Ambient Halo Charger",
                    "price": "45.00",
                    "quantity": 1
                },
                {
                    "id": 2,
                    "sku": "PRT-STOCHAST-LG-OBS",
                    "title": "Stochastic Gradient Boxy Tee",
                    "price": "40.00",
                    "quantity": 1
                }
            ]
        }

        order = order_router.process_incoming_shopify_order(mock_payload)
        self.assertEqual(order.shopify_order_number, "1099")
        self.assertGreater(order.net_profit, 0)
        self.assertEqual(len(order.items), 2)

        # Verify fulfillments were logged in database
        active = db.list_active_fulfillments()
        self.assertGreaterEqual(len(active), 1)

    def test_fulfillment_tracker_sync(self):
        res = fulfillment_tracker.sync_all_active_fulfillments()
        self.assertIn("total_checked", res)
        self.assertIn("updated_to_shipped", res)


if __name__ == "__main__":
    unittest.main()
