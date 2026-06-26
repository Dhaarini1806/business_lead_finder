"""Template context processors for Forge OS branding and navigation."""

from django.conf import settings


def branding(request):
    return {
        "BRAND_NAME": getattr(settings, "BRAND_NAME", "FORGE.OS"),
        "BRAND_WORKSPACE": getattr(settings, "BRAND_WORKSPACE", "Lead Intelligence"),
        "BRAND_VERSION": getattr(settings, "BRAND_VERSION", "Operator v2.4"),
    }
