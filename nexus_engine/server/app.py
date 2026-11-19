"""
FastAPI Server & Webhook Listener for Nexus Dropship & POD Engine.
Handles incoming Shopify order webhooks, serves the operational multi-store dashboard,
and exposes autonomous growth, SEO, and viral marketing APIs.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from nexus_engine.config import config
from nexus_engine.core.database import db
from nexus_engine.core.fulfillment_tracker import fulfillment_tracker
from nexus_engine.core.growth_daemon import growth_daemon
from nexus_engine.core.growth_engine import growth_engine
from nexus_engine.core.multi_store_manager import multi_store_manager
from nexus_engine.core.niche_scout import niche_scout
from nexus_engine.core.order_router import order_router
from nexus_engine.models import PlatformType, StoreConfig
from nexus_engine.clients.shopify import ShopifyClient

logger = logging.getLogger("nexus.server")

app = FastAPI(
    title="Nexus Omni-Dropship & POD Growth Engine",
    description="Autonomous Multi-Store Dropshipping & Print-On-Demand Fulfillment System",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_shopify_webhook(raw_body: bytes, hmac_header: str) -> bool:
    """Verifies HMAC-SHA256 signature from Shopify."""
    if not config.shopify_webhook_secret or config.simulation_mode:
        return True
    digest = hmac.new(config.shopify_webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    computed_hmac = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed_hmac, hmac_header)


# ---------------- Webhook Endpoints ----------------

@app.post("/webhooks/shopify/orders-create")
@app.post("/webhooks/shopify/orders-paid")
async def handle_shopify_order_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
):
    raw_body = await request.body()
    if not verify_shopify_webhook(raw_body, x_shopify_hmac_sha256 or ""):
        raise HTTPException(status_code=401, detail="Invalid Shopify HMAC Signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
        order = order_router.process_incoming_shopify_order(payload)
        return {
            "status": "success",
            "message": "Order processed and routed to suppliers",
            "order_id": order.order_id,
            "net_profit": order.net_profit,
        }
    except Exception as e:
        logger.error("Failed processing webhook: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------- Multi-Store Endpoints ----------------

class AddStoreRequest(BaseModel):
    name: str
    shop_url: str
    target_niche: str
    platform: str = "shopify"
    access_token: str = ""
    currency: str = "USD"


@app.get("/api/stores")
async def list_stores():
    return [s.model_dump() for s in multi_store_manager.list_stores()]


@app.post("/api/stores")
async def add_store(req: AddStoreRequest):
    platform_enum = PlatformType(req.platform.lower()) if req.platform.lower() in [p.value for p in PlatformType] else PlatformType.SHOPIFY
    store = multi_store_manager.register_store(
        name=req.name,
        shop_url=req.shop_url,
        target_niche=req.target_niche,
        platform=platform_enum,
        access_token=req.access_token,
        currency=req.currency,
    )
    return {"status": "success", "store": store.model_dump()}


# ---------------- Growth & Marketing Endpoints ----------------

@app.post("/api/growth/execute")
async def trigger_growth_cycle():
    """Triggers the full multi-store expansion, product publishing, SEO, and ad generation cycle."""
    summary = growth_daemon.execute_growth_cycle()
    return {"status": "success", "summary": summary}


@app.get("/api/seo-articles")
async def get_seo_articles():
    return [a.model_dump() for a in db.list_seo_articles(limit=25)]


@app.get("/api/creative-packs")
async def get_creative_packs():
    return [c.model_dump() for c in db.list_creative_packs(limit=25)]


@app.get("/api/influencers")
async def get_influencers():
    return [i.model_dump() for i in db.list_influencer_campaigns(limit=25)]


# ---------------- Catalog & Order APIs ----------------

@app.get("/api/metrics")
async def get_metrics(store_id: Optional[str] = None):
    return db.get_financial_summary(store_id=store_id)


@app.get("/api/products")
async def get_products(store_id: Optional[str] = None):
    return [p.model_dump() for p in db.list_products(limit=50, store_id=store_id)]


@app.get("/api/orders")
async def get_orders(store_id: Optional[str] = None):
    return [o.model_dump() for o in db.list_orders(limit=50, store_id=store_id)]


@app.post("/api/catalog/seed")
async def seed_catalog():
    catalog = niche_scout.generate_curated_catalog()
    for prod in catalog:
        db.save_product(prod)
    return {"status": "success", "seeded_products": len(catalog)}


@app.post("/api/catalog/publish-all")
async def publish_all_to_shopify():
    client = ShopifyClient()
    products = db.list_products()
    published = 0
    for prod in products:
        if not prod.is_published:
            res = client.create_product(prod)
            prod.shopify_product_id = str(res.get("id"))
            prod.is_published = True
            db.save_product(prod)
            published += 1
    return {"status": "success", "published_count": published}


@app.post("/api/fulfillments/sync")
async def trigger_fulfillment_sync():
    res = fulfillment_tracker.sync_all_active_fulfillments()
    return {"status": "success", "results": res}


@app.post("/api/orders/simulate")
async def simulate_order():
    """Generates a realistic test order containing both a CJ item and a POD item."""
    mock_order = {
        "id": int(uuid.uuid4().int % 100000000),
        "order_number": f"10{uuid.uuid4().int % 900 + 100}",
        "email": "sarah.connor@cyberdyne.io",
        "total_price": "89.98",
        "currency": "USD",
        "shipping_address": {
            "first_name": "Sarah",
            "last_name": "Connor",
            "address1": "8404 Tech Ridge Blvd",
            "city": "Austin",
            "province": "TX",
            "zip": "78753",
            "country_code": "US",
            "country": "United States",
            "phone": "+1-512-555-0144"
        },
        "line_items": [
            {
                "id": 89012,
                "variant_id": 9901,
                "sku": "PRT-STOCHAST-SM-WAS",
                "title": "Stochastic Gradient Descent Heavyweight Boxy Tee - S / Washed Charcoal",
                "price": "34.00",
                "quantity": 1
            },
            {
                "id": 89013,
                "variant_id": 9902,
                "sku": "CJ-CHG-BLK",
                "title": "MagSafe Ambient Halo 3-in-1 Fast Wireless Charging Station - Midnight Black",
                "price": "44.99",
                "quantity": 1
            }
        ]
    }
    order = order_router.process_incoming_shopify_order(mock_order)
    return {
        "status": "success",
        "order_number": order.shopify_order_number,
        "revenue": order.total_revenue,
        "net_profit": order.net_profit,
        "items": len(order.items),
    }


# ---------------- Live Operations Dashboard ----------------

@app.get("/", response_class=HTMLResponse)
async def dashboard_view():
    metrics = db.get_financial_summary()
    stores = multi_store_manager.list_stores()
    orders = db.list_orders(limit=8)
    products = db.list_products(limit=8)
    seo_articles = db.list_seo_articles(limit=5)
    creatives = db.list_creative_packs(limit=4)

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nexus Omni-Dropship & Multi-Store Growth Hub</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          fontFamily: {{
            mono: ['JetBrains Mono', 'monospace'],
            sans: ['Plus Jakarta Sans', 'sans-serif'],
          }},
          colors: {{
            brand: {{ 900: '#06090e', 850: '#0b1017', 800: '#121924', border: '#1c2636', accent: '#00f2fe', green: '#00e676', amber: '#ffab00', rose: '#ff1744', purple: '#b388ff' }}
          }}
        }}
      }}
    }}
  </script>
</head>
<body class="bg-brand-900 text-slate-100 font-sans min-h-screen selection:bg-brand-accent selection:text-black">
  <!-- HEADER -->
  <header class="border-b border-brand-border bg-brand-850/90 backdrop-blur-md sticky top-0 z-30">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-accent via-brand-purple to-brand-green flex items-center justify-center font-bold text-black font-mono text-lg shadow-lg">
          ⚡
        </div>
        <div>
          <span class="font-extrabold text-white text-base font-mono tracking-tight">NEXUS OMNI-GROWTH ENGINE</span>
          <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-green/10 border border-brand-green/30 text-brand-green ml-2">MULTI-STORE & VIRAL GROWTH</span>
        </div>
      </div>
      <div class="flex items-center space-x-3 text-xs font-mono">
        <button onclick="triggerGrowthCycle()" class="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-brand-accent to-brand-green text-black font-extrabold hover:opacity-90 transition shadow-lg">
          🚀 Run Autonomous Growth
        </button>
        <button onclick="triggerSimulateOrder()" class="px-3 py-1.5 rounded-lg bg-brand-800 border border-brand-border text-slate-200 hover:text-white transition">
          + Order
        </button>
        <button onclick="triggerSync()" class="px-3 py-1.5 rounded-lg bg-brand-800 border border-brand-border text-slate-200 hover:text-white transition">
          🔄 Sync
        </button>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">
    <!-- METRIC CARDS -->
    <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-4 shadow-sm">
        <span class="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Gross Revenue</span>
        <div class="text-xl font-mono font-extrabold text-white mt-1">${metrics['gross_revenue']:.2f}</div>
        <span class="text-[10px] font-mono text-brand-green mt-1 inline-block">{metrics['total_orders']} orders</span>
      </div>
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-4 shadow-sm">
        <span class="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Net Profit</span>
        <div class="text-xl font-mono font-extrabold text-brand-green mt-1">${metrics['net_profit']:.2f}</div>
        <span class="text-[10px] font-mono text-slate-400 mt-1 inline-block">{metrics['profit_margin_pct']}% margin</span>
      </div>
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-4 shadow-sm">
        <span class="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Active Stores</span>
        <div class="text-xl font-mono font-extrabold text-brand-accent mt-1">{len(stores)}</div>
        <span class="text-[10px] font-mono text-slate-400 mt-1 inline-block">Multi-Niche Fleet</span>
      </div>
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-4 shadow-sm">
        <span class="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Catalog Products</span>
        <div class="text-xl font-mono font-extrabold text-white mt-1">{metrics['total_products']}</div>
        <span class="text-[10px] font-mono text-slate-400 mt-1 inline-block">CJ + Printify POD</span>
      </div>
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-4 shadow-sm">
        <span class="text-[10px] font-mono text-slate-400 uppercase tracking-wider">SEO Articles</span>
        <div class="text-xl font-mono font-extrabold text-brand-purple mt-1">{metrics['seo_articles_published']}</div>
        <span class="text-[10px] font-mono text-slate-400 mt-1 inline-block">JSON-LD Indexed</span>
      </div>
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-4 shadow-sm">
        <span class="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Creative Packs</span>
        <div class="text-xl font-mono font-extrabold text-brand-amber mt-1">{metrics['creative_packs_generated']}</div>
        <span class="text-[10px] font-mono text-slate-400 mt-1 inline-block">TikTok/Meta/Pin</span>
      </div>
    </div>

    <!-- STORE NETWORK STATUS -->
    <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 space-y-4">
      <div class="flex justify-between items-center">
        <div>
          <h3 class="text-sm font-bold font-mono text-white">Active Multi-Storefront Network</h3>
          <p class="text-xs text-slate-400 font-mono">Cross-platform storefronts managed autonomously by Nexus.</p>
        </div>
        <button onclick="promptAddStore()" class="text-xs font-mono px-3 py-1.5 rounded-lg bg-brand-800 border border-brand-border text-brand-accent hover:text-white transition">
          + Add Store
        </button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        {"".join([f'''
        <div class="bg-brand-900 border border-brand-border/70 rounded-xl p-4 space-y-2">
          <div class="flex justify-between items-start">
            <span class="text-xs font-bold text-white font-mono">{s.name}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-brand-green/10 text-brand-green border border-brand-green/30">ONLINE</span>
          </div>
          <div class="text-[11px] font-mono text-slate-400 truncate">{s.shop_url}</div>
          <div class="text-[11px] font-mono text-brand-accent">🎯 {s.target_niche}</div>
          <div class="text-[10px] font-mono text-slate-500 pt-1 border-t border-brand-border/40 flex justify-between">
            <span>Platform: {s.platform.value.upper()}</span>
            <span>Currency: {s.currency}</span>
          </div>
        </div>
        ''' for s in stores])}
      </div>
    </div>

    <!-- VIRAL CREATIVES & PROGRAMMATIC SEO SECTION -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- VIRAL CREATIVE PACKS -->
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 space-y-4">
        <div class="flex justify-between items-center">
          <h3 class="text-sm font-bold font-mono text-white">Viral Social Media Ad Packs (TikTok / Meta / Pinterest)</h3>
          <span class="text-xs font-mono text-brand-accent">{len(creatives)} packs ready</span>
        </div>
        <div class="space-y-3">
          {"".join([f'''
          <div class="bg-brand-900 border border-brand-border/60 rounded-xl p-3.5 space-y-2 text-xs font-mono">
            <div class="flex justify-between items-center">
              <b class="text-white truncate">{c.product_title}</b>
              <span class="text-[10px] text-brand-amber font-bold">3-ACT SCRIPT READY</span>
            </div>
            <div class="text-[11px] text-slate-300 bg-brand-850 p-2.5 rounded border border-brand-border/40">
              <span class="text-brand-accent font-bold">🎬 0-3s Hook:</span> "{c.tiktok_storyboard.get('hook_0_3s', {{}}).get('voiceover', '')}"<br>
              <span class="text-brand-green font-bold">📢 Headline:</span> {c.meta_ad_copy.get('headline', '')}
            </div>
            <div class="text-[10px] text-slate-400 truncate">
              Tags: {" ".join(c.tiktok_storyboard.get('hashtags', [])[:5])}
            </div>
          </div>
          ''' for c in creatives]) if creatives else '<div class="py-6 text-center text-slate-500 text-xs font-mono">No ad packs generated yet. Click "Run Autonomous Growth" above.</div>'}
        </div>
      </div>

      <!-- PROGRAMMATIC SEO ARTICLES -->
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 space-y-4">
        <div class="flex justify-between items-center">
          <h3 class="text-sm font-bold font-mono text-white">Programmatic SEO Articles & Google Rich Snippets</h3>
          <span class="text-xs font-mono text-brand-purple">{len(seo_articles)} articles</span>
        </div>
        <div class="space-y-3">
          {"".join([f'''
          <div class="bg-brand-900 border border-brand-border/60 rounded-xl p-3.5 space-y-2 text-xs font-mono">
            <div class="flex justify-between items-center">
              <b class="text-white truncate max-w-[280px]">{a.title}</b>
              <span class="text-[10px] text-brand-green font-bold">{'INDEXED & LIVE' if a.is_published else 'DRAFT'}</span>
            </div>
            <div class="text-[11px] text-slate-400 truncate">{a.meta_description}</div>
            <div class="text-[10px] text-brand-accent flex justify-between items-center pt-1 border-t border-brand-border/40">
              <span>Keywords: {", ".join(a.target_keywords[:3])}</span>
              <span>Schema: JSON-LD (FAQ+Product)</span>
            </div>
          </div>
          ''' for a in seo_articles]) if seo_articles else '<div class="py-6 text-center text-slate-500 text-xs font-mono">No SEO articles published yet. Click "Run Autonomous Growth" above.</div>'}
        </div>
      </div>
    </div>

    <!-- RECENT ORDERS -->
    <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 space-y-4">
      <div class="flex justify-between items-center">
        <h3 class="text-sm font-bold font-mono text-white">Recent Customer Orders</h3>
        <span class="text-xs font-mono text-slate-500">{len(orders)} total</span>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-mono">
          <thead class="border-b border-brand-border text-slate-400">
            <tr>
              <th class="pb-2">Order #</th>
              <th class="pb-2">Customer</th>
              <th class="pb-2">Revenue</th>
              <th class="pb-2">Profit</th>
              <th class="pb-2">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-brand-border/50">
            {"".join([f'''
            <tr class="hover:bg-brand-800/40 transition">
              <td class="py-2.5 font-bold text-white">#{o.shopify_order_number}</td>
              <td class="py-2.5 text-slate-300 truncate max-w-[140px]">{o.customer_name}</td>
              <td class="py-2.5 text-white">${o.total_revenue:.2f}</td>
              <td class="py-2.5 text-brand-green font-bold">+${o.net_profit:.2f}</td>
              <td class="py-2.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-brand-accent/10 text-brand-accent border border-brand-accent/30">{o.status.value.upper()}</span></td>
            </tr>
            ''' for o in orders]) if orders else '<tr><td colspan="5" class="py-6 text-center text-slate-500">No customer orders recorded yet. Click "+ Order" to simulate.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  </main>

  <footer class="border-t border-brand-border bg-brand-850/40 py-6 text-center text-xs font-mono text-slate-500">
    Nexus Omni-Dropship & Multi-Store Growth Hub • Built autonomously by <a href="https://sunzzx.github.io/ayush-kandwal-portfolio/" class="text-slate-400 hover:text-white">Ayush Kandwal (@Sunzzx)</a>
  </footer>

  <script>
    async function triggerGrowthCycle() {{
      const btn = event.target;
      btn.textContent = "⏳ Running Growth Loop...";
      btn.disabled = true;
      try {{
        const res = await fetch('/api/growth/execute', {{ method: 'POST' }});
        const data = await res.json();
        alert('🎉 Growth Cycle Complete! Seeded: ' + data.summary.products_seeded + ', SEO Articles: ' + data.summary.seo_articles_published + ', Creatives: ' + data.summary.creative_packs_synthesized);
        window.location.reload();
      }} catch (e) {{
        alert('Growth cycle triggered.');
        window.location.reload();
      }}
    }}

    async function triggerSimulateOrder() {{
      const res = await fetch('/api/orders/simulate', {{ method: 'POST' }});
      const data = await res.json();
      alert('✓ Simulated order created: #' + data.order_number + ' (Profit: $' + data.net_profit + ')');
      window.location.reload();
    }}

    async function triggerSync() {{
      const res = await fetch('/api/fulfillments/sync', {{ method: 'POST' }});
      const data = await res.json();
      alert('✓ Fulfillment sync complete: ' + JSON.stringify(data.results));
      window.location.reload();
    }}

    async function promptAddStore() {{
      const name = prompt("Store Name (e.g. Apex Streetwear):");
      if (!name) return;
      const url = prompt("Shopify Store URL (e.g. https://apex-streetwear.myshopify.com):");
      if (!url) return;
      const niche = prompt("Target Niche (e.g. Urban Streetwear):", "Streetwear");
      const res = await fetch('/api/stores', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ name: name, shop_url: url, target_niche: niche }})
      }});
      alert("✓ Store registered successfully into Nexus!");
      window.location.reload();
    }}
  </script>
</body>
</html>"""
    return html
