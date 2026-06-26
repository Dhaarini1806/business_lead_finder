from django.urls import path

from . import views

app_name = "leads"

urlpatterns = [
    # Public landing
    path("", views.landing, name="landing"),

    # Console
    path("app/", views.dashboard, name="dashboard"),

    # Modules
    path("app/gmaps/", views.gmaps, name="gmaps"),
    path("app/linkedin/", views.linkedin, name="linkedin"),
    path("app/scraper/", views.scraper, name="scraper"),
    path("app/email-finder/", views.emailfinder, name="emailfinder"),
    path("app/enrichment/", views.enrichment, name="enrichment"),
    path("app/enrichment/<int:business_id>/run/", views.enrich_lead, name="enrich_lead"),

    # Account
    path("app/settings/", views.settings_view, name="settings"),
    path("app/billing/", views.billing, name="billing"),
    path("app/packages/", views.packages, name="packages"),

    # Shared
    path("app/results/<int:search_id>/", views.results_partial, name="results"),
    path("app/export/<int:search_id>/", views.export, name="export"),

    path("health/", views.health, name="health"),
]
