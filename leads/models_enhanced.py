"""
Enhanced Database models for Forge OS — Lead Intelligence platform.

New features:
* :class:`LeadStatus`     — Lead status tracking (New, Contacted, Qualified, Converted)
* :class:`EmailTemplate`  — Pre-built email templates for outreach
* :class:`LeadActivity`   — Activity timeline per lead
* :class:`WebsiteAnalysis` — Website health check results
"""

from urllib.parse import quote_plus
from django.db import models
from django.utils import timezone


class LeadStatusChoices(models.TextChoices):
    """Lead status for CRM tracking."""
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUALIFIED = "qualified", "Qualified"
    CONVERTED = "converted", "Converted"
    REJECTED = "rejected", "Rejected"


class EmailTemplateType(models.TextChoices):
    """Pre-built email template types."""
    COLD_OUTREACH = "cold_outreach", "Cold Outreach - Website Services"
    IT_SERVICES = "it_services", "IT Services Pitch"
    WEBSITE_AUDIT = "website_audit", "Website Audit & SEO Optimization"
    FOLLOW_UP = "follow_up", "Follow-up Email"
    CUSTOM = "custom", "Custom Template"


class EmailTemplate(models.Model):
    """Pre-built email templates for outreach campaigns."""
    
    template_type = models.CharField(
        max_length=20,
        choices=EmailTemplateType.choices,
        unique=True,
        db_index=True
    )
    subject = models.CharField(max_length=200)
    body = models.TextField()
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["template_type"]
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"
    
    def __str__(self):
        return f"{self.get_template_type_display()}"


class LeadActivity(models.Model):
    """Activity timeline for each lead (emails sent, calls, notes, etc.)."""
    
    ACTIVITY_TYPES = [
        ("email_sent", "Email Sent"),
        ("call_made", "Call Made"),
        ("note_added", "Note Added"),
        ("status_changed", "Status Changed"),
        ("website_analyzed", "Website Analyzed"),
        ("enriched", "Lead Enriched"),
    ]
    
    business = models.ForeignKey(
        "Business",
        on_delete=models.CASCADE,
        related_name="activities"
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # Store template used, etc.
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lead Activity"
        verbose_name_plural = "Lead Activities"
        indexes = [
            models.Index(fields=["business", "-created_at"]),
            models.Index(fields=["activity_type", "-created_at"]),
        ]
    
    def __str__(self):
        return f"{self.business.name} - {self.get_activity_type_display()}"


class WebsiteAnalysis(models.Model):
    """Website health check results."""
    
    business = models.OneToOneField(
        "Business",
        on_delete=models.CASCADE,
        related_name="website_analysis",
        null=True,
        blank=True
    )
    url = models.URLField(max_length=400, db_index=True)
    
    # SSL/HTTPS check
    has_ssl = models.BooleanField(default=False)
    ssl_valid = models.BooleanField(default=False)
    ssl_expires_at = models.DateTimeField(null=True, blank=True)
    
    # SEO metrics
    seo_score = models.PositiveIntegerField(default=0)  # 0-100
    has_meta_description = models.BooleanField(default=False)
    has_h1_tag = models.BooleanField(default=False)
    has_sitemap = models.BooleanField(default=False)
    
    # Performance
    page_load_time_ms = models.PositiveIntegerField(null=True, blank=True)
    is_mobile_responsive = models.BooleanField(default=False)
    
    # Recommendations
    recommendations = models.JSONField(default=list, blank=True)
    
    # Status
    last_checked_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=[
            ("healthy", "Healthy"),
            ("warning", "Warning"),
            ("critical", "Critical"),
            ("error", "Error"),
        ],
        default="warning"
    )
    
    class Meta:
        verbose_name = "Website Analysis"
        verbose_name_plural = "Website Analyses"
        indexes = [
            models.Index(fields=["url"]),
            models.Index(fields=["-last_checked_at"]),
        ]
    
    def __str__(self):
        return f"Analysis for {self.url}"


# ============================================================================
# ENHANCED Business Model (add to existing)
# ============================================================================
# Add these fields to the existing Business model:
#
#   # CRM Fields
#   status = models.CharField(
#       max_length=20,
#       choices=LeadStatusChoices.choices,
#       default=LeadStatusChoices.NEW,
#       db_index=True
#   )
#   notes = models.TextField(blank=True)
#   last_contacted_at = models.DateTimeField(null=True, blank=True)
#   
#   # Add to Meta.indexes:
#   models.Index(fields=["status", "-created_at"]),
#   models.Index(fields=["-last_contacted_at"]),
