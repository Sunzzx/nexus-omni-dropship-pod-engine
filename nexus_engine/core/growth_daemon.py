"""
Autonomous Store Growth, Multi-Store Expansion & Visibility Daemon.
Runs periodically to seed winning products, publish SEO content, generate viral ad kits,
and execute micro-influencer outreach across all active storefronts.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from nexus_engine.config import DATA_DIR
from nexus_engine.core.database import db
from nexus_engine.core.growth_engine import growth_engine
from nexus_engine.core.multi_store_manager import multi_store_manager
from nexus_engine.core.niche_scout import niche_scout
from nexus_engine.clients.shopify import ShopifyClient

logger = logging.getLogger("nexus.growth_daemon")
MARKETING_DIR = DATA_DIR / "marketing_assets"
MARKETING_DIR.mkdir(parents=True, exist_ok=True)


class GrowthDaemon:
    """Autonomous continuous growth runner."""

    def execute_growth_cycle(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        """Executes a full multi-store expansion and visibility cycle."""
        logger.info("==================================================")
        logger.info("🚀 STARTING AUTONOMOUS STORE EXPANSION & GROWTH CYCLE")
        logger.info("==================================================")

        multi_store_manager.ensure_default_stores()
        stores = multi_store_manager.list_stores(active_only=True)
        if store_id:
            stores = [s for s in stores if s.store_id == store_id]
            if not stores:
                logger.warning("No store found matching store_id=%s", store_id)
                stores = multi_store_manager.list_stores(active_only=True)
        logger.info("Active Storefront Network: %d stores registered", len(stores))

        # 1. Product Discovery & Multi-Store Seeding
        catalog = niche_scout.generate_curated_catalog()
        seeded_count = 0
        published_count = 0

        # Partition products by niche across stores
        for idx, prod in enumerate(catalog):
            # Target matching store by niche
            matched_store = stores[0]
            for s in stores:
                if any(w.lower() in s.target_niche.lower() for w in prod.tags):
                    matched_store = s
                    break

            prod.target_store_id = matched_store.store_id
            db.save_product(prod)
            seeded_count += 1

            # Auto-publish to Shopify
            client = multi_store_manager.get_client_for_store(matched_store.store_id)
            if not prod.is_published:
                res = client.create_product(prod)
                prod.shopify_product_id = str(res.get("id"))
                prod.is_published = True
                db.save_product(prod)
                published_count += 1

        logger.info("✓ Product Fleet: %d seeded, %d published to stores", seeded_count, published_count)

        # 2. Programmatic SEO Generation & Publishing
        all_prods = db.list_products(limit=20)
        articles_created = 0
        for p in all_prods:
            target_store = multi_store_manager.get_store(p.target_store_id or stores[0].store_id) or stores[0]
            art = growth_engine.generate_programmatic_seo_article(p, target_store, publish_to_store=True)
            articles_created += 1

        logger.info("✓ Programmatic SEO: %d rich buyer guides generated with JSON-LD", articles_created)

        # 3. Viral Social Media & Ad Creative Synthesis
        creatives_created = 0
        for p in all_prods[:10]:
            target_store = multi_store_manager.get_store(p.target_store_id or stores[0].store_id) or stores[0]
            pack = growth_engine.generate_creative_pack(p, target_store)
            creatives_created += 1

            # Save exportable file for social media automation / marketing team
            pack_file = MARKETING_DIR / f"{p.handle}_creative_pack.json"
            pack_file.write_text(pack.model_dump_json(indent=2), encoding="utf-8")

        logger.info("✓ Viral Marketing: %d Creative Packs (TikTok/Meta/Pinterest) synthesized", creatives_created)

        # 4. Micro-Influencer Outreach & VIP Discount Code Generation
        outreach_created = 0
        discounts_created = 0
        for s in stores:
            camp = growth_engine.generate_influencer_outreach_campaign(s)
            outreach_created += 1

            # Provision dynamic discount on store
            client = multi_store_manager.get_client_for_store(s.store_id)
            client.create_discount_code(f"VIP{s.name[:3].upper()}15", percentage_off=15.0)
            discounts_created += 1

        logger.info("✓ Influencer Outreach: %d campaigns provisioned with 20%% affiliate rev-share", outreach_created)

        summary = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "stores_analyzed": len(stores),
            "products_seeded": seeded_count,
            "products_published": published_count,
            "seo_articles_published": articles_created,
            "creative_packs_synthesized": creatives_created,
            "influencer_campaigns_created": outreach_created,
            "discount_codes_provisioned": discounts_created,
        }

        logger.info("🎉 Autonomous Store Growth Cycle Complete: %s", json.dumps(summary))
        return summary


growth_daemon = GrowthDaemon()
