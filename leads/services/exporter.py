"""
Excel export utilities for the Business Lead Finder.

Generates a polished ``business_leads.xlsx`` workbook using OpenPyXL with:
    * A styled header row.
    * Auto-sized columns.
    * Clickable OpenStreetMap / Google Maps links.

The exporter accepts either a Django queryset of :class:`leads.models.Business`
or any iterable of objects exposing the same attributes, so it can be reused
from views and the admin.
"""

from __future__ import annotations

from typing import Iterable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADERS = [
    "Name",
    "Category",
    "Address",
    "Phone",
    "Website",
    "Latitude",
    "Longitude",
    "Maps Link",
]


def build_workbook(businesses: Iterable) -> Workbook:
    """Build and return an OpenPyXL workbook for the given businesses."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Business Leads"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill("solid", fgColor="2563EB")
    center = Alignment(horizontal="center", vertical="center")

    sheet.append(HEADERS)
    for col_idx, _ in enumerate(HEADERS, start=1):
        cell = sheet.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center

    for biz in businesses:
        maps_link = getattr(biz, "google_maps_link", "") or ""
        sheet.append(
            [
                getattr(biz, "name", "") or "",
                getattr(biz, "category", "") or "",
                getattr(biz, "address", "") or "",
                getattr(biz, "phone", "") or "",
                getattr(biz, "website", "") or "",
                getattr(biz, "latitude", "") if getattr(biz, "latitude", None) is not None else "",
                getattr(biz, "longitude", "") if getattr(biz, "longitude", None) is not None else "",
                maps_link,
            ]
        )

    # Make Website and Maps Link columns clickable hyperlinks.
    for row in range(2, sheet.max_row + 1):
        website_cell = sheet.cell(row=row, column=5)
        if website_cell.value:
            website_cell.hyperlink = website_cell.value
            website_cell.font = Font(color="2563EB", underline="single")
        maps_cell = sheet.cell(row=row, column=8)
        if maps_cell.value:
            maps_cell.hyperlink = maps_cell.value
            maps_cell.font = Font(color="2563EB", underline="single")

    # Auto-size columns (capped) for readability.
    widths = {1: 32, 2: 18, 3: 48, 4: 18, 5: 34, 6: 12, 7: 12, 8: 40}
    for idx, width in widths.items():
        sheet.column_dimensions[get_column_letter(idx)].width = width

    sheet.freeze_panes = "A2"
    return workbook
