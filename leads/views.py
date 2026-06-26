"""
Views for Forge OS — Lead Intelligence platform.

Modules: Dashboard, Google Maps Extraction, LinkedIn Extraction, Website
Scraper, Email Finder & Verifier, AI Enrichment, plus Settings / Billing /
Packages and a public landing page.

Extraction logic is delegated to :mod:`leads.services.*`. Leads are persisted
with ``bulk_create`` for speed.
"""

from __future__ import annotations

import json
import time
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import (
    EmailFinderForm,
    GoogleMapsForm,
    LinkedInForm,
    WebsiteScraperForm,
)
from .models import Business, Enrichment, ExportLog, JobStatus, Search, Source
from .services.emailfinder import find_emails
from .services.enrichment import enrich_business
from .services.exporter import build_csv, build_workbook
from .services.linkedin import ingest as linkedin_ingest
from .services.osm import fetch_businesses
from .services.scraper import scrape_website

SORT_FIELDS = {
    "name": "name", "category": "category", "address": "address",
    "phone": "phone", "company": "company", "industry": "industry",
    "email": "email", "rating": "rating",
}
PAGE_SIZES = {"50": 50, "100": 100, "200": 200, "all": 100_000}


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


# ======================================================================= #
# Landing page
# ======================================================================= #
def landing(request):
    return render(request, "landing.html", {"hide_chrome": True})


# ======================================================================= #
# Dashboard
# ======================================================================= #
@require_http_methods(["GET"])
def dashboard(request):
    today = timezone.localdate()
    stats = {
        "total_leads": Business.objects.count(),
        "today_searches": Search.objects.filter(created_at__date=today).count(),
        "successful": Search.objects.filter(status=JobStatus.COMPLETED).count(),
        "enriched": Enrichment.objects.count(),
        "exported": ExportLog.objects.aggregate(n=Sum("record_count"))["n"] or 0,
    }

    # Daily searches (last 14 days)
    days, daily_counts, daily_leads = [], [], []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        days.append(d.strftime("%b %d"))
        qs = Search.objects.filter(created_at__date=d)
        daily_counts.append(qs.count())
        daily_leads.append(qs.aggregate(n=Sum("total_results"))["n"] or 0)

    # cumulative lead growth
    growth, running = [], 0
    for v in daily_leads:
        running += v
        growth.append(running)

    top_industries = list(
        Business.objects.exclude(category="")
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")[:6]
    )

    recent = Search.objects.all()[:8]

    charts = {
        "labels": days,
        "daily": daily_counts,
        "growth": growth,
        "ind_labels": [t["category"] for t in top_industries] or ["No data"],
        "ind_values": [t["count"] for t in top_industries] or [1],
    }

    return render(request, "dashboard.html", {
        "active": "dashboard",
        "page_title": "System Overview",
        "page_subtitle": "Real-time lead intelligence & extraction metrics",
        "stats": stats,
        "recent": recent,
        "charts_json": json.dumps(charts),
    })


# ======================================================================= #
# Shared results rendering (Google Maps / generic lead tables)
# ======================================================================= #
def _results_context(request, search: Search) -> dict:
    sort = request.GET.get("sort", "name")
    direction = request.GET.get("dir", "asc")
    query = request.GET.get("q", "").strip()
    size_key = request.GET.get("size", "50")

    field = SORT_FIELDS.get(sort, "name")
    order = field if direction == "asc" else f"-{field}"

    qs = search.businesses.all()
    if query:
        qs = qs.filter(
            Q(name__icontains=query) | Q(category__icontains=query)
            | Q(address__icontains=query) | Q(phone__icontains=query)
            | Q(company__icontains=query) | Q(email__icontains=query)
        )
    qs = qs.order_by(order)

    per_page = PAGE_SIZES.get(size_key, 50)
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return {
        "search": search,
        "page_obj": page_obj,
        "total": qs.count(),
        "sort": sort, "dir": direction, "q": query, "size": size_key,
        "page_sizes": ["50", "100", "200", "all"],
        "source": search.source,
    }


@require_http_methods(["GET"])
def results_partial(request, search_id: int):
    search = get_object_or_404(Search, pk=search_id)
    return render(request, "partials/results.html", _results_context(request, search))


# ======================================================================= #
# Module 1 — Google Maps Extraction
# ======================================================================= #
@require_http_methods(["GET", "POST"])
def gmaps(request):
    if request.method == "POST":
        form = GoogleMapsForm(request.POST)
        if not form.is_valid():
            return render(request, "partials/results.html",
                          {"error": "Please provide both a keyword and a location."})
        bt = form.cleaned_data["business_type"]
        loc = form.cleaned_data["location"]
        radius_km = form.cleaned_data.get("radius_km")
        max_results = form.cleaned_data.get("max_results")
        radius_m = int(radius_km * 1000) if radius_km else None

        start = time.perf_counter()
        outcome = fetch_businesses(bt, loc, radius=radius_m, max_results=max_results)
        duration = round(time.perf_counter() - start, 2)

        if outcome.error:
            Search.objects.create(
                source=Source.GOOGLE_MAPS, business_type=bt, location=loc,
                status=JobStatus.FAILED, error=outcome.error,
                duration_seconds=duration,
            )
            return render(request, "partials/results.html", {"error": outcome.error})

        search = Search.objects.create(
            source=Source.GOOGLE_MAPS, business_type=bt, location=loc,
            radius_km=radius_km, max_results=max_results,
            latitude=outcome.geocode.latitude if outcome.geocode else None,
            longitude=outcome.geocode.longitude if outcome.geocode else None,
            display_name=outcome.geocode.display_name if outcome.geocode else "",
            total_results=len(outcome.businesses),
            duration_seconds=duration, status=JobStatus.COMPLETED,
        )
        Business.objects.bulk_create([
            Business(
                search=search, source=Source.GOOGLE_MAPS,
                osm_type=r.osm_type, osm_id=r.osm_id, name=r.name,
                category=r.category, address=r.address,
                latitude=r.latitude, longitude=r.longitude,
                phone=r.phone, website=r.website, email=r.email,
            ) for r in outcome.businesses
        ], batch_size=500, ignore_conflicts=True)

        ctx = _results_context(request, search)
        ctx["duration"] = duration
        return render(request, "partials/results.html", ctx)

    return render(request, "modules/gmaps.html", {
        "active": "gmaps", "page_title": "Google Maps Extraction",
        "page_subtitle": "Pull local businesses, contacts & coordinates from OpenStreetMap",
        "form": GoogleMapsForm(),
        "recent": Search.objects.filter(source=Source.GOOGLE_MAPS)[:6],
    })


# ======================================================================= #
# Module 2 — LinkedIn Extraction (compliant intake)
# ======================================================================= #
@require_http_methods(["GET", "POST"])
def linkedin(request):
    if request.method == "POST":
        form = LinkedInForm(request.POST)
        if not form.is_valid():
            return render(request, "partials/results.html", {"error": "Invalid input."})
        url = form.cleaned_data.get("search_url", "")
        keyword = form.cleaned_data.get("keyword", "")
        pasted = form.cleaned_data.get("pasted", "")

        start = time.perf_counter()
        result = linkedin_ingest(search_url=url, pasted=pasted)
        duration = round(time.perf_counter() - start, 2)

        if result.error and not result.leads:
            return render(request, "partials/results.html", {"error": result.error})

        label = keyword or (result.parsed_filters.get("Keywords") if result.parsed_filters else "") or "LinkedIn import"
        search = Search.objects.create(
            source=Source.LINKEDIN, business_type=label, location=url[:255],
            total_results=len(result.leads), duration_seconds=duration,
            status=JobStatus.COMPLETED, extra=result.parsed_filters,
        )
        Business.objects.bulk_create([
            Business(
                search=search, source=Source.LINKEDIN, name=l.name,
                position=l.position, company=l.company, industry=l.industry,
                company_size=l.company_size, linkedin_url=l.linkedin_url,
            ) for l in result.leads
        ], batch_size=500)

        ctx = _results_context(request, search)
        ctx["duration"] = duration
        ctx["note"] = result.parsed_filters
        return render(request, "partials/results.html", ctx)

    return render(request, "modules/linkedin.html", {
        "active": "linkedin", "page_title": "LinkedIn Lead Generation",
        "page_subtitle": "Compliant intake of profiles, companies & Sales Navigator results",
        "form": LinkedInForm(),
        "recent": Search.objects.filter(source=Source.LINKEDIN)[:6],
    })


# ======================================================================= #
# Module 3 — Website Scraper
# ======================================================================= #
@require_http_methods(["GET", "POST"])
def scraper(request):
    if request.method == "POST":
        form = WebsiteScraperForm(request.POST)
        if not form.is_valid():
            return render(request, "partials/scrape_result.html",
                          {"error": "Please provide a valid URL."})
        url = form.cleaned_data["url"]
        crawl = form.cleaned_data.get("crawl") or False
        max_pages = form.cleaned_data.get("max_pages") or 5

        start = time.perf_counter()
        res = scrape_website(url, crawl=crawl, max_pages=max_pages)
        duration = round(time.perf_counter() - start, 2)

        if res.error:
            return render(request, "partials/scrape_result.html", {"error": res.error})

        total = len(res.emails) + len(res.phones)
        search = Search.objects.create(
            source=Source.WEBSITE, business_type="website", location=res.url[:255],
            total_results=total, duration_seconds=duration,
            status=JobStatus.COMPLETED,
            extra={"title": res.title, "pages": res.pages_crawled},
        )
        leads = []
        for em in res.emails:
            leads.append(Business(
                search=search, source=Source.WEBSITE,
                name=res.title or res.url, email=em, website=res.url,
                phone=res.phones[0] if res.phones else "",
                social_links=res.socials,
            ))
        if not leads:  # store one record so the scrape is logged
            leads.append(Business(
                search=search, source=Source.WEBSITE,
                name=res.title or res.url, website=res.url,
                phone=res.phones[0] if res.phones else "",
                social_links=res.socials,
            ))
        Business.objects.bulk_create(leads, batch_size=500)

        return render(request, "partials/scrape_result.html", {
            "res": res, "duration": duration, "search": search,
        })

    return render(request, "modules/scraper.html", {
        "active": "scraper", "page_title": "Website Scraper",
        "page_subtitle": "Crawl any domain & extract emails, phones, socials and metadata",
        "form": WebsiteScraperForm(),
        "recent": Search.objects.filter(source=Source.WEBSITE)[:6],
    })


# ======================================================================= #
# Module 4 — Email Finder & Verifier
# ======================================================================= #
@require_http_methods(["GET", "POST"])
def emailfinder(request):
    if request.method == "POST":
        form = EmailFinderForm(request.POST)
        if not form.is_valid():
            return render(request, "partials/email_result.html",
                          {"error": "Please provide a domain."})
        person = form.cleaned_data.get("person", "")
        domain = form.cleaned_data["domain"]
        company = form.cleaned_data.get("company", "")
        verify = form.cleaned_data.get("verify")

        start = time.perf_counter()
        res = find_emails(person, domain, company=company, verify=bool(verify))
        duration = round(time.perf_counter() - start, 2)

        if res.error:
            return render(request, "partials/email_result.html", {"error": res.error})

        search = Search.objects.create(
            source=Source.EMAIL_FINDER, business_type=person or domain,
            location=company or domain, total_results=len(res.candidates),
            duration_seconds=duration, status=JobStatus.COMPLETED,
        )
        Business.objects.bulk_create([
            Business(
                search=search, source=Source.EMAIL_FINDER,
                name=person or c.email, company=company, email=c.email,
                email_status=c.status, email_confidence=c.confidence,
                website=f"https://{domain}",
            ) for c in res.candidates
        ], batch_size=500)

        return render(request, "partials/email_result.html", {
            "res": res, "duration": duration, "search": search,
        })

    return render(request, "modules/emailfinder.html", {
        "active": "emailfinder", "page_title": "Email Finder & Verifier",
        "page_subtitle": "Discover & verify professional emails — free MX/SMTP checks",
        "form": EmailFinderForm(),
        "recent": Search.objects.filter(source=Source.EMAIL_FINDER)[:6],
    })


# ======================================================================= #
# Module 5 — AI Enrichment
# ======================================================================= #
@require_http_methods(["GET"])
def enrichment(request):
    candidates = (
        Business.objects.filter(source=Source.GOOGLE_MAPS)
        .exclude(website="")
        .select_related("search")[:50]
    )
    return render(request, "modules/enrichment.html", {
        "active": "enrichment", "page_title": "AI Lead Enrichment",
        "page_subtitle": "Augment leads with firmographics, summaries & AI lead scores",
        "candidates": candidates,
        "enriched_count": Enrichment.objects.count(),
    })


@require_http_methods(["POST"])
def enrich_lead(request, business_id: int):
    business = get_object_or_404(Business, pk=business_id)
    res = enrich_business(business)
    enrich, _ = Enrichment.objects.update_or_create(
        business=business,
        defaults={
            "description": res.description, "industry": res.industry,
            "employee_count": res.employee_count, "technologies": res.technologies,
            "social_links": res.social_links, "domain": res.domain,
            "business_category": res.business_category, "ai_summary": res.ai_summary,
            "ai_score": res.ai_score,
        },
    )
    if res.industry and not business.industry:
        business.industry = res.industry
        business.save(update_fields=["industry"])
    return render(request, "partials/enrichment_drawer.html",
                  {"b": business, "e": enrich})


# ======================================================================= #
# Exports (Excel / CSV)
# ======================================================================= #
@require_http_methods(["GET"])
def export(request, search_id: int):
    search = get_object_or_404(Search, pk=search_id)
    size_key = request.GET.get("size", "all")
    fmt = request.GET.get("fmt", "xlsx")
    limit = PAGE_SIZES.get(size_key, 100_000)
    businesses = list(search.businesses.all().order_by("name")[:limit])

    ExportLog.objects.create(
        search=search, source=search.source, fmt=fmt,
        business_type=search.business_type, location=search.location,
        record_count=len(businesses),
    )

    if fmt == "csv":
        data = build_csv(businesses, source=search.source)
        resp = HttpResponse(data, content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="leads.csv"'
        return resp

    workbook = build_workbook(businesses, source=search.source)
    resp = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = 'attachment; filename="leads.xlsx"'
    workbook.save(resp)
    return resp


# ======================================================================= #
# Settings / Billing / Packages
# ======================================================================= #
@require_http_methods(["GET"])
def settings_view(request):
    return render(request, "settings.html", {
        "active": "settings", "page_title": "Settings",
        "page_subtitle": "Profile, theme, API keys & export preferences",
    })


@require_http_methods(["GET"])
def billing(request):
    invoices = ExportLog.objects.all()[:10]
    return render(request, "billing.html", {
        "active": "billing", "page_title": "Billing",
        "page_subtitle": "Usage, invoices & payment method",
        "invoices": invoices,
    })


@require_http_methods(["GET"])
def packages(request):
    return render(request, "packages.html", {
        "active": "packages", "page_title": "Packages",
        "page_subtitle": "Choose the extraction capacity that fits your pipeline",
    })


# ======================================================================= #
# Health
# ======================================================================= #
def health(request):
    return JsonResponse({"status": "ok"})
