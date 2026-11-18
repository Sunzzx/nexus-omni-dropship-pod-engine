# 🚀 Launch Kit: Nexus Omni-Dropship & POD Engine

Ready-to-post promotional and technical launch copy across developer and indie hacker channels.

---

## 1. Show HN (Hacker News)

**Title:** Show HN: Nexus – Autonomous Multi-Supplier Dropship & POD Engine for Shopify

**Link / GitHub:** https://github.com/Sunzzx/nexus-omni-dropship-pod-engine

**Body:**
> Hey HN,
>
> When running a hybrid dropshipping and print-on-demand store, handling orders with mixed items (e.g. an imported gadget from CJ Dropshipping alongside custom DTG apparel from Printify) is notoriously painful. Most merchants either pay $50–$150/month for brittle Shopify apps or manually copy-paste customer shipping details and tracking numbers back and forth.
>
> I built **Nexus**: a 100% autonomous, zero-cost e-commerce orchestration engine.
>
> What it does:
> - Intercepts Shopify `orders/paid` webhooks with HMAC validation.
> - Automatically decomposes mixed line items based on SKU rules and routes orders to CJ Dropshipping and Printify Open APIs concurrently.
> - Runs a tracking synchronization daemon that polls suppliers for USPS / CJ Packet tracking codes and closes the fulfillment loop in Shopify.
> - Built-in Niche Scout with strict unit economic margin modeling (220%+ markup floor).
> - Includes a zero-config simulation mode so you can test entire multi-supplier routing and webhook flows without live API credentials.
>
> Code is fully open source (MIT): https://github.com/Sunzzx/nexus-omni-dropship-pod-engine
>
> Would love your feedback on the architecture!

---

## 2. Reddit (r/SideProject, r/dropship, r/indiehackers)

**Title:** I built an open-source engine that automates Shopify order routing between CJ Dropshipping and Print-on-Demand (POD)

**Body:**
> If you sell both physical products (CJ Dropshipping) and custom apparel/prints (Printify/Printful) on Shopify, you know the headache of order splitting.
>
> I created **Nexus Omni-Dropship & POD Engine** to automate the entire pipeline:
>
> 1. **Zero-Touch Routing:** When an order hits Shopify, Nexus inspects the cart, splits CJ items from POD items, and places wholesale orders with both suppliers in real time.
> 2. **Automated Tracking Sync:** Polls supplier logistics APIs and automatically pushes tracking numbers back to Shopify to trigger customer dispatch emails.
> 3. **Profit & Margin Guard:** Enforces strict markup and min profit dollars so you never lose money on freight.
> 4. **Modern Local Dashboard:** Real-time web UI showing gross revenue, COGS, net margin %, and active fulfillment states.
>
> Check it out on GitHub: https://github.com/Sunzzx/nexus-omni-dropship-pod-engine
