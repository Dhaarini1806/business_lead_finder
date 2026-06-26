# FORGE.OS — Lead Intelligence Operator Terminal

**Production-ready Django web application** for extracting, verifying, and enriching business leads using **100% free OpenStreetMap APIs**.

Dark operator terminal with HTMX real-time updates, premium tables, analytics dashboard, and instant Excel/CSV exports.

---

## 🎯 Features

### 5 Extraction Modules

1. **Google Maps Extraction** — Local business data from OpenStreetMap
   - Search by business type + location
   - Radius search (configurable)
   - Name, category, address, phone, website, coordinates
   - < 5 second searches, fully cached

2. **LinkedIn Lead Gen** — Compliant professional profile intake
   - Paste search results or LinkedIn URLs
   - Parse company, role, industry, company size
   - No automated scraping (respects ToS)

3. **Website Scraper** — Extract contact intelligence
   - Emails, phone numbers, social profiles
   - Crawl internal pages (configurable depth)
   - Metadata extraction (title, description)

4. **Email Finder & Verifier** — Generate & verify professional emails
   - Pattern generation (firstname.lastname@, f.lastname@, etc.)
   - Free MX record verification
   - SMTP verification (best-effort)
   - Confidence scoring

5. **AI Enrichment** — Augment leads with AI
   - Website scrape → LLM summary
   - Industry, employee count, technologies
   - AI lead score (0-100)
   - Powered by your LLM (OpenAI-compatible)

### Dashboard & Analytics

- **Metrics** — Total leads, today's searches, successful extractions, enriched leads, exports
- **Charts** — Daily search volume, lead growth, industry breakdown (Chart.js)
- **Recent jobs** — Live extraction history with status
- **Usage tracking** — Billing & export activity

### Premium Results Table

- **Sortable columns** — Click headers to sort
- **In-table search** — Real-time filtering
- **Lead count selector** — 50 / 100 / 200 / All
- **Pagination** — Navigate large result sets
- **Instant export** — Excel (.xlsx) or CSV (.csv)
- **Maps links** — Google Maps & OpenStreetMap

### Account & Settings

- **Profile** — Display name, email
- **Data sources** — Status of Nominatim, Overpass, AI
- **Export preferences** — Default format, lead count
- **Appearance** — Dark theme (light coming soon)
- **Billing** — Usage metrics, monthly credits, activity

---

## 🏗️ Architecture

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0.6 (Python 3.13) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Django Templates + Tailwind + HTMX + Alpine.js |
| Analytics | Chart.js |
| Data | Nominatim + Overpass API (free) |
| Export | OpenPyXL + CSV |

### Project Structure

```
business_lead_finder/
├── config/                    # Django settings
│   ├── settings.py           # Production-ready config
│   ├── urls.py
│   └── wsgi.py
├── leads/                     # Main app
│   ├── models.py             # Search, Business, Enrichment, ExportLog
│   ├── views.py              # All module views
│   ├── forms.py              # Search forms
│   ├── urls.py
│   ├── admin.py              # Admin with custom actions
│   ├── tests.py              # 19 unit + integration tests
│   └── services/
│       ├── osm.py            # Nominatim + Overpass
│       ├── scraper.py        # Website crawling
│       ├── emailfinder.py    # Email generation & verification
│       ├── linkedin.py       # LinkedIn intake
│       ├── enrichment.py     # AI enrichment
│       └── exporter.py       # Excel/CSV builders
├── templates/
│   ├── base.html             # Forge OS chrome
│   ├── landing.html          # Public landing page
│   ├── dashboard.html        # Dashboard
│   ├── modules/
│   │   ├── gmaps.html
│   │   ├── linkedin.html
│   │   ├── scraper.html
│   │   ├── emailfinder.html
│   │   └── enrichment.html
│   ├── settings.html
│   ├── billing.html
│   ├── packages.html
│   └── partials/             # HTMX partials
├── static/css/
│   └── forge.css             # Forge OS theme
├── db.sqlite3
├── manage.py
├── requirements.txt
└── README.md
```

### Database Models

**Search** — Extraction job
- `source` — google_maps, linkedin, website, email_finder, enrichment
- `business_type`, `location` — Query parameters
- `status` — running, completed, failed
- `total_results`, `duration_seconds`
- Indexes for fast queries

**Business** — Lead row (shared across sources)
- Core: name, category, address, phone, website, email, latitude, longitude
- LinkedIn: position, company, industry, company_size, linkedin_url
- Email: email_status, email_confidence
- OSM: osm_type, osm_id (deduplication)
- Misc: social_links, extra (JSON)

**Enrichment** — OneToOne with Business
- ai_summary, ai_score (0-100)
- industry, employee_count, business_category
- technologies, social_links (JSON)
- domain

**ExportLog** — Export audit trail
- source, fmt (xlsx/csv), record_count
- business_type, location
- created_at

---

## 🚀 Quick Start

### Installation

```bash
cd C:\Users\HEY\business_lead_finder
venv\Scripts\activate
pip install -r requirements.txt
```

### Run Migrations

```bash
python manage.py migrate
```

### Create Admin User

```bash
python manage.py createsuperuser
```

### Start Dev Server

```bash
python manage.py runserver 127.0.0.1:8000
```

Open **http://127.0.0.1:8000/** in your browser.

### Run Tests

```bash
python manage.py test leads -v 1
```

All 19 tests pass ✓

---

## 📖 Usage

### Google Maps Extraction

1. Navigate to **Extractors → Google Maps**
2. Enter:
   - Business Type (e.g., "Bakery")
   - Location (e.g., "Chromepet, Chennai")
   - Radius (km) — default 5
   - Max Results — default 50
3. Click **Run Extraction**
4. Results table appears with:
   - Sortable columns
   - In-table search filter
   - Lead count selector (50/100/200/All)
   - Export to Excel or CSV

### Website Scraper

1. Navigate to **Extractors → Website Scraper**
2. Enter domain URL
3. Optionally enable **Crawl internal pages**
4. Click **Scrape Website**
5. View extracted emails, phones, socials, metadata

### Email Finder & Verifier

1. Navigate to **Extractors → Email Finder**
2. Enter:
   - Person Name (optional)
   - Company Domain (required)
   - Company (optional)
3. Optionally enable **Run SMTP/MX verification**
4. Click **Find Emails**
5. View candidates with verification status & confidence

### LinkedIn Intake

1. Navigate to **Extractors → LinkedIn Lead Gen**
2. Paste search results or LinkedIn URLs
3. Click **Ingest Leads**
4. Leads parsed with company, role, industry

### AI Enrichment

1. Navigate to **Extractors → AI Enrichment**
2. View Google Maps leads with websites
3. Click **Enrich** on any lead
4. AI generates summary, industry, score

### Dashboard

- View metrics (total leads, today's searches, exports)
- See charts (daily volume, industry breakdown)
- Browse recent jobs

### Export

- Click **Export Excel** or **Export CSV** on any results table
- Downloads instantly with all lead fields

### Settings

- Update profile (name, email)
- View data sources status
- Set export preferences
- Choose appearance

### Billing

- View current plan & usage
- See recent activity (all exports)
- Upgrade to Pro or Agency

---

## ⚙️ Configuration

### Django Settings (`config/settings.py`)

**OSM Configuration:**
```python
OSM_SEARCH_RADIUS = 5  # km (default)
OSM_CACHE_TIMEOUT = 3600  # seconds
OSM_USER_AGENT = "FORGE.OS Lead Intelligence / 1.0"
```

**Database:**
```python
# SQLite (dev)
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'db.sqlite3'}}

# PostgreSQL (production)
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'forge_db', ...}}
```

**Caching:**
```python
# Development (in-memory)
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

# Production (Redis)
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': 'redis://127.0.0.1:6379/1'}}
```

**LLM (AI Enrichment):**
```python
# Uses OPENAI_API_KEY and OPENAI_API_BASE from environment
```

---

## 🏭 Production Deployment

### Using Gunicorn + PostgreSQL + Redis

```bash
# Install production dependencies
pip install gunicorn psycopg2-binary redis

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Start Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Environment Variables

```bash
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost/forge_db
REDIS_URL=redis://localhost:6379/1
OPENAI_API_KEY=sk-...
```

### PostgreSQL Setup

```bash
createdb forge_db
python manage.py migrate
python manage.py createsuperuser
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    client_max_body_size 10M;

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test leads -v 1

# Run specific test class
python manage.py test leads.tests.ViewTests -v 1

# Run with coverage
pip install coverage
coverage run --source='leads' manage.py test leads
coverage report
```

**Test Coverage:**
- Models: Search, Business, Enrichment, ExportLog
- Services: OSM, scraper, email finder, enrichment
- Views: All modules, HTMX endpoints, exports
- Forms: Validation

---

## 🔗 Free APIs Used

| Service | Endpoint | Rate Limit | Cost |
|---------|----------|-----------|------|
| Nominatim | nominatim.openstreetmap.org | 1 req/sec | Free |
| Overpass | overpass-api.de | ~1 req/sec | Free |
| MX Lookup | dnspython | Unlimited | Free |
| SMTP Check | Custom | Unlimited | Free |
| LLM (Optional) | OpenAI-compatible | Per token | Variable |

**No Google API billing. No subscriptions. 100% free infrastructure.**

---

## 🆘 Troubleshooting

### "Could not find the location"
- Nominatim geocoding failed
- Try a more specific location name
- Example: "Chromepet, Chennai" instead of "Chennai"

### "The OpenStreetMap data service is temporarily busy"
- Overpass API rate limit hit
- Wait a few minutes and retry
- Cached searches return instantly

### No emails extracted from website
- Website may not have contact info on homepage
- Enable **Crawl internal pages** to search deeper
- Some sites block scraping; respect robots.txt

### Email verification shows "Risky"
- Domain exists (MX found) but SMTP check inconclusive
- Email may still be valid; use with caution

### Admin panel not accessible
- Create superuser: `python manage.py createsuperuser`
- Navigate to `/admin/`

---

## 📋 Usage Policy (Important)

This project uses the **public** OpenStreetMap Nominatim and Overpass endpoints, which are free but rate-limited. Please respect their usage policies:

- Send a descriptive `User-Agent` (configured via `OSM_USER_AGENT`)
- Avoid heavy bulk scraping; the built-in caching helps
- For high volume, consider self-hosting Nominatim/Overpass

Policies:
- Nominatim: https://operations.osmfoundation.org/policies/nominatim/
- Overpass: https://dev.overpass-api.de/overpass-doc/

---

## 📜 License & Attribution

Business data is © OpenStreetMap contributors, available under the **Open Database License (ODbL)**. When publishing results, attribute OpenStreetMap accordingly.

---

## 🗺️ Roadmap

- [ ] Celery async tasks for large extractions
- [ ] Redis caching for production
- [ ] Team collaboration (multiple users)
- [ ] API key authentication
- [ ] Webhook integrations (Zapier, Make)
- [ ] Advanced filtering & saved searches
- [ ] Bulk import (CSV upload)
- [ ] Lead scoring rules engine
- [ ] CRM integrations (Salesforce, HubSpot)
- [ ] Mobile app (React Native)

---

**Built with ❤️ using Django, OpenStreetMap, and free APIs.**

**FORGE.OS — The operator terminal for local lead intelligence.**
