"""Tests for the Business Lead Finder."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse

from leads.models import Business, ExportLog, Search
from leads.services import osm
from leads.services.exporter import build_workbook


class ModelTests(TestCase):
    def test_business_links(self):
        s = Search.objects.create(business_type="Bakery", location="Chromepet")
        b = Business.objects.create(
            search=s, osm_type="node", osm_id=123,
            name="Sweet Bakery", latitude=12.95, longitude=80.14,
        )
        self.assertIn("node/123", b.osm_link)
        self.assertIn("google.com/maps", b.google_maps_link)


class OverpassQueryTests(TestCase):
    def test_known_category_filters(self):
        filters, fuzzy = osm._category_filters("Bakery")
        self.assertFalse(fuzzy)
        self.assertIn('shop"="bakery', filters)

    def test_unknown_category_is_fuzzy(self):
        filters, fuzzy = osm._category_filters("Spaceship Dealership")
        self.assertTrue(fuzzy)

    def test_query_builds(self):
        q = osm._build_overpass_query(['shop"="bakery'], False, 12.9, 80.1, 5000)
        self.assertIn("out:json", q)
        self.assertIn("around:5000", q)


class ExporterTests(TestCase):
    def test_workbook_headers(self):
        wb = build_workbook([])
        ws = wb.active
        self.assertEqual(ws.cell(row=1, column=1).value, "Name")
        self.assertEqual(ws.cell(row=1, column=8).value, "Maps Link")


class ViewTests(TestCase):
    def test_home_get(self):
        resp = self.client.get(reverse("leads:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Business Lead Finder")

    def test_dashboard(self):
        resp = self.client.get(reverse("leads:dashboard"))
        self.assertEqual(resp.status_code, 200)

    @mock.patch("leads.views.fetch_businesses")
    def test_search_post_creates_records(self, mock_fetch):
        mock_fetch.return_value = osm.SearchOutcome(
            geocode=osm.GeocodeResult(12.95, 80.14, "Chromepet, Chennai"),
            businesses=[
                osm.BusinessRecord(
                    osm_type="node", osm_id=1, name="ABC Bakery",
                    category="Bakery", latitude=12.95, longitude=80.14,
                ),
                osm.BusinessRecord(
                    osm_type="node", osm_id=2, name="XYZ Cakes",
                    category="Confectionery",
                ),
            ],
        )
        resp = self.client.post(
            reverse("leads:home"),
            {"business_type": "Bakery", "location": "Chromepet"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Search.objects.count(), 1)
        self.assertEqual(Business.objects.count(), 2)
        self.assertContains(resp, "ABC Bakery")

    @mock.patch("leads.views.fetch_businesses")
    def test_export_creates_log(self, mock_fetch):
        s = Search.objects.create(business_type="Gym", location="Tambaram")
        Business.objects.create(search=s, osm_type="node", osm_id=9, name="Fit Gym")
        resp = self.client.get(reverse("leads:export", args=[s.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(ExportLog.objects.count(), 1)
