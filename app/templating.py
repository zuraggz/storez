"""Jinja environment: one place for the filters the templates rely on.

The formatting rules are the ones the design uses — "$ 30.00 USD", "Nov 29,
2022", "3.4k views" — so pages and the JSON API never disagree about how a
number is written.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlencode

from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, get_settings
from app.services.catalog import SORT_OPTIONS

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def format_price(value: Decimal | float | None) -> str:
    """`$ 30.00 USD` — matches the price treatment in the design."""
    if value is None:
        return ""
    return f"$ {Decimal(str(value)):.2f} USD"


def format_date(value: datetime | None) -> str:
    """`Nov 29, 2022`"""
    if value is None:
        return ""
    # SQLite hands back naive datetimes; everything is stored as UTC.
    moment = value if value.tzinfo else value.replace(tzinfo=UTC)
    return f"{moment:%b} {moment.day}, {moment.year}"


def format_count(value: int | None) -> str:
    if not value:
        return "0"
    return f"{value / 1000:.1f}k" if value >= 1000 else str(value)


def query_string(params: dict[str, object]) -> str:
    """Build `?a=1&b=2`, dropping empty values, for filter and pager links."""
    cleaned = {
        key: str(value)
        for key, value in params.items()
        if value is not None and value != "" and value is not False
    }
    return f"?{urlencode(cleaned)}" if cleaned else ""


def shop_url(
    *,
    search: str | None = None,
    category: str = "all",
    sort: str = "popular",
    on_sale: bool = False,
    page: int = 1,
) -> str:
    """The canonical shop URL for a set of filters — every control links to one."""
    params: dict[str, object] = {}

    if search:
        params["search"] = search
    if category and category != "all":
        params["category"] = category
    if sort and sort != "popular":
        params["sort"] = sort
    if on_sale:
        params["onSale"] = "true"
    if page and page > 1:
        params["page"] = page

    return "/shop" + query_string(params)


def page_window(page: int, total_pages: int) -> list[int | str]:
    """Compact pager: first, last, and a window around the current page."""
    if total_pages <= 7:
        return list(range(1, total_pages + 1))

    wanted = {1, total_pages, page, page - 1, page + 1}
    ordered = sorted(number for number in wanted if 1 <= number <= total_pages)

    result: list[int | str] = []
    previous = 0

    for current in ordered:
        if previous and current - previous > 1:
            result.append("gap")
        result.append(current)
        previous = current

    return result


templates.env.filters["price"] = format_price
templates.env.filters["date"] = format_date
templates.env.filters["count"] = format_count
templates.env.globals["query_string"] = query_string
templates.env.globals["shop_url"] = shop_url
templates.env.globals["page_window"] = page_window
templates.env.globals["sort_options"] = SORT_OPTIONS
templates.env.globals["settings"] = get_settings()
templates.env.globals["now"] = lambda: datetime.now(UTC)
