"""Catalogue queries: search, filter, sort and page the products."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Product

#: value -> label, in the order the shop's sort menu shows them.
SORT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("popular", "Most popular"),
    ("newest", "Newest first"),
    ("rating", "Highest rated"),
    ("price-asc", "Price: low to high"),
    ("price-desc", "Price: high to low"),
    ("name-asc", "Name: A to Z"),
    ("name-desc", "Name: Z to A"),
)

VALID_SORTS = {value for value, _ in SORT_OPTIONS} | {"oldest"}

DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 60


def _escape_like(term: str) -> str:
    """Neutralise LIKE wildcards so a search for "50%" is not a match-anything."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class ProductQuery:
    """The query-string contract for the shop, already normalised."""

    search: str | None = None
    category: str | None = None
    sort: str = "popular"
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    on_sale: bool | None = None
    featured: bool | None = None
    special: bool | None = None
    in_stock: bool | None = None

    @classmethod
    def create(
        cls,
        *,
        search: str | None = None,
        category: str | None = None,
        sort: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        min_price: Decimal | float | None = None,
        max_price: Decimal | float | None = None,
        on_sale: bool | None = None,
        featured: bool | None = None,
        special: bool | None = None,
        in_stock: bool | None = None,
    ) -> ProductQuery:
        cleaned_search = (search or "").strip()[:120] or None
        cleaned_category = (category or "").strip().lower() or None
        if cleaned_category == "all":
            cleaned_category = None

        chosen_sort = (sort or "popular").strip().lower()
        if chosen_sort not in VALID_SORTS:
            chosen_sort = "popular"

        return cls(
            search=cleaned_search,
            category=cleaned_category,
            sort=chosen_sort,
            page=max(1, page or 1),
            page_size=min(MAX_PAGE_SIZE, max(1, page_size or DEFAULT_PAGE_SIZE)),
            min_price=Decimal(str(min_price)) if min_price is not None else None,
            max_price=Decimal(str(max_price)) if max_price is not None else None,
            on_sale=on_sale,
            featured=featured,
            special=special,
            in_stock=in_stock,
        )


@dataclass(frozen=True)
class Page:
    items: list[Product]
    page: int
    page_size: int
    total_count: int

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return -(-self.total_count // self.page_size)

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def _apply_filters(statement: Select, query: ProductQuery) -> Select:
    if query.search:
        term = f"%{_escape_like(query.search)}%"
        statement = statement.where(
            Product.name.ilike(term, escape="\\")
            | Product.short_description.ilike(term, escape="\\")
            | Category.name.ilike(term, escape="\\")
        )

    if query.category:
        statement = statement.where(Category.slug == query.category)

    if query.min_price is not None:
        statement = statement.where(Product.price >= query.min_price)
    if query.max_price is not None:
        statement = statement.where(Product.price <= query.max_price)
    if query.on_sale:
        statement = statement.where(
            Product.old_price.is_not(None), Product.old_price > Product.price
        )
    if query.featured is not None:
        statement = statement.where(Product.is_featured.is_(query.featured))
    if query.special is not None:
        statement = statement.where(Product.is_special.is_(query.special))
    if query.in_stock:
        statement = statement.where(Product.stock > 0)

    return statement


def _apply_sort(statement: Select, sort: str) -> Select:
    match sort:
        case "newest":
            return statement.order_by(Product.created_at.desc(), Product.id)
        case "oldest":
            return statement.order_by(Product.created_at.asc(), Product.id)
        case "price-asc":
            return statement.order_by(Product.price.asc(), Product.id)
        case "price-desc":
            return statement.order_by(Product.price.desc(), Product.id)
        case "name-asc":
            return statement.order_by(Product.name.asc(), Product.id)
        case "name-desc":
            return statement.order_by(Product.name.desc(), Product.id)
        case "rating":
            return statement.order_by(
                Product.rating.desc(), Product.review_count.desc(), Product.id
            )
        case _:
            # "popular" is the default: most viewed first.
            return statement.order_by(Product.views.desc(), Product.id)


def search_products(session: Session, query: ProductQuery) -> Page:
    base = select(Product).join(Category, Product.category_id == Category.id)
    filtered = _apply_filters(base, query)

    total_count = session.scalar(
        _apply_filters(
            select(func.count(Product.id)).join(Category, Product.category_id == Category.id),
            query,
        )
    )

    items = (
        session.scalars(
            _apply_sort(filtered, query.sort)
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        .unique()
        .all()
    )

    return Page(
        items=list(items),
        page=query.page,
        page_size=query.page_size,
        total_count=int(total_count or 0),
    )


def get_product_by_slug(session: Session, slug: str) -> Product | None:
    return session.scalars(
        select(Product).options(selectinload(Product.images)).where(Product.slug == slug)
    ).unique().first()


def record_product_view(session: Session, product_id: int) -> None:
    """Atomic increment, so concurrent readers cannot lose a count."""
    session.execute(
        update(Product).where(Product.id == product_id).values(views=Product.views + 1)
    )
    session.commit()


def get_related_products(
    session: Session, product: Product, limit: int = 4
) -> list[Product]:
    """Most-viewed products from the same category, excluding this one."""
    limit = 4 if limit < 1 or limit > 12 else limit

    return list(
        session.scalars(
            select(Product)
            .where(Product.category_id == product.category_id, Product.id != product.id)
            .order_by(Product.views.desc(), Product.id)
            .limit(limit)
        ).unique()
    )


def list_categories(session: Session) -> list[tuple[Category, int]]:
    """Every category with its product count, for the shop's filter rail."""
    rows = session.execute(
        select(Category, func.count(Product.id))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.sort_order, Category.id)
    ).all()

    return [(category, int(count)) for category, count in rows]
