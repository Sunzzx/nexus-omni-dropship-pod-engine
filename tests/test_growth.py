"""
Unit & Integration Test Suite for Nexus Multi-Store Fleet & Autonomous Growth Engine.
Validates multi-tenant stores, programmatic SEO JSON-LD, viral creative packs, and continuous growth daemon.
"""

import json
import unittest
from nexus_engine.config import config
from nexus_engine.core.database import db
from nexus_engine.core.growth_daemon import growth_daemon
from nexus_engine.core.growth_engine import growth_engine
from nexus_engine.core.multi_store_manager import multi_store_manager
from nexus_engine.core.niche_scout import niche_scout
from nexus_engine.clients.shopify import ShopifyClient
from nexus_engine.models import PlatformType, StoreConfig


class TestMultiStoreAndGrowthEngine(unittest.TestCase):
    def setUp(self):
        config.simulation_mode = True
        multi_store_manager.ensure_default_stores()

    def test_multi_store_manager_defaults(self):
        stores = multi_store_manager.list_stores(active_only=True)
        self.assertGreaterEqual(len(stores), 3)
        store_ids = [s.store_id for s in stores]
        self.assertIn("store-streetwear-01", store_ids)
        self.assertIn("store-desktech-02", store_ids)
        self.assertIn("store-decor-03", store_ids)

        # Test store property alias
        self.assertTrue(stores[0].niche)
        self.assertEqual(stores[0].niche, stores[0].target_niche)

    def test_register_new_store(self):
        new_store = multi_store_manager.register_store(
            name="Quantum Mechanical Keyboards",
            shop_url="https://quantum-keebs.myshopify.com",
            target_niche="Custom Mechanical Keyboards & Artisan Keycaps",
            platform=PlatformType.SHOPIFY,
        )
        self.assertTrue(new_store.store_id.startswith("store-"))
        self.assertEqual(new_store.name, "Quantum Mechanical Keyboards")

        fetched = multi_store_manager.get_store(new_store.store_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.shop_url, "https://quantum-keebs.myshopify.com")

    def test_programmatic_seo_article_generation(self):
        catalog = niche_scout.generate_curated_catalog()
        prod = catalog[0]
        store = multi_store_manager.list_stores(active_only=True)[0]

        article = growth_engine.generate_programmatic_seo_article(
            product=prod,
            store=store,
            publish_to_store=True,
        )
        self.assertTrue(article.article_id.startswith("SEO-"))
        self.assertTrue(article.slug)
        self.assertIn(prod.handle, article.slug)
        self.assertGreater(len(article.target_keywords), 2)
        self.assertTrue(article.is_published)
        self.assertIn(store.shop_url, article.published_url)

        # Verify Schema.org JSON-LD validity
        parsed_schema = json.loads(article.json_ld_schema)
        self.assertEqual(parsed_schema["@context"], "https://schema.org")
        self.assertIn("@graph", parsed_schema)
        graph_types = [item["@type"] for item in parsed_schema["@graph"]]
        self.assertIn("Article", graph_types)
        self.assertIn("Product", graph_types)
        self.assertIn("FAQPage", graph_types)

    def test_creative_pack_synthesis(self):
        catalog = niche_scout.generate_curated_catalog()
        prod = catalog[0]
        store = multi_store_manager.list_stores(active_only=True)[0]

        pack = growth_engine.generate_creative_pack(prod, store)
        self.assertTrue(pack.pack_id.startswith("CRV-"))
        self.assertEqual(pack.product_id, prod.product_id)

        # Verify TikTok 3-act structure
        sb = pack.tiktok_storyboard
        self.assertIn("hook_0_3s", sb)
        self.assertIn("body_3_15s", sb)
        self.assertIn("cta_15_20s", sb)
        self.assertIn("hashtags", sb)
        self.assertGreater(len(sb["hashtags"]), 3)

        # Verify Meta ad copy
        meta = pack.meta_ad_copy
        self.assertIn("headline", meta)
        self.assertIn("primary_text", meta)
        self.assertIn("destination_url", meta)

        # Verify Pinterest rich pin
        pin = pack.pinterest_pin
        self.assertIn("pin_title", pin)
        self.assertIn("pin_description", pin)

    def test_influencer_outreach_campaign(self):
        store = multi_store_manager.list_stores(active_only=True)[0]
        camp = growth_engine.generate_influencer_outreach_campaign(store)
        self.assertTrue(camp.campaign_id.startswith("INF-"))
        self.assertEqual(camp.niche, store.target_niche)
        self.assertIn(store.name, camp.dm_pitch)
        self.assertIn(store.shop_url, camp.email_pitch)

    def test_shopify_blog_and_discount_api(self):
        client = ShopifyClient()
        # Test publishing blog article
        article_res = client.publish_blog_article(
            title="The 2026 Developer Desk Setup Guide",
            body_html="<p>Minimalist ergonomics and focused productivity.</p>",
            author="Nexus Lab",
            tags=["desksetup", "minimalism"],
            handle="developer-desk-setup-guide-2026",
        )
        self.assertIn("article", article_res)
        self.assertEqual(article_res["article"]["title"], "The 2026 Developer Desk Setup Guide")

        # Test creating discount code
        discount_res = client.create_discount_code("TESTOFF20", percentage_off=20.0)
        self.assertTrue(discount_res.get("success"))
        self.assertEqual(discount_res.get("code"), "TESTOFF20")

    def test_growth_daemon_execution(self):
        summary = growth_daemon.execute_growth_cycle()
        self.assertGreater(summary["stores_analyzed"], 0)
        self.assertGreater(summary["products_seeded"], 0)
        self.assertGreater(summary["seo_articles_published"], 0)
        self.assertGreater(summary["creative_packs_synthesized"], 0)
        self.assertGreater(summary["influencer_campaigns_created"], 0)
        self.assertGreater(summary["discount_codes_provisioned"], 0)


if __name__ == "__main__":
    unittest.main()
