"""
Nexus Omni-Dropship & POD CLI.
Unified command line interface for store management, product scouting, order simulation, fulfillment syncing, and autonomous growth engine.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from nexus_engine.config import config
from nexus_engine.core.database import db
from nexus_engine.core.fulfillment_tracker import fulfillment_tracker
from nexus_engine.core.growth_daemon import growth_daemon
from nexus_engine.core.growth_engine import growth_engine
from nexus_engine.core.multi_store_manager import multi_store_manager
from nexus_engine.core.niche_scout import niche_scout
from nexus_engine.core.order_router import order_router
from nexus_engine.clients.shopify import ShopifyClient
from nexus_engine.models import PlatformType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def cmd_status(args):
    print("=" * 70)
    print("⚡ NEXUS OMNI-DROPSHIP & POD AUTONOMOUS OPERATIONS STATUS")
    print("=" * 70)
    metrics = db.get_financial_summary()
    stores = multi_store_manager.list_stores()
    print(f"Active Stores:       {len(stores)}")
    print(f"Total Orders:        {metrics['total_orders']}")
    print(f"Gross Revenue:       ${metrics['gross_revenue']:.2f}")
    print(f"Total COGS:          ${metrics['total_cogs']:.2f}")
    print(f"Net Profit:          ${metrics['net_profit']:.2f} ({metrics['profit_margin_pct']}% margin)")
    print(f"Catalog Products:    {metrics['total_products']}")
    print(f"Active Fulfillments: {metrics['active_fulfillments']}")
    print(f"SEO Articles:        {metrics.get('total_seo_articles', 0)}")
    print(f"Creative Packs:      {metrics.get('total_creative_packs', 0)}")
    print("-" * 70)
    print(f"Shopify Store URL:   {config.shopify_shop_url}")
    print(f"Simulation Mode:     {config.simulation_mode}")
    print(f"Auto-Fulfill Orders: {config.auto_fulfill_orders}")
    print("=" * 70)


def cmd_stores(args):
    stores = multi_store_manager.list_stores()
    print(f"🏪 Active Storefront Fleet ({len(stores)} stores):")
    print("-" * 70)
    for s in stores:
        status_icon = "🟢" if s.is_active else "🔴"
        print(f"  {status_icon} [{s.store_id}] {s.name} ({s.platform.value.upper()})")
        print(f"     Niche:    {s.niche}")
        print(f"     URL:      {s.shop_url}")
        print(f"     Currency: {s.currency}")
    print("-" * 70)


def cmd_add_store(args):
    platform_map = {
        "shopify": PlatformType.SHOPIFY,
        "woocommerce": PlatformType.WOOCOMMERCE,
        "tiktok": PlatformType.TIKTOK_SHOP,
        "etsy": PlatformType.ETSY,
    }
    platform = platform_map.get(args.platform.lower(), PlatformType.SHOPIFY)
    store = multi_store_manager.register_store(
        name=args.name,
        shop_url=args.url,
        target_niche=args.niche,
        platform=platform,
    )
    print(f"🎉 Registered new store successfully:")
    print(f"   ID:       {store.store_id}")
    print(f"   Name:     {store.name}")
    print(f"   Niche:    {store.niche}")
    print(f"   URL:      {store.shop_url}")
    print(f"   Platform: {store.platform.value}")


def cmd_grow(args):
    print("🚀 Triggering Autonomous Growth & Scaling Cycle...")
    summary = growth_daemon.execute_growth_cycle(store_id=args.store_id)
    print("\n📈 Growth Cycle Completed Successfully:")
    print(f"  • Stores Processed:              {summary.get('stores_analyzed', 0)}")
    print(f"  • Winning Products Seeded:       {summary.get('products_seeded', 0)}")
    print(f"  • Products Published to Store:   {summary.get('products_published', 0)}")
    print(f"  • Programmatic SEO Guides:       {summary.get('seo_articles_published', 0)}")
    print(f"  • Viral Creative Packs:          {summary.get('creative_packs_synthesized', 0)}")
    print(f"  • Influencer Campaigns:          {summary.get('influencer_campaigns_created', 0)}")
    print(f"  • VIP Promo Codes Provisioned:   {summary.get('discount_codes_provisioned', 0)}")
    print("-" * 70)


def cmd_generate_seo(args):
    stores = multi_store_manager.list_stores(active_only=True)
    target_store = stores[0]
    if args.store_id:
        store = multi_store_manager.get_store(args.store_id)
        if store:
            target_store = store

    products = db.list_products(limit=5)
    if not products:
        niche_scout.generate_curated_catalog()
        products = db.list_products(limit=5)

    target_product = products[0]
    print(f"📝 Synthesizing Programmatic SEO Buying Guide for '{target_product.title}' (Store: {target_store.name})...")
    article = growth_engine.generate_programmatic_seo_article(
        product=target_product,
        store=target_store,
        publish_to_store=True,
    )
    print(f"\n✓ Generated Article: '{article.title}'")
    print(f"  Article ID:  {article.article_id}")
    print(f"  Slug:        {article.slug}")
    print(f"  Keywords:    {', '.join(article.target_keywords[:5])}")
    print(f"  JSON-LD:     {len(article.json_ld_schema)} chars of structured data")
    print(f"  Published:   {'YES' if article.is_published else 'NO'}")


def cmd_generate_creatives(args):
    stores = multi_store_manager.list_stores(active_only=True)
    target_store = stores[0]
    products = db.list_products(limit=10)
    if not products:
        print("❌ No products found in catalog. Run 'nexus-ecom seed' first.")
        return

    target_product = products[0]
    if args.product_id:
        found = [p for p in products if p.product_id == args.product_id]
        if found:
            target_product = found[0]

    print(f"🎬 Synthesizing Viral TikTok / Meta Creative Pack for '{target_product.title}'...")
    pack = growth_engine.generate_creative_pack(target_product, target_store)
    print(f"\n✓ Creative Pack Synthesized (ID: {pack.pack_id}):")
    print(f"  Product:        {pack.product_title}")
    print(f"  TikTok Hook:    {pack.tiktok_storyboard['hook_0_3s']['on_screen_text']}")
    print(f"  TikTok Visual:  {pack.tiktok_storyboard['hook_0_3s']['visual']}")
    print(f"  Meta Ad Hook:   {pack.meta_ad_copy['headline']}")
    print(f"  Pinterest Pin:  {pack.pinterest_pin['pin_title']}")


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
            "phone": "+1-555-0182",
        },
        "line_items": [
            {
                "id": 101,
                "variant_id": 201,
                "sku": "PRT-STOCHAST-MD-VNT",
                "title": "Stochastic Gradient Descent Heavyweight Boxy Tee - M / Vintage Black",
                "price": "34.00",
                "quantity": 1,
            },
            {
                "id": 102,
                "variant_id": 202,
                "sku": "CJ-CHG-WHT",
                "title": "MagSafe Ambient Halo 3-in-1 Fast Wireless Charging Station - Arctic White",
                "price": "44.99",
                "quantity": 1,
            },
        ],
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
    sub.add_parser("stores", help="List all storefronts in the automated network")
    
    add_store_parser = sub.add_parser("add-store", help="Register a new store into the network")
    add_store_parser.add_argument("--name", required=True, help="Store brand name")
    add_store_parser.add_argument("--url", required=True, help="Store domain / URL")
    add_store_parser.add_argument("--niche", required=True, help="Store focus niche")
    add_store_parser.add_argument("--platform", default="shopify", choices=["shopify", "woocommerce", "tiktok", "etsy"], help="Store platform")

    grow_parser = sub.add_parser("grow", help="Run autonomous growth, SEO, creative ad generation, and promo cycle")
    grow_parser.add_argument("--store-id", default=None, help="Target specific store ID (or all if omitted)")

    seo_parser = sub.add_parser("generate-seo", help="Generate programmatic SEO buying guide")
    seo_parser.add_argument("--niche", default="", help="Niche for SEO guide")
    seo_parser.add_argument("--store-id", default="store-streetwear-001", help="Store ID")

    creative_parser = sub.add_parser("generate-creatives", help="Generate TikTok & Meta ad creative pack")
    creative_parser.add_argument("--product-id", default=None, help="Target product ID")

    sub.add_parser("seed", help="Discover and seed winning dropship + POD products")
    sub.add_parser("publish", help="Publish catalog to Shopify")
    sub.add_parser("simulate", help="Simulate a customer order and test supplier routing")
    sub.add_parser("sync", help="Sync fulfillment tracking numbers back to Shopify")
    sub.add_parser("serve", help="Run webhook listener and web dashboard")

    args = parser.parse_args()
    dispatch = {
        "status": cmd_status,
        "stores": cmd_stores,
        "add-store": cmd_add_store,
        "grow": cmd_grow,
        "generate-seo": cmd_generate_seo,
        "generate-creatives": cmd_generate_creatives,
        "seed": cmd_seed,
        "publish": cmd_publish,
        "simulate": cmd_simulate,
        "sync": cmd_sync,
        "serve": cmd_serve,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
