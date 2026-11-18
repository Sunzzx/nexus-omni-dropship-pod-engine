# ⚡ Nexus Omni-Dropship & Print-on-Demand (POD) Autonomous Engine

[![Architecture: Zero-Touch Multi-Supplier](https://img.shields.io/badge/Architecture-Zero--Touch%20Multi--Supplier-00f2fe?style=for-the-badge)](README.md)
[![Shopify: Admin API v2024-10](https://img.shields.io/badge/Shopify-Admin%20API%20v2024--10-96bf48?style=for-the-badge&logo=shopify)](https://shopify.dev)
[![Fulfillment: CJ Dropship + Printify](https://img.shields.io/badge/Fulfillment-CJ%20Dropship%20%2B%20Printify-ff6d00?style=for-the-badge)](https://cjdropshipping.com)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-00e676?style=for-the-badge)](README.md)

**Nexus Omni-Dropship & POD Engine** is a high-throughput, autonomous e-commerce orchestration pipeline that bridges **Shopify stores**, **CJ Dropshipping**, and **Print-on-Demand providers (Printify & Printful)** into a unified, zero-touch fulfillment engine.

---

## 🎯 What It Solves

Traditional dropshipping and print-on-demand businesses suffer from:
1. **Manual Order Splitting**: Orders containing both physical imported goods (CJ Dropshipping) and custom apparel (Printify/Printful) require tedious manual copying and pasting of addresses.
2. **Delayed Tracking Updates**: Tracking numbers must be copied manually from supplier portals into Shopify, leading to customer anxiety and chargeback risks.
3. **Margin Leakage**: Blind product selection without strict COGS, freight estimation, and target markup rules.
4. **Fragile Webhooks**: Unverified webhooks or missed order events causing dropped deliveries.

**Nexus eliminates manual intervention completely.** It intercepts orders via verified Shopify webhooks, classifies line items by supplier SKU rules, dispatches wholesale fulfillment API calls to CJ Dropshipping and Printify simultaneously, polls for carrier tracking numbers, and pushes fulfillments directly back to Shopify with customer notification emails.

---

## 🏗️ Architectural Topology

```mermaid
flowchart TD
    subgraph Storefront
        Customer["Customer Order (Shopify Checkout)"]
    end

    subgraph "Nexus Omni Engine (Port 8090)"
        Webhook["Shopify Webhook Listener (/webhooks/shopify/orders-paid)"]
        Router["Multi-Supplier Order Router (order_router.py)"]
        DB[("Nexus SQLite WAL Ledger (nexus_ledger.db)")]
        Tracker["Automated Tracking Sync Daemon (fulfillment_tracker.py)"]
        Dashboard["Operations Command Center (dashboard.html)"]
    end

    subgraph "Global Fulfillment Networks"
        CJ["CJ Dropshipping Open API (Tech / EDC / Gadgets)"]
        Printify["Printify REST API (Heavyweight Streetwear / Canvas)"]
        Printful["Printful v2 API (Direct-to-Garment / Hats)"]
    end

    Customer -->|orders/paid| Webhook
    Webhook --> Router
    Router -->|Split & Save| DB
    Router -->|POST shopping/order/createOrder| CJ
    Router -->|POST shops/orders.json| Printify
    Router -->|POST orders| Printful

    Tracker -->|Poll Tracking Checkpoints| CJ
    Tracker -->|Poll Tracking Checkpoints| Printify
    Tracker -->|POST orders/{id}/fulfillments.json| Customer
    Dashboard <--> DB
```

---

## 🚀 Key Capabilities

- **Intelligent Multi-Supplier Order Routing**: Automatically decomposes mixed shopping carts (e.g., 1 Boxy Heavyweight Tee from Printify + 1 Ambient Wireless Charger from CJ Dropshipping) and dispatches independent wholesale fulfillments in parallel.
- **Continuous Tracking Synchronization**: Background polling loop queries CJ Dropshipping and Printify APIs for newly assigned tracking codes (USPS, CJ Packet, DHL, FedEx) and syncs them back to Shopify.
- **Niche & Margin Scout**: Built-in algorithmic product ideation with automated COGS calculations, freight modeling, and targeted profit margin filters (default: 220% markup / 57%+ net margin).
- **Graceful Sandbox Simulation Mode**: Runs fully offline in simulation mode out-of-the-box. Developers can test order splitting, webhook handling, and fulfillment tracking without risking production capital or needing live store credentials upfront.
- **Live Operations Dashboard**: High-aesthetic dark-mode command center running on `http://localhost:8090` displaying gross revenue, COGS, net profit, catalog variants, and live order status.

---

## 📦 CLI Reference (`nexus-ecom`)

Nexus provides a unified CLI available anywhere in your terminal:

```bash
# View financial performance, active fulfillments & store configuration
nexus-ecom status

# Scout trending winning niches and seed curated catalog
nexus-ecom seed

# Publish unlisted catalog products to Shopify Admin API
nexus-ecom publish

# Simulate realistic customer order and test multi-supplier routing
nexus-ecom simulate

# Poll suppliers and push tracking numbers to Shopify orders
nexus-ecom sync

# Launch the webhook listener and real-time operations dashboard
nexus-ecom serve
```

---

## ⚙️ Configuration (`nexus_config.json` or `.env`)

```json
{
  "shopify_shop_url": "https://your-store.myshopify.com",
  "shopify_access_token": "shpat_xxxxxxxxxxxxxxxxxxxx",
  "shopify_webhook_secret": "whsec_xxxxxxxxxxxxxxxxxxxx",
  "cj_email": "operator@domain.com",
  "cj_api_key": "cjak_xxxxxxxxxxxxxxxxxxxx",
  "printify_api_token": "prt_xxxxxxxxxxxxxxxxxxxx",
  "printify_shop_id": "10849201",
  "default_markup_percent": 220.0,
  "min_profit_dollars": 12.0,
  "simulation_mode": false,
  "auto_fulfill_orders": true
}
```

---

## 👤 Author
**Ayush Kandwal (@Sunzzx)**  
AI & Quant Researcher (Dual IIT Scholar)  
- Portfolio: [https://sunzzx.github.io/ayush-kandwal-portfolio/](https://sunzzx.github.io/ayush-kandwal-portfolio/)
- GitHub: [https://github.com/Sunzzx](https://github.com/Sunzzx)
