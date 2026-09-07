"""Server-rendered pages.

Every page works without JavaScript: the tabs, filters, search and pager are
ordinary links and forms. `store.js` then upgrades the same URLs to in-place
swaps through the `/partials/*` endpoints, so the storefront feels exactly like
the single-page original while remaining crawlable and refresh-proof.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas import VALIDATION_MESSAGES, ContactRequest
from app.services import catalog, inbox, journal
from app.templating import templates

router = APIRouter(include_in_schema=False)

DbSession = Annotated[Session, Depends(get_db)]

SHOP_PAGE_SIZE = 9

#: id -> (label, query) for the three collections on the home page.
HOME_TABS: dict[str, tuple[str, dict[str, object]]] = {
    "latest": ("Latest Product", {"sort": "newest"}),
    "featured": ("Featured Product", {"featured": True, "sort": "popular"}),
    "special": ("Special Product", {"special": True, "sort": "popular"}),
}

PROMISES = (
    (
        "truck",
        "Free delivery over $80",
        "Dispatched within a day, tracked the whole way to your door.",
    ),
    (
        "leaf",
        "Made in small batches",
        "Responsibly sourced fabric, cut and finished in limited runs.",
    ),
    (
        "shield",
        "30-day easy returns",
        "Changed your mind? Send it back, no questions and no fee.",
    ),
)

ABOUT_STATS = (
    ("2014", "Founded in London"),
    ("24", "Pieces in the core range"),
    ("31", "Countries shipped to"),
    ("4.7", "Average product rating"),
)

ABOUT_VALUES = (
    (
        "leaf",
        "Fabric first",
        (
            "We choose the cloth before we draw the garment. Mills we can visit, fibres we can "
            "trace, and weights that hold their shape past the first season."
        ),
    ),
    (
        "shield",
        "Built to be repaired",
        (
            "Flat-felled seams, generous hems and welted soles. Everything we sell is made so "
            "that a cobbler or a tailor can give it a second life."
        ),
    ),
    (
        "truck",
        "Small batches only",
        (
            "We produce in runs of a few hundred and restock what sells. Nothing is made to be "
            "discounted into a landfill at the end of a season."
        ),
    ),
)

HERO_SLIDES = (
    {
        "eyebrow": "Special Price",
        "title": "New Product Collection",
        "href": "/shop?sort=newest",
        "image": "/images/hero/slide-1.svg",
        "alt": "Illustration of a summer dress from the new collection",
    },
    {
        "eyebrow": "Autumn Layers",
        "title": "Outerwear That Lasts",
        "href": "/shop?category=men",
        "image": "/images/hero/slide-2.svg",
        "alt": "Illustration of a camel wool overcoat",
    },
    {
        "eyebrow": "Everyday Carry",
        "title": "Bags Built To Travel",
        "href": "/shop?category=bags",
        "image": "/images/hero/slide-3.svg",
        "alt": "Illustration of a black backpack",
    },
)


def _home_products(session: Session, tab: str) -> list:
    label_query = HOME_TABS.get(tab) or HOME_TABS["latest"]
    query = catalog.ProductQuery.create(page_size=6, **label_query[1])  # type: ignore[arg-type]
    return catalog.search_products(session, query).items


def _shop_context(session: Session, request: Request) -> dict[str, object]:
    params = request.query_params

    search = params.get("search", "").strip()
    category = params.get("category", "all").strip().lower() or "all"
    sort = params.get("sort", "popular")
    on_sale = params.get("onSale") == "true"

    try:
        page = max(1, int(params.get("page", "1")))
    except ValueError:
        page = 1

    query = catalog.ProductQuery.create(
        search=search or None,
        category=category,
        sort=sort,
        page=page,
        page_size=SHOP_PAGE_SIZE,
        on_sale=True if on_sale else None,
    )

    result = catalog.search_products(session, query)

    return {
        "result": result,
        "search": search,
        "category": category,
        "sort": query.sort,
        "on_sale": on_sale,
        "has_active_filters": bool(search) or category != "all" or on_sale,
    }


# ------------------------------------------------------------------- pages
@router.get("/", response_class=HTMLResponse)
def home(request: Request, session: DbSession, tab: str = "latest"):
    active_tab = tab if tab in HOME_TABS else "latest"

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "page_title": "Qlonil — Modern Fashion Store",
            "hero_slides": HERO_SLIDES,
            "tabs": HOME_TABS,
            "active_tab": active_tab,
            "products": _home_products(session, active_tab),
            "promises": PROMISES,
            "posts": journal.list_posts(session, 3),
        },
    )


@router.get("/shop", response_class=HTMLResponse)
def shop(request: Request, session: DbSession):
    context: dict[str, object] = {"page_title": "Shop — Qlonil"}
    context.update(_shop_context(session, request))
    context["categories"] = catalog.list_categories(session)

    return templates.TemplateResponse(request, "shop.html", context)


@router.get("/product/{slug}", response_class=HTMLResponse)
def product_detail(slug: str, request: Request, session: DbSession):
    product = catalog.get_product_by_slug(session, slug)

    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    views = product.views + 1
    related = catalog.get_related_products(session, product, 4)

    response = templates.TemplateResponse(
        request,
        "product.html",
        {
            "page_title": f"{product.name} — Qlonil",
            "product": product,
            "views": views,
            "related": related,
        },
    )

    # Recorded after the page is built so the count shown includes this visit.
    catalog.record_product_view(session, product.id)
    return response


@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        {"page_title": "About — Qlonil", "stats": ABOUT_STATS, "values": ABOUT_VALUES},
    )


@router.get("/blog", response_class=HTMLResponse)
def blog(request: Request, session: DbSession):
    return templates.TemplateResponse(
        request,
        "blog.html",
        {"page_title": "Journal — Qlonil", "posts": journal.list_posts(session, 12)},
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
def blog_post(slug: str, request: Request, session: DbSession):
    post = journal.get_post_by_slug(session, slug)

    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    views = post.views + 1

    response = templates.TemplateResponse(
        request,
        "blog_post.html",
        {"page_title": f"{post.title} — Qlonil", "post": post, "views": views},
    )

    journal.record_post_view(session, post.id)
    return response


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse(
        request, "contact.html", {"page_title": "Contact — Qlonil", "form": {}, "errors": {}}
    )


@router.post("/contact", response_class=HTMLResponse)
def submit_contact(
    request: Request,
    session: DbSession,
    name: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    subject: Annotated[str, Form()] = "",
    message: Annotated[str, Form()] = "",
):
    """Validate on the server, then re-render with either errors or a receipt."""
    submitted = {"name": name, "email": email, "subject": subject, "message": message}

    try:
        payload = ContactRequest(**submitted)
    except ValidationError as error:
        errors = {
            str(item["loc"][-1]): VALIDATION_MESSAGES.get(
                str(item["loc"][-1]), item.get("msg", "Invalid value.")
            )
            for item in error.errors()
        }

        return templates.TemplateResponse(
            request,
            "contact.html",
            {
                "page_title": "Contact — Qlonil",
                "form": submitted,
                "errors": errors,
            },
            status_code=400,
        )

    inbox.save_contact_message(
        session,
        name=payload.name,
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
    )

    return templates.TemplateResponse(
        request,
        "contact.html",
        {
            "page_title": "Contact — Qlonil",
            "form": {},
            "errors": {},
            "sent": "Thanks for getting in touch. We reply within two working days.",
        },
    )


@router.post("/newsletter")
def submit_newsletter(
    request: Request,
    session: DbSession,
    email: Annotated[str, Form()] = "",
    next: Annotated[str, Form()] = "/",
):
    r"""No-JavaScript fallback for the footer signup: subscribe, then come back.

    `next` comes from the page the form was rendered on, but it arrives as form
    data — so only a same-site path is honoured. `//evil.example` and
    `/\evil.example` are protocol-relative URLs, not paths.
    """
    destination = next if next.startswith("/") and not next.startswith(("//", "/\\")) else "/"

    address = email.strip().lower()
    if "@" not in address or "." not in address.split("@")[-1]:
        state = "invalid"
    else:
        state = "already" if inbox.subscribe(session, address) else "ok"

    separator = "&" if "?" in destination else "?"
    return RedirectResponse(
        f"{destination}{separator}subscribed={state}#newsletter",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/account", response_class=HTMLResponse)
def account(request: Request):
    return templates.TemplateResponse(request, "account.html", {"page_title": "Account — Qlonil"})


# ---------------------------------------------------------------- partials
@router.get("/partials/home-products", response_class=HTMLResponse)
def home_products_partial(request: Request, session: DbSession, tab: str = "latest"):
    active_tab = tab if tab in HOME_TABS else "latest"

    return templates.TemplateResponse(
        request,
        "partials/product_grid.html",
        {"products": _home_products(session, active_tab)},
    )


@router.get("/partials/shop-results", response_class=HTMLResponse)
def shop_results_partial(request: Request, session: DbSession):
    return templates.TemplateResponse(
        request, "partials/shop_results.html", _shop_context(session, request)
    )
