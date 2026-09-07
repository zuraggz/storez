# Qlonil — a Python storefront

A server-rendered e-commerce storefront written entirely in **Python**: a **FastAPI** application
with **Jinja2** templates and **SQLAlchemy 2.0** on **PostgreSQL**, deployed to **Vercel** as a
single serverless function. Same design, same catalogue and same API contract as the original
ASP.NET Core + React build — one language, one deployable.

```
project-root/
├── api/index.py                Vercel entrypoint: exports the ASGI app
├── vercel.json                 function config + routing (static files win first)
├── requirements.txt            runtime dependencies
├── app/
│   ├── main.py                 app factory: CORS, RFC 7807 errors, static mounts
│   ├── config.py               environment settings, database URL normalisation
│   ├── database.py             engine (NullPool), sessions, one-shot bootstrap
│   ├── models.py               ORM entities and indexes
│   ├── schemas.py              request/response contracts (camelCase on the wire)
│   ├── seed.py                 idempotent demo data: 6 categories, 24 products, 6 posts
│   ├── cli.py                  python -m app.cli init | seed | check | reset
│   ├── deps.py                 request-scoped session
│   ├── templating.py           Jinja filters: price, date, count, shop URLs
│   ├── routers/api.py          the JSON API
│   ├── routers/views.py        the HTML pages and partials
│   └── templates/              base, pages, components, icons, partials
├── public/                     served by Vercel's CDN, mounted locally by FastAPI
│   ├── css/app.css             the design system, unchanged from the original
│   ├── js/store.js             progressive enhancement: cart, carousel, in-place swaps
│   └── images/                 every illustration, generated as flat SVG
├── scripts/generate_images.py  regenerates public/images
├── tests/                      pytest suite: API, pages, cold-start bootstrap
├── Dockerfile, docker-compose.yml   local Postgres parity (not used by Vercel)
└── README.md
```

---

## Quick start

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # macOS/Linux: .venv/bin/pip
cp .env.example .env
.venv/Scripts/python -m app.cli init
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

The storefront is at <http://localhost:8000>, the API reference (development only) at
<http://localhost:8000/docs>.

With no `DATABASE_URL` set, the app uses a local SQLite file so the first run needs nothing
installed. Point `DATABASE_URL` at Postgres — locally, on Neon, anywhere — and the same code runs
unchanged.

Prefer containers? `docker compose up --build` starts Postgres and the app together.

---

## Features

**Shop page** — search by name, filter by category, filter to sale items, sort, paginate. Every
control is reflected in the URL, so `/shop?search=denim&sort=price-asc&page=2` is shareable and
survives a refresh or the back button.

**Sorting** — most popular (by view count), newest, highest rated, price ascending/descending, and
name A→Z / Z→A. Popularity is real: each product detail view atomically increments that product's
`views` column, and the "most popular" sort orders by it.

**Product detail** — reached from the *View Product* button on any card, at `/product/{slug}`.
Gallery with thumbnails, rating, stock, SKU, quantity picker and add-to-cart.

**About page**, **journal** (list + article), and a **contact form** that validates on both sides
and persists messages.

**Cart** — client-side, persisted to `localStorage`, opens in a drawer from the header.

**Works without JavaScript** — the pages are rendered on the server, so the tabs, filters, search,
sort, pager and the contact and newsletter forms are ordinary links and forms. `public/js/store.js`
then upgrades those same URLs to in-place swaps through `/partials/*`, which is what makes the shop
feel like the single-page original. Only the cart and the hero carousel genuinely need the browser.

---

## Architecture notes

**Why server-rendered.** The original shipped a React bundle that called a separate .NET API, which
meant two deployments, a CORS policy between them, and a build-time `VITE_API_URL` that could not
change without a rebuild. Rendering the same markup from Jinja collapses that into one Vercel
project with no cross-origin hop — and the JSON API is still there for anything else that wants it.

**Why Postgres.** Vercel functions have a read-only, ephemeral filesystem, so SQLite cannot persist
anything in production. Neon is serverless Postgres with a pooled endpoint, which suits functions
that come and go: the engine uses `NullPool` so each request opens and closes its own connection
rather than holding one open against the database's connection limit. Any Postgres works — Supabase,
Railway, RDS — the code only needs a URL.

**Schema and seeding.** `Base.metadata.create_all()` plus an idempotent seeder, run once per process
behind a flag (`AUTO_INIT_DB`, on by default). A first deployment under traffic means several cold
starts bootstrapping the same empty database at once — and concurrent `CREATE TABLE` statements do
not merely duplicate work, Postgres fails one of them with a unique violation on its own catalogue.
So the whole bootstrap runs under a session-level advisory lock: the first process creates and
seeds, the rest wait and find the work done. There is a test for it. Once the schema is stable you
can turn the bootstrap off and manage migrations yourself.

**Error shape.** Failures come back as RFC 7807 `application/problem+json`, and validation errors
carry an `errors` map keyed by field — the same contract the original API exposed, so existing
clients do not have to change.

---

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | SQLite file | Postgres URL. `postgres://`, `postgresql://` and `postgresql+psycopg://` all work. **Required on Vercel.** |
| `ENVIRONMENT` | `production` | `development` mounts `/docs` and includes exception detail in 500s. |
| `AUTO_INIT_DB` | `true` | Create the schema on first boot. |
| `SEED_DEMO_DATA` | `true` | Seed the 24-product catalogue into empty tables. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:8000,http://localhost:3000` | Comma-separated. An entry may use `*` as a single-segment wildcard (`https://*.vercel.app`); a bare `*` allows any origin. Only matters for cross-origin API clients. |

---

## API

Base URL is the site itself. Errors come back as `application/problem+json`.

### `GET /api/products`

| Query | Type | Default | Notes |
|---|---|---|---|
| `search` | string | – | Matches product name, blurb or category name |
| `category` | string | – | Category slug, or `all` |
| `sort` | string | `popular` | `popular`, `newest`, `oldest`, `rating`, `price-asc`, `price-desc`, `name-asc`, `name-desc` |
| `page` | int | `1` | |
| `pageSize` | int | `12` | 1–60 |
| `minPrice` / `maxPrice` | decimal | – | |
| `onSale` | bool | – | Products with a struck-through original price |
| `featured` / `special` | bool | – | Drive the three home-page tabs |
| `inStock` | bool | – | |

Returns `{ items, page, pageSize, totalCount, totalPages, hasPrevious, hasNext }`.

```bash
curl "http://localhost:8000/api/products?search=denim&sort=price-asc&pageSize=6"
```

### Other endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/products/{slug}` | Product detail. **Increments the view counter.** |
| `GET` | `/api/products/{slug}/related?limit=4` | Most-viewed products in the same category |
| `GET` | `/api/categories` | Categories with product counts |
| `GET` | `/api/blog?limit=6` | Journal posts, newest first |
| `GET` | `/api/blog/{slug}` | One article. Increments its view counter. |
| `POST` | `/api/newsletter` | `{ "email": "..." }`. Re-subscribing is a no-op, not an error. |
| `POST` | `/api/contact` | `{ name, email, subject?, message }` |
| `GET` | `/api/health` | Liveness plus a database round-trip |

Pages live alongside it: `/`, `/shop`, `/product/{slug}`, `/about`, `/blog`, `/blog/{slug}`,
`/contact`, `/account`, plus `/partials/home-products` and `/partials/shop-results` for the in-place
swaps.

---

## Database

Entities: `Category` → `Product` → `ProductImage`, plus `BlogPost`, `Subscriber` and
`ContactMessage`. Indexes cover the columns the shop actually sorts and filters on — `views`,
`created_at`, `price`, `(is_featured, is_special)` — and slugs are unique.

```bash
python -m app.cli check    # which database, is it reachable, row counts
python -m app.cli init     # create the schema and seed
python -m app.cli seed     # seed only; skips tables that already have rows
python -m app.cli reset --force   # drop everything, then recreate and seed
```

Seeding is idempotent: it skips any table that already has rows, so restarts never duplicate data.

---

## Images

Every product, journal and hero image is a flat SVG illustration generated by
`scripts/generate_images.py` — no external image host, works offline and on Vercel.

```bash
python scripts/generate_images.py
```

The seeder stores paths like `/images/products/shirt-blue.svg`, served from `public/`. If a file is
ever missing, the template's `smart_image` macro falls back to a placeholder rather than showing a
broken image. To use real photography instead, point the `image` column at absolute URLs — the
templates pass any `http(s)` value straight through.

---

## Tests

```bash
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest
```

41 tests run against a temporary SQLite database seeded with the same demo data: the API contract
(paging, sorting, filters, view counters, validation shapes), the pages (rendering, the server-side
filter and pager links, the no-JavaScript form paths) and the cold-start bootstrap.

Point them at the engine production uses to run the same suite on Postgres — including the
concurrent cold-start test, which is skipped on SQLite:

```bash
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/qlonil_test python -m pytest
```

---

## Deployment to Vercel

One project, no separate backend. The whole app is a single Python function; `public/` is served
straight from the CDN.

### 1. Provision a database

Vercel → your project → **Storage** → **Neon** (Marketplace) → create a database. That sets
`DATABASE_URL` on the project automatically. Anything else that gives you a Postgres URL works too —
just add `DATABASE_URL` yourself under **Settings → Environment Variables** for Production, Preview
and Development.

### 2. Deploy

```bash
npm i -g vercel
vercel link
vercel --prod
```

Or push to GitHub and import the repository in the dashboard. There is nothing to configure: leave
the framework preset as **Other** and the build settings empty — `vercel.json` does the rest.

On the first request the app creates its tables and seeds the catalogue, so the deployment is
usable straight away. Confirm with:

```bash
curl https://<your-app>.vercel.app/api/health
```

To seed from your machine instead — useful if you would rather deploy with `AUTO_INIT_DB=false`:

```bash
vercel env pull .env
python -m app.cli init
```

### How the routing works

| Request | Served by |
|---|---|
| `/css/*`, `/js/*`, `/images/*`, `/favicon.svg` | Vercel's CDN, straight from `public/` |
| everything else | `api/index.py`, via the catch-all rewrite |

Vercel checks the filesystem before applying rewrites, so static assets never reach the function.
`vercel.json` also pins `includeFiles: "app/**"` so the templates and application code are bundled
with the function, and sets a 30-second `maxDuration`.

### Notes

- **Python version.** `.python-version` pins 3.12. The code targets 3.11+.
- **Cold starts.** The bootstrap runs once per process and is a boolean check afterwards. Set
  `AUTO_INIT_DB=false` once the schema is stable to skip it entirely.
- **Connection limits.** `NullPool` plus Neon's pooled endpoint (`-pooler` in the host name) is the
  combination that survives many concurrent functions. If you use an unpooled host, expect to hit
  the connection cap under load.

---

## Notes and limitations

- **No authentication.** Nothing here needs it, so the app ships without an auth layer and
  `/account` says so plainly.
- **No checkout.** The cart is real and persists, but there is no payment flow.
- **The seeder owns the schema.** For anything beyond demo data, add Alembic and turn
  `AUTO_INIT_DB` off.
- `*` in `CORS_ALLOWED_ORIGINS` is convenient while testing and a bad idea in production — pin it to
  your domain once the URL is stable.
