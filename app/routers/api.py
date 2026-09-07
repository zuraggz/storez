"""The JSON API. Same contract as the storefront has always exposed."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import database_is_reachable
from app.deps import get_db
from app.schemas import (
    BlogPostDetail,
    BlogPostListItem,
    CategoryRead,
    ContactRequest,
    PagedResult,
    ProductDetail,
    ProductListItem,
    SubscribeRequest,
)
from app.services import catalog, inbox, journal

logger = logging.getLogger("qlonil.api")

router = APIRouter(prefix="/api", tags=["api"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/products", response_model=PagedResult[ProductListItem])
def get_products(
    session: DbSession,
    search: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=140)] = None,
    sort: str = "popular",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=catalog.MAX_PAGE_SIZE)] = 12,
    min_price: Annotated[Decimal | None, Query(alias="minPrice", ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(alias="maxPrice", ge=0)] = None,
    on_sale: Annotated[bool | None, Query(alias="onSale")] = None,
    featured: bool | None = None,
    special: bool | None = None,
    in_stock: Annotated[bool | None, Query(alias="inStock")] = None,
) -> PagedResult[ProductListItem]:
    """Search, filter, sort and page the catalogue."""
    query = catalog.ProductQuery.create(
        search=search,
        category=category,
        sort=sort,
        page=page,
        page_size=page_size,
        min_price=min_price,
        max_price=max_price,
        on_sale=on_sale,
        featured=featured,
        special=special,
        in_stock=in_stock,
    )

    result = catalog.search_products(session, query)

    return PagedResult[ProductListItem](
        items=[ProductListItem.from_product(product) for product in result.items],
        page=result.page,
        page_size=result.page_size,
        total_count=result.total_count,
    )


@router.get("/products/{slug}", response_model=ProductDetail)
def get_product(slug: str, session: DbSession) -> ProductDetail:
    """One product by slug. Records a view, which feeds the popular sort."""
    product = catalog.get_product_by_slug(session, slug)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No product exists with the slug '{slug}'.",
        )

    payload = ProductDetail.from_product(product, views=product.views + 1)
    catalog.record_product_view(session, product.id)
    return payload


@router.get("/products/{slug}/related", response_model=list[ProductListItem])
def get_related(slug: str, session: DbSession, limit: int = 4) -> list[ProductListItem]:
    """Most-viewed products from the same category, excluding this one."""
    product = catalog.get_product_by_slug(session, slug)

    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return [
        ProductListItem.from_product(other)
        for other in catalog.get_related_products(session, product, limit)
    ]


@router.get("/categories", response_model=list[CategoryRead])
def get_categories(session: DbSession) -> list[CategoryRead]:
    """Categories with their product counts, for the shop's filter rail."""
    return [
        CategoryRead.from_category(category, count)
        for category, count in catalog.list_categories(session)
    ]


@router.get("/blog", response_model=list[BlogPostListItem])
def get_posts(session: DbSession, limit: int = 6) -> list[BlogPostListItem]:
    return [BlogPostListItem.from_post(post) for post in journal.list_posts(session, limit)]


@router.get("/blog/{slug}", response_model=BlogPostDetail)
def get_post(slug: str, session: DbSession) -> BlogPostDetail:
    post = journal.get_post_by_slug(session, slug)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No blog post exists with the slug '{slug}'.",
        )

    payload = BlogPostDetail.from_post(post, views=post.views + 1)
    journal.record_post_view(session, post.id)
    return payload


@router.post("/newsletter")
def subscribe(request: SubscribeRequest, session: DbSession) -> dict[str, object]:
    """Footer signup. Re-submitting a known address is a no-op, not an error."""
    already_subscribed = inbox.subscribe(session, request.email)

    if already_subscribed:
        return {"message": "You are already on the list.", "alreadySubscribed": True}

    logger.info("New newsletter subscriber")
    return {
        "message": "Thanks for subscribing. Your 32% code is on its way.",
        "alreadySubscribed": False,
    }


@router.post("/contact", status_code=status.HTTP_201_CREATED)
def send_contact(request: ContactRequest, session: DbSession) -> dict[str, object]:
    message = inbox.save_contact_message(
        session,
        name=request.name,
        email=request.email,
        subject=request.subject,
        message=request.message,
    )

    return {
        "id": message.id,
        "message": "Thanks for getting in touch. We reply within two working days.",
    }


@router.get("/health")
def health(response: Response) -> dict[str, object]:
    """Liveness plus a database round-trip."""
    if database_is_reachable():
        return {
            "status": "healthy",
            "database": "up",
            "utc": datetime.now(UTC).isoformat(),
        }

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "database": "down"}
