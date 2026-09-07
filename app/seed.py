"""Idempotent demo data: 6 categories, 24 products and 6 journal posts.

Each block checks whether its table already has rows, so running this against a
populated database does nothing. That makes it safe to call on every boot.
"""

from __future__ import annotations

import logging
import zlib
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BlogPost, Category, Product, ProductImage, utcnow

logger = logging.getLogger("qlonil.seed")


def slugify(value: str) -> str:
    cleaned = value.lower().replace("'", "")
    slug = "".join(character if character.isalnum() else "-" for character in cleaned)

    while "--" in slug:
        slug = slug.replace("--", "-")

    return slug.strip("-")


def _sku(slug: str) -> str:
    """A stable per-product SKU derived from the slug."""
    return f"QL-{10000 + zlib.crc32(slug.encode()) % 90000}"


@dataclass(frozen=True)
class ProductSeed:
    name: str
    category: str
    price: str
    old_price: str | None
    image: str
    featured: bool
    special: bool
    views: int
    rating: str
    reviews: int
    stock: int
    days_ago: int
    blurb: str


@dataclass(frozen=True)
class BlogSeed:
    title: str
    author: str
    excerpt: str
    content: str
    image: str
    views: int


CATEGORY_SEEDS: tuple[tuple[str, str, int, str], ...] = (
    ("Men", "men", 1, "Tailored shirts, denim and outerwear built for everyday wear."),
    ("Women", "women", 2, "Soft linens, easy dresses and layering pieces for every season."),
    ("Kids", "kids", 3, "Hard-wearing basics that survive the school run."),
    ("Bags", "bags", 4, "Leather and canvas carry, from daily totes to weekenders."),
    ("Shoes", "shoes", 5, "Sneakers, boots and loafers finished by hand."),
    ("Accessories", "accessories", 6, "The small things that finish the look."),
)

PRODUCT_SEEDS: tuple[ProductSeed, ...] = (
    ProductSeed(
        "Men's Cotton Shirt", "men", "30", "45", "shirt-blue", True, True, 4820, "4.7", 128, 42, 2,
        "A crisp poplin shirt with a soft collar that holds its shape all day.",
    ),
    ProductSeed(
        "Men's Denim Pant", "men", "70", "85", "jeans-indigo", True, True, 6310, "4.8", 214, 31, 4,
        "Mid-rise straight denim in a rigid 12oz weave that breaks in fast.",
    ),
    ProductSeed(
        "Men's Wool Overcoat", "men", "180", None, "coat-camel", True, False, 2140, "4.9", 46, 12, 9,
        "An unstructured overcoat in a brushed wool blend, cut long.",
    ),
    ProductSeed(
        "Men's Slim Chino", "men", "55", None, "chino-olive", False, False, 1780, "4.4", 73, 55, 14,
        "Garment-dyed cotton twill with just enough stretch to move in.",
    ),
    ProductSeed(
        "Men's Knit Polo", "men", "42", "55", "polo-sand", False, True, 2960, "4.5", 91, 38, 6,
        "A fine-gauge knit polo that dresses up as easily as it dresses down.",
    ),
    ProductSeed(
        "Men's Grey Sweatshirt", "men", "65", None, "sweatshirt-grey", True, False, 5410, "4.6", 167, 47, 3,
        "Heavyweight loopback cotton, brushed inside and ribbed at the cuff.",
    ),
    ProductSeed(
        "Women's Linen Blouse", "women", "48", None, "blouse-white", True, False, 3890, "4.6", 104, 29, 5,
        "Airy European linen with a relaxed shoulder and shell buttons.",
    ),
    ProductSeed(
        "Women's Summer Dress", "women", "95", "120", "dress-rose", True, True, 7240, "4.8", 232, 18, 1,
        "A midi dress with a tie waist that moves the way summer should.",
    ),
    ProductSeed(
        "Women's Wide Leg Trouser", "women", "72", None, "trouser-black", False, False, 2510, "4.5", 88, 34, 11,
        "High-waisted, sharply pressed, and long enough for a heel.",
    ),
    ProductSeed(
        "Women's Wrap Cardigan", "women", "85", "105", "cardigan-cream", True, True, 3320, "4.7", 76, 22, 8,
        "A merino wrap cardigan that belts at the waist or hangs open.",
    ),
    ProductSeed(
        "Women's Silk Scarf", "women", "35", None, "scarf-teal", False, False, 1240, "4.3", 41, 63, 16,
        "Hand-rolled edges on a lightweight silk twill square.",
    ),
    ProductSeed(
        "Boy's School Bag", "kids", "25", None, "backpack-black", True, False, 5980, "4.5", 189, 74, 2,
        "A water-resistant daypack with a padded laptop sleeve and reflective trim.",
    ),
    ProductSeed(
        "Kid's Puffer Jacket", "kids", "60", "75", "puffer-navy", True, True, 4130, "4.7", 112, 40, 5,
        "Lightweight recycled fill with a fleece-lined collar for the cold walk in.",
    ),
    ProductSeed(
        "Kid's Cotton Tee", "kids", "18", None, "tee-pink", False, False, 2870, "4.4", 156, 96, 10,
        "Soft-washed jersey that keeps its shape through a hundred washes.",
    ),
    ProductSeed(
        "Girl's Denim Dungaree", "kids", "40", "52", "dungaree-blue", False, True, 1960, "4.6", 67, 44, 13,
        "Adjustable straps and roomy pockets, built for climbing things.",
    ),
    ProductSeed(
        "Leather Tote Bag", "bags", "130", "160", "tote-tan", True, True, 6720, "4.9", 198, 16, 3,
        "Full-grain vegetable-tanned leather that darkens beautifully with use.",
    ),
    ProductSeed(
        "Canvas Weekender", "bags", "110", None, "weekender-olive", False, False, 2280, "4.6", 59, 21, 12,
        "Waxed cotton canvas with leather handles and a wide zip opening.",
    ),
    ProductSeed(
        "Mini Crossbody Bag", "bags", "78", "95", "crossbody-black", True, True, 4460, "4.7", 143, 37, 7,
        "Just enough room for the essentials, on an adjustable webbing strap.",
    ),
    ProductSeed(
        "Classic White Sneaker", "shoes", "90", None, "sneaker-white", True, False, 8150, "4.8", 276, 52, 1,
        "A clean leather court shoe on a cupsole that actually lasts.",
    ),
    ProductSeed(
        "Leather Chelsea Boot", "shoes", "145", "175", "boot-brown", True, True, 5230, "4.8", 121, 24, 6,
        "Goodyear-welted and resoleable, with twin elastic gussets.",
    ),
    ProductSeed(
        "Suede Loafer", "shoes", "120", None, "loafer-navy", False, False, 1830, "4.5", 63, 30, 15,
        "An unlined suede loafer that wears like a slipper from day one.",
    ),
    ProductSeed(
        "Minimal Wrist Watch", "accessories", "160", None, "watch-silver", True, False, 4970, "4.7", 134, 19, 4,
        "A 38mm brushed steel case, sapphire crystal and a quiet movement.",
    ),
    ProductSeed(
        "Ribbed Beanie", "accessories", "22", "30", "beanie-grey", False, True, 3540, "4.4", 187, 88, 9,
        "A double-layer merino rib that holds its shape and never itches.",
    ),
    ProductSeed(
        "Round Sunglasses", "accessories", "45", "60", "sunglasses-gold", True, True, 3910, "4.5", 95, 51, 8,
        "Thin gold-tone frames with polarised, UV400 lenses.",
    ),
)

BLOG_SEEDS: tuple[BlogSeed, ...] = (
    BlogSeed(
        "Beauty Products We Used In Our Teens",
        "Admin",
        "The formulas that defined a decade of getting ready, revisited with a decade of hindsight.",
        "Everyone has a shelf they would rather forget. The sticky lip gloss, the glitter that never "
        "quite washed out, the toner that stripped your face raw in the name of feeling clean.\n\n"
        "Looking back, the products were rarely the problem. The routine was. We treated skin as "
        "something to be corrected rather than kept, and we did it three times a day.\n\n"
        "The good news is that almost everything we loved then has a gentler descendant now. Here is "
        "what we would keep, what we would replace, and the one thing we would happily buy again "
        "tomorrow.",
        "storefront",
        3420,
    ),
    BlogSeed(
        "Take Time For Ready Yourself",
        "Monica",
        "Getting dressed is the last quiet part of the morning. It is worth protecting.",
        "There is a version of the morning where you pull the first clean thing off the pile and "
        "leave. Most of us live there most days.\n\n"
        "But the ten minutes you spend deciding are not wasted time. They are the last stretch of the "
        "day that belongs entirely to you, before the messages start and the day picks a direction of "
        "its own.\n\n"
        "Build a small rotation you trust and keep it visible. Then spend the ten minutes on the "
        "coffee instead.",
        "flatlay",
        2870,
    ),
    BlogSeed(
        "These Fashion Looks Go With Every Thing",
        "Fardino",
        "Five combinations that answer the outfit question before you have finished asking it.",
        "A capsule wardrobe is not about owning less. It is about owning things that agree with each "
        "other.\n\n"
        "Start with a neutral base you actually like the feel of, add exactly one texture, and let the "
        "shoes do the talking. That is the whole formula, and it survives contact with almost any "
        "weather.\n\n"
        "Below are five pairings we keep returning to, and the pieces that make each one work.",
        "atelier",
        2190,
    ),
    BlogSeed(
        "How To Read A Fabric Label",
        "Admin",
        "Grams, weaves and blends, explained in the time it takes to queue for a fitting room.",
        "GSM tells you weight, not quality. A 180gsm jersey and a 320gsm loopback are both cotton, but "
        "only one of them keeps its shape through a winter.\n\n"
        "Blends are not a compromise either. A few percent elastane is the difference between a "
        "trouser you wear and a trouser you fold.\n\n"
        "Here is the short version of what each number on the label is actually telling you.",
        "storefront",
        1640,
    ),
    BlogSeed(
        "The Case For Buying The Boot Twice",
        "Monica",
        "Why resoleable footwear works out cheaper by year three, with the arithmetic to prove it.",
        "A welted boot costs roughly three times a glued one. It also lasts roughly six times as long, "
        "and a resole costs less than a new pair of the cheap ones.\n\n"
        "The maths is not subtle. What stops most people is the number on the first day, not the "
        "number over ten years.\n\n"
        "We ran the figures on our own pairs, repairs included, and the result surprised even us.",
        "atelier",
        1980,
    ),
    BlogSeed(
        "Packing Light Without Packing Badly",
        "Fardino",
        "One bag, six days, and no laundry crisis on the fourth morning.",
        "The trick to a small bag is not rolling technique. It is deciding, before you pack, which "
        "single colour everything will answer to.\n\n"
        "Pick the palette first and the volume takes care of itself, because every top now works with "
        "every bottom and you stop packing insurance.\n\n"
        "Here is the exact list we take for a working week away.",
        "flatlay",
        1470,
    ),
)


def _build_description(seed: ProductSeed) -> str:
    return (
        f"{seed.blurb} Cut from responsibly sourced fabric and finished in small batches, the "
        f"{seed.name.lower()} is made to sit comfortably alongside the wardrobe you already own. "
        "Pre-washed for a soft handle, reinforced at every stress point, and sized true to fit. "
        "Machine wash cold, line dry, warm iron if needed."
    )


def _count(session: Session, model: type) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def seed_database(session: Session) -> None:
    """Populate empty tables. Anything already present is left alone."""
    now = utcnow()

    if _count(session, Category) == 0:
        session.add_all(
            [
                Category(name=name, slug=slug, sort_order=order, description=description)
                for name, slug, order, description in CATEGORY_SEEDS
            ]
        )
        session.flush()
        logger.info("Seeded %d categories", len(CATEGORY_SEEDS))

    if _count(session, Product) == 0:
        category_ids = {
            slug: identifier
            for slug, identifier in session.execute(select(Category.slug, Category.id)).all()
        }

        for seed in PRODUCT_SEEDS:
            slug = slugify(seed.name)
            image_url = f"/images/products/{seed.image}.svg"

            product = Product(
                name=seed.name,
                slug=slug,
                short_description=seed.blurb,
                description=_build_description(seed),
                price=Decimal(seed.price),
                old_price=Decimal(seed.old_price) if seed.old_price else None,
                sku=_sku(slug),
                stock=seed.stock,
                category_id=category_ids[seed.category],
                image_url=image_url,
                is_featured=seed.featured,
                is_special=seed.special,
                rating=Decimal(seed.rating),
                review_count=seed.reviews,
                views=seed.views,
                created_at=now - timedelta(days=seed.days_ago),
            )

            product.images = [
                ProductImage(url=image_url, sort_order=0),
                ProductImage(url=f"/images/products/{seed.image}-alt.svg", sort_order=1),
                ProductImage(url=f"/images/products/{seed.image}-detail.svg", sort_order=2),
            ]

            session.add(product)

        session.flush()
        logger.info("Seeded %d products", len(PRODUCT_SEEDS))

    if _count(session, BlogPost) == 0:
        session.add_all(
            [
                BlogPost(
                    title=seed.title,
                    slug=slugify(seed.title),
                    author=seed.author,
                    excerpt=seed.excerpt,
                    content=seed.content,
                    image_url=f"/images/blog/{seed.image}.svg",
                    published_at=now - timedelta(days=index * 9 + 3),
                    views=seed.views,
                )
                for index, seed in enumerate(BLOG_SEEDS)
            ]
        )
        session.flush()
        logger.info("Seeded %d journal posts", len(BLOG_SEEDS))
