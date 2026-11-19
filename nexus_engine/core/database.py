"""
Durable SQLite ledger for Nexus Dropship & POD Engine.
Manages persistent multi-store catalogs, order histories, fulfillments, SEO articles, and creative growth assets.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from nexus_engine.config import DATA_DIR
from nexus_engine.models import (
    CatalogProduct,
    CreativePack,
    CustomerOrder,
    FulfillmentRecord,
    FulfillmentStatus,
    InfluencerOutreach,
    OrderItem,
    PlatformType,
    ProductVariant,
    SEOArticle,
    ShippingAddress,
    StoreConfig,
    SupplierType,
)

DB_PATH = DATA_DIR / "nexus_ledger.db"


class NexusDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
        return self._conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS stores (
                store_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                shop_url TEXT NOT NULL,
                access_token TEXT,
                target_niche TEXT,
                currency TEXT DEFAULT 'USD',
                is_active INTEGER DEFAULT 1,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                shopify_product_id TEXT,
                title TEXT NOT NULL,
                handle TEXT NOT NULL,
                vendor TEXT,
                product_type TEXT,
                supplier_type TEXT NOT NULL,
                supplier_product_id TEXT NOT NULL,
                target_store_id TEXT,
                data_json TEXT NOT NULL,
                is_published INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS variants (
                variant_id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                sku TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                cost_price REAL NOT NULL,
                retail_price REAL NOT NULL,
                supplier_variant_id TEXT,
                supplier_sku TEXT,
                data_json TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                store_id TEXT,
                shopify_order_id TEXT UNIQUE NOT NULL,
                shopify_order_number TEXT NOT NULL,
                customer_email TEXT,
                customer_name TEXT,
                total_revenue REAL NOT NULL,
                total_cost REAL NOT NULL,
                net_profit REAL NOT NULL,
                status TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fulfillments (
                fulfillment_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                shopify_order_id TEXT NOT NULL,
                supplier_type TEXT NOT NULL,
                supplier_order_id TEXT NOT NULL,
                status TEXT NOT NULL,
                carrier TEXT,
                tracking_number TEXT,
                tracking_url TEXT,
                supplier_cost REAL DEFAULT 0.0,
                shipping_cost REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS seo_articles (
                article_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                product_id TEXT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL,
                target_keywords TEXT,
                meta_description TEXT,
                body_html TEXT NOT NULL,
                json_ld_schema TEXT,
                published_url TEXT,
                is_published INTEGER DEFAULT 0,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS creative_packs (
                pack_id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                product_title TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS influencer_campaigns (
                campaign_id TEXT PRIMARY KEY,
                niche TEXT NOT NULL,
                influencer_tier TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS supplier_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                supplier_type TEXT NOT NULL,
                action TEXT NOT NULL,
                request_payload TEXT,
                response_payload TEXT,
                status_code INTEGER,
                is_success INTEGER
            );
            """)

            # Auto-migrate columns if table already existed prior to multi-store/growth expansion
            try:
                conn.execute("ALTER TABLE products ADD COLUMN target_store_id TEXT;")
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute("ALTER TABLE orders ADD COLUMN store_id TEXT;")
            except sqlite3.OperationalError:
                pass

    # ---------------- Multi-Store Operations ----------------

    def save_store(self, store: StoreConfig) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO stores (
                    store_id, name, platform, shop_url, access_token,
                    target_niche, currency, is_active, data_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    store.store_id,
                    store.name,
                    store.platform.value,
                    store.shop_url,
                    store.access_token,
                    store.target_niche,
                    store.currency,
                    1 if store.is_active else 0,
                    store.model_dump_json(),
                    store.created_at,
                ),
            )

    def get_store(self, store_id: str) -> Optional[StoreConfig]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT data_json FROM stores WHERE store_id = ?", (store_id,)).fetchone()
            if row:
                return StoreConfig.model_validate_json(row["data_json"])
        return None

    def list_stores(self, active_only: bool = False) -> List[StoreConfig]:
        with self._get_conn() as conn:
            q = "SELECT data_json FROM stores"
            if active_only:
                q += " WHERE is_active = 1"
            q += " ORDER BY created_at ASC"
            rows = conn.execute(q).fetchall()
            return [StoreConfig.model_validate_json(r["data_json"]) for r in rows]

    # ---------------- Product Operations ----------------

    def save_product(self, product: CatalogProduct) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO products (
                    product_id, shopify_product_id, title, handle, vendor,
                    product_type, supplier_type, supplier_product_id,
                    target_store_id, data_json, is_published, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.product_id,
                    product.shopify_product_id,
                    product.title,
                    product.handle,
                    product.vendor,
                    product.product_type,
                    product.supplier_type.value,
                    product.supplier_product_id,
                    product.target_store_id,
                    product.model_dump_json(),
                    1 if product.is_published else 0,
                    product.created_at,
                ),
            )
            for v in product.variants:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO variants (
                        variant_id, product_id, sku, title, cost_price,
                        retail_price, supplier_variant_id, supplier_sku, data_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        v.variant_id,
                        product.product_id,
                        v.sku,
                        v.title,
                        v.cost_price,
                        v.retail_price,
                        v.supplier_variant_id,
                        v.supplier_sku,
                        v.model_dump_json(),
                    ),
                )

    def get_product(self, product_id: str) -> Optional[CatalogProduct]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT data_json FROM products WHERE product_id = ?", (product_id,)).fetchone()
            if row:
                return CatalogProduct.model_validate_json(row["data_json"])
        return None

    def get_variant_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT v.*, p.supplier_type, p.supplier_product_id
                FROM variants v
                JOIN products p ON v.product_id = p.product_id
                WHERE v.sku = ?
                """,
                (sku,),
            ).fetchone()
            if row:
                return dict(row)
        return None

    def list_products(self, limit: int = 100, store_id: Optional[str] = None) -> List[CatalogProduct]:
        with self._get_conn() as conn:
            if store_id:
                rows = conn.execute(
                    "SELECT data_json FROM products WHERE target_store_id = ? ORDER BY created_at DESC LIMIT ?",
                    (store_id, limit),
                ).fetchall()
            else:
                rows = conn.execute("SELECT data_json FROM products ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [CatalogProduct.model_validate_json(r["data_json"]) for r in rows]

    # ---------------- Order Operations ----------------

    def save_order(self, order: CustomerOrder) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO orders (
                    order_id, store_id, shopify_order_id, shopify_order_number, customer_email,
                    customer_name, total_revenue, total_cost, net_profit, status,
                    data_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.order_id,
                    order.store_id,
                    order.shopify_order_id,
                    order.shopify_order_number,
                    order.customer_email,
                    order.customer_name,
                    order.total_revenue,
                    order.total_cost,
                    order.net_profit,
                    order.status.value,
                    order.model_dump_json(),
                    order.created_at,
                ),
            )

    def get_order(self, order_id: str) -> Optional[CustomerOrder]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT data_json FROM orders WHERE order_id = ? OR shopify_order_id = ?", (order_id, order_id)).fetchone()
            if row:
                return CustomerOrder.model_validate_json(row["data_json"])
        return None

    def list_orders(self, limit: int = 100, store_id: Optional[str] = None) -> List[CustomerOrder]:
        with self._get_conn() as conn:
            if store_id:
                rows = conn.execute("SELECT data_json FROM orders WHERE store_id = ? ORDER BY created_at DESC LIMIT ?", (store_id, limit)).fetchall()
            else:
                rows = conn.execute("SELECT data_json FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [CustomerOrder.model_validate_json(r["data_json"]) for r in rows]

    # ---------------- Fulfillment Operations ----------------

    def save_fulfillment(self, record: FulfillmentRecord) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO fulfillments (
                    fulfillment_id, order_id, shopify_order_id, supplier_type,
                    supplier_order_id, status, carrier, tracking_number,
                    tracking_url, supplier_cost, shipping_cost, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.fulfillment_id,
                    record.order_id,
                    record.shopify_order_id,
                    record.supplier_type.value,
                    record.supplier_order_id,
                    record.status.value,
                    record.carrier,
                    record.tracking_number,
                    record.tracking_url,
                    record.supplier_cost,
                    record.shipping_cost,
                    record.created_at,
                    record.updated_at,
                ),
            )

    def list_active_fulfillments(self) -> List[FulfillmentRecord]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM fulfillments
                WHERE status IN ('pending', 'dispatched', 'in_production')
                """
            ).fetchall()
            res = []
            for r in rows:
                res.append(
                    FulfillmentRecord(
                        fulfillment_id=r["fulfillment_id"],
                        order_id=r["order_id"],
                        shopify_order_id=r["shopify_order_id"],
                        supplier_type=SupplierType(r["supplier_type"]),
                        supplier_order_id=r["supplier_order_id"],
                        status=FulfillmentStatus(r["status"]),
                        carrier=r["carrier"],
                        tracking_number=r["tracking_number"],
                        tracking_url=r["tracking_url"],
                        supplier_cost=r["supplier_cost"],
                        shipping_cost=r["shipping_cost"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                )
            return res

    # ---------------- Growth: SEO & Marketing Assets ----------------

    def save_seo_article(self, article: SEOArticle) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO seo_articles (
                    article_id, store_id, product_id, title, slug,
                    target_keywords, meta_description, body_html, json_ld_schema,
                    published_url, is_published, data_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.article_id,
                    article.store_id,
                    article.product_id,
                    article.title,
                    article.slug,
                    ", ".join(article.target_keywords),
                    article.meta_description,
                    article.body_html,
                    article.json_ld_schema,
                    article.published_url,
                    1 if article.is_published else 0,
                    article.model_dump_json(),
                    article.created_at,
                ),
            )

    def list_seo_articles(self, limit: int = 50) -> List[SEOArticle]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT data_json FROM seo_articles ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [SEOArticle.model_validate_json(r["data_json"]) for r in rows]

    def save_creative_pack(self, pack: CreativePack) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO creative_packs (
                    pack_id, product_id, product_title, data_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pack.pack_id,
                    pack.product_id,
                    pack.product_title,
                    pack.model_dump_json(),
                    pack.created_at,
                ),
            )

    def list_creative_packs(self, limit: int = 50) -> List[CreativePack]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT data_json FROM creative_packs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [CreativePack.model_validate_json(r["data_json"]) for r in rows]

    def save_influencer_campaign(self, campaign: InfluencerOutreach) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO influencer_campaigns (
                    campaign_id, niche, influencer_tier, data_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    campaign.campaign_id,
                    campaign.niche,
                    campaign.influencer_tier,
                    campaign.model_dump_json(),
                    campaign.created_at,
                ),
            )

    def list_influencer_campaigns(self, limit: int = 50) -> List[InfluencerOutreach]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT data_json FROM influencer_campaigns ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [InfluencerOutreach.model_validate_json(r["data_json"]) for r in rows]

    # ---------------- Metrics & Analytics ----------------

    def get_financial_summary(self, store_id: Optional[str] = None) -> Dict[str, Any]:
        with self._get_conn() as conn:
            where_clause = " WHERE store_id = ?" if store_id else ""
            params = (store_id,) if store_id else ()

            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) as total_orders,
                    COALESCE(SUM(total_revenue), 0) as gross_revenue,
                    COALESCE(SUM(total_cost), 0) as total_cogs,
                    COALESCE(SUM(net_profit), 0) as net_profit
                FROM orders{where_clause}
                """,
                params,
            ).fetchone()

            p_count = conn.execute(
                f"SELECT COUNT(*) as count FROM products{' WHERE target_store_id = ?' if store_id else ''}",
                params,
            ).fetchone()["count"]

            f_active = conn.execute(
                "SELECT COUNT(*) as count FROM fulfillments WHERE status IN ('pending', 'dispatched', 'in_production')"
            ).fetchone()["count"]

            s_count = conn.execute("SELECT COUNT(*) as count FROM stores WHERE is_active = 1").fetchone()["count"]
            articles_count = conn.execute("SELECT COUNT(*) as count FROM seo_articles").fetchone()["count"]
            creatives_count = conn.execute("SELECT COUNT(*) as count FROM creative_packs").fetchone()["count"]

            gross = row["gross_revenue"]
            profit = row["net_profit"]
            margin_pct = (profit / gross * 100.0) if gross > 0 else 0.0

            return {
                "total_orders": row["total_orders"],
                "gross_revenue": round(gross, 2),
                "total_cogs": round(row["total_cogs"], 2),
                "net_profit": round(profit, 2),
                "profit_margin_pct": round(margin_pct, 1),
                "total_products": p_count,
                "active_fulfillments": f_active,
                "active_stores": max(s_count, 1),
                "seo_articles_published": articles_count,
                "creative_packs_generated": creatives_count,
            }


db = NexusDatabase()
