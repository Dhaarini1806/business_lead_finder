"""
OpenStreetMap service layer for the Business Lead Finder.

This module talks to two *free* OpenStreetMap services:

* **Nominatim** — converts a textual location ("Chromepet") into latitude /
  longitude coordinates (geocoding).
* **Overpass API** — returns businesses (nodes / ways / relations) of a given
  type around those coordinates.

Performance features
--------------------
* **Caching** — both geocoding and Overpass responses are cached
  (``django.core.cache``) so repeat searches return in well under five seconds.
* **Concurrency** — the two Overpass mirror endpoints are tried, and HTTP
  requests use a shared :class:`requests.Session` with a connection pool.
* **Defensive parsing** — missing names, phones, websites and addresses are
  handled gracefully so a lead is never dropped because a tag is absent.

The module is import-safe and contains no Django view logic.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Iterable

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("leads")


# --------------------------------------------------------------------------- #
# A lightweight, JSON-serialisable representation of one business lead.
# --------------------------------------------------------------------------- #
@dataclass
class BusinessRecord:
    osm_type: str = ""
    osm_id: int | None = None
    name: str = ""
    category: str = ""
    address: str = ""
    latitude: float | None = None
    longitude: float | None = None
    phone: str = ""
    website: str = ""

    def as_dict(self) -> dict:
        return {
            "osm_type": self.osm_type,
            "osm_id": self.osm_id,
            "name": self.name,
            "category": self.category,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "phone": self.phone,
            "website": self.website,
        }


@dataclass
class GeocodeResult:
    latitude: float
    longitude: float
    display_name: str = ""


@dataclass
class SearchOutcome:
    geocode: GeocodeResult | None = None
    businesses: list[BusinessRecord] = field(default_factory=list)
    error: str = ""


# --------------------------------------------------------------------------- #
# Category mapping: human business type -> OSM tag filters.
#
# Each entry produces one or more Overpass tag selectors. Anything not listed
# falls back to a fuzzy name + shop/amenity search so arbitrary business types
# still return useful results.
# --------------------------------------------------------------------------- #
CATEGORY_TAGS: dict[str, list[str]] = {
    "bakery": ['shop"="bakery'],
    "cake shop": ['shop"="bakery', 'shop"="confectionery', 'shop"="pastry'],
    "cake": ['shop"="bakery', 'shop"="confectionery'],
    "restaurant": ['amenity"="restaurant'],
    "cafe": ['amenity"="cafe'],
    "coffee": ['amenity"="cafe'],
    "gym": ['leisure"="fitness_centre', 'sport"="fitness'],
    "fitness": ['leisure"="fitness_centre'],
    "dental clinic": ['amenity"="dentist', 'healthcare"="dentist'],
    "dentist": ['amenity"="dentist'],
    "clinic": ['amenity"="clinic', 'healthcare"="clinic'],
    "hospital": ['amenity"="hospital'],
    "pharmacy": ['amenity"="pharmacy'],
    "hotel": ['tourism"="hotel'],
    "school": ['amenity"="school'],
    "college": ['amenity"="college'],
    "salon": ['shop"="hairdresser', 'shop"="beauty'],
    "beauty parlour": ['shop"="beauty', 'shop"="hairdresser'],
    "supermarket": ['shop"="supermarket'],
    "grocery": ['shop"="convenience', 'shop"="supermarket', 'shop"="grocery'],
    "clothing": ['shop"="clothes'],
    "electronics": ['shop"="electronics'],
    "mobile shop": ['shop"="mobile_phone'],
    "hardware": ['shop"="hardware', 'shop"="doityourself'],
    "bank": ['amenity"="bank'],
    "atm": ['amenity"="atm'],
    "petrol": ['amenity"="fuel'],
    "fuel": ['amenity"="fuel'],
    "car repair": ['shop"="car_repair'],
    "bar": ['amenity"="bar', 'amenity"="pub'],
    "pizza": ['amenity"="restaurant', 'cuisine"="pizza'],
}


def _category_filters(business_type: str) -> tuple[list[str], bool]:
    """
    Return Overpass tag selectors for the given business type.

    The boolean indicates whether this was a *fuzzy* (name-based) fallback,
    used to widen the search when the type is unknown.
    """
    key = business_type.strip().lower()
    if key in CATEGORY_TAGS:
        return CATEGORY_TAGS[key], False
    # Partial match (e.g. "cake shop near" -> "cake shop").
    for known, tags in CATEGORY_TAGS.items():
        if known in key or key in known:
            return tags, False
    # Fuzzy fallback: match on name tag + any shop/amenity.
    return [business_type.strip()], True


# --------------------------------------------------------------------------- #
# HTTP session (connection pooling for speed).
# --------------------------------------------------------------------------- #
_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10, pool_maxsize=10, max_retries=2
        )
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
        # Nominatim's usage policy rejects bare/automated User-Agents with a
        # 403. A descriptive, browser-like header set keeps requests valid.
        _session.headers.update(
            {
                "User-Agent": settings.OSM_USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.openstreetmap.org/",
            }
        )
    return _session


def _cache_key(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"blf:{prefix}:{digest}"


# --------------------------------------------------------------------------- #
# Geocoding (Nominatim).
# --------------------------------------------------------------------------- #
def geocode(location: str) -> GeocodeResult | None:
    """Convert a textual location into coordinates using Nominatim."""
    location = location.strip()
    if not location:
        return None

    key = _cache_key("geo", location.lower())
    cached = cache.get(key)
    if cached is not None:
        return GeocodeResult(**cached)

    params = {
        "q": location,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    try:
        resp = _get_session().get(
            settings.NOMINATIM_URL,
            params=params,
            timeout=settings.OSM_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Nominatim geocoding failed for %r: %s", location, exc)
        return None

    if not data:
        return None

    top = data[0]
    try:
        result = GeocodeResult(
            latitude=float(top["lat"]),
            longitude=float(top["lon"]),
            display_name=top.get("display_name", location),
        )
    except (KeyError, TypeError, ValueError):
        return None

    cache.set(
        key,
        {
            "latitude": result.latitude,
            "longitude": result.longitude,
            "display_name": result.display_name,
        },
        settings.OSM_CACHE_TIMEOUT,
    )
    return result


# --------------------------------------------------------------------------- #
# Overpass query construction & execution.
# --------------------------------------------------------------------------- #
def _build_overpass_query(
    filters: list[str], fuzzy: bool, lat: float, lon: float, radius: int
) -> str:
    """Build an Overpass QL query for businesses around a point."""
    around = f"(around:{radius},{lat},{lon})"
    parts: list[str] = []

    if fuzzy:
        # Name-based fuzzy search across shops/amenities/offices.
        name = filters[0].replace('"', "")
        for kind in ("node", "way", "relation"):
            parts.append(f'{kind}["name"~"{name}",i]{around};')
            parts.append(f'{kind}["shop"]["name"~"{name}",i]{around};')
    else:
        for sel in filters:
            # sel looks like  shop"="bakery   ->  ["shop"="bakery"]
            tag = f'["{sel}"]'
            for kind in ("node", "way", "relation"):
                parts.append(f"{kind}{tag}{around};")

    body = "\n  ".join(parts)
    return f"[out:json][timeout:25];\n(\n  {body}\n);\nout center tags;"


def _parse_element(element: dict, fallback_category: str) -> BusinessRecord | None:
    """Convert one Overpass element into a :class:`BusinessRecord`."""
    tags = element.get("tags", {}) or {}
    name = tags.get("name") or tags.get("brand") or ""
    if not name:
        # Skip unnamed elements — they are not useful leads.
        return None

    # Coordinates: nodes use lat/lon; ways/relations use "center".
    lat = element.get("lat")
    lon = element.get("lon")
    if lat is None and "center" in element:
        lat = element["center"].get("lat")
        lon = element["center"].get("lon")

    # Address assembly from individual addr:* tags.
    address_bits = [
        tags.get("addr:housenumber", ""),
        tags.get("addr:street", ""),
        tags.get("addr:suburb", ""),
        tags.get("addr:city", ""),
        tags.get("addr:postcode", ""),
        tags.get("addr:state", ""),
    ]
    address = ", ".join(bit for bit in address_bits if bit).strip(", ")

    # Category: prefer the most specific shop/amenity/etc. tag.
    category = (
        tags.get("shop")
        or tags.get("amenity")
        or tags.get("leisure")
        or tags.get("tourism")
        or tags.get("healthcare")
        or tags.get("office")
        or fallback_category
    )

    phone = (
        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("contact:mobile")
        or tags.get("mobile")
        or ""
    )
    website = (
        tags.get("website")
        or tags.get("contact:website")
        or tags.get("url")
        or ""
    )

    return BusinessRecord(
        osm_type=element.get("type", ""),
        osm_id=element.get("id"),
        name=name.strip()[:255],
        category=str(category).replace("_", " ").title()[:120],
        address=address[:500],
        latitude=float(lat) if lat is not None else None,
        longitude=float(lon) if lon is not None else None,
        phone=phone.strip()[:64],
        website=website.strip()[:400],
    )


def _run_overpass(query: str) -> list[dict]:
    """Execute an Overpass query, trying the primary then mirror endpoints."""
    endpoints = [
        settings.OVERPASS_URL,
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    session = _get_session()
    last_error: Exception | None = None
    for url in endpoints:
        try:
            resp = session.post(
                url, data={"data": query}, timeout=settings.OSM_HTTP_TIMEOUT
            )
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logger.warning("Overpass endpoint %s failed: %s", url, exc)
            continue
    if last_error:
        raise last_error
    return []


def _dedupe(records: Iterable[BusinessRecord]) -> list[BusinessRecord]:
    """Remove duplicate OSM elements while preserving order."""
    seen: set[tuple[str, int | None]] = set()
    unique: list[BusinessRecord] = []
    for rec in records:
        key = (rec.osm_type, rec.osm_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(rec)
    return unique


def fetch_businesses(
    business_type: str,
    location: str,
    radius: int | None = None,
) -> SearchOutcome:
    """
    High-level entry point: geocode the location then fetch businesses.

    Results (geocode + business list) are cached so repeated identical
    searches complete almost instantly.
    """
    radius = radius or settings.OSM_SEARCH_RADIUS
    outcome = SearchOutcome()

    geo = geocode(location)
    if geo is None:
        outcome.error = (
            f"Could not find the location '{location}'. "
            "Try a more specific or correctly spelled place name."
        )
        return outcome
    outcome.geocode = geo

    cache_key = _cache_key(
        "biz", f"{business_type.lower()}|{location.lower()}|{radius}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        outcome.businesses = [BusinessRecord(**row) for row in cached]
        return outcome

    filters, fuzzy = _category_filters(business_type)
    query = _build_overpass_query(
        filters, fuzzy, geo.latitude, geo.longitude, radius
    )

    try:
        elements = _run_overpass(query)
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        logger.error("Overpass query failed: %s", exc)
        outcome.error = (
            "The OpenStreetMap data service is temporarily busy. "
            "Please try again in a moment."
        )
        return outcome

    fallback_category = business_type.strip().title()
    records = [
        rec
        for el in elements
        if (rec := _parse_element(el, fallback_category)) is not None
    ]
    records = _dedupe(records)
    records.sort(key=lambda r: r.name.lower())

    outcome.businesses = records
    cache.set(
        cache_key,
        [r.as_dict() for r in records],
        settings.OSM_CACHE_TIMEOUT,
    )
    return outcome
