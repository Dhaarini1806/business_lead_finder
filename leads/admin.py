"""
Django admin configuration for the Business Lead Finder.

Admins can:
    * View and search searches and businesses.
    * Delete duplicate business leads (custom action).
    * Export selected business records to Excel (custom action).
"""

from django.contrib import admin
from django.http import HttpResponse

from .models import Business, ExportLog, Search
from .services.exporter import build_workbook


@admin.register(Search)
class SearchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business_type",
        "location",
        "total_results",
        "duration_seconds",
        "created_at",
    )
    list_filter = ("business_type", "created_at")
    search_fields = ("business_type", "location", "display_name")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "address",
        "phone",
        "website",
        "search",
    )
    list_filter = ("category", "search__business_type")
    search_fields = ("name", "category", "address", "phone", "website")
    list_select_related = ("search",)
    actions = ("delete_duplicates", "export_to_excel")

    @admin.action(description="Delete duplicate leads (same name + address)")
    def delete_duplicates(self, request, queryset):
        """Remove duplicate businesses keeping the lowest-id record."""
        seen = set()
        to_delete = []
        for biz in Business.objects.all().order_by("id"):
            key = (biz.name.strip().lower(), biz.address.strip().lower())
            if key in seen:
                to_delete.append(biz.id)
            else:
                seen.add(key)
        deleted, _ = Business.objects.filter(id__in=to_delete).delete()
        self.message_user(request, f"Deleted {deleted} duplicate lead(s).")

    @admin.action(description="Export selected leads to Excel")
    def export_to_excel(self, request, queryset):
        workbook = build_workbook(queryset)
        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )
        response["Content-Disposition"] = (
            'attachment; filename="business_leads.xlsx"'
        )
        workbook.save(response)
        return response


@admin.register(ExportLog)
class ExportLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business_type",
        "location",
        "record_count",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("business_type", "location")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


admin.site.site_header = "Business Lead Finder Admin"
admin.site.site_title = "Business Lead Finder"
admin.site.index_title = "Lead Management"
