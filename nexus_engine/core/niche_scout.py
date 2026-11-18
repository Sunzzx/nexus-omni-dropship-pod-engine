"""
Autonomous Niche & Winning Product Scout for Dropshipping + POD.
Analyzes trending e-commerce product categories, computes unit economics, and generates curated catalog listings.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List
from nexus_engine.config import config
from nexus_engine.models import CatalogProduct, ProductVariant, SupplierType

WINNING_NICHES = [
    {
        "niche": "Quant & Cyberpunk Developer Streetwear",
        "category": "POD Apparel",
        "supplier": SupplierType.PRINTIFY,
        "blueprint_id": "PRT-BLP-12",
        "products": [
            {
                "title": "Stochastic Gradient Descent Heavyweight Boxy Tee",
                "handle": "stochastic-gradient-descent-heavyweight-tee",
                "cogs": 11.50,
                "shipping": 4.50,
                "retail": 34.00,
                "tags": ["streetwear", "machine-learning", "boxy-tee", "dev-apparel"],
                "image": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=800",
                "description_points": [
                    "240 GSM 100% Combed Ring-Spun Heavy Cotton",
                    "Dropped shoulder boxy streetwear fit",
                    "High-definition direct-to-garment (DTG) print with archival inks",
                    "Pre-shrunk fabric to maintain tailored shape after repeated washing"
                ],
                "sizes": ["S", "M", "L", "XL", "2XL"],
                "colors": ["Washed Charcoal", "Vintage Black", "Eggshell"]
            },
            {
                "title": "Black-Scholes Heat Diffusion French Terry Hoodie",
                "handle": "black-scholes-heat-diffusion-french-terry-hoodie",
                "cogs": 21.00,
                "shipping": 6.50,
                "retail": 58.00,
                "tags": ["quant", "hoodie", "finance", "minimalism"],
                "image": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=800",
                "description_points": [
                    "420 GSM Ultra-Dense French Terry Knit",
                    "Double-layered structured hood with no drawstrings for clean aesthetic",
                    "Bar-tack reinforced kangaroo pocket",
                    "Embroidered stochastic PDE equation on chest with tonal typography"
                ],
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Obsidian", "Heather Slate"]
            }
        ]
    },
    {
        "niche": "Ergonomic Desk Tech & Ambient Workspace",
        "category": "CJ Dropshipping",
        "supplier": SupplierType.CJ_DROPSHIPPING,
        "blueprint_id": "CJ-WH-TECH",
        "products": [
            {
                "title": "MagSafe Ambient Halo 3-in-1 Fast Wireless Charging Station",
                "handle": "magsafe-ambient-halo-3in1-wireless-charger",
                "cogs": 14.20,
                "shipping": 4.80,
                "retail": 44.99,
                "tags": ["tech-accessories", "magsafe", "desk-setup", "wireless-charging"],
                "image": "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=800",
                "description_points": [
                    "15W Peak Fast Charging with Cryo-Boost Heat Dissipation Fan",
                    "Solid Aerospace-Grade Aluminum Alloy CNC Body",
                    "Simultaneous charging for Phone, Watch, and Wireless Earbuds",
                    "Touch-capacitive warm halo nightlight with 3 dimming steps"
                ],
                "sizes": ["Standard"],
                "colors": ["Space Grey", "Matte Silver"]
            },
            {
                "title": "Haptic Mechanical Clicker EDC Executive Titanium Pen",
                "handle": "haptic-mechanical-clicker-titanium-pen",
                "cogs": 8.50,
                "shipping": 3.80,
                "retail": 29.99,
                "tags": ["edc", "desk-gear", "executive", "fidget-tool"],
                "image": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=800",
                "description_points": [
                    "Grade 5 TC4 Precision-Milled Titanium Construction",
                    "Magnetic bolt-action haptic deployment mechanism with satisfying click",
                    "Accepts standard Schmidt / Parker G2 ballpoint refills",
                    "Emergency tungsten steel glass-breaker crown"
                ],
                "sizes": ["One Size"],
                "colors": ["Stonewash Grey", "Anodized Midnight"]
            }
        ]
    },
    {
        "niche": "Minimalist Mathematical & Geometric Wall Decor",
        "category": "POD Canvas & Prints",
        "supplier": SupplierType.PRINTIFY,
        "blueprint_id": "PRT-BLP-CANVAS",
        "products": [
            {
                "title": "Lorentz Strange Attractor Chaos Theory Gallery Canvas",
                "handle": "lorentz-strange-attractor-chaos-theory-canvas",
                "cogs": 13.80,
                "shipping": 5.20,
                "retail": 42.00,
                "tags": ["wall-art", "math", "canvas", "modern-decor"],
                "image": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=800",
                "description_points": [
                    "FSC-Certified Pinewood Frame with 1.25-inch Gallery Wrap",
                    "Acid-free archival grade canvas substrate preventing color degradation",
                    "Pre-installed sawtooth mounting hardware ready to hang out of box",
                    "High-dynamic range pigment printing rendering intricate orbit trajectories"
                ],
                "sizes": ["12x18 in", "18x24 in", "24x36 in"],
                "colors": ["Monochrome Dark", "Chroma Glow"]
            }
        ]
    }
]


class NicheScout:
    """Discovers high-probability winning products with optimal margin structures."""

    def __init__(self):
        self.markup_pct = config.default_markup_percent
        self.min_profit = config.min_profit_dollars

    def generate_curated_catalog(self) -> List[CatalogProduct]:
        """Translates curated winning product models into full typed CatalogProducts."""
        catalog: List[CatalogProduct] = []

        for niche in WINNING_NICHES:
            supplier = niche["supplier"]
            for item in niche["products"]:
                prod_id = f"NEX-{uuid.uuid4().hex[:8].upper()}"
                variants: List[ProductVariant] = []

                # Build variants across sizes and colors
                for size in item["sizes"]:
                    for color in item["colors"]:
                        cogs = item["cogs"]
                        shipping = item["shipping"]
                        total_cost = cogs + shipping
                        
                        # Apply markup rule
                        calculated_retail = max(
                            round(total_cost * (self.markup_pct / 100.0), 2),
                            round(total_cost + self.min_profit, 2),
                            item["retail"]
                        )

                        var_sku = f"{supplier.value[:3].upper()}-{item['handle'][:8].upper()}-{size[:2].upper()}-{color[:3].upper()}"
                        var_id = f"VAR-{uuid.uuid4().hex[:8].upper()}"

                        variants.append(
                            ProductVariant(
                                variant_id=var_id,
                                title=f"{size} / {color}",
                                sku=var_sku,
                                cost_price=round(total_cost, 2),
                                retail_price=calculated_retail,
                                size=size,
                                color=color,
                                supplier_variant_id=f"SUP-{var_sku}",
                                supplier_sku=var_sku,
                            )
                        )

                # HTML formatted description
                bullets_html = "".join([f"<li><b>{p.split(' ')[0]}</b> {' '.join(p.split(' ')[1:])}</li>" for p in item["description_points"]])
                desc_html = f"""
                <div class="nexus-product-description">
                  <p class="nexus-hook">Engineered for quality, longevity, and uncompromising aesthetic execution.</p>
                  <h3>Key Features & Specifications</h3>
                  <ul>{bullets_html}</ul>
                  <h3>Shipping & Delivery</h3>
                  <p>All orders are packed and dispatched directly from our regional fulfillment centers with live track-and-trace monitoring.</p>
                </div>
                """

                cat_prod = CatalogProduct(
                    product_id=prod_id,
                    title=item["title"],
                    handle=item["handle"],
                    description_html=desc_html.strip(),
                    vendor="Nexus Apparel & Tech",
                    product_type=niche["category"],
                    supplier_type=supplier,
                    supplier_product_id=f"{supplier.value[:3].upper()}-CAT-{uuid.uuid4().hex[:6].upper()}",
                    tags=item["tags"],
                    images=[item["image"]],
                    variants=variants,
                    is_published=False,
                )
                catalog.append(cat_prod)

        return catalog


niche_scout = NicheScout()
