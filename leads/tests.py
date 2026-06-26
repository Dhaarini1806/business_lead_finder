"""Tests for Forge OS — Lead Intelligence."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse

from leads.models import Business, Enrichment, ExportLog, Search, Source
from leads.services import osm
from leads.services.emailfinder import _name_parts, _patterns
from leads.services.exporter import build_csv, build_workbook
from leads.services.linkedin import parse_pasted_leads, parse_search_url
from leads.services.scraper import EMAIL_RE


class ModelTests(TestCase):
    def test_business_links(self):
        s = Search.objects.create(business_type="Bakery", location="Chromepet")
        b = Business.objects.create(
            search=s, osm_type="node", osm_id=123,
            name="Sweet Bakery", latitude=12.95, longitude=80.14,
        )
        self.assertIn("node/123", b.osm_link)
        self.assertIn("google.com/maps", b.google_maps_link)

    def test_job_id_and_label(self):
        s = Search.objects.create(business_type="Gym", location="Tambaram")
        self.assertTrue(s.job_id.startswith("JOB-"))
        self.assertIn("Gym", s.query_label)


class OverpassQueryTests(TestCase):
    def test_known_category_filters(self):
        filters, fuzzy = osm._category_filters("Bakery")
        self.assertFalse(fuzzy)
        self.assertIn('shop"="bakery', filters)

    def test_unknown_category_is_fuzzy(self):
        _, fuzzy = osm._category_filters("Spaceship Dealership")
        self.assertTrue(fuzzy)

    def test_query_builds(self):
        q = osm._build_overpass_query(['shop"="bakery'], False, 12.9, 80.1, 5000)
        self.assertIn("out:json", q)
        self.assertIn("around:5000", q)


class ExporterTests(TestCase):
    def test_gmaps_headers(self):
        wb = build_workbook([], source="google_maps")
        ws = wb.active
        self.assertEqual(ws.cell(row=1, column=1).value, "Name")

    def test_csv_bytes(self):
        data = build_csv([], source="google_maps")
        self.assertIn(b"Name", data)


class ServiceUnitTests(TestCase):
    def test_email_name_parts(self):
        self.assertEqual(_name_parts("Jane Doe"), ("jane", "doe"))

    def test_email_patterns(self):
        pats = _patterns("jane", "doe", "acme.com")
        emails = [e for e, _ in pats]
        self.assertIn("jane.doe@acme.com", emails)

    def test_linkedin_parse_paste(self):
        leads = parse_pasted_leads("Jane Doe, VP Sales, Acme, SaaS, 200, https://linkedin.com/in/jane")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0].company, "Acme")

    def test_linkedin_parse_url(self):
        filters = parse_search_url("https://www.linkedin.com/search/results/people/?keywords=cto")
        self.assertEqual(filters.get("Keywords"), "cto")

    def test_email_regex(self):
        self.assertTrue(EMAIL_RE.search("contact us at hi@test.com please"))


class ViewTests(TestCase):
    def test_landing(self):
        resp = self.client.get(reverse("leads:landing"))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard(self):
        resp = self.client.get(reverse("leads:dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_module_pages(self):
        for name in ("gmaps", "linkedin", "scraper", "emailfinder",
                     "enrichment", "settings", "billing", "packages"):
            resp = self.client.get(reverse(f"leads:{name}"))
            self.assertEqual(resp.status_code, 200, name)

    @mock.patch("leads.views.fetch_businesses")
    def test_gmaps_post_creates_records(self, mock_fetch):
        mock_fetch.return_value = osm.SearchOutcome(
            geocode=osm.GeocodeResult(12.95, 80.14, "Chromepet, Chennai"),
            businesses=[
                osm.BusinessRecord(osm_type="node", osm_id=1, name="ABC Bakery",
                                   category="Bakery", latitude=12.95, longitude=80.14),
                osm.BusinessRecord(osm_type="node", osm_id=2, name="XYZ Cakes",
                                   category="Confectionery"),
            ],
        )
        resp = self.client.post(
            reverse("leads:gmaps"),
            {"business_type": "Bakery", "location": "Chromepet"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Search.objects.count(), 1)
        self.assertEqual(Business.objects.count(), 2)
        self.assertContains(resp, "ABC Bakery")

    def test_linkedin_post(self):
        resp = self.client.post(
            reverse("leads:linkedin"),
            {"pasted": "Jane Doe, VP Sales, Acme, SaaS, 200, https://linkedin.com/in/jane"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Business.objects.filter(source=Source.LINKEDIN).count(), 1)

    def test_export_creates_log(self):
        s = Search.objects.create(source=Source.GOOGLE_MAPS, business_type="Gym",
                                  location="Tambaram")
        Business.objects.create(search=s, osm_type="node", osm_id=9, name="Fit Gym")
        resp = self.client.get(reverse("leads:export", args=[s.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ExportLog.objects.count(), 1)

    def test_export_csv(self):
        s = Search.objects.create(business_type="Gym", location="Tambaram")
        Business.objects.create(search=s, name="Fit Gym")
        resp = self.client.get(reverse("leads:export", args=[s.id]) + "?fmt=csv")
        self.assertEqual(resp["Content-Type"], "text/csv")
