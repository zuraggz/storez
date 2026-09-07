"""Request and response contracts for the JSON API.

Field names are camelCase on the wire, matching the storefront's original
contract, while the Python side stays snake_case.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator
from pydantic.alias_generators import to_camel

from app.models import BlogPost, Category, Product

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ---------------------------------------------------------------- products
class ProductListItem(ApiModel):
    id: int
    name: str
    slug: str
    short_description: str
    price: float
    old_price: float | None
    image_url: str
    category_name: str
    category_slug: str
    is_featured: bool
    is_special: bool
    rating: float
    review_count: int
    views: int
    stock: int
    created_at: datetime
    is_on_sale: bool
    in_stock: bool
    discount_percent: int

    @classmethod
    def from_product(cls, product: Product, *, views: int | None = None) -> ProductListItem:
        return cls(
            id=product.id,
            name=product.name,
            slug=product.slug,
            short_description=product.short_description,
            price=float(product.price),
            old_price=float(product.old_price) if product.old_price is not None else None,
            image_url=product.image_url,
            category_name=product.category.name if product.category else "",
            category_slug=product.category.slug if product.category else "",
            is_featured=product.is_featured,
            is_special=product.is_special,
            rating=float(product.rating),
            review_count=product.review_count,
            views=product.views if views is None else views,
            stock=product.stock,
            created_at=product.created_at,
            is_on_sale=product.is_on_sale,
            in_stock=product.in_stock,
            discount_percent=product.discount_percent,
        )


class ProductDetail(ProductListItem):
    description: str
    sku: str
    images: list[str]

    @classmethod
    def from_product(cls, product: Product, *, views: int | None = None) -> ProductDetail:
        base = ProductListItem.from_product(product, views=views)
        return cls(
            **base.model_dump(),
            description=product.description,
            sku=product.sku,
            images=product.gallery,
        )


class PagedResult(ApiModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total_count: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        return 0 if self.page_size <= 0 else math.ceil(self.total_count / self.page_size)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


# -------------------------------------------------------------- categories
class CategoryRead(ApiModel):
    id: int
    name: str
    slug: str
    description: str | None
    product_count: int

    @classmethod
    def from_category(cls, category: Category, product_count: int) -> CategoryRead:
        return cls(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            product_count=product_count,
        )


# -------------------------------------------------------------------- blog
class BlogPostListItem(ApiModel):
    id: int
    title: str
    slug: str
    author: str
    excerpt: str
    image_url: str
    published_at: datetime
    views: int

    @classmethod
    def from_post(cls, post: BlogPost, *, views: int | None = None) -> BlogPostListItem:
        return cls(
            id=post.id,
            title=post.title,
            slug=post.slug,
            author=post.author,
            excerpt=post.excerpt,
            image_url=post.image_url,
            published_at=post.published_at,
            views=post.views if views is None else views,
        )


class BlogPostDetail(BlogPostListItem):
    content: str

    @classmethod
    def from_post(cls, post: BlogPost, *, views: int | None = None) -> BlogPostDetail:
        base = BlogPostListItem.from_post(post, views=views)
        return cls(**base.model_dump(), content=post.content)


# ---------------------------------------------------------------- requests
class ContactRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(max_length=200)
    subject: str | None = Field(default=None, max_length=200)
    message: str = Field(min_length=10, max_length=4000)

    @field_validator("subject")
    @classmethod
    def empty_subject_is_none(cls, value: str | None) -> str | None:
        return value or None


class SubscribeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(max_length=200)


#: Human wording for the two request models, keyed by "field.rule". FastAPI's
#: default messages are accurate but terse; the storefront shows these verbatim.
VALIDATION_MESSAGES: dict[str, str] = {
    "name": "Please tell us your name.",
    "email": "That does not look like a valid email address.",
    "message": "Messages need to be at least 10 characters.",
    "subject": "That subject is too long.",
}
