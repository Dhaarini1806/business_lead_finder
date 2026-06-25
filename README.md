# Business Lead Finder

A complete, production-ready **Django** web application that finds local
business leads by **business type** and **location**, using only **free
OpenStreetMap services** — no Google Places API, no billing, no subscriptions.

Search examples that work out of the box:

| Business Type | Location  |
|---------------|-----------|
| Bakery        | Chromepet |
| Cake Shop     | Chennai   |
| Gym           | Tambaram  |
| Dental Clinic | Velachery |

Results can be browsed in a fast, sortable, paginated table and exported to
`business_leads.xlsx` with one click.

---

## Features

- **Search** by business type + location (HTMX-powered, no full page reloads).
- **Free geocoding** via **Nominatim** (location → coordinates).
- **Free business data** via the **Overpass API** (businesses around a point).
- **Rich business info**: name, category, address, latitude, longitude,
  OpenStreetMap link, Google Maps search link, phone and website (when
  available). Missing values are handled gracefully.
- **Modern results table** with pagination, column sorting, and "search within
  results" — fully mobile responsive (Bootstrap 5).
- **Lead-count selector**: `50 / 100 / 200 / All` to choose how many records to
  prepare for export.
- **Excel export** (`business_leads.xlsx`) generated with **OpenPyXL**,
  including clickable links and a styled header.
- **Search history** (business type, location, date, total results, duration).
- **Dashboard** with totals: searches, businesses found, exports, today's
  searches, and top business types.
- **Django Admin**: view searches/businesses, **delete duplicates**, and
  **export selected leads** to Excel.
- **Performance**: response caching (geocoding + Overpass), database indexing,
  bulk inserts, connection pooling, multiple Overpass mirrors, and HTMX partial
  updates. Cached searches return in well under five seconds.

---

## Technology Stack

| Layer     | Technology                                              |
|-----------|---------------------------------------------------------|
| Backend   | Django 5/6, Python 3.12+                                 |
| Database  | SQLite (development), PostgreSQL (production ready)      |
| Frontend  | Django Templates, Bootstrap 5, HTMX, JavaScript          |
| Export    | Pandas, OpenPyXL                                        |
| Maps/Data | OpenStreetMap — Nominatim API + Overpass API (all free) |

---

## Project Structure

```
business_lead_finder/
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3
├── config/                     # Django project package
│   ├── settings.py             # SQLite/PostgreSQL, caching, OSM config
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── leads/                      # Main application
│   ├── models.py               # Search, Business, ExportLog (+ indexes)
│   ├── views.py                # search, results partial, export, dashboard
│   ├── urls.py
│   ├── forms.py
│   ├── admin.py                # admin + delete-duplicates + export actions
│   ├── tests.py                # unit + integration tests
│   ├── migrations/
│   └── services/
│       ├── osm.py              # Nominatim + Overpass integration & caching
│       └── exporter.py         # OpenPyXL workbook builder
└── templates/
    ├── base.html
    ├── home.html               # search page
    ├── dashboard.html
    ├── history.html
    └── partials/
        ├── results.html        # HTMX results table (sort/paginate/filter)
        └── empty.html
```

---

## Quick Start (Development)

> A virtual environment (`venv/`) is already included. Use it directly, or
> recreate one as shown below.

```bash
# 1. (Optional) create / activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. (Optional) create an admin user for the Django Admin panel
python manage.py createsuperuser

# 5. Run the development server
python manage.py runserver
```

Then open:

- App:        http://127.0.0.1:8000/
- Dashboard:  http://127.0.0.1:8000/dashboard/
- History:    http://127.0.0.1:8000/history/
- Admin:      http://127.0.0.1:8000/admin/

---

## How a Search Works

1. The user enters a **business type** and a **location** and clicks **Search**.
2. HTMX POSTs the form; the view calls `leads.services.osm.fetch_businesses()`.
3. **Nominatim** converts the location text into latitude/longitude.
4. An **Overpass QL** query fetches matching businesses within a configurable
   radius (default 8 km) around that point.
5. Results are parsed, de-duplicated, sorted, **cached**, and **bulk-inserted**
   into the database under a new `Search` record.
6. The results table is rendered back into the page via HTMX — instantly.

Both the geocoding and Overpass responses are cached (6 hours by default), so
repeating an identical search returns almost immediately.

---

## Excel Export

Click **Export Excel** on any result set (or use the **History** page) to
download `business_leads.xlsx`. Columns:

```
Name | Category | Address | Phone | Website | Latitude | Longitude | Maps Link
```

The Website and Maps Link cells are clickable hyperlinks.

---

## Admin Panel

Log in at `/admin/`. Admins can:

- Browse and search **Searches** and **Businesses**.
- **Delete duplicate leads** (same name + address) via a bulk action.
- **Export selected leads** to Excel directly from the change list.
- Review **Export Logs**.

---

## Production Deployment

The same code base is production ready. Configure via environment variables:

| Variable                     | Purpose                                   |
|------------------------------|-------------------------------------------|
| `DJANGO_DEBUG`               | `False` in production                     |
| `DJANGO_SECRET_KEY`          | Strong secret key                         |
| `DJANGO_ALLOWED_HOSTS`       | Comma-separated host list                 |
| `DJANGO_CSRF_TRUSTED_ORIGINS`| Comma-separated trusted origins           |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` | Use PostgreSQL |
| `REDIS_URL`                  | Use Redis as the cache backend            |
| `OSM_USER_AGENT`             | Identify your app to Nominatim politely    |
| `OSM_SEARCH_RADIUS`          | Search radius in meters (default 8000)    |

Example production run:

```bash
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY="your-strong-secret"
export DJANGO_ALLOWED_HOSTS="yourdomain.com"
export POSTGRES_DB=leads POSTGRES_USER=leads POSTGRES_PASSWORD=secret POSTGRES_HOST=localhost

pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

WhiteNoise serves static files, so no separate static server is required.

---

## Running Tests

```bash
python manage.py test leads
```

The suite covers models, the OSM query builder, the Excel exporter, and the
search / export views (the network layer is mocked, so tests run offline).

---

## Usage Policy Note (Important)

This project uses the **public** OpenStreetMap Nominatim and Overpass endpoints,
which are free but rate-limited and intended for moderate use. Please respect
their usage policies:

- Send a descriptive `User-Agent` (configured via `OSM_USER_AGENT`).
- Avoid heavy bulk scraping; the built-in caching helps here.
- For high volume, consider self-hosting Nominatim/Overpass and pointing
  `NOMINATIM_URL` / `OVERPASS_URL` at your own instances.

Policies:
- Nominatim: <https://operations.osmfoundation.org/policies/nominatim/>
- Overpass:  <https://dev.overpass-api.de/overpass-doc/>

---

## License & Data Attribution

Business data is © OpenStreetMap contributors, available under the
**Open Database License (ODbL)**. When publishing results, attribute
OpenStreetMap accordingly.
