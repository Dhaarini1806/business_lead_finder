"""
Views for the Business Lead Finder.

Endpoints
---------
* ``home``            — search page (GET) and HTMX search handler (POST).
* ``results_partial`` — HTMX partial for pagination / sorting / in-table search.
* ``export_excel``    — download ``business_leads.xlsx`` for a search.
* ``history``         — recent searches list.
* ``dashboard``       — aggregate statistics.

The search itself is delegated to :mod:`leads.services.osm`. Results are stored
with a single ``bulk_create`` for speed and to satisfy the "bulk inserts"
requirement.
"""

from __future__ import annotations

import time

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import SearchForm
from .models import Business, ExportLog, Search
from .services.exporter import build_workbook
from .services.osm import fetch_businesses

# Allowed sort columns -> ORM field (whitelist guards against injection).
SORT_FIELDS = {
    "name": "name",
    "category": "category",
    "address": "address",
    "phone": "phone",
}

# Allowed page sizes for the lead-count selector.
PAGE_SIZES = {"50": 50, "100": 100, "200": 200, "all": 10_000}


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


@require_http_methods(["GET", "POST"])
def home(request):
    """Render the search page and handle search submissions (HTMX-aware)."""
    if request.method == "POST":
        form = SearchForm(request.POST)
        if not form.is_valid():
            context = {"form": form, "error": "Please fill in both fields."}
            if _is_htmx(request):
                return render(request, "partials/results.html", context)
            return render(request, "home.html", context)

        business_type = form.cleaned_data["business_type"]
        location = form.cleaned_data["location"]

        start = time.perf_counter()
        outcome = fetch_businesses(business_type, location)
        duration = round(time.perf_counter() - start, 2)

        if outcome.error:
            context = {"form": SearchForm(), "error": outcome.error}
            return render(request, "partials/results.html", context)

        # Persist the search (history) and its businesses (bulk insert).
        search = Search.objects.create(
            business_type=business_type,
            location=location,
            latitude=outcome.geocode.latitude if outcome.geocode else None,
            longitude=outcome.geocode.longitude if outcome.geocode else None,
            display_name=outcome.geocode.display_name if outcome.geocode else "",
            total_results=len(outcome.businesses),
            duration_seconds=duration,
        )

        Business.objects.bulk_create(
            [
                Business(
                    search=search,
                    osm_type=rec.osm_type,
                    osm_id=rec.osm_id,
                    name=rec.name,
                    category=rec.category,
                    address=rec.address,
                    latitude=rec.latitude,
                    longitude=rec.longitude,
                    phone=rec.phone,
                    website=rec.website,
                )
                for rec in outcome.businesses
            ],
            batch_size=500,
            ignore_conflicts=True,
        )

        context = _results_context(request, search)
        context["duration"] = duration
        return render(request, "partials/results.html", context)

    # GET: render the full search page.
    return render(request, "home.html", {"form": SearchForm()})


def _results_context(request, search: Search) -> dict:
    """Build the context for the results partial (sorting + pagination)."""
    sort = request.GET.get("sort", "name")
    direction = request.GET.get("dir", "asc")
    query = request.GET.get("q", "").strip()
    size_key = request.GET.get("size", "50")

    field = SORT_FIELDS.get(sort, "name")
    order = field if direction == "asc" else f"-{field}"

    qs = search.businesses.all()
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(category__icontains=query)
            | Q(address__icontains=query)
            | Q(phone__icontains=query)
        )
    qs = qs.order_by(order)

    per_page = PAGE_SIZES.get(size_key, 50)
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return {
        "search": search,
        "page_obj": page_obj,
        "total": qs.count(),
        "sort": sort,
        "dir": direction,
        "q": query,
        "size": size_key,
        "page_sizes": ["50", "100", "200", "all"],
    }


@require_http_methods(["GET"])
def results_partial(request, search_id: int):
    """HTMX endpoint for re-rendering results on sort / page / filter change."""
    search = get_object_or_404(Search, pk=search_id)
    return render(request, "partials/results.html", _results_context(request, search))


@require_http_methods(["GET"])
def export_excel(request, search_id: int):
    """Generate and download an Excel workbook of leads for a search."""
    search = get_object_or_404(Search, pk=search_id)

    size_key = request.GET.get("size", "all")
    limit = PAGE_SIZES.get(size_key, 10_000)
    businesses = list(search.businesses.all().order_by("name")[:limit])

    workbook = build_workbook(businesses)

    ExportLog.objects.create(
        search=search,
        business_type=search.business_type,
        location=search.location,
        record_count=len(businesses),
    )

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    )
    response["Content-Disposition"] = 'attachment; filename="business_leads.xlsx"'
    workbook.save(response)
    return response


@require_http_methods(["GET"])
def history(request):
    """List recent searches."""
    searches = Search.objects.all()[:50]
    return render(request, "history.html", {"searches": searches})


@require_http_methods(["GET"])
def dashboard(request):
    """Aggregate statistics for the dashboard."""
    today = timezone.localdate()
    stats = {
        "total_searches": Search.objects.count(),
        "total_businesses": Business.objects.count(),
        "total_exports": ExportLog.objects.count(),
        "today_searches": Search.objects.filter(created_at__date=today).count(),
        "today_exports": ExportLog.objects.filter(created_at__date=today).count(),
        "exported_records": ExportLog.objects.aggregate(n=Sum("record_count"))["n"]
        or 0,
    }
    top_types = (
        Search.objects.values("business_type")
        .annotate(count=Count("id"), leads=Sum("total_results"))
        .order_by("-count")[:8]
    )
    recent = Search.objects.all()[:10]
    return render(
        request,
        "dashboard.html",
        {"stats": stats, "top_types": top_types, "recent": recent},
    )
