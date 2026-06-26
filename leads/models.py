"""
Database models for Forge OS — Lead Intelligence platform.

The schema powers five extraction modules plus history, exports and
AI enrichment:

* :class:`Search`        — one row per extraction job (history / recent).
* :class:`Business`      — a lead row (Google Maps, Website, LinkedIn, etc.).
* :class:`Enrichment`    — AI / firmographic enrichment attached to a lead.
* :class:`ExportLog`     — one row per export (Excel / CSV) for the dashboard.

Indexes and uniqueness constraints keep large extractions fast and
de-duplicated.
"""

from urllib.parse import quote_plus

from django.db import models
from django.utils import timezone


class Source(models.TextChoices):
    """The five extraction sources (modules)."""

    GOOGLE_MAPS = "google_maps", "Google Maps"
    LINKEDIN = "linkedin", "LinkedIn"
    WEBSITE = "website", "Website Scraper"
    EMAIL_FINDER = "email_finder", "Email Finder"
    ENRICHMENT = "enrichment", "AI Enrichment"


class JobStatus(models.TextChoices):
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Search(models.Model):
    """A single extraction job performed by a user (history / recent)."""

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.GOOGLE_MAPS,
        db_index=True,
    )

    # Human-readable query parts. Re-used across modules:
    #   Google Maps -> business_type=keyword, location=location
    #   LinkedIn    -> business_type=role/keyword, location=search url/location
    #   Website     -> business_type="website", location=domain
    #   Email       -> business_type=person/domain, location=company
    business_type = models.CharField(max_length=160, db_index=True)
    location = models.CharField(max_length=255, db_index=True, blank=True)

    # Optional parameters captured from the wizard.
    radius_km = models.FloatField(null=True, blank=True)
    max_results = models.PositiveIntegerField(null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    # Geocoded coordinates of the searched location (Nominatim result).
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    display_name = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=12,
        choices=JobStatus.choices,
        default=JobStatus.COMPLETED,
        db_index=True,
    )
    total_results = models.PositiveIntegerField(default=0)
    duration_seconds = models.FloatField(default=0.0)
    error = models.CharField(max_length=400, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Search"
        verbose_name_plural = "Searches"
        indexes = [
            models.Index(fields=["source", "-created_at"]),
            models.Index(fields=["business_type", "location"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.get_source_display()}] {self.business_type} ({self.total_results})"

    @property
    def query_label(self) -> str:
        parts = [p for p in (self.business_type, self.location) if p]
        return " · ".join(parts)

    @property
    def job_id(self) -> str:
        return f"JOB-{self.pk:05d}" if self.pk else "JOB-—"


class Business(models.Model):
    """A lead row. Fields are shared across all extraction sources;
    only the relevant ones are populated per source."""

    search = models.ForeignKey(
        Search, on_delete=models.CASCADE, related_name="businesses"
    )
    source = models.CharField(
        max_length=20, choices=Source.choices,
        default=Source.GOOGLE_MAPS, db_index=True,
    )

    # OSM element identity (type + id) — used to deduplicate map results.
    osm_type = models.CharField(max_length=10, blank=True)
    osm_id = models.BigIntegerField(null=True, blank=True, db_index=True)

    # ----- Core / Google Maps fields ----- #
    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=160, blank=True, db_index=True)
    address = models.CharField(max_length=500, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    website = models.URLField(max_length=400, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    rating = models.FloatField(null=True, blank=True)
    reviews = models.PositiveIntegerField(null=True, blank=True)

    # ----- LinkedIn / people fields ----- #
    position = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    industry = models.CharField(max_length=160, blank=True)
    company_size = models.CharField(max_length=80, blank=True)
    linkedin_url = models.URLField(max_length=400, blank=True)

    # ----- Email finder verification ----- #
    email_status = models.CharField(max_length=20, blank=True)  # verified/risky/invalid
    email_confidence = models.PositiveIntegerField(null=True, blank=True)

    # ----- Misc / scraper ----- #
    social_links = models.JSONField(default=dict, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["source"]),
            models.Index(fields=["search", "name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["search", "osm_type", "osm_id"],
                name="unique_business_per_search",
                condition=models.Q(osm_id__isnull=False),
            )
        ]

    def __str__(self) -> str:
        return self.name or "Unnamed lead"

    # ----- Convenience link helpers ----- #
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
            return (
                "https://www.google.com/maps/search/?api=1&query="
                + quote_plus(f"{self.name} {self.address}".strip())
            )
        return ""

    @property
    def coordinates(self) -> str:
        if self.latitude is not None and self.longitude is not None:
            return f"{self.latitude:.5f}, {self.longitude:.5f}"
        return ""

    @property
    def has_enrichment(self) -> bool:
        return hasattr(self, "enrichment")


class Enrichment(models.Model):
    """AI / firmographic enrichment for a single lead."""

    business = models.OneToOneField(
        Business, on_delete=models.CASCADE, related_name="enrichment"
    )
    description = models.TextField(blank=True)
    industry = models.CharField(max_length=160, blank=True)
    employee_count = models.CharField(max_length=80, blank=True)
    technologies = models.JSONField(default=list, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    domain = models.CharField(max_length=200, blank=True)
    business_category = models.CharField(max_length=160, blank=True)
    ai_summary = models.TextField(blank=True)
    ai_score = models.PositiveIntegerField(null=True, blank=True)  # 0-100
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Enrichment"
        verbose_name_plural = "Enrichments"

    def __str__(self) -> str:
        return f"Enrichment for {self.business_id}"


class ExportLog(models.Model):
    """Records each export (Excel / CSV) so the dashboard can report totals."""

    FORMAT_CHOICES = [("xlsx", "Excel"), ("csv", "CSV")]

    search = models.ForeignKey(
        Search, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="exports",
    )
    source = models.CharField(max_length=20, blank=True)
    fmt = models.CharField(max_length=8, choices=FORMAT_CHOICES, default="xlsx")
    business_type = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=255, blank=True)
    record_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Export Log"
        verbose_name_plural = "Export Logs"

    def __str__(self) -> str:
        return f"{self.fmt.upper()} export of {self.record_count} leads"
