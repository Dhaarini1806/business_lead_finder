"""
Database models for the Business Lead Finder.

Three models power the application:

* :class:`Search`     — one row per search the user performs (history).
* :class:`Business`   — one row per business found (the leads themselves).
* :class:`ExportLog`  — one row per Excel export (used by the dashboard).

Indexes and ``unique_together`` constraints are added to keep large
searches fast and to avoid duplicate leads.
"""

from django.db import models
from django.utils import timezone


class Search(models.Model):
    """A single business search performed by a user (search history)."""

    business_type = models.CharField(max_length=120, db_index=True)
    location = models.CharField(max_length=160, db_index=True)

    # Geocoded coordinates of the searched location (Nominatim result).
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    display_name = models.CharField(max_length=255, blank=True)

    total_results = models.PositiveIntegerField(default=0)
    duration_seconds = models.FloatField(default=0.0)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Search"
        verbose_name_plural = "Searches"
        indexes = [
            models.Index(fields=["business_type", "location"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.business_type} in {self.location} ({self.total_results})"

    @property
    def query_label(self) -> str:
        return f"{self.business_type} {self.location}".strip()


class Business(models.Model):
    """A business lead retrieved from OpenStreetMap via the Overpass API."""

    search = models.ForeignKey(
        Search, on_delete=models.CASCADE, related_name="businesses"
    )

    # OSM element identity (type + id) — used to deduplicate.
    osm_type = models.CharField(max_length=10, blank=True)  # node / way / relation
    osm_id = models.BigIntegerField(null=True, blank=True, db_index=True)

    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=120, blank=True, db_index=True)
    address = models.CharField(max_length=500, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    phone = models.CharField(max_length=64, blank=True)
    website = models.URLField(max_length=400, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]
        verbose_name = "Business"
        verbose_name_plural = "Businesses"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["search", "name"]),
        ]
        # Prevent the same OSM element appearing twice within one search.
        constraints = [
            models.UniqueConstraint(
                fields=["search", "osm_type", "osm_id"],
                name="unique_business_per_search",
            )
        ]

    def __str__(self) -> str:
        return self.name or "Unnamed business"

    # ----- Convenience link helpers used by templates & export ----- #
    @property
    def osm_link(self) -> str:
        if self.osm_type and self.osm_id:
            return f"https://www.openstreetmap.org/{self.osm_type}/{self.osm_id}"
        if self.latitude is not None and self.longitude is not None:
            return (
                f"https://www.openstreetmap.org/?mlat={self.latitude}"
                f"&mlon={self.longitude}#map=18/{self.latitude}/{self.longitude}"
            )
        return ""

    @property
    def google_maps_link(self) -> str:
        if self.latitude is not None and self.longitude is not None:
            return (
                "https://www.google.com/maps/search/?api=1&query="
                f"{self.latitude},{self.longitude}"
            )
        if self.name:
            from urllib.parse import quote_plus

            return (
                "https://www.google.com/maps/search/?api=1&query="
                + quote_plus(f"{self.name} {self.address}".strip())
            )
        return ""


class ExportLog(models.Model):
    """Records each Excel export so the dashboard can report totals."""

    search = models.ForeignKey(
        Search,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exports",
    )
    business_type = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=160, blank=True)
    record_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Export Log"
        verbose_name_plural = "Export Logs"

    def __str__(self) -> str:
        return f"Export of {self.record_count} leads at {self.created_at:%Y-%m-%d %H:%M}"
