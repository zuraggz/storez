"""The JSON API contract."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_the_database(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"] == "up"


def test_products_are_paged_and_camel_cased(client: TestClient) -> None:
    response = client.get("/api/products", params={"pageSize": 5})
    body = response.json()

    assert response.status_code == 200
    assert body["pageSize"] == 5
    assert body["totalCount"] == 24
    assert body["totalPages"] == 5
    assert body["hasNext"] is True
    assert body["hasPrevious"] is False
    assert len(body["items"]) == 5

    item = body["items"][0]
    assert {"shortDescription", "oldPrice", "imageUrl", "categorySlug", "isOnSale"} <= item.keys()


def test_default_sort_is_most_viewed(client: TestClient) -> None:
    items = client.get("/api/products", params={"pageSize": 5}).json()["items"]
    views = [item["views"] for item in items]

    assert views == sorted(views, reverse=True)


def test_price_sort_and_discount_maths(client: TestClient) -> None:
    items = client.get("/api/products", params={"sort": "price-asc", "pageSize": 60}).json()["items"]
    prices = [item["price"] for item in items]

    assert prices == sorted(prices)

    on_sale = next(item for item in items if item["isOnSale"])
    expected = round((on_sale["oldPrice"] - on_sale["price"]) / on_sale["oldPrice"] * 100)
    assert on_sale["discountPercent"] == expected


def test_search_matches_name_blurb_and_category(client: TestClient) -> None:
    names = [
        item["name"] for item in client.get("/api/products", params={"search": "denim"}).json()["items"]
    ]

    assert "Men's Denim Pant" in names
    assert "Girl's Denim Dungaree" in names


def test_search_treats_wildcards_literally(client: TestClient) -> None:
    body = client.get("/api/products", params={"search": "%"}).json()

    assert body["totalCount"] == 0


def test_category_and_on_sale_filters(client: TestClient) -> None:
    bags = client.get("/api/products", params={"category": "bags"}).json()
    assert bags["totalCount"] == 3
    assert {item["categorySlug"] for item in bags["items"]} == {"bags"}

    on_sale = client.get("/api/products", params={"onSale": "true", "pageSize": 60}).json()
    assert on_sale["totalCount"] == 12
    assert all(item["isOnSale"] for item in on_sale["items"])


def test_featured_and_special_drive_the_home_tabs(client: TestClient) -> None:
    featured = client.get("/api/products", params={"featured": "true", "pageSize": 60}).json()
    special = client.get("/api/products", params={"special": "true", "pageSize": 60}).json()

    assert all(item["isFeatured"] for item in featured["items"])
    assert all(item["isSpecial"] for item in special["items"])


def test_page_size_out_of_range_is_a_problem_response(client: TestClient) -> None:
    response = client.get("/api/products", params={"pageSize": 0})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert "errors" in response.json()


def test_product_detail_increments_views(client: TestClient) -> None:
    before = client.get("/api/products/suede-loafer").json()
    after = client.get("/api/products/suede-loafer").json()

    assert after["views"] == before["views"] + 1
    assert after["sku"].startswith("QL-")
    assert len(after["images"]) == 3


def test_unknown_product_is_a_404_problem(client: TestClient) -> None:
    response = client.get("/api/products/not-a-real-product")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


def test_related_products_share_the_category_and_exclude_the_source(client: TestClient) -> None:
    related = client.get("/api/products/leather-tote-bag/related", params={"limit": 4}).json()

    assert related
    assert all(item["categorySlug"] == "bags" for item in related)
    assert all(item["slug"] != "leather-tote-bag" for item in related)


def test_categories_carry_product_counts(client: TestClient) -> None:
    categories = client.get("/api/categories").json()

    assert [category["slug"] for category in categories][:2] == ["men", "women"]
    assert sum(category["productCount"] for category in categories) == 24


def test_blog_list_and_detail(client: TestClient) -> None:
    posts = client.get("/api/blog", params={"limit": 3}).json()
    assert len(posts) == 3

    slug = posts[0]["slug"]
    first = client.get(f"/api/blog/{slug}").json()
    second = client.get(f"/api/blog/{slug}").json()

    assert "content" in first
    assert second["views"] == first["views"] + 1


def test_newsletter_signup_is_idempotent(client: TestClient, unique_email: str) -> None:
    first = client.post("/api/newsletter", json={"email": unique_email.upper()}).json()
    second = client.post("/api/newsletter", json={"email": unique_email}).json()

    assert first["alreadySubscribed"] is False
    assert second["alreadySubscribed"] is True


def test_newsletter_rejects_a_bad_address(client: TestClient) -> None:
    response = client.post("/api/newsletter", json={"email": "nope"})

    assert response.status_code == 400
    assert response.json()["errors"]["email"]


def test_contact_message_is_stored(client: TestClient) -> None:
    response = client.post(
        "/api/contact",
        json={
            "name": "Zura",
            "email": "zura@example.com",
            "subject": "Sizing",
            "message": "Does the chelsea boot run true to size?",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] > 0


def test_contact_validation_names_the_bad_fields(client: TestClient) -> None:
    response = client.post(
        "/api/contact", json={"name": "", "email": "nope", "message": "short"}
    )

    assert response.status_code == 400
    errors = response.json()["errors"]
    assert set(errors) == {"name", "email", "message"}
    assert errors["message"] == ["Messages need to be at least 10 characters."]
