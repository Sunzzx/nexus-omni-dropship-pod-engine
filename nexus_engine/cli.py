"""
Nexus Omni-Dropship & POD CLI.
Unified command line interface for store management, product scouting, order simulation, and fulfillment syncing.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from nexus_engine.config import config
from nexus_engine.core.database import db
from nexus_engine.core.fulfillment_tracker import fulfillment_tracker
from nexus_engine.core.niche_scout import niche_scout
from nexus_engine.core.order_router import order_router
from nexus_engine.clients.shopify import ShopifyClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def cmd_status(args):
    print("=" * 65)
    print("⚡ NEXUS OMNI-DROPSHIP & POD AUTONOMOUS OPERATIONS STATUS")
    print("=" * 65)
    metrics = db.get_financial_summary()
    print(f"Total Orders:        {metrics['total_orders']}")
    print(f"Gross Revenue:       ${metrics['gross_revenue']:.2f}")
    print(f"Total COGS:          ${metrics['total_cogs']:.2f}")
    print(f"Net Profit:          ${metrics['net_profit']:.2f} ({metrics['profit_margin_pct']}% margin)")
    print(f"Catalog Products:    {metrics['total_products']}")
    print(f"Active Fulfillments: {metrics['active_fulfillments']}")
    print("-" * 65)
    print(f"Shopify Store URL:   {config.shopify_shop_url}")
    print(f"Simulation Mode:     {config.simulation_mode}")
    print(f"Auto-Fulfill Orders: {config.auto_fulfill_orders}")
    print("=" * 65)


def cmd_seed(args):
    print("🔍 Scouting and seeding winning dropship & POD products...")
    catalog = niche_scout.generate_curated_catalog()
    for p in catalog:
        db.save_product(p)
        print(f"  ✓ [{p.supplier_type.value}] {p.title} (Variants: {len(p.variants)})")
    print(f"\n🎉 Successfully seeded {len(catalog)} products into local catalog database.")


def cmd_publish(args):
    print("🚀 Publishing local catalog to Shopify Admin API...")
    client = ShopifyClient()
    products = db.list_products()
    count = 0
    for p in products:
        if not p.is_published:
            res = client.create_product(p)
            p.shopify_product_id = str(res.get("id"))
            p.is_published = True
            db.save_product(p)
            count += 1
            print(f"  ✓ Published '{p.title}' -> Shopify ID: {p.shopify_product_id}")
        else:
            print(f"  • '{p.title}' already published (ID: {p.shopify_product_id})")
    print(f"\n🎉 Total published in this run: {count}")


def cmd_simulate(args):
    import uuid
    print("🛒 Generating realistic customer order with CJ & POD items...")
    mock_order = {
        "id": int(uuid.uuid4().int % 100000000),
        "order_number": f"10{uuid.uuid4().int % 900 + 100}",
        "email": "alex.mercer@prototype.io",
        "total_price": "78.99",
        "currency": "USD",
        "shipping_address": {
            "first_name": "Alex",
            "last_name": "Mercer",
            "address1": "742 Evergreen Terrace",
            "city": "Springfield",
            "province": "OR",
            "zip": "97477",
            "country_code": "US",
            "country": "United States",
            "phone": "+1-555-0182"
        },
        "line_items": [
            {
                "id": 101,
                "variant_id": 201,
                "sku": "PRT-STOCHAST-MD-VNT",
                "title": "Stochastic Gradient Descent Heavyweight Boxy Tee - M / Vintage Black",
                "price": "34.00",
                "quantity": 1
            },
            {
                "id": 102,
                "variant_id": 202,
                "sku": "CJ-CHG-WHT",
                "title": "MagSafe Ambient Halo 3-in-1 Fast Wireless Charging Station - Arctic White",
                "price": "44.99",
                "quantity": 1
            }
        ]
    }
    order = order_router.process_incoming_shopify_order(mock_order)
    print(f"\n✅ Order Created & Dispatched:")
    print(f"   Order Number: #{order.shopify_order_number}")
    print(f"   Customer:     {order.customer_name} ({order.customer_email})")
    print(f"   Revenue:      ${order.total_revenue:.2f}")
    print(f"   Cost (COGS):  ${order.total_cost:.2f}")
    print(f"   Net Profit:   ${order.net_profit:.2f}")
    print(f"   Status:       {order.status.value.upper()}")


def cmd_sync(args):
    print("🔄 Checking active fulfillments against CJ Dropshipping & Printify...")
    res = fulfillment_tracker.sync_all_active_fulfillments()
    print(f"✓ Checked {res['total_checked']} in-flight fulfillments.")
    print(f"✓ Newly updated to SHIPPED: {res['updated_to_shipped']}")


def cmd_serve(args):
    import uvicorn
    print(f"🚀 Starting Nexus Omni-Dropship Server on {config.server_host}:{config.server_port}...")
    uvicorn.run("nexus_engine.server.app:app", host=config.server_host, port=config.server_port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Nexus Omni-Dropship & POD Autonomous CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="View store operations & profit metrics")
    sub.add_parser("seed", help="Discover and seed winning dropship + POD products")
    sub.add_parser("publish", help="Publish catalog to Shopify")
    sub.add_parser("simulate", help="Simulate a customer order and test supplier routing")
    sub.add_parser("sync", help="Sync fulfillment tracking numbers back to Shopify")
    sub.add_parser("serve", help="Run webhook listener and web dashboard")

    args = parser.parse_args()
    dispatch = {
        "status": cmd_status,
        "seed": cmd_seed,
        "publish": cmd_publish,
        "simulate": cmd_simulate,
        "sync": cmd_sync,
        "serve": cmd_serve,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
