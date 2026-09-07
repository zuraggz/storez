"""ORM entities.

The shape mirrors the storefront's original schema one for one: Category →
Product → ProductImage, plus BlogPost, Subscriber and ContactMessage. Indexes
cover exactly the columns the shop sorts and filters on.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    products: Mapped[list[Product]] = relationship(
        back_populates="category", cascade="save-update, merge"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Category {self.slug}>"


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_views", "views"),
        Index("ix_products_created_at", "created_at"),
        Index("ix_products_price", "price"),
        Index("ix_products_featured_special", "is_featured", "is_special"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    short_description: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    #: Price before the discount. NULL when the product is not on sale.
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    sku: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    category: Mapped[Category] = relationship(back_populates="products", lazy="joined")

    image_url: Mapped[str] = mapped_column(String(400), nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_special: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0"), nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Detail-page hit counter. Drives the "Most popular" sort.
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )

    # --- derived fields, mirrored by the API contract ----------------------
    @property
    def is_on_sale(self) -> bool:
        return self.old_price is not None and self.old_price > self.price

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def discount_percent(self) -> int:
        if not self.is_on_sale or not self.old_price:
            return 0
        return round((self.old_price - self.price) / self.old_price * 100)

    @property
    def gallery(self) -> list[str]:
        urls = [image.url for image in sorted(self.images, key=lambda i: i.sort_order)]
        return urls or [self.image_url]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Product {self.slug}>"


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product: Mapped[Product] = relationship(back_populates="images")
    url: Mapped[str] = mapped_column(String(400), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class BlogPost(Base):
    __tablename__ = "blog_posts"
    __table_args__ = (Index("ix_blog_posts_published_at", "published_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    slug: Mapped[str] = mapped_column(String(240), nullable=False, unique=True, index=True)
    author: Mapped[str] = mapped_column(String(80), nullable=False)
    excerpt: Mapped[str] = mapped_column(String(400), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_url: Mapped[str] = mapped_column(String(400), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    @property
    def paragraphs(self) -> list[str]:
        return [block.strip() for block in self.content.split("\n\n") if block.strip()]


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
