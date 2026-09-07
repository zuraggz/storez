"""The server-rendered pages, including the no-JavaScript form paths."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("path", "needle"),
    [
        ("/", "New Product Collection"),
        ("/shop", "All products"),
        ("/about", "A small studio with a long memory"),
        ("/blog", "Journal"),
        ("/contact", "We read everything"),
        ("/account", "Accounts are not enabled in this build"),
        ("/product/leather-tote-bag", "Full-grain vegetable-tanned leather"),
        ("/blog/how-to-read-a-fabric-label", "GSM tells you weight"),
    ],
)
def test_pages_render(client: TestClient, path: str, needle: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert needle in response.text


def test_home_tabs_change_the_collection(client: TestClient) -> None:
    special = client.get("/", params={"tab": "special"})

    assert 'data-tab="special"' in special.text
    assert 'href="/?tab=special#collection"' in special.text
    assert special.text.count('class="product-card"') == 6


def test_shop_filters_render_server_side(client: TestClient) -> None:
    response = client.get("/shop", params={"category": "bags", "sort": "price-asc"})

    assert "<strong>3</strong> products" in response.text
    assert 'aria-pressed="true"' in response.text


def test_shop_search_reports_the_term(client: TestClient) -> None:
    response = client.get("/shop", params={"search": "denim"})

    assert "<strong>2</strong> products" in response.text
    assert "denim" in response.text


def test_shop_pagination_links_carry_the_filters(client: TestClient) -> None:
    response = client.get("/shop", params={"onSale": "true"})

    assert "onSale=true&amp;page=2" in response.text


def test_missing_page_renders_the_404_view(client: TestClient) -> None:
    response = client.get("/product/nothing-here", headers={"accept": "text/html"})

    assert response.status_code == 404
    assert "This page went out of stock" in response.text


def test_partials_return_fragments_not_full_pages(client: TestClient) -> None:
    grid = client.get("/partials/home-products", params={"tab": "featured"})
    results = client.get("/partials/shop-results", params={"category": "shoes"})

    assert "<html" not in grid.text
    assert "product-grid" in grid.text
    assert "<strong>3</strong> products" in results.text


def test_contact_form_posts_without_javascript(client: TestClient) -> None:
    response = client.post(
        "/contact",
        data={
            "name": "Zura",
            "email": "zura@example.com",
            "subject": "",
            "message": "Please tell me about the wool overcoat.",
        },
    )

    assert response.status_code == 200
    assert "We reply within two working days." in response.text


def test_contact_form_re_renders_with_errors(client: TestClient) -> None:
    response = client.post("/contact", data={"name": "", "email": "nope", "message": "short"})

    assert response.status_code == 400
    assert "Please tell us your name." in response.text
    assert "That does not look like a valid email address." in response.text
    assert "Messages need to be at least 10 characters." in response.text


def test_newsletter_form_redirects_back(client: TestClient, unique_email: str) -> None:
    response = client.post(
        "/newsletter",
        data={"email": unique_email, "next": "/shop"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/shop?subscribed=ok#newsletter"

    again = client.post(
        "/newsletter",
        data={"email": unique_email, "next": "/shop"},
        follow_redirects=False,
    )
    assert again.headers["location"] == "/shop?subscribed=already#newsletter"


@pytest.mark.parametrize("target", ["https://evil.example", "//evil.example", "/\\evil.example"])
def test_newsletter_form_refuses_an_open_redirect(
    client: TestClient, unique_email: str, target: str
) -> None:
    response = client.post(
        "/newsletter",
        data={"email": unique_email, "next": target},
        follow_redirects=False,
    )

    assert response.headers["location"].startswith("/?subscribed=")


def test_product_page_records_a_view(client: TestClient) -> None:
    before = client.get("/api/products/canvas-weekender").json()["views"]
    client.get("/product/canvas-weekender")
    after = client.get("/api/products/canvas-weekender").json()["views"]

    # Each detail read reports the count including itself, so `before` already
    # banked one view; the page visit adds the second.
    assert after == before + 2
