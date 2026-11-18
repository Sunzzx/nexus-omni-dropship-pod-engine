"""
FastAPI Server & Webhook Listener for Nexus Dropship & POD Engine.
Handles incoming Shopify order webhooks, serves the operational dashboard, and exposes management APIs.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import uuid
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from nexus_engine.config import config
from nexus_engine.core.database import db
from nexus_engine.core.fulfillment_tracker import fulfillment_tracker
from nexus_engine.core.niche_scout import niche_scout
from nexus_engine.core.order_router import order_router
from nexus_engine.clients.shopify import ShopifyClient

logger = logging.getLogger("nexus.server")

app = FastAPI(
    title="Nexus Omni-Dropship & POD Engine",
    description="Autonomous Enterprise Dropshipping & Print-On-Demand Fulfillment System",
    version="1.0.0",
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


# ---------------- API Management Endpoints ----------------

@app.get("/api/metrics")
async def get_metrics():
    return db.get_financial_summary()


@app.get("/api/products")
async def get_products():
    return [p.model_dump() for p in db.list_products(limit=50)]


@app.get("/api/orders")
async def get_orders():
    return [o.model_dump() for o in db.list_orders(limit=50)]


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
    orders = db.list_orders(limit=10)
    products = db.list_products(limit=10)

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nexus Omni-Dropship & POD Operations Hub</title>
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
            brand: {{ 900: '#06090e', 850: '#0b1017', 800: '#121924', border: '#1c2636', accent: '#00f2fe', green: '#00e676', amber: '#ffab00', rose: '#ff1744' }}
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
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-accent to-brand-green flex items-center justify-center font-bold text-black font-mono text-lg shadow-lg">
          ⚡
        </div>
        <div>
          <span class="font-extrabold text-white text-base font-mono tracking-tight">NEXUS OMNI-DROPSHIP & POD</span>
          <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-green/10 border border-brand-green/30 text-brand-green ml-2">100% AUTONOMOUS</span>
        </div>
      </div>
      <div class="flex items-center space-x-3 text-xs font-mono">
        <button onclick="triggerSimulateOrder()" class="px-3 py-1.5 rounded-lg bg-brand-accent text-black font-bold hover:opacity-90 transition shadow">
          + Simulate Order
        </button>
        <button onclick="triggerSync()" class="px-3 py-1.5 rounded-lg bg-brand-800 border border-brand-border text-slate-200 hover:text-white transition">
          🔄 Sync Fulfillments
        </button>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">
    <!-- METRIC CARDS -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 shadow-sm">
        <span class="text-xs font-mono text-slate-400 uppercase tracking-wider">Gross Revenue</span>
        <div class="text-2xl font-mono font-extrabold text-white mt-1">${metrics['gross_revenue']:.2f}</div>
        <span class="text-[11px] font-mono text-brand-green mt-1 inline-block">From {metrics['total_orders']} orders</span>
      </div>
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 shadow-sm">
        <span class="text-xs font-mono text-slate-400 uppercase tracking-wider">Net Profit</span>
        <div class="text-2xl font-mono font-extrabold text-brand-green mt-1">${metrics['net_profit']:.2f}</div>
        <span class="text-[11px] font-mono text-slate-400 mt-1 inline-block">{metrics['profit_margin_pct']}% margin</span>
      </div>
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 shadow-sm">
        <span class="text-xs font-mono text-slate-400 uppercase tracking-wider">Catalog Products</span>
        <div class="text-2xl font-mono font-extrabold text-brand-accent mt-1">{metrics['total_products']}</div>
        <span class="text-[11px] font-mono text-slate-400 mt-1 inline-block">CJ Dropship + Printify POD</span>
      </div>
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 shadow-sm">
        <span class="text-xs font-mono text-slate-400 uppercase tracking-wider">Active Fulfillments</span>
        <div class="text-2xl font-mono font-extrabold text-brand-amber mt-1">{metrics['active_fulfillments']}</div>
        <span class="text-[11px] font-mono text-slate-400 mt-1 inline-block">In-flight at supplier hubs</span>
      </div>
    </div>

    <!-- QUICK ACTIONS BANNER -->
    <div class="bg-gradient-to-r from-brand-850 via-brand-800 to-brand-850 border border-brand-border rounded-2xl p-6 flex flex-col md:flex-row items-center justify-between gap-4">
      <div>
        <h3 class="text-base font-bold text-white font-mono">Autonomous Production Engine Active</h3>
        <p class="text-xs text-slate-400 font-mono mt-0.5">Webhook listening on <code>/webhooks/shopify/orders-paid</code>. Multi-supplier order routing & tracking active.</p>
      </div>
      <div class="flex items-center space-x-3 text-xs font-mono">
        <button onclick="triggerSeedCatalog()" class="px-4 py-2 rounded-xl bg-brand-800 border border-brand-border text-slate-200 hover:text-white transition">
          Seed Curated Catalog
        </button>
        <button onclick="triggerPublishAll()" class="px-4 py-2 rounded-xl bg-brand-green text-black font-bold hover:opacity-90 transition">
          Publish All to Shopify
        </button>
      </div>
    </div>

    <!-- TABLES: ORDERS & PRODUCTS -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
                <td class="py-2.5 text-slate-300 truncate max-w-[120px]">{o.customer_name}</td>
                <td class="py-2.5 text-white">${o.total_revenue:.2f}</td>
                <td class="py-2.5 text-brand-green font-bold">+${o.net_profit:.2f}</td>
                <td class="py-2.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-brand-accent/10 text-brand-accent border border-brand-accent/30">{o.status.value.upper()}</span></td>
              </tr>
              ''' for o in orders]) if orders else '<tr><td colspan="5" class="py-6 text-center text-slate-500">No customer orders recorded yet. Click "+ Simulate Order" to test.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>

      <!-- CATALOG PREVIEW -->
      <div class="bg-brand-850 border border-brand-border rounded-2xl p-5 space-y-4">
        <div class="flex justify-between items-center">
          <h3 class="text-sm font-bold font-mono text-white">Curated Product Catalog</h3>
          <span class="text-xs font-mono text-slate-500">{len(products)} products</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead class="border-b border-brand-border text-slate-400">
              <tr>
                <th class="pb-2">Product</th>
                <th class="pb-2">Supplier</th>
                <th class="pb-2">Cost / Retail</th>
                <th class="pb-2">Variants</th>
                <th class="pb-2">Shopify</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-brand-border/50">
              {"".join([f'''
              <tr class="hover:bg-brand-800/40 transition">
                <td class="py-2.5 font-bold text-white truncate max-w-[160px]">{p.title}</td>
                <td class="py-2.5"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-brand-800 border border-brand-border text-slate-300">{p.supplier_type.value}</span></td>
                <td class="py-2.5 text-slate-300">${p.variants[0].cost_price:.2f} / <b class="text-white">${p.variants[0].retail_price:.2f}</b></td>
                <td class="py-2.5 text-slate-400">{len(p.variants)}</td>
                <td class="py-2.5 font-mono text-[10px] text-brand-green">{'PUBLISHED' if p.is_published else 'LOCAL'}</td>
              </tr>
              ''' for p in products]) if products else '<tr><td colspan="5" class="py-6 text-center text-slate-500">Catalog is empty. Click "Seed Curated Catalog" above.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </main>

  <footer class="border-t border-brand-border bg-brand-850/40 py-6 text-center text-xs font-mono text-slate-500">
    Nexus Omni-Dropship & POD Engine • Built autonomously by <a href="https://sunzzx.github.io/ayush-kandwal-portfolio/" class="text-slate-400 hover:text-white">Ayush Kandwal (@Sunzzx)</a>
  </footer>

  <script>
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

    async function triggerSeedCatalog() {{
      const res = await fetch('/api/catalog/seed', {{ method: 'POST' }});
      const data = await res.json();
      alert('✓ Catalog seeded with ' + data.seeded_products + ' curated winning products');
      window.location.reload();
    }}

    async function triggerPublishAll() {{
      const res = await fetch('/api/catalog/publish-all', {{ method: 'POST' }});
      const data = await res.json();
      alert('✓ Published ' + data.published_count + ' products to Shopify');
      window.location.reload();
    }}
  </script>
</body>
</html>"""
    return html
